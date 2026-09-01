"""Disk-backed cache for quotes and historical price data."""

import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from emfin_capstone import config

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Directory / file name constants
# ---------------------------------------------------------------------------

_QUOTES_DIR_NAME = "quotes"
_HISTORY_DIR_NAME = "history"
_QUOTE_FILENAME_SUFFIX = ".json"
_HISTORY_FILENAME_SUFFIX = ".csv"

# ---------------------------------------------------------------------------
# JSON key constants
# ---------------------------------------------------------------------------

_PRICE_KEY = "price"
_FETCHED_AT_KEY = "fetched_at"

# ---------------------------------------------------------------------------
# DataFrame column constants
# ---------------------------------------------------------------------------

_DATE_COL = "Date"
_CLOSE_COL = "Close"

# ---------------------------------------------------------------------------
# Public provider key constants (consumed by providers)
# ---------------------------------------------------------------------------

YAHOO_PROVIDER_KEY = "yahoo"
BINANCE_PROVIDER_KEY = "binance"
YAHOO_FX_PROVIDER_KEY = "yahoo_fx"
STOOQ_PROVIDER_KEY = "stooq"


class PriceCache:
    """Filesystem-backed cache for quotes and OHLCV history."""

    def __init__(self, base_dir: Path = config.CACHE_DIR) -> None:
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # Internal path helpers
    # ------------------------------------------------------------------

    def _quotes_path(self, provider_key: str) -> Path:
        return self._base_dir / _QUOTES_DIR_NAME / provider_key

    def _history_path(self, provider_key: str, symbol: str) -> Path:
        safe_symbol = symbol.replace("/", "_").replace(":", "_")
        return (
            self._base_dir
            / _HISTORY_DIR_NAME
            / provider_key
            / (safe_symbol + _HISTORY_FILENAME_SUFFIX)
        )

    def _quotes_file(self, provider_key: str) -> Path:
        return self._quotes_path(provider_key) / ("quotes" + _QUOTE_FILENAME_SUFFIX)

    # ------------------------------------------------------------------
    # Quote cache
    # ------------------------------------------------------------------

    def get_fresh_quotes(
        self,
        provider_key: str,
        symbols: list[str],
        ttl_seconds: float,
    ) -> tuple[dict[str, float], list[str]]:
        """Return (cached_price_dict, stale_or_missing_symbols)."""
        cached_price_dict: dict[str, float] = {}
        stale_symbols: list[str] = []

        quotes_file = self._quotes_file(provider_key)
        if not quotes_file.exists():
            return {}, list(symbols)

        try:
            raw = json.loads(quotes_file.read_text())
        except Exception as exc:
            logger.warning("Corrupt quotes cache for %s: %s", provider_key, exc)
            return {}, list(symbols)

        now = datetime.now(tz=timezone.utc).timestamp()

        for symbol in symbols:
            entry = raw.get(symbol)
            if entry is None:
                stale_symbols.append(symbol)
                continue
            fetched_at_str = entry.get(_FETCHED_AT_KEY)
            if fetched_at_str is None:
                stale_symbols.append(symbol)
                continue
            try:
                fetched_ts = datetime.fromisoformat(fetched_at_str).timestamp()
            except ValueError:
                stale_symbols.append(symbol)
                continue
            if (now - fetched_ts) > ttl_seconds:
                stale_symbols.append(symbol)
            else:
                price = entry.get(_PRICE_KEY)
                if price is not None:
                    cached_price_dict[symbol] = float(price)
                else:
                    stale_symbols.append(symbol)

        return cached_price_dict, stale_symbols

    def put_quotes(self, provider_key: str, price_dict: dict[str, float]) -> None:
        """Merge price_dict into the JSON store with the current UTC timestamp."""
        quotes_file = self._quotes_file(provider_key)
        quotes_file.parent.mkdir(parents=True, exist_ok=True)

        existing: dict = {}
        if quotes_file.exists():
            try:
                existing = json.loads(quotes_file.read_text())
            except Exception as exc:
                logger.warning(
                    "Corrupt quotes file for %s, resetting: %s", provider_key, exc
                )

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        for symbol, price in price_dict.items():
            existing[symbol] = {_PRICE_KEY: price, _FETCHED_AT_KEY: now_iso}

        self._atomic_write_json(quotes_file, existing)

    # ------------------------------------------------------------------
    # History cache
    # ------------------------------------------------------------------

    def get_history(self, provider_key: str, symbol: str) -> Optional[pd.DataFrame]:
        """Return DataFrame indexed by Date with a Close column, or None if missing."""
        path = self._history_path(provider_key, symbol)
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path, parse_dates=[_DATE_COL], index_col=_DATE_COL)
            df.index = pd.to_datetime(df.index).normalize()
            return df[[_CLOSE_COL]]
        except Exception as exc:
            logger.warning(
                "Corrupt history cache for %s/%s: %s", provider_key, symbol, exc
            )
            return None

    def append_history(
        self,
        provider_key: str,
        symbol: str,
        frame: pd.DataFrame,
    ) -> None:
        """Merge frame with existing cached data, dedupe by Date (last wins), atomic write."""
        existing = self.get_history(provider_key, symbol)

        incoming = frame.copy()
        incoming.index = pd.to_datetime(incoming.index).normalize()
        incoming = incoming[[_CLOSE_COL]]

        if existing is not None and not existing.empty:
            merged = pd.concat([existing, incoming])
        else:
            merged = incoming

        merged = merged[~merged.index.duplicated(keep="last")]
        merged = merged.sort_index()

        path = self._history_path(provider_key, symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_csv(path, merged)

    def last_cached_date(self, provider_key: str, symbol: str) -> Optional[date]:
        """Return the most recent Date in the cached history, or None."""
        df = self.get_history(provider_key, symbol)
        if df is None or df.empty:
            return None
        return df.index.max().date()

    # ------------------------------------------------------------------
    # Atomic write helpers
    # ------------------------------------------------------------------

    def _atomic_write_json(self, path: Path, data: dict) -> None:
        tmp = Path(str(path) + ".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2))
            os.replace(tmp, path)
        except Exception as exc:
            logger.warning("Failed to write cache file %s: %s", path, exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def _atomic_write_csv(self, path: Path, df: pd.DataFrame) -> None:
        tmp = Path(str(path) + ".tmp")
        try:
            df.to_csv(tmp)
            os.replace(tmp, path)
        except Exception as exc:
            logger.warning("Failed to write history file %s: %s", path, exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
