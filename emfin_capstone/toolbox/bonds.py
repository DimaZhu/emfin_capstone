"""Fixed-maturity bond invariants and scenario pricing.

Equity invariants (compounded returns) do not transfer to bonds: a bond's
price converges to face value at maturity, so its returns are not i.i.d.
The standard fixed-maturity recipe (Meucci Ch. 3.1) treats *changes in
yield to maturity* as the i.i.d. invariant and reprices the bond exactly
under each scenario — duration/convexity and roll-down then fall out of
the pricing equation rather than being approximated.

Simplifications (documented for the paper's limitations section):
  * flat per-bond yield curve: the scenario moves one yield, not a curve;
  * deterministic coupons, no credit-spread layer yet (a spread invariant
    can be added as a second factor exactly like the yield change);
  * semiannual coupons, US Treasury convention.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

COUPONS_PER_YEAR = 2


@dataclass(frozen=True)
class Bond:
    """A plain vanilla fixed-coupon bond.

    ``ytm`` and ``coupon_rate`` are annual decimals (0.048 = 4.8%).
    ``years_to_maturity`` is measured at the pricing date and rolls down
    as the horizon advances.
    """

    name: str
    face_value: float
    coupon_rate: float
    years_to_maturity: float
    ytm: float


def price_from_ytm(ytm: float | np.ndarray, years_to_maturity: float, coupon_rate: float, face_value: float) -> np.ndarray:
    """Dirty price under a flat yield, vectorized over scenarios of ytm.

    Exact repricing: coupon dates are at semiannual grid points; the first
    coupon is one period (half a year) out.  Near maturity the price pulls
    to par — the convergence that makes equity-style return invariants
    invalid here.
    """
    y = np.atleast_1d(np.asarray(ytm, dtype=float))
    n_periods = max(1, int(np.ceil(years_to_maturity * COUPONS_PER_YEAR - 1e-9)))
    coupon = coupon_rate * face_value / COUPONS_PER_YEAR
    # Cashflow times measured from the pricing date: the last cashflow lands
    # at the remaining maturity and earlier ones step back in coupon periods,
    # so a fractional remaining maturity (mid-period pricing) carries the
    # accrued-interest drift - with unchanged yield the price accretes
    # toward the next coupon instead of sitting flat.
    times = years_to_maturity - (n_periods - 1 - np.arange(n_periods)) / COUPONS_PER_YEAR
    discount = (1 + y[:, None] / COUPONS_PER_YEAR) ** (-COUPONS_PER_YEAR * times[None, :])
    cashflows = np.full(n_periods, coupon)
    cashflows[-1] += face_value
    return discount @ cashflows


def macaulay_duration_years(ytm: float, years_to_maturity: float, coupon_rate: float, face_value: float) -> float:
    """Sanity anchor for tests and for communicating rate sensitivity."""
    n_periods = max(1, int(np.ceil(years_to_maturity * COUPONS_PER_YEAR - 1e-9)))
    coupon = coupon_rate * face_value / COUPONS_PER_YEAR
    times = years_to_maturity - (n_periods - 1 - np.arange(n_periods)) / COUPONS_PER_YEAR
    discount = (1 + ytm / COUPONS_PER_YEAR) ** (-COUPONS_PER_YEAR * times)
    cashflows = np.full(n_periods, coupon)
    cashflows[-1] += face_value
    pv = discount * cashflows
    return float((pv @ times) / pv.sum())


def weekly_yield_change_invariants(yield_series: pd.Series) -> pd.Series:
    """Weekly changes in yield (percentage points → decimal).

    Input is a Wednesday-paired weekly yield series in *percent* (as the
    snapshot stores ^TNX); output is the week-over-week change in decimal
    (0.0005 = 5bp).  These are the i.i.d. invariants to estimate moments on.
    """
    return yield_series.diff().dropna() / 100.0


def project_yield_scenarios(
    current_ytm: float,
    change_mean: float,
    change_std: float,
    horizon_weeks: int,
    n_scenarios: int,
    seed: int,
) -> np.ndarray:
    """Gaussian yield-change invariants projected to the horizon.

    Under i.i.d. weekly changes, the τ-week change is N(τμ, τσ²) — the same
    square-root rule the equity engine uses, applied to the yield invariant.
    Returns scenario yields (decimal), shape (n_scenarios,).
    """
    rng = np.random.default_rng(seed)
    change = change_mean * horizon_weeks + change_std * np.sqrt(horizon_weeks) * rng.standard_normal(n_scenarios)
    return current_ytm + change


def bond_price_scenarios(
    bond: Bond,
    yield_scenarios: np.ndarray,
    horizon_weeks: int,
) -> np.ndarray:
    """Horizon prices: reprice at each scenario yield with rolled-down maturity.

    Roll-down is the τ-week reduction of time to maturity: with unchanged
    yield the position still earns carry + roll, which the exact repricing
    captures without any duration approximation.
    """
    remaining = max(bond.years_to_maturity - horizon_weeks / 52.0, 1e-6)
    return price_from_ytm(yield_scenarios, remaining, bond.coupon_rate, bond.face_value)


def credit_price_scenarios(
    bond: Bond,
    treasury_yield_scenarios: np.ndarray,
    spread_scenarios: np.ndarray,
    horizon_weeks: int,
) -> np.ndarray:
    """Credit sleeve pricing: reprice at treasury yield + spread, rolled down.

    A corporate bond is priced off its own yield to maturity, which splits
    into a treasury component and a credit spread.  Both components are
    invariants-driven (weekly changes in each), and the bond is repriced
    exactly at the combined scenario yield with rolled-down maturity - so
    duration, convexity, carry and roll-down all fall out of the pricing
    equation, and a spread widening scenario hits the price through the
    same discounting a treasury move does.  No separate spread-duration
    approximation anywhere.
    """
    tsy = np.asarray(treasury_yield_scenarios, dtype=float).ravel()
    spr = np.asarray(spread_scenarios, dtype=float).ravel()
    if tsy.shape != spr.shape:
        raise ValueError("treasury and spread scenarios must align scenario-for-scenario")
    return bond_price_scenarios(bond, tsy + spr, horizon_weeks)
