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


def _losses_and_level(loss_samples, confidence_level):
    losses=np.asarray(loss_samples,dtype=float).ravel()
    if not len(losses) or not np.isfinite(losses).all() or not np.isscalar(confidence_level) or not np.isfinite(confidence_level) or not 0<=confidence_level<1:
        raise ValueError('finite nonempty losses and confidence in [0,1) required')
    return np.sort(losses)


def empirical_cvar(loss_samples: np.ndarray, confidence_level: float) -> float:
    """CVaR (expected shortfall) of the empirical loss distribution at level c.

    Exact for any sample count: sorts the losses, takes the worst
    ceil((1-c)N) atoms, and gives the straddling atom its fractional weight.
    """
    losses = _losses_and_level(loss_samples, confidence_level)
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
    """Generalized inverse empirical CDF, not an interpolated artificial loss.

    VaR_c = inf{x: F_n(x)>=c}; use the minimum observed loss at c=0.
    Meucci (2005), section5.5, defines quantiles through the inverse CDF.
    This convention preserves probability atoms used by the ES evaluator.
    """
    losses = _losses_and_level(loss_samples, confidence_level)
    index=max(0,int(np.searchsorted(np.arange(1,len(losses)+1)/len(losses),confidence_level,side='left')))
    return float(losses[index])
