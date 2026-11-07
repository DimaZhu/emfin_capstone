import numpy as np

from emfin_capstone.toolbox import shrinkage


def test_lw_intensity_bounds_and_pd_repair():
    rng = np.random.default_rng(1)
    # more assets than observations: sample cov is singular
    x = rng.standard_normal((5, 8))
    shrunk, delta = shrinkage.ledoit_wolf_cov(x)
    assert 0.0 < delta <= 1.0
    assert np.all(np.linalg.eigvalsh(shrunk) > 0)


def _correlated(rng, t, n=4):
    # non-identity truth (equicorrelation + heterogeneous variances) so the
    # scaled-identity target differs from the truth and intensity < 1
    cov = np.full((n, n), 0.5) + 0.5 * np.eye(n)
    cov = cov * np.outer(np.arange(1, n + 1), np.arange(1, n + 1)) * 0.1
    return rng.multivariate_normal(np.zeros(n), cov, size=t)


def test_lw_shrinks_less_with_more_data():
    rng = np.random.default_rng(2)
    _, d_small = shrinkage.ledoit_wolf_cov(_correlated(rng, 20))
    _, d_large = shrinkage.ledoit_wolf_cov(_correlated(rng, 2000))
    assert 0.0 <= d_large < d_small <= 1.0


def test_lw_ess_scales_intensity():
    rng = np.random.default_rng(3)
    x = _correlated(rng, 200)
    _, d_full = shrinkage.ledoit_wolf_cov(x, ess=200)
    _, d_thin = shrinkage.ledoit_wolf_cov(x, ess=30)
    assert d_thin > d_full


def test_mean_shrinkage_endpoints():
    mean = np.array([0.01, 0.02, 0.03])
    target = np.zeros(3)
    shrunk_no, w0 = shrinkage.shrink_mean(mean, target, t_eff=1000.0, t0=1.0)
    shrunk_all, w1 = shrinkage.shrink_mean(mean, target, t_eff=1.0, t0=1000.0)
    assert w0 < 0.01 and w1 > 0.99
    np.testing.assert_allclose(shrunk_no, mean, atol=1e-3)
    np.testing.assert_allclose(shrunk_all, target, atol=1e-3)
