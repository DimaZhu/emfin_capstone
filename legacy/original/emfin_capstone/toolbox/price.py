"""Historical price-fetching seam + concrete fetchers for the enriching layer.

``PriceFetcher`` Protocol — narrow, symbol-only contract.
Each implementer returns a ``PriceHistory`` (symbol identity + a list
of typed ``PriceObservation`` records), or ``None`` when no data is
available.  Fetchers never touch routing — they only know how to fetch
one symbol from one upstream (Yahoo / Binance / Stooq / a splice).

Concrete fetchers: ``YahooPriceFetcher`` (US/HK/SHE equities via yfinance),
``BinancePriceFetcher`` (crypto via REST), ``StooqPriceFetcher`` (HK
fallback), ``SplicedPriceFetcher`` (Yahoo post-inception + Stooq
level-scaled pre-Yahoo for HK).

``PriceFetcherFactory`` routes an ``Asset`` to the correct fetcher by
exchange.  It wires the default set internally — Yahoo for US/HK/SHE,
Binance for crypto, HK splice (Yahoo + Stooq).

Live-price (regular-market quote) functionality from the previous
``PriceProvider`` Protocol has been removed — ``Portfolio`` no longer
carries last prices and no caller in the enriching path needs them.  If a
"latest price" need re-emerges, derive it as the last row of the history
fetch rather than re-introducing a parallel quote API.
"""

from __future__ import annotations

import io
import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

import pandas as pd
import yfinance as yf

from emfin_capstone import config
from emfin_capstone.toolbox.cache import (
    BINANCE_PROVIDER_KEY,
    STOOQ_PROVIDER_KEY,
    YAHOO_PROVIDER_KEY,
    PriceCache,
)
from emfin_capstone.data_types import Exchange, AssetType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DataFrame column constants
# ---------------------------------------------------------------------------

_CLOSE_COL = "Close"
_DATE_COL = "Date"
_SYMBOL_COL = "symbol"
_PRICE_COL = "price"


# ---------------------------------------------------------------------------
# Venue → upstream routing tables (PRIVATE to the price layer)
#
# These are the only place that maps a trading venue to a concrete upstream
# (Yahoo / Stooq) and its ticker suffix.  Nothing above the ``PriceFetcher``
# seam — not the domain types, not the builder — knows these vendors exist.
# Venues absent from ``_YAHOO_SUFFIX_BY_EXCHANGE`` have no market feed wired
# and the factory raises for them.
# ---------------------------------------------------------------------------

_YAHOO_SUFFIX_BY_EXCHANGE: dict[Exchange, str] = {
    Exchange.NYSE_ARCA: "",
    Exchange.NYSE: "",
    Exchange.NASDAQ: "",
    Exchange.US: "",
    Exchange.HK: ".HK",
    Exchange.SHE: ".SZ",
}

# Venues we splice Yahoo (recent, dividend-adjusted) with Stooq (deep history).
_STOOQ_SUFFIX_BY_EXCHANGE: dict[Exchange, str] = {
    Exchange.HK: ".HK",
}


# ---------------------------------------------------------------------------
# Boundary types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceObservation:
    """A single (date, close) point within one symbol's history.

    Sibling to ``PriceData`` — the latter tags the symbol per-row because it
    lives in a multi-symbol ``PriceSeries``; this one omits the symbol because
    it lives inside a ``PriceHistory`` that already carries the identity.
    """

    date: date
    close: float


@dataclass(frozen=True)
class PriceHistory:
    """One symbol's daily Close history — the leaf-layer return type.

    Carries the symbol identity alongside an ordered list of close
    observations.  Leaves typically build a pandas DataFrame internally
    (idiomatic for the cache + slice + concat operations they perform) and
    convert at the return site via :meth:`from_dataframe`.

    Invariants:
      * ``closes`` is sorted by date ascending,
      * dates fall within the requested window,
      * no NaN closes.
    """

    symbol: str
    closes: list[PriceObservation]

    def to_dataframe(self) -> pd.DataFrame:
        """Render as a date-indexed DataFrame with a single ``Close`` column.

        Useful for callers (e.g. ``SplicedPriceFetcher``) that operate on
        DataFrames internally before re-wrapping.
        """
        if not self.closes:
            return pd.DataFrame(columns=[_CLOSE_COL])
        rows = [(obs.date, obs.close) for obs in self.closes]
        df = pd.DataFrame(rows, columns=[_DATE_COL, _CLOSE_COL])
        df[_DATE_COL] = pd.to_datetime(df[_DATE_COL])
        return df.set_index(_DATE_COL).sort_index()

    @classmethod
    def from_dataframe(
        cls, symbol: str, df: Optional[pd.DataFrame]
    ) -> Optional["PriceHistory"]:
        """Build a ``PriceHistory`` from a date-indexed Close DataFrame.

        Returns ``None`` when ``df`` is missing, empty, or lacks ``Close``.
        Callers can use this at their ``return`` site to wrap fetch output
        without manual emptiness checks.
        """
        if df is None or df.empty or _CLOSE_COL not in df.columns:
            return None
        observations = [
            PriceObservation(
                date=ts.date() if hasattr(ts, "date") else ts,
                close=float(value),
            )
            for ts, value in df[_CLOSE_COL].items()
        ]
        return cls(symbol=symbol, closes=observations)


# ---------------------------------------------------------------------------
# Protocol — source-agnostic seam
# ---------------------------------------------------------------------------


@runtime_checkable
class PriceFetcher(Protocol):
    """Per-symbol leaf seam used by ``PriceFetcherFactory``.

    Implementers fetch a single symbol's daily Close history from one
    upstream (Yahoo, Binance, Stooq, or a splice).  They have no concept
    of routing — that's the factory's job.

    Returns a :class:`PriceHistory` (``symbol`` + ordered ``closes``) on
    success.

    Returns ``None`` when fetch was attempted but no data is available
    (transient upstream failure, missing symbol on this source, no API
    key, etc.).  Construction-time misuse — e.g. an unknown ``exchange=``
    argument — must still raise.
    """

    def fetch_symbol(
        self, symbol: str, start: date, end: date
    ) -> Optional[PriceHistory]: ...


# ---------------------------------------------------------------------------
# Cache-segment helper (shared across sources)
# ---------------------------------------------------------------------------


def _missing_segments(
    cache: Optional[PriceCache],
    provider_key: str,
    symbol: str,
    start: date,
    end: date,
) -> list[tuple[date, date]]:
    """Return the sub-ranges of ``[start, end]`` not already covered by cache.

    Backward-extension aware: emits separate segments for any pre-first and
    post-last gaps so historical extensions trigger fetches rather than
    silently returning the clamped cached slice.
    """
    if cache is None:
        return [(start, end)]
    cached = cache.get_history(provider_key, symbol)
    if cached is None or cached.empty:
        return [(start, end)]
    first_cached = cached.index.min().date()
    last_cached = cached.index.max().date()
    segments: list[tuple[date, date]] = []
    if start < first_cached:
        segments.append((start, first_cached - timedelta(days=1)))
    if end > last_cached:
        segments.append((last_cached + timedelta(days=1), end))
    return segments


def _trim(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Restrict ``df`` to rows whose index lies in ``[start, end]``."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    return df[(df.index >= start_ts) & (df.index <= end_ts)]


# ---------------------------------------------------------------------------
# Yahoo source — uses yfinance
# ---------------------------------------------------------------------------


class YahooPriceFetcher:
    """Daily Yahoo close fetcher via the ``yfinance`` library.

    Constructed with the venue's yfinance ticker ``suffix`` (the factory owns
    the venue→suffix map).  ``Close`` returned is the **raw** (unadjusted)
    close (``auto_adjust=False``).  We deliberately
    use raw closes because Layer-1 ``Asset.events`` already encode SPLIT and
    STOCK_AS_DIVIDEND as discrete ``quantity_change`` events.  Replaying those
    events against raw closes gives the correct historical market value;
    using auto-adjusted prices alongside split-adjusted-quantity replay would
    double-count every split and stock dividend.
    Cached on disk under ``YAHOO_PROVIDER_KEY``.
    """

    def __init__(
        self,
        suffix: str = "",
        cache: Optional[PriceCache] = None,
        adjust_price: Optional[bool] = False,
    ) -> None:
        # ``suffix`` is the yfinance ticker suffix for the venue (e.g. ".HK",
        # ".SZ", or "" for US listings). The factory owns the venue→suffix map.
        self._suffix = suffix
        self._cache = cache
        self._adjust_price = adjust_price

    def fetch_symbol(
        self, symbol: str, start: date, end: date
    ) -> Optional[PriceHistory]:
        segments = _missing_segments(
            self._cache, YAHOO_PROVIDER_KEY, symbol, start, end
        )

        last_frame: Optional[pd.DataFrame] = None
        for seg_start, seg_end in segments:
            frame = self._download(symbol, seg_start, seg_end)
            if frame is not None and not frame.empty and self._cache is not None:
                self._cache.append_history(YAHOO_PROVIDER_KEY, symbol, frame)
            if frame is not None:
                last_frame = frame

        final_frame: Optional[pd.DataFrame] = None
        if self._cache is not None:
            cached = self._cache.get_history(YAHOO_PROVIDER_KEY, symbol)
            if cached is not None:
                final_frame = _trim(cached, start, end)
        if final_frame is None:
            final_frame = last_frame
        return PriceHistory.from_dataframe(symbol, final_frame)

    def _download(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        ticker = symbol + self._suffix
        logger.info("Fetching history for %s via yfinance", ticker)
        try:
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(
                start=start,
                end=end + timedelta(days=1),
                auto_adjust=self._adjust_price,
                actions=False,
                repair=True,
            )
        except Exception as exc:
            logger.warning("Failed to fetch history for %s: %s", ticker, exc)
            return None

        if df is None or df.empty or _CLOSE_COL not in df.columns:
            return None

        normalised_index = df.index.tz_localize(None).normalize()
        out = pd.DataFrame(
            {_CLOSE_COL: df[_CLOSE_COL].to_numpy()}, index=normalised_index
        )
        out.index.name = _DATE_COL
        return out.dropna()


# ---------------------------------------------------------------------------
# Binance source — yfinance doesn't cover crypto, so REST is used directly
# ---------------------------------------------------------------------------


_BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
_BINANCE_KLINES_LIMIT = 1000
_USER_AGENT = "Mozilla/5.0"


def _to_binance_symbol(symbol: str) -> str:
    """Normalise a generic symbol to Binance pair format (BTC-USD → BTCUSDT)."""
    return symbol.replace("-", "").replace("USD", "USDT")


class BinancePriceFetcher:
    """Daily Binance kline-close fetcher via the public REST API.

    yfinance does not cover Binance pairs, so this uses ``urllib`` directly.
    Cached on disk under ``BINANCE_PROVIDER_KEY``.
    """

    def __init__(self, cache: Optional[PriceCache] = None) -> None:
        self._cache = cache

    def fetch_symbol(
        self, symbol: str, start: date, end: date
    ) -> Optional[PriceHistory]:
        segments = _missing_segments(
            self._cache, BINANCE_PROVIDER_KEY, symbol, start, end
        )

        last_frame: Optional[pd.DataFrame] = None
        for seg_start, seg_end in segments:
            frame = self._download_klines(symbol, seg_start, seg_end)
            if frame is not None and not frame.empty and self._cache is not None:
                self._cache.append_history(BINANCE_PROVIDER_KEY, symbol, frame)
            if frame is not None:
                last_frame = frame

        final_frame: Optional[pd.DataFrame] = None
        if self._cache is not None:
            cached = self._cache.get_history(BINANCE_PROVIDER_KEY, symbol)
            if cached is not None:
                final_frame = _trim(cached, start, end)
        if final_frame is None:
            final_frame = last_frame
        return PriceHistory.from_dataframe(symbol, final_frame)

    def _download_klines(
        self, symbol: str, start: date, end: date
    ) -> Optional[pd.DataFrame]:
        binance_symbol = _to_binance_symbol(symbol)
        start_ms = int(pd.Timestamp(start).timestamp() * 1000)
        end_ms = int(pd.Timestamp(end).timestamp() * 1000)

        rows: list[tuple[int, float]] = []
        current_start_ms = start_ms

        while True:
            params = urllib.parse.urlencode(
                {
                    "symbol": binance_symbol,
                    "interval": "1d",
                    "startTime": current_start_ms,
                    "endTime": end_ms,
                    "limit": _BINANCE_KLINES_LIMIT,
                }
            )
            url = _BINANCE_KLINES_URL + "?" + params
            try:
                with urllib.request.urlopen(url) as response:
                    klines = json.loads(response.read())
            except Exception as exc:
                logger.warning("Failed to fetch klines for %s: %s", binance_symbol, exc)
                break

            if not klines:
                break

            for kline in klines:
                rows.append((int(kline[0]), float(kline[4])))

            if len(klines) < _BINANCE_KLINES_LIMIT:
                break
            # Advance start past the last returned candle
            current_start_ms = int(klines[-1][0]) + 1

        if not rows:
            return None

        open_times_ms, closes = zip(*rows)
        dates = (
            pd.to_datetime(open_times_ms, unit="ms", utc=True)
            .normalize()
            .tz_localize(None)
        )
        df = pd.DataFrame({_CLOSE_COL: closes}, index=dates)
        df.index.name = _DATE_COL
        # Dedup by date, keeping the last occurrence so today's partial bar wins
        return df[~df.index.duplicated(keep="last")]


# ---------------------------------------------------------------------------
# Stooq source — REST (no yfinance coverage)
# ---------------------------------------------------------------------------


_STOOQ_HISTORY_URL = "https://stooq.com/q/d/l/"
_STOOQ_WARNING_FIRED: set[str] = set()


class StooqPriceFetcher:
    """Stooq split-adjusted daily close fetcher (history-only).

    Stooq requires a per-user API key obtained via captcha at
    ``https://stooq.com/q/d/?s=<symbol>&get_apikey``.  Pass it as ``api_key``.
    Without a key, every request returns an instruction page; this is detected
    and treated as a no-op (returns ``None`` with a per-symbol WARNING).

    Bias caveat: Stooq Close is split-adjusted only, NOT dividend-adjusted.
    Total return is understated by cumulative dividends over any window
    relying solely on Stooq.  ``SplicedPriceSource`` emits a per-symbol
    WARNING when the pre-Yahoo Stooq segment is used.
    """

    def __init__(
        self,
        suffix: str = "",
        cache: Optional[PriceCache] = None,
        api_key: Optional[str] = None,
    ) -> None:
        # ``suffix`` is the Stooq ticker suffix for the venue (e.g. ".HK").
        # The factory owns the venue→suffix map.
        self._suffix = suffix
        self._cache = cache
        self._api_key = api_key

    def fetch_symbol(
        self, symbol: str, start: date, end: date
    ) -> Optional[PriceHistory]:
        segments = _missing_segments(
            self._cache, STOOQ_PROVIDER_KEY, symbol, start, end
        )

        last_frame: Optional[pd.DataFrame] = None
        for seg_start, seg_end in segments:
            frame = self._download(symbol, seg_start, seg_end)
            if frame is not None and not frame.empty and self._cache is not None:
                self._cache.append_history(STOOQ_PROVIDER_KEY, symbol, frame)
            if frame is not None:
                last_frame = frame

        final_frame: Optional[pd.DataFrame] = None
        if self._cache is not None:
            cached = self._cache.get_history(STOOQ_PROVIDER_KEY, symbol)
            if cached is not None:
                final_frame = _trim(cached, start, end)
        if final_frame is None:
            final_frame = last_frame
        return PriceHistory.from_dataframe(symbol, final_frame)

    def _download(self, symbol: str, start: date, end: date) -> Optional[pd.DataFrame]:
        ticker = (symbol + self._suffix).lower()
        params_dict: dict[str, str] = {
            "s": ticker,
            "d1": start.strftime("%Y%m%d"),
            "d2": end.strftime("%Y%m%d"),
            "i": "d",
        }
        if self._api_key is not None:
            params_dict["apikey"] = self._api_key
        url = _STOOQ_HISTORY_URL + "?" + urllib.parse.urlencode(params_dict)
        logger.info("Fetching history for %s from Stooq", ticker)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:
            logger.warning("Failed to fetch Stooq history for %s: %s", ticker, exc)
            return None

        if raw.startswith("Get your apikey"):
            logger.warning(
                "Stooq requires an API key for %s. Obtain one at "
                "https://stooq.com/q/d/?s=%s&get_apikey and pass it as "
                "api_key= to StooqPriceSource.",
                ticker,
                ticker,
            )
            return None

        try:
            df = pd.read_csv(io.StringIO(raw))
            if df.empty or _DATE_COL not in df.columns:
                return None
            df[_DATE_COL] = pd.to_datetime(df[_DATE_COL])
            df = df.set_index(_DATE_COL)
            df.index = pd.to_datetime(df.index).normalize()
            if _CLOSE_COL not in df.columns:
                logger.warning(
                    "Stooq response for %s has no Close column; columns: %s",
                    ticker,
                    df.columns.tolist(),
                )
                return None
            return df[[_CLOSE_COL]].dropna().sort_index()
        except Exception as exc:
            logger.warning("Failed to parse Stooq CSV for %s: %s", ticker, exc)
            return None


# ---------------------------------------------------------------------------
# Spliced source — Yahoo (post-inception) + Stooq (pre-Yahoo, level-scaled)
# ---------------------------------------------------------------------------


class SplicedPriceFetcher:
    """Splices Yahoo (dividend-adjusted) with Stooq (split-adjusted) histories.

    For dates where Yahoo has data, Yahoo's Close is used.  For dates earlier
    than Yahoo's first observation, Stooq's Close is level-scaled so the log
    level is continuous at the join date.

    Bias caveat: the pre-Yahoo Stooq segment is not dividend-adjusted; total
    return is understated by cumulative dividends in that window.  A WARNING
    is emitted once per symbol when a Stooq pre-segment is actually used.
    """

    def __init__(
        self,
        primary: YahooPriceFetcher,
        fallback: StooqPriceFetcher,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def fetch_symbol(
        self, symbol: str, start: date, end: date
    ) -> Optional[PriceHistory]:
        yahoo_history = self._primary.fetch_symbol(symbol, start, end)
        stooq_history = self._fallback.fetch_symbol(symbol, start, end)
        # Splice math is wide-frame-shaped; round-trip via .to_dataframe()
        # / .from_dataframe() at the boundaries.
        yahoo_frame = (
            yahoo_history.to_dataframe() if yahoo_history is not None else None
        )
        stooq_frame = (
            stooq_history.to_dataframe() if stooq_history is not None else None
        )

        # Splice on raw DataFrames (idiomatic pandas: index masks, concat,
        # dedup, sort). Wrap once at the function exit.
        final_frame: Optional[pd.DataFrame]
        if yahoo_frame is None or yahoo_frame.empty:
            final_frame = stooq_frame
        elif stooq_frame is None or stooq_frame.empty:
            final_frame = yahoo_frame
        else:
            yahoo_first_ts = yahoo_frame.index.min()
            stooq_pre = stooq_frame[stooq_frame.index < yahoo_first_ts]
            stooq_at_join = stooq_frame[stooq_frame.index <= yahoo_first_ts]
            yahoo_join_rows = yahoo_frame[yahoo_frame.index == yahoo_first_ts]

            if stooq_pre.empty or stooq_at_join.empty or yahoo_join_rows.empty:
                final_frame = yahoo_frame
            else:
                stooq_join_close = float(stooq_at_join[_CLOSE_COL].iloc[-1])
                yahoo_join_close = float(yahoo_join_rows[_CLOSE_COL].iloc[0])
                if stooq_join_close == 0.0:
                    final_frame = yahoo_frame
                else:
                    scale_factor = yahoo_join_close / stooq_join_close
                    scaled_pre = stooq_pre.copy()
                    scaled_pre[_CLOSE_COL] = scaled_pre[_CLOSE_COL] * scale_factor

                    if symbol not in _STOOQ_WARNING_FIRED:
                        _STOOQ_WARNING_FIRED.add(symbol)
                        logger.warning(
                            "Pre-Yahoo returns for %s are dividend-unadjusted (Stooq); "
                            "total return is understated by ~dividend_yield during that window.",
                            symbol,
                        )

                    combined = pd.concat([scaled_pre, yahoo_frame])
                    combined = combined[
                        ~combined.index.duplicated(keep="last")
                    ].sort_index()
                    final_frame = _trim(combined, start, end)

        return PriceHistory.from_dataframe(symbol, final_frame)


# ---------------------------------------------------------------------------
# Face-value source — assets with no market feed (cash)
# ---------------------------------------------------------------------------


class FaceValuePriceFetcher:
    """``PriceFetcher`` for assets always worth their face value (cash).

    Emits a single 1.0 native-currency observation at ``start``; the builder's
    forward-fill carries it across every day.  This keeps the builder uniform —
    it asks the factory for a fetcher for *every* asset and never special-cases
    cash — while still making zero network calls.
    """

    def fetch_symbol(
        self, symbol: str, start: date, end: date
    ) -> Optional[PriceHistory]:
        return PriceHistory(
            symbol=symbol, closes=[PriceObservation(date=start, close=1.0)]
        )


# ---------------------------------------------------------------------------
# Per-asset routing factory
# ---------------------------------------------------------------------------


class PriceFetcherFactory:
    """Routes an ``Asset`` to the correct ``PriceFetcher``.

    Routing reads only the asset's domain attributes — ``asset_type`` and
    ``exchange`` — and is the single seam where those map to a concrete
    upstream.  Callers (the builder) stay entirely vendor-agnostic.

    Routing order:
      * ``AssetType.CASH``   → face-value 1.0 (no network)
      * ``AssetType.CRYPTO`` → Binance
      * a trading ``exchange`` → Yahoo, or a Yahoo+Stooq splice for venues in
        ``_STOOQ_SUFFIX_BY_EXCHANGE`` (HK)

    Raises ``KeyError`` for a venue with no feed wired, so
    misconfiguration can't silently drop an asset.
    """

    def __init__(
        self,
        cache_dir: Path = config.CACHE_DIR,
        stooq_api_key: Optional[str] = None,
        adjust_prices: bool = False,
    ) -> None:
        cache = PriceCache(cache_dir)
        venue_sources: dict[Exchange, PriceFetcher] = {}
        for venue, suffix in _YAHOO_SUFFIX_BY_EXCHANGE.items():
            yahoo = YahooPriceFetcher(suffix, cache=cache, adjust_price=adjust_prices)
            stooq_suffix = _STOOQ_SUFFIX_BY_EXCHANGE.get(venue)
            if stooq_suffix is not None:
                venue_sources[venue] = SplicedPriceFetcher(
                    primary=yahoo,
                    fallback=StooqPriceFetcher(
                        stooq_suffix, cache=cache, api_key=stooq_api_key
                    ),
                )
            else:
                venue_sources[venue] = yahoo
        self._venue_sources = venue_sources
        self._face_value = FaceValuePriceFetcher()
        self._crypto = BinancePriceFetcher(cache=cache)

    def build_price_fetcher(self, asset_type: AssetType, exchange: Exchange) -> PriceFetcher:
        if asset_type == AssetType.CASH:
            return self._face_value
        if asset_type == AssetType.CRYPTO:
            return self._crypto
        source = self._venue_sources.get(exchange)
        if source is None:
            raise KeyError(
                f"no PriceFetcher registered for venue {exchange!r} "
            )
        return source
