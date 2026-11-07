"""Black-Litterman posterior — the benchmark's classical views benchmark.

BL is the special case of entropy pooling for a normal prior and views on
means only; the team's engine uses entropy pooling, and this module exists
so the benchmark can grade both against plain mean-variance on identical
data and identical judges.

Standard textbook form (He & Litterman 1999; Idzorek 2005):
  prior:     mu ~ N(pi, tau * Sigma),  pi = delta * Sigma * w_mkt
  views:     P mu = Q + eps,  eps ~ N(0, Omega)
  posterior mean:  [(tau Sigma)^-1 + P' Omega^-1 P]^-1 [(tau Sigma)^-1 pi + P' Omega^-1 Q]
  posterior covariance (of the mean): the same bracket inverse;
  predictive covariance: Sigma + posterior covariance.

The equilibrium prior needs market weights for the 3-ETF universe — an
exposed assumption (see docstring of ``equilibrium_prior``); the benchmark
therefore reports BL under the stated weights, and the paper should run
the sensitivity.
"""

from __future__ import annotations

import numpy as np


def equilibrium_prior(cov_matrix: np.ndarray, market_weights: np.ndarray, risk_aversion: float) -> np.ndarray:
    """Implied equilibrium returns pi = delta * Sigma * w_mkt.

    ``market_weights`` for this toy universe (three Dimensional funds) are
    a modeling input, not observable market caps of the world portfolio —
    the benchmark pins its choice and the paper reports the sensitivity.
    """
    w = np.asarray(market_weights, dtype=float).ravel()
    if not np.isclose(w.sum(), 1.0):
        raise ValueError("market weights must sum to 1")
    return risk_aversion * cov_matrix @ w


def posterior(
    cov_matrix: np.ndarray,
    prior_mean: np.ndarray,
    views_p: np.ndarray,
    views_q: np.ndarray,
    tau: float,
    omega: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """BL posterior (mean, predictive covariance).

    ``views_p``: (k, n) pick matrix — each row a view portfolio.
    ``views_q``: (k,) view returns.
    ``omega``: (k, k) view uncertainty; defaults to tau * P Sigma P'
    (the common "uncertainty proportional to prior variance of the view"
    choice, which makes BL a disciplined interpolation).
    """
    sigma = np.asarray(cov_matrix, dtype=float)
    n = sigma.shape[0]
    p = np.asarray(views_p, dtype=float).reshape(-1, n)
    q = np.asarray(views_q, dtype=float).ravel()
    if p.shape[0] != q.shape[0]:
        raise ValueError("one target per view row")
    if omega is None:
        omega = tau * p @ sigma @ p.T
    omega = np.asarray(omega, dtype=float)

    tau_sigma_inv = np.linalg.inv(tau * sigma)
    omega_inv = np.linalg.inv(omega)
    posterior_cov_mean = np.linalg.inv(tau_sigma_inv + p.T @ omega_inv @ p)
    posterior_mean = posterior_cov_mean @ (tau_sigma_inv @ prior_mean + p.T @ omega_inv @ q)
    predictive_cov = sigma + posterior_cov_mean
    return posterior_mean, predictive_cov
