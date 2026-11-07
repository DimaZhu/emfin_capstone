"""Pinned data snapshot loader — the reproducibility seam.

The notebook pulls live yfinance data up to ``date.today()``, so results
drift between runs and between teammates' machines.  This module loads the
pinned snapshot committed under ``data/snapshot/`` instead: one frozen set
of adjusted closes (plus the 10Y Treasury yield index) that every run,
backtest and paper number comes from.  Regenerate deliberately with
``scripts/pin_data_snapshot.py`` and commit the result — never as a side
effect of an analysis run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from emfin_capstone import config
from emfin_capstone.toolbox import price, returns

SNAPSHOT_DIR: Path = config.DATA_DIR / "snapshot"
CLOSES_FILENAME = "closes.csv"
MANIFEST_FILENAME = "manifest.json"

EQUITY_TICKERS = ["DFUS", "DFAI", "DFAE"]
YIELD_TICKER = "^TNX"  # CBOE 10Y Treasury yield index, in percent


@dataclass(frozen=True)
class Snapshot:
    """The pinned market data: aligned daily closes + provenance."""

    closes: pd.DataFrame  # date-indexed, one column per ticker, no NaN
    manifest: dict

    @property
    def last_date(self) -> date:
        return self.closes.index[-1].date()


def load_snapshot(snapshot_dir: Path = SNAPSHOT_DIR) -> Snapshot:
    """Load the committed snapshot, failing loudly if it is missing or dirty."""
    closes_path = snapshot_dir / CLOSES_FILENAME
    manifest_path = snapshot_dir / MANIFEST_FILENAME
    if not closes_path.exists():
        raise FileNotFoundError(
            f"No pinned snapshot at {closes_path}. "
            "Run scripts/pin_data_snapshot.py and commit the result."
        )
    closes = pd.read_csv(closes_path, index_col="Date", parse_dates=True)
    if closes.isna().any().any():
        raise ValueError(f"Snapshot {closes_path} contains NaNs; regenerate it.")
    manifest = json.loads(manifest_path.read_text())
    return Snapshot(closes=closes, manifest=manifest)


def _column_to_price_history(closes: pd.DataFrame, symbol: str) -> price.PriceHistory:
    frame = pd.DataFrame({"Close": closes[symbol]})
    history = price.PriceHistory.from_dataframe(symbol, frame)
    assert history is not None
    return history


def weekly_log_returns(snapshot: Snapshot, tickers: list[str] | None = None) -> pd.DataFrame:
    """Wednesday-to-Wednesday log returns from the pinned closes.

    Reuses the single implementation in ``toolbox.returns`` (7-calendar-day
    Wednesday pairs, holiday weeks skipped) so snapshot and live pipelines
    cannot drift apart in their return construction.
    """
    tickers = tickers or EQUITY_TICKERS
    weekly: dict[str, pd.Series] = {}
    for symbol in tickers:
        history = _column_to_price_history(snapshot.closes, symbol)
        collection = returns.convert_history_prices_to_weekly_returns(history)
        weekly[symbol] = pd.Series(
            [r.equity_return for r in collection.equity_returns],
            index=pd.DatetimeIndex([r.date for r in collection.equity_returns]),
            name=symbol,
        )
    return pd.DataFrame(weekly).dropna()


def weekly_yield_changes(snapshot: Snapshot) -> pd.Series:
    """Wednesday-to-Wednesday changes in the 10Y yield (percentage points).

    Bonds do not share the equity invariant (compounded returns); the
    fixed-maturity recipe uses yield changes as the invariant — see
    ``toolbox.bonds``.  Same Wednesday pairing as the equity returns so the
    two series align row for row on dates they share.
    """
    history = _column_to_price_history(snapshot.closes, YIELD_TICKER)
    closes = history.to_dataframe()["Close"]
    wed = closes[closes.index.weekday == 2]
    changes = wed.diff().dropna()
    changes.index.name = "Date"
    return changes.rename(YIELD_TICKER)
