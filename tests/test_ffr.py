"""Tests for toolbox/ffr.py - Fully Flexible Resampling priors."""

import numpy as np
import pytest

from emfin_v2.toolbox import entropy_pooling as ep
from emfin_v2.toolbox import ffr


class TestTimeDecayWeights:
    def test_sums_to_one_and_decays(self):
        w = ffr.time_decay_weights(200, half_life=52)
        assert w.sum() == pytest.approx(1.0)
        # most recent observation heaviest; monotone non-increasing into the past
        assert np.all(np.diff(w) >= 0)
        # one half-life back carries half the weight of the latest
        assert w[-1 - 52] == pytest.approx(w[-1] / 2, rel=1e-12)

    def test_infinite_half_life_is_uniform(self):
        w = ffr.time_decay_weights(50, half_life=np.inf)
        np.testing.assert_allclose(w, np.full(50, 0.02))

    def test_invalid_half_life_raises(self):
        with pytest.raises(ValueError):
            ffr.time_decay_weights(10, half_life=0.0)


class TestKernelWeights:
    def test_peak_at_target(self):
        state = np.linspace(0.1, 0.3, 41)
        w = ffr.kernel_weights(state, target=0.2, bandwidth=0.05)
        assert w.sum() == pytest.approx(1.0)
        assert np.argmax(w) == 20  # the observation at the target
        # symmetric decay around the target
        assert w[19] == pytest.approx(w[21], rel=1e-12)

    def test_wide_bandwidth_recovers_uniform(self):
        state = np.linspace(0.1, 0.3, 30)
        w = ffr.kernel_weights(state, target=0.2, bandwidth=1e6)
        np.testing.assert_allclose(w, np.full(30, 1 / 30), rtol=1e-6)


class TestCombineAndESS:
    def test_combine_is_product_normalized(self):
        a = ffr.time_decay_weights(10, 5)
        b = np.full(10, 0.1)
        c = ffr.combine_weights(a, b)
        np.testing.assert_allclose(c, a)  # uniform factor changes nothing

    def test_ess_bounds(self):
        assert ffr.effective_sample_size(np.full(100, 0.01)) == pytest.approx(100.0)
        one_hot = np.zeros(100); one_hot[3] = 1.0
        assert ffr.effective_sample_size(one_hot) == pytest.approx(1.0)

    def test_combine_zero_mass_raises(self):
        with pytest.raises(ValueError):
            ffr.combine_weights(np.array([1.0, 0.0]), np.array([0.0, 1.0]))


class TestWeightedMoments:
    def test_uniform_matches_sample_moments(self):
        rng = np.random.default_rng(7)
        x = rng.standard_normal((500, 3)) @ np.array([[1.0, 0.3, 0.0], [0.0, 1.0, 0.2], [0.0, 0.0, 1.0]])
        w = np.full(500, 1 / 500)
        mean, cov = ffr.weighted_moments(x, w)
        np.testing.assert_allclose(mean, x.mean(axis=0), atol=1e-12)
        np.testing.assert_allclose(cov, np.cov(x, rowvar=False, ddof=1), rtol=1e-10)

    def test_weights_shift_moments(self):
        x = np.arange(100.0).reshape(-1, 1)
        w = ffr.time_decay_weights(100, half_life=10)
        mean, _ = ffr.weighted_moments(x, w)
        assert mean[0] > x.mean()  # recency tilts toward the high end


class TestBootstrap:
    def test_reproducible_and_shaped(self):
        rng = np.random.default_rng(1)
        x = rng.standard_normal((260, 4)) * 0.02
        w = ffr.time_decay_weights(260, 104)
        a = ffr.bootstrap_horizon_invariants(x, w, 13, 1000, seed=5)
        b = ffr.bootstrap_horizon_invariants(x, w, 13, 1000, seed=5)
        assert a.shape == (1000, 4)
        np.testing.assert_array_equal(a, b)

    def test_uniform_bootstrap_recovers_history_moments(self):
        rng = np.random.default_rng(2)
        x = rng.standard_normal((5000, 2)) * np.array([0.02, 0.01]) + np.array([0.001, -0.002])
        w = np.full(5000, 1 / 5000)
        scen = ffr.bootstrap_horizon_invariants(x, w, 13, 200_000, seed=6)
        np.testing.assert_allclose(scen.mean(axis=0), 13 * x.mean(axis=0), atol=2e-4)
        np.testing.assert_allclose(scen.std(axis=0), np.sqrt(13) * x.std(axis=0), rtol=2e-2)

    def test_heavy_conditioning_still_valid(self):
        rng = np.random.default_rng(3)
        x = rng.standard_normal((260, 2)) * 0.02
        state = np.linspace(-1, 1, 260)
        prior = ffr.build_ffr_prior(260, half_life=52, state=state, target=1.0,
                                    bandwidth=0.2, state_name="toy")
        scen = ffr.bootstrap_horizon_invariants(x, prior.weights, 13, 500, seed=8)
        assert scen.shape == (500, 2)
        assert prior.ess < 260 / 3  # aggressive conditioning burns sample


class TestFFRWithEntropyPooling:
    def test_ep_tilts_weighted_prior_and_views_hold(self):
        rng = np.random.default_rng(4)
        x = rng.standard_normal((300, 1)) * 0.02
        w = ffr.time_decay_weights(300, 52)
        scen = ffr.bootstrap_horizon_invariants(x, w, 13, 20_000, seed=9)
        view = ep.mean_view(scen, 0, target_mean=0.05)
        pooled = ep.joint_entropy_pooling(len(scen), [view])
        assert pooled.per_view_achieved[0][0] == pytest.approx(0.05, abs=1e-8)
        assert pooled.effective_n_scenarios_ratio < 1.0
