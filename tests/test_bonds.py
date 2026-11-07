"""Bond invariants: exact-pricing identities and invariant construction."""

import numpy as np
import pandas as pd
import pytest

from emfin_capstone.toolbox import bonds


def test_par_bond_prices_at_face():
    price = bonds.price_from_ytm(0.05, 10.0, 0.05, 100.0)
    assert price[0] == pytest.approx(100.0, abs=1e-10)


def test_price_decreases_in_yield():
    low = bonds.price_from_ytm(0.04, 10.0, 0.04, 100.0)
    high = bonds.price_from_ytm(0.06, 10.0, 0.04, 100.0)
    assert high[0] < low[0]


def test_duration_matches_textbook_10y():
    # A 10y 4% bond at 5% has Macaulay duration around 8.2-8.4 years
    d = bonds.macaulay_duration_years(0.05, 10.0, 0.04, 100.0)
    assert 8.0 < d < 8.5
    # First-order check: price move for +1% yield ~ -duration/(1+y/2) percent
    p0 = bonds.price_from_ytm(0.05, 10.0, 0.04, 100.0)[0]
    p1 = bonds.price_from_ytm(0.06, 10.0, 0.04, 100.0)[0]
    approx = -d / (1 + 0.05 / 2) * 0.01  # modified duration x yield change (1%)
    assert (p1 - p0) / p0 == pytest.approx(approx, rel=0.1)


def test_pull_to_par():
    # Premium bond loses value as maturity shrinks at unchanged yield
    bond = bonds.Bond("T", 100.0, 0.06, 10.0, 0.04)
    p_now = bonds.price_from_ytm(0.04, 10.0, 0.06, 100.0)[0]
    p_later = bonds.bond_price_scenarios(bond, np.array([0.04]), horizon_weeks=52)[0]
    assert p_now > 100.0
    assert p_later < p_now
    # At maturity the price is par (plus final coupon handled in pricing)
    p_mat = bonds.price_from_ytm(0.04, 0.5, 0.06, 100.0)[0]
    assert p_mat == pytest.approx(103.0 * (1.02) ** -1 * 1.0 + 0.0, rel=0.05)


def test_yield_change_invariants_units():
    yields = pd.Series([4.0, 4.05, 4.02], index=pd.date_range("2026-01-07", periods=3, freq="7D"))
    changes = bonds.weekly_yield_change_invariants(yields)
    assert list(changes) == pytest.approx([0.0005, -0.0003])


def test_projection_scales_moments():
    bond = bonds.Bond("T", 100.0, 0.04, 10.0, 0.04)
    ys = bonds.project_yield_scenarios(0.04, 0.0001, 0.001, 52, 20000, 3)
    assert ys.mean() == pytest.approx(0.04 + 0.0052, abs=0.0002)
    assert ys.std() == pytest.approx(0.001 * np.sqrt(52), rel=0.02)
