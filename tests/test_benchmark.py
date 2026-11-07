import numpy as np
import pytest

from emfin_v2.toolbox import benchmark


def test_mv_picks_dominant_asset_long_only():
    # one asset with strictly better return and same risk -> full allocation
    prices = np.array([100.0, 100.0])
    mean = np.array([101.0, 102.0])
    cov = np.diag([1.0, 1.0])
    alloc = benchmark.mean_variance_allocation(mean, cov, prices, wealth=1e6, risk_tolerance=1e5)
    w = alloc * prices / 1e6
    assert w[1] == pytest.approx(1.0, abs=1e-4)


def test_mv_budget_constraint():
    prices = np.array([100.0, 100.0])
    mean = np.array([101.0, 101.0])
    cov = np.diag([1.0, 1.0])
    alloc = benchmark.mean_variance_allocation(mean, cov, prices, wealth=1e6, risk_tolerance=1e5)
    assert (alloc * prices).sum() == pytest.approx(1e6, rel=1e-6)


def test_judge_is_deterministic_and_paired():
    rng = np.random.default_rng(0)
    prices = np.array([100.0, 100.0])
    mean = np.array([101.0, 100.5])
    cov = np.diag([4.0, 1.0])
    alloc_a = benchmark.mean_variance_allocation(mean, cov, prices, 1e6, 1e5)
    alloc_b = np.array([0.0, 1e4])  # all in asset 2

    def sampler(seed):
        r = np.random.default_rng(seed)
        return prices * np.exp(r.normal([0.01, 0.005], [0.02, 0.01], size=(2000, 2)))

    allocations = {"risky": alloc_a, "safe": alloc_b}
    r1 = benchmark.judge_allocations(allocations, sampler, 3, 100, 1e6, 1e5)
    r2 = benchmark.judge_allocations(allocations, sampler, 3, 100, 1e6, 1e5)
    np.testing.assert_array_equal(r1.ce_by_seed, r2.ce_by_seed)  # pinned seeds
    s = r1.summary()
    assert set(s["paired_diff_vs_risky"]) == {"risky", "safe"}
    assert s["paired_diff_vs_risky"]["risky"]["mean"] == 0.0
    # higher drift asset wins on average under the same draws
    assert r1.ce_by_seed[:, 0].mean() > r1.ce_by_seed[:, 1].mean()
