import numpy as np
import pytest

from emfin_v2.toolbox import liabilities as liab
from emfin_v2.toolbox import risk_stats


def test_cvar_fractional_atom_matches_sorted_tail():
    losses = np.arange(1, 101, dtype=float)  # 1..100
    # c = 0.95, N=100: tail mass 5 -> worst 5 atoms exactly
    assert risk_stats.empirical_cvar(losses, 0.95) == pytest.approx(np.mean([96, 97, 98, 99, 100]))
    # c = 0.955: tail mass 4.5 -> worst 4 + half of the 5th
    expected = (97 + 98 + 99 + 100 + 0.5 * 96) / 4.5
    assert risk_stats.empirical_cvar(losses, 0.955) == pytest.approx(expected)


def test_cvar_agrees_with_existing_engine_when_integer():
    from emfin_v2.toolbox import scenario_market
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
    assert diag_tight["weights"][1] > 0.6  # constraint binds: mostly safe asset

    # The realized funding-gap CVaR honors each budget (small numerical slack)
    for alloc, gs in [(alloc_loose, 0.02), (alloc_tight, 0.002)]:
        wealth_samples = samples @ alloc
        m = liab.funding_gap_metrics(wealth_samples, 980_000, 0.95)
        assert m.shortfall_cvar <= gs * 980_000 * 1.05


def _linear_calibration_problem(crossing: float):
    """Synthetic monotone problem: realized OOS CVaR = mult * 2 * target,
    so the constraint realized <= target holds exactly for mult <= crossing
    with crossing = 0.5.  solve_fn records the multipliers it saw."""
    seen = []

    def solve(mult):
        seen.append(mult)
        return np.array([mult, 1.0 - mult])

    def evaluate(alloc):
        return alloc[0] * 2.0 * 100.0  # target = 100 -> crossing at 0.5

    return solve, evaluate, seen


def test_calibration_keeps_nominal_when_it_passes_oos():
    from emfin_v2.toolbox.liabilities import calibrate_shortfall_budget

    solve, evaluate, seen = _linear_calibration_problem(0.5)
    # target above anything hi can realize -> nominal passes immediately
    cal = calibrate_shortfall_budget(solve, evaluate, target=500.0)
    assert cal.best_multiplier == 1.0
    assert seen == [1.0]  # one probe only, no wasted solves
    np.testing.assert_allclose(cal.best_allocation, [1.0, 0.0])


def test_calibration_finds_largest_feasible_multiplier():
    from emfin_v2.toolbox.liabilities import calibrate_shortfall_budget

    solve, evaluate, _ = _linear_calibration_problem(0.5)
    cal = calibrate_shortfall_budget(solve, evaluate, target=100.0, tol=0.05)
    # crossing is at mult = 0.5: best must be feasible and within tol of it
    assert cal.best_multiplier <= 0.5 + 1e-9
    assert cal.best_multiplier >= 0.5 - 0.05 - 1e-9
    assert evaluate(cal.best_allocation) <= 100.0 + 1e-9
    # history is sorted by multiplier and records every probe
    mults = [m for m, _ in cal.history]
    assert mults == sorted(mults) and len(mults) >= 3


def test_calibration_reports_failure_when_even_tightest_fails():
    from emfin_v2.toolbox.liabilities import calibrate_shortfall_budget

    solve, evaluate, _ = _linear_calibration_problem(0.5)
    # target below what lo = 0.1 realizes (20) is fine; use target 10 -> fail
    cal = calibrate_shortfall_budget(solve, evaluate, target=10.0, lo=0.1)
    assert cal.best_multiplier == 0.1
    assert evaluate(cal.best_allocation) > 10.0  # honest failure, visible in history


def _steady_paths(n_scen=200, n_steps=6, growth=1.01, n_assets=2):
    """Deterministic upward paths: every asset grows `growth` per step."""
    rng = np.random.default_rng(7)
    base = np.tile(np.array([100.0, 50.0]), (n_scen, 1)) * rng.lognormal(0, 0.001, (n_scen, n_assets))
    paths = np.stack([base * growth ** t for t in range(1, n_steps + 1)], axis=1)
    prices = base[0].copy() if False else np.array([100.0, 50.0])
    return paths, prices


def test_multiperiod_zero_liabilities_matches_asset_only_direction():
    from emfin_v2.toolbox.liabilities import optimization_multiperiod

    paths, prices = _steady_paths()
    n_scen, n_steps, _ = paths.shape
    mm_growth = np.tile(1.001 ** np.arange(1, n_steps + 1), (n_scen, 1))
    alloc, diag = optimization_multiperiod(
        paths, prices, wealth=1e6,
        liability_scenarios=np.zeros((n_scen, 1)), payout_steps=np.array([3]),
        liability_base=np.array([0.0]), mm_growth_paths=mm_growth,
        risk_tolerance=5e4, confidence_level=0.95, gamma_loss=0.5, gamma_shortfall=1.0,
        n_optimization_scenarios=n_scen,
    )
    assert diag["status"] in ("optimal", "optimal_inaccurate")
    assert alloc.sum() > 0
    np.testing.assert_allclose((diag["weights"] >= -1e-9).all(), True)


def test_multiperiod_gap_constraint_forces_funding():
    from emfin_v2.toolbox.liabilities import optimization_multiperiod

    paths, prices = _steady_paths()
    n_scen, n_steps, _ = paths.shape
    mm_growth = np.tile(1.001 ** np.arange(1, n_steps + 1), (n_scen, 1))
    # liability larger than any plausible wealth at step 2 -> infeasible gap
    # budget zero unless the allocation keeps value high early
    alloc, diag = optimization_multiperiod(
        paths, prices, wealth=1e6,
        liability_scenarios=np.full((n_scen, 1), 5e5), payout_steps=np.array([2]),
        liability_base=np.array([5e5]), mm_growth_paths=mm_growth,
        risk_tolerance=5e4, confidence_level=0.95, gamma_loss=0.5, gamma_shortfall=0.0,
        n_optimization_scenarios=n_scen,
    )
    value_at_2 = (paths[:, 1, :] / prices) @ diag["weights"] * 1e6
    # with a zero gap budget, wealth at the due date must cover the payout
    assert value_at_2.min() >= 5e5 - 1e-3 * 5e5


def test_multiperiod_metrics_per_date():
    from emfin_v2.toolbox.liabilities import multiperiod_gap_metrics

    values = np.array([[100.0, 110.0, 120.0], [90.0, 95.0, 130.0]])
    liabilities = np.array([[100.0, 100.0], [100.0, 100.0]])
    steps = np.array([1, 3])
    growth = np.ones((2, 3))
    m = multiperiod_gap_metrics(values, liabilities, steps, growth, 0.95)
    np.testing.assert_allclose(m.shortfall_probability, [0.5, 1.0])
    assert m.shortfall_cvar[0] == pytest.approx(10.)
    assert m.shortfall_cvar[1] == pytest.approx(80.)
    # terminal net = final value minus each payout (growth factors are 1)
    np.testing.assert_allclose(m.terminal_net, [120.0 - 200.0, 130.0 - 200.0])


def test_multiperiod_rejects_misaligned_inputs():
    from emfin_v2.toolbox.liabilities import optimization_multiperiod

    paths, prices = _steady_paths()
    n_scen, n_steps, _ = paths.shape
    mm_growth = np.tile(1.001 ** np.arange(1, n_steps + 1), (n_scen, 1))
    with np.testing.assert_raises(ValueError):
        # payout step beyond the path length
        optimization_multiperiod(
            paths, prices, wealth=1e6,
            liability_scenarios=np.ones((n_scen, 1)), payout_steps=np.array([n_steps + 5]),
            liability_base=np.array([1.0]), mm_growth_paths=mm_growth,
            risk_tolerance=5e4, confidence_level=0.95, gamma_loss=0.5, gamma_shortfall=1.0,
            n_optimization_scenarios=n_scen,
        )


def test_money_market_handles_short_series():
    import pandas as pd
    from emfin_v2.toolbox import moneymarket

    # two observations -> one return; the diff alignment must not crash
    mm = moneymarket.money_market_weekly_returns(pd.Series([0.04, 0.05]))
    assert len(mm) == 1
    np.testing.assert_allclose(mm.iloc[0], 0.04 / 52.0 - 0.25 * 0.01, rtol=1e-12)


def test_crra_tolerance_tracks_surplus_ratio():
    from emfin_v2.toolbox.liabilities import crra_scaled_tolerance

    base, f0 = 2_500_000.0, 0.10
    assert crra_scaled_tolerance(base, f0, f0) == base  # reference point is identity
    richer = crra_scaled_tolerance(base, 0.20, f0)
    poorer = crra_scaled_tolerance(base, 0.05, f0)
    assert poorer < base < richer  # risk capacity falls with the funding ratio
    assert richer == 2 * base and poorer == 0.5 * base  # proportional, like CRRA
    # negative surplus floors instead of producing a negative tolerance
    assert crra_scaled_tolerance(base, -0.5, f0) > 0


def test_centered_exponential_ce_matches_logsumexp_value():
    from scipy.special import logsumexp
    samples, prices = _toy_market(n=1000)
    alloc, diag = liab.optimization_liability_aware(
        samples, prices, 1e6, 950_000, 50_000, 0.95, 0.2, 0.2)
    net = samples @ alloc - 950_000
    expected = -50_000 * (logsumexp(-net / 50_000) - np.log(len(net)))
    assert diag['ce_in_solver'] == pytest.approx(expected, abs=0.1)


def test_cml_budget_detects_intermediate_losses_and_covers_mixtures():
    from emfin_v2.toolbox.mpep import cml_of_paths
    n=200
    # All terminal risky outcomes recover, but half lose 30% mid-path.
    paths=np.ones((n,2,2))
    paths[:100,0,0]=.7
    paths[:,1,0]=1.08
    paths[:,:,1]=1.001
    stress=np.r_[np.full(100,.009),np.full(100,.001)]
    a,diag=liab.optimization_multiperiod(
        market_paths=paths,prices_vector=np.ones(2),wealth=1e6,
        liability_scenarios=np.zeros((n,1)),payout_steps=np.array([2]),liability_base=np.array([1.]),
        mm_growth_paths=np.ones((n,2)),risk_tolerance=1e6,confidence_level=.8,
        gamma_loss=.2,gamma_shortfall=1.,cml_budget=.06,stress_probabilities=[stress])
    w=a/1e6
    assert w[0] <= .061/.301 + 1e-5
    losses=np.maximum(0.,1.-paths@w).max(1)
    for mix in (0.,.2,.7,1.):
        p=(1-mix)*np.full(n,1/n)+mix*stress
        assert cml_of_paths(losses,p,.8) <= .06001


def test_second_payout_counts_prior_withdrawals():
    values=np.full((20,2),100.)
    payouts=np.tile([60.,60.],(20,1))
    m=liab.multiperiod_gap_metrics(values,payouts,np.array([1,2]),np.ones((20,2)),.95)
    np.testing.assert_allclose(m.shortfall_cvar,[0.,20.])
    np.testing.assert_allclose(m.terminal_net,-20.)


def test_same_date_payouts_are_not_double_funded():
    values=np.full((20,1),100.)
    payouts=np.tile([60.,60.],(20,1))
    m=liab.multiperiod_gap_metrics(values,payouts,np.array([1,1]),np.ones((20,1)),.95)
    np.testing.assert_allclose(m.shortfall_cvar,[0.,20.])
