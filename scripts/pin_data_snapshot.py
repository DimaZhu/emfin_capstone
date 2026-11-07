"""Regenerate the pinned data snapshot under data/snapshot/.

Deliberate, manual step: run this, eyeball the result, commit.  Analysis
code never calls it — it reads the committed CSVs via toolbox.snapshot.
"""



from __future__ import annotations

# Run from a fresh clone without installing the package:
# scripts/ resolves imports against the repo root directly.
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import yfinance as yf

TICKERS = ["DFUS", "DFAI", "DFAE", "^TNX"]
START = "2021-06-15"
from emfin_v2.config import DATA_DIR
OUT_DIR = DATA_DIR / "snapshot"


def main() -> None:
    frames = {}
    for ticker in TICKERS:
        history = yf.Ticker(ticker).history(
            start=START,
            auto_adjust=(ticker != "^TNX"),  # total-return closes for ETFs
            actions=False,
            repair=(ticker != "^TNX"),  # repair path needs sklearn; yields don't need it
        )
        series = history["Close"].copy()
        series.index = series.index.tz_localize(None).normalize()
        series.index.name = "Date"
        frames[ticker] = series.dropna()
    closes = pd.DataFrame(frames).dropna()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    closes.to_csv(OUT_DIR / "closes.csv")
    previous_path=OUT_DIR/'manifest.json'
    previous=json.loads(previous_path.read_text()) if previous_path.exists() else {}
    manifest = dict(previous)
    manifest.update({
        "tickers": TICKERS,
        "source": "yfinance (Yahoo Finance), auto_adjust=True for ETFs, raw close for ^TNX (percent)",
        "start": START,
        "end": str(closes.index.max().date()),
        "fetched_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rows": len(closes),
    })
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(closes)} rows through {manifest['end']} to {OUT_DIR}")


if __name__ == "__main__":
    main()
