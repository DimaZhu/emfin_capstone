"""Shrinkage estimators for the moment inputs - estimation-error control.

The external review's point: raw sample means from ~150 weekly observations
drive the allocation, and a mean-variance benchmark built on them is a
straw man.  Two classical, communicable shrinkages:

* Covariance: Ledoit-Wolf (2004) toward the scaled identity, with the
  closed-form optimal intensity.  For weighted moment estimates (the FFR
  prior) the effective sample size replaces the raw count in the intensity
  formula - documented approximation.
* Mean: Bayes-Stein style toward structural targets with intensity
  w = T0 / (T0 + T_eff): equity log-return means shrink toward their grand
  mean (Jorion 1986), rate and spread CHANGES shrink toward zero (the
  standard unpredictability prior), and the money-market sleeve is left
  unshrunk - its mean is carry, which is structural, not estimated noise.

Both shrinkages make the vanilla MV benchmark fair: it now optimizes the
same shrunk moments the EP allocations are built on.
"""

from __future__ import annotations

import numpy as np


def ledoit_wolf_cov(samples: np.ndarray, ess: float | None = None) -> tuple[np.ndarray, float]:
    """Ledoit-Wolf shrunk covariance and the intensity used.

    ``samples``: (T, n) observations.  ``ess``: effective sample size for
    weighted estimators (defaults to T).  Returns (shrunk_cov, delta).
    """
    x = np.asarray(samples, dtype=float)
    t, n = x.shape
    if t < 2:
        raise ValueError("need at least two observations")
    t_eff = float(ess) if ess is not None else float(t)
    if t_eff < 2:
        raise ValueError("effective sample size too small for shrinkage")
    # Shrink in standardized coordinates. Identity shrinkage on raw equity,
    # yield and money-market invariants would depend on their chosen units
    # and could manufacture large volatility in the cash sleeve.
    scales = x.std(axis=0, ddof=1)
    if not np.isfinite(x).all() or np.any(scales <= 0):
        raise ValueError("finite nondegenerate columns required")
    x = (x - x.mean(0)) / scales
    s = np.atleast_2d(np.cov(x, rowvar=False, ddof=1))
    m = float(np.trace(s) / n)
    f = m * np.eye(n)
    d2 = float(((s - f) ** 2).sum() / n)
    centered = x - x.mean(axis=0)
    # b_bar^2 = average squared Frobenius distance of the single-observation
    # covariance estimates from s (Ledoit-Wolf 2004, scaled-identity target)
    b2 = 0.0
    for row in centered:
        outer = np.outer(row, row)
        b2 += float(((outer - s) ** 2).sum())
    b2 /= (t_eff ** 2) * n
    delta = min(b2 / d2, 1.0) if d2 > 0 else 1.0
    return ((1.0 - delta) * s + delta * f) * np.outer(scales,scales), delta


def shrink_mean(
    mean: np.ndarray,
    targets: np.ndarray,
    t_eff: float,
    t0: float,
) -> tuple[np.ndarray, float]:
    """Bayes-Stein style mean shrinkage: (1-w) mean + w target.

    w = T0 / (T0 + T_eff): the prior target is worth T0 observations.
    Returns (shrunk_mean, w).
    """
    if t0 < 0 or t_eff <= 0:
        raise ValueError("t0 must be >= 0 and t_eff > 0")
    w = t0 / (t0 + t_eff)
    return (1.0 - w) * np.asarray(mean, dtype=float) + w * np.asarray(targets, dtype=float), w
