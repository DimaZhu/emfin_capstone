"""Build the real-estate observer series from a licensed raw drop and run the
latent-return layer on it - the real-data validation path for the Abu Dhabi
module.

Run: python scripts/build_re_observer.py  (uses the committed BIS/FRED UAE
RPPI drop; quarterly log returns -> moment fit -> Kalman smoothing ->
Layer-3 diagnostics on the invariant).
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import numpy as np

from emfin_v2.toolbox import real_estate as re_
from emfin_v2.toolbox.raw_data import series_file

RAW = series_file("QAEN628BIS")


def main() -> None:
    adapter = re_.CsvIndexAdapter(RAW)
    series = adapter.observer_series()[adapter.name]
    print(f"observer '{adapter.name}': {len(series)} quarterly log returns, "
          f"mean {series.mean():.4f}, vol {series.std(ddof=1):.4f}")
    print(f"raw lag-1 autocorrelation: {re_.acf(series, 1)[1]:.3f} "
          "(smoothing signature; genuine momentum is NOT forced out)")

    # single-observer moment fit + Kalman smoothing
    model = re_.moment_fit(series.reshape(-1, 1))
    print(f"moment fit: mu {model.mu:.4f}, rho {model.rho:.2f}, q {model.q:.6f}, smoothing c {model.smoothing[0]:.2f} "
          "(crude fit - EM is documented future work)")
    out = re_.kalman_smooth(series.reshape(-1, 1), model)
    inv = out["invariant"]
    lb = re_.ljung_box(inv, 8)
    arch = re_.arch_lm(inv, 4)
    print(f"invariant: {len(inv)} quarters, lag-1 ACF {re_.acf(inv, 1)[1]:.3f}, "
          f"Ljung-Box p {lb['p_value']:.3f}, ARCH-LM p {arch['p_value']:.3f}")

    # baselines for comparison
    unsmoothed, c_hat = re_.fgw_unsmooth(series)
    print(f"FGW baseline: c* {c_hat:.2f}, unsmoothed vol {unsmoothed.std(ddof=1):.4f} "
          f"vs raw {series.std(ddof=1):.4f} (vol ratio {unsmoothed.std(ddof=1)/series.std(ddof=1):.2f}x)")
    print("note: UAE-wide REIDIN-derived index, nominal, 2010=100, through 2024Q1; "
          "Abu Dhabi composition effects and the stale tail are known caveats.")


if __name__ == "__main__":
    main()
