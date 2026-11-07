"""Empirical tail statistics with exact fractional-atom weighting.

``scenario_market.empirical_cvar`` raises whenever (1-c)*N is not an
integer — correct but brittle for liability metrics, where the shortfall
sample count is not ours to choose.  This is the Rockafellar & Uryasev
(2002) discrete form: the straddling atom enters with fractional weight.

Reference:
    Rockafellar & Uryasev (2002), "Conditional Value-at-Risk for General
    Loss Distributions", JBF 26(7), 1443-1471.
"""

from __future__ import annotations

import numpy as np


def empirical_cvar(loss_samples: np.ndarray, confidence_level: float) -> float:
    """CVaR (expected shortfall) of the empirical loss distribution at level c.

    Exact for any sample count: sorts the losses, takes the worst
    ceil((1-c)N) atoms, and gives the straddling atom its fractional weight.
    """
    losses = np.sort(np.asarray(loss_samples, dtype=float).ravel())
    n = len(losses)
    tail_mass = (1 - confidence_level) * n
    if tail_mass <= 0:
        raise ValueError("confidence level too close to 1 for this sample size")
    full = int(np.floor(tail_mass))
    frac = tail_mass - full
    # worst `full` losses, plus fractional weight on the next one
    cvar = losses[n - full:].sum() if full > 0 else 0.0
    if frac > 1e-12:
        cvar += frac * losses[n - full - 1]
    return float(cvar / tail_mass)


def empirical_var(loss_samples: np.ndarray, confidence_level: float) -> float:
    """VaR as the quantile of the loss distribution (upper linear interpolation)."""
    losses = np.sort(np.asarray(loss_samples, dtype=float).ravel())
    n = len(losses)
    pos = confidence_level * (n - 1)
    lo = int(np.floor(pos))
    frac = pos - lo
    if lo + 1 >= n:
        return float(losses[-1])
    return float(losses[lo] * (1 - frac) + losses[lo + 1] * frac)
