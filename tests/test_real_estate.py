"""Tests for toolbox/real_estate.py - all validation is on synthetic data
with known truth until a licensed/open source lands (see module docstring)."""

import numpy as np
import pytest

from emfin_capstone.toolbox import real_estate as re_


class TestUnsmoothing:
    def test_geltner_recovers_truth_from_ar1_smoothing(self):
        rng = np.random.default_rng(0)
        r = rng.standard_normal(400) * 0.03
        c = 0.6
        o = np.empty(401)
        o[0] = 0.0
        for t in range(1, 401):
            o[t] = (1 - c) * r[t - 1] + c * o[t - 1]
        rec = re_.geltner_unsmooth(o, c)
        np.testing.assert_allclose(rec[1:], r[1:], atol=1e-10)

    def test_fgw_zeroes_lag1_autocorr(self):
        rng = np.random.default_rng(1)
        r = rng.standard_normal(500) * 0.03
        c = 0.5
        o = np.empty(501)
        o[0] = 0.0
        for t in range(1, 501):
            o[t] = (1 - c) * r[t - 1] + c * o[t - 1]
        unsmoothed, c_hat = re_.fgw_unsmooth(o)
        acf1 = np.corrcoef(unsmoothed[1:], unsmoothed[:-1])[0, 1]
        assert abs(acf1) < 0.05
        # the zero-ACF point need not equal the recursive smoothing weight:
        # FGW targets zero autocorrelation, not exact parameter recovery
        assert c_hat == pytest.approx(c, abs=0.15)

    def test_unsmoothing_raises_vol(self):
        rng = np.random.default_rng(2)
        r = rng.standard_normal(500) * 0.03
        c = 0.6
        o = np.empty(501)
        o[0] = 0.0
        for t in range(1, 501):
            o[t] = (1 - c) * r[t - 1] + c * o[t - 1]
        rec = re_.geltner_unsmooth(o, c)
        assert rec.std() > o[1:].std() * 1.5  # smoothing understates variance

    def test_invalid_smoothing_raises(self):
        with pytest.raises(ValueError):
            re_.geltner_unsmooth(np.arange(10.0), 1.0)


class TestStateSpace:
    def test_kalman_recovers_latent_path(self):
        obs, truth = re_.simulate_smoothed_observations(
            n_periods=240, mu=0.01, rho=0.3, q=0.0004,
            smoothing=(0.6, 0.3), obs_var=(1e-5, 1e-5), seed=3)
        model = re_.LatentReturnModel(mu=0.01, rho=0.3, q=0.0004,
                                      smoothing=(0.6, 0.3), obs_var=(1e-5, 1e-5))
        out = re_.kalman_smooth(obs, model)
        latent = out["latent_smoothed"]
        corr = np.corrcoef(latent, truth)[0, 1]
        assert corr > 0.9  # smoothed estimate tracks the known truth
        # multi-observer beats the naive single raw observer
        raw_corr = np.corrcoef(obs[:, 0], truth)[0, 1]
        assert corr > raw_corr

    def test_missing_observations_handled(self):
        obs, truth = re_.simulate_smoothed_observations(
            120, 0.01, 0.2, 0.0004, (0.5, 0.2), (1e-5, 1e-5), seed=4)
        obs[::7, 1] = np.nan  # thin quarters for the second observer
        model = re_.LatentReturnModel(0.01, 0.2, 0.0004, (0.5, 0.2), (1e-5, 1e-5))
        out = re_.kalman_smooth(obs, model)
        assert np.isfinite(out["latent_smoothed"]).all()

    def test_moment_fit_plausible(self):
        obs, _ = re_.simulate_smoothed_observations(
            400, 0.01, 0.0, 0.0004, (0.55,), (1e-5,), seed=5)
        model = re_.moment_fit(obs)
        assert model.mu == pytest.approx(0.01, abs=0.01)
        assert 0.2 < model.smoothing[0] < 0.9


class TestDiagnostics:
    def test_iid_residual_passes_ljung_box(self):
        rng = np.random.default_rng(6)
        x = rng.standard_normal(400)
        assert re_.ljung_box(x, 10)["p_value"] > 0.01

    def test_autocorrelated_series_fails_ljung_box(self):
        rng = np.random.default_rng(7)
        e = rng.standard_normal(400)
        x = np.convolve(e, [0.8, 0.5])[:400]
        assert re_.ljung_box(x, 10)["p_value"] < 0.01

    def test_arch_lm_detects_vol_clustering(self):
        rng = np.random.default_rng(8)
        vol = 1.0 + np.arange(400) % 50 / 25  # deterministic vol cycles
        x = rng.standard_normal(400) * vol
        assert re_.arch_lm(x, 5)["p_value"] < 0.01
        x_iid = rng.standard_normal(400)
        assert re_.arch_lm(x_iid, 5)["p_value"] > 0.01


class TestBootstrap:
    def test_block_bootstrap_shape_and_dependence(self):
        rng = np.random.default_rng(9)
        d = 2
        common = rng.standard_normal(300)
        x = np.column_stack([common + 0.1 * rng.standard_normal(300),
                             common + 0.1 * rng.standard_normal(300)])
        scen = re_.block_bootstrap_with_parameter_uncertainty(
            x, horizon_periods=4, n_scenarios=5000, block_length=12, seed=10)
        assert scen.shape == (5000, d)
        # cross-dependence survives block resampling
        assert np.corrcoef(scen[:, 0], scen[:, 1])[0, 1] > 0.8

    def test_parameter_uncertainty_changes_scenarios(self):
        rng = np.random.default_rng(11)
        base = rng.standard_normal((300, 1)) * 0.02
        smoothings = np.array([[0.2], [0.6], [0.8]])
        def refit(c):
            return base * (1 + c)  # stand-in: higher smoothing -> larger residual scale
        scen = re_.block_bootstrap_with_parameter_uncertainty(
            base, 4, 3000, 12, 12, param_draws=(smoothings,), refit_fn=refit)
        assert scen.shape == (3000, 1)
        # batches under different parameters differ in scale
        assert scen.std() > base.std()
