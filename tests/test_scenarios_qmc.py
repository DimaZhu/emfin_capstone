"""Quasi-random scenario generation: the measured tail-noise reduction."""

import numpy as np
from scipy.stats import norm, qmc

from emfin_capstone.toolbox.risk_stats import empirical_cvar


def _sobol(mean, cov, n, seed):
    chol = np.linalg.cholesky(cov)
    sob = qmc.Sobol(len(mean), scramble=True, seed=seed)
    m = 1 << int(np.ceil(np.log2(n)))
    u = np.clip(sob.random_base2(int(np.log2(m)))[:n], 1e-12, 1 - 1e-12)
    return mean + norm.ppf(u) @ chol.T


def test_sobol_scenarios_match_target_moments():
    mean = np.array([0.01, -0.02, 0.03])
    cov = np.array([[0.04, 0.01, 0.0], [0.01, 0.09, 0.02], [0.0, 0.02, 0.01]])
    x = _sobol(mean, cov, 100_000, seed=5)
    np.testing.assert_allclose(x.mean(axis=0), mean, atol=2e-3)
    np.testing.assert_allclose(np.cov(x.T), cov, atol=2e-3)


def test_sobol_cuts_cvar_estimator_noise():
    mean = np.array([0.01, -0.02])
    cov = np.array([[0.04, 0.01], [0.01, 0.09]])
    rng = np.random.default_rng(3)
    plain, sobol = [], []
    for _ in range(100):
        d = rng.multivariate_normal(mean, cov, size=10_000)
        plain.append(empirical_cvar(-(d[:, 0] + d[:, 1]), 0.95))
        ds = _sobol(mean, cov, 8192, seed=int(rng.integers(1e9)))
        sobol.append(empirical_cvar(-(ds[:, 0] + ds[:, 1]), 0.95))
    # measured ~0.03 on this pipeline; assert a decisive reduction
    assert np.std(sobol) < 0.2 * np.std(plain)
    # and no bias: same expectation as the pseudo-random estimator
    assert abs(np.mean(sobol) - np.mean(plain)) < 0.2 * np.std(plain)


def test_student_t_scenarios_fat_tails_matched_covariance():
    nu = 8.0
    rng = np.random.default_rng(9)
    cov = np.array([[0.04, 0.01], [0.01, 0.09]])
    chol = np.linalg.cholesky(cov)
    z = rng.standard_normal((200_000, 2)) @ chol.T
    chi2 = rng.chisquare(nu, size=(200_000, 1))
    t = z / np.sqrt(chi2 / nu) * np.sqrt((nu - 2.0) / nu)
    # covariance preserved by the scaling
    np.testing.assert_allclose(np.cov(t.T), cov, atol=2e-3)
    # excess kurtosis of a t_nu is 6/(nu-4); marginals show it
    from scipy.stats import kurtosis
    k = kurtosis(t[:, 0])
    assert abs(k - 6.0 / (nu - 4.0)) < 0.4
