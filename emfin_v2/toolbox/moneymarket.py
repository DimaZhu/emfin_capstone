"""Money-market sleeve: a rolling 3-month Treasury bill position.

The engine's cash sleeve used to be a crude proxy accruing at the lagged
10Y yield.  A money-market sleeve is a proper (if low-risk) asset:

  * Carry: each week accrues the current short rate, r(t-1) / 52.
  * Rate-change risk: a 3M bill has ~0.25 years of duration, so a weekly
    rate change of dr moves the position by about -0.25 * dr.  Small but
    real, and it correlates the sleeve correctly with the yield invariant.
  * Liquidity: same-day cash - zero transaction cost in the Meucci overlay.

Under a random-walk short rate the i.i.d. weekly invariant sums telescope
exactly: the 13-week horizon P&L is total carry minus duration times the
horizon rate change.  Rate series: FRED DGS3MO (see data/raw/manifest.json).
"""

from __future__ import annotations

import pandas as pd

MM_DURATION_YEARS = 0.25  # a 3-month bill
WEEKS_PER_YEAR = 52.0


def money_market_weekly_returns(rate: pd.Series, duration: float = MM_DURATION_YEARS) -> pd.Series:
    """Weekly log-return-ish invariant for a rolling money-market position.

    ``rate`` is a decimal short-rate series sampled on the same Wednesdays
    as the other invariants.  Returns carry - duration * drate, aligned on
    the diff() index (first observation dropped).
    """
    carry = rate.shift(1) / WEEKS_PER_YEAR
    rate_risk = -duration * rate.diff()
    mm = carry + rate_risk
    mm.name = "MMKT"
    return mm.dropna()
