"""Tests for toolbox/meucci_liquidity.py (Meucci 2012, FAJ 68(6))."""

import numpy as np
import pytest
from scipy import stats

from emfin_capstone.toolbox import meucci_liquidity as ml

PARAMS = [
    ml.MeucciLiquidityParams(alpha=0.001, beta=0.5, delta=1e-4, ann_vol=0.20, adv=1e6),
    ml.MeucciLiquidityParams(alpha=0.002, beta=0.7, delta=2e-4, ann_vol=0.25, adv=5e5),
]
CORR = np.array([[1.0, 0.3], [0.3, 1.0]])


class TestAdjustmentMoments:
    def test_zero_amounts_zero_adjustment(self):
        mu, sigma = ml.adjustment_moments(
            np.zeros((5, 2)), np.array([100.0, 50.0]), PARAMS, CORR, gamma=0.9)
        np.testing.assert_allclose(mu, 0.0)
        np.testing.assert_allclose(sigma, 0.0)

    def test_expected_cost_negative_and_superlinear(self):
        e = np.array([100.0, 50.0])
        mu1, _ = ml.adjustment_moments(np.full((1, 2), 1000.0), e, PARAMS, CORR, 0.9)
        mu2, _ = ml.adjustment_moments(np.full((1, 2), 2000.0), e, PARAMS, CORR, 0.9)
        assert mu1[0] < 0  # liquidation costs money on average
        # square-root impact makes the cost more than proportional in size
        assert mu2[0] / mu1[0] > 2.0

    def test_state_stress_worsens_cost(self):
        e = np.array([100.0, 50.0])
        dh = np.full((2, 2), 1000.0)
        mu, sigma = ml.adjustment_moments(dh, e, PARAMS, CORR, 0.9,
                                          state_multiplier=np.array([1.0, 3.0]))
        assert mu[1] < mu[0]  # stressed scenario costs more
        assert sigma[1] > sigma[0]

    def test_gamma_one_gives_perfect_correlation(self):
        e = np.array([100.0, 50.0])
        dh = np.full((1, 2), 1000.0)
        # perfect correlation => portfolio sigma is the sum of asset sigmas
        mu, sig_full = ml.adjustment_moments(dh, e, PARAMS, CORR, gamma=1.0)
        d = np.array([p.delta for p in PARAMS])
        v = np.array([p.adv for p in PARAMS])
        s = d * np.sqrt(v) * e * 1000.0
        assert sig_full[0] == pytest.approx(s.sum(), rel=1e-10)

    def test_invalid_gamma_raises(self):
        with pytest.raises(ValueError):
            ml.adjustment_moments(np.ones((1, 2)), np.ones(2), PARAMS, CORR, gamma=1.5)


class TestApplyMeucciLiquidity:
    def test_shape_reproducible_and_net_below_gross(self):
        rng = np.random.default_rng(0)
        prices = 100.0 * np.exp(rng.standard_normal((2000, 2)) * 0.1)
        amounts = np.full((2000, 2), 500.0)
        net_a = ml.apply_meucci_liquidity(prices, amounts, PARAMS, CORR, 0.9, seed=3)
        net_b = ml.apply_meucci_liquidity(prices, amounts, PARAMS, CORR, 0.9, seed=3)
        assert net_a.shape == prices.shape
        np.testing.assert_allclose(net_a, net_b)
        # the expected adjustment is negative (liquidation costs money), even
        # though per-scenario impact uncertainty can dominate the mean
        assert (net_a - prices).mean() < 0
        # with no impact uncertainty (delta=0) every scenario nets below gross
        no_noise = [ml.MeucciLiquidityParams(p.alpha, p.beta, 0.0, p.ann_vol, p.adv)
                    for p in PARAMS]
        net_det = ml.apply_meucci_liquidity(prices, amounts, no_noise, CORR, 0.9, seed=3)
        assert (net_det < prices).all()

    def test_zero_amounts_leave_prices_untouched(self):
        prices = np.full((10, 2), 100.0)
        net = ml.apply_meucci_liquidity(prices, np.zeros((10, 2)), PARAMS, CORR, 0.9, seed=1)
        np.testing.assert_allclose(net, prices)


class TestDensityAndScore:
    def test_density_integrates_to_one(self):
        rng = np.random.default_rng(1)
        pi = rng.standard_normal(500) * 0.1
        mu = -0.001 * np.ones(500)
        sig = 0.002 * np.ones(500)
        grid = np.linspace(-0.5, 0.5, 20001)
        f = ml.total_pnl_density(grid, pi, mu, sig)
        assert np.trapezoid(f, grid) == pytest.approx(1.0, abs=1e-3)

    def test_no_adjustment_recovers_empirical(self):
        pi = np.linspace(-0.2, 0.2, 401)
        # sigma small but grid-resolved: spikes of width ~sigma are sampled
        grid = np.linspace(-0.21, 0.21, 42001)
        f = ml.total_pnl_density(grid, pi, np.zeros(401), 2e-4 * np.ones(401))
        assert np.trapezoid(f, grid) == pytest.approx(1.0, abs=1e-3)

    def test_liquidity_score_bounds(self):
        assert ml.liquidity_score(1.0, 1.0) == pytest.approx(1.0)
        assert 0 < ml.liquidity_score(1.0, 2.0) < 1
        with pytest.raises(ValueError):
            ml.liquidity_score(-1.0, 2.0)

    def test_cvar_decomposition_adds_up(self):
        rng = np.random.default_rng(2)
        pi = rng.standard_normal(2000) * 0.05
        mu = -0.002 * np.ones(2000)
        sig = 0.003 * np.ones(2000)
        out = ml.cvar_liquidity_contribution(pi, mu, sig, confidence=0.95)
        total = out["cvar_total"]
        assert out["market_contribution"] + out["liquidity_contribution"] == pytest.approx(total)
        assert out["liquidity_contribution"] > 0  # the overlay adds tail risk
        # sanity: total CVaR of the loss exceeds the Gaussian-market-only value
        assert total > 0.05 * (stats.norm.pdf(stats.norm.ppf(0.95)) / 0.05) * 0.9
