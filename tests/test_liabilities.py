import numpy as np
import pytest

from emfin_capstone.toolbox import liabilities as liab
from emfin_capstone.toolbox import risk_stats


def test_cvar_fractional_atom_matches_sorted_tail():
    losses = np.arange(1, 101, dtype=float)  # 1..100
    # c = 0.95, N=100: tail mass 5 -> worst 5 atoms exactly
    assert risk_stats.empirical_cvar(losses, 0.95) == pytest.approx(np.mean([96, 97, 98, 99, 100]))
    # c = 0.955: tail mass 4.5 -> worst 4 + half of the 5th
    expected = (97 + 98 + 99 + 100 + 0.5 * 96) / 4.5
    assert risk_stats.empirical_cvar(losses, 0.955) == pytest.approx(expected)


def test_cvar_agrees_with_existing_engine_when_integer():
    from emfin_capstone.toolbox import scenario_market
    rng = np.random.default_rng(5)
    losses = rng.standard_normal(4000)
    assert risk_stats.empirical_cvar(losses, 0.95) == pytest.approx(
        scenario_market.empirical_cvar(losses, 0.95), rel=1e-12
    )


def test_amount_due_by():
    schedule = liab.LiabilitySchedule(items=(
        liab.Liability("school", 50_000, week=12),
        liab.Liability("villa", 2_000_000, week=40),
        liab.Liability("later", 999_000, week=100),
    ))
    assert schedule.amount_due_by(10) == 0
    assert schedule.amount_due_by(12) == 50_000
    assert schedule.amount_due_by(52) == 2_050_000


def test_gap_metrics_known_case():
    wealth = np.array([80.0, 90.0, 100.0, 110.0, 120.0])
    m = liab.funding_gap_metrics(wealth, liability_due=100.0, confidence_level=0.8)
    assert m.shortfall_probability == pytest.approx(0.4)
    assert m.expected_shortfall == pytest.approx((20 + 10) / 5)
    # gaps = [20,10,0,0,0]; c=0.8, N=5: tail mass 1 -> worst atom = 20
    assert m.shortfall_cvar == pytest.approx(20.0)


def _toy_market(n=4000, seed=1):
    rng = np.random.default_rng(seed)
    prices = np.array([100.0, 100.0])
    rets = rng.normal([0.002, 0.0005], [0.03, 0.01], size=(n, 2))
    samples = prices * np.exp(rets)
    return samples, prices


def test_zero_liability_reduces_to_asset_only():
    samples, prices = _toy_market()
    alloc, diag = liab.optimization_liability_aware(
        market_samples=samples, prices_vector=prices, wealth=1e6,
        liability_due=0.0, risk_tolerance=1e6, confidence_level=0.95,
        gamma_loss=1.0, gamma_shortfall=1.0,
    )
    np.testing.assert_allclose((prices * alloc).sum(), 1e6, rtol=1e-6)
    # loose loss budget, no liability -> tilts to the higher-drift asset
    assert alloc[0] * prices[0] > 0.9e6


def test_shortfall_budget_binds_and_tightens_monotonically():
    samples, prices = _toy_market()
    # Liability of 980k against 1e6 wealth makes tail funding matter.
    # A loose shortfall budget allows more of the high-drift asset; a tight
    # one forces the liability into the low-vol asset.
    def solve(gamma_shortfall):
        alloc, diag = liab.optimization_liability_aware(
            market_samples=samples, prices_vector=prices, wealth=1e6,
            liability_due=980_000, risk_tolerance=1e6, confidence_level=0.95,
            gamma_loss=1.0, gamma_shortfall=gamma_shortfall,
        )
        assert diag["status"] == "optimal"
        return alloc, diag

    alloc_loose, diag_loose = solve(0.02)
    alloc_tight, diag_tight = solve(0.002)
    assert diag_loose["weights"][1] < diag_tight["weights"][1]
    assert diag_tight["weights"][1] > 0.8

    # The realized funding-gap CVaR honors each budget (small numerical slack)
    for alloc, gs in [(alloc_loose, 0.02), (alloc_tight, 0.002)]:
        wealth_samples = samples @ alloc
        m = liab.funding_gap_metrics(wealth_samples, 980_000, 0.95)
        assert m.shortfall_cvar <= gs * 980_000 * 1.05
