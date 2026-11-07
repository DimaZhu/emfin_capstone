"""SAA optimism measurement: in-solver vs held-out certainty equivalent.

The optimizer exploits the noise in its own scenario set, so the CE it
reports in-solver is biased up relative to what the same allocation earns
on fresh draws.  Quantify it: solve on K independent scenario sets drawn
from the SAME prior, evaluate every resulting allocation on ONE large
shared held-out set, and report the gap with a t-confidence interval
across the K replicates.  A 1/N allocation row serves as the control:
it fits nothing, so its gap should be statistically indistinguishable
from zero on average. A particular CI need not cover zero. The CI is
conditional on the common evaluation set and omits its Monte Carlo error.
"""

from __future__ import annotations

import numpy as np
from scipy import stats as _stats


def t_ci(values: np.ndarray, confidence: float = 0.95) -> tuple[float, float, float]:
    """Mean and t-confidence interval of i.i.d. replicates."""
    v = np.asarray(values, dtype=float).ravel()
    if len(v) < 2:
        raise ValueError("need at least 2 replicates for a CI")
    mean = float(v.mean())
    half = float(_stats.t.ppf(0.5 + confidence / 2, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v)))
    return mean, mean - half, mean + half


def optimism_gaps(in_sample_ce: dict[str, np.ndarray],
                  held_out_ce: dict[str, np.ndarray]) -> dict[str, dict[str, float]]:
    """Per-method optimism gap (in-solver minus held-out CE) with 95% CI.

    Both dicts map method name -> array of per-replicate CEs; keys and
    replicate counts must match between the two.
    """
    if set(in_sample_ce) != set(held_out_ce):
        raise ValueError("in-sample and held-out method sets differ")
    out = {}
    for name, ce_in in in_sample_ce.items():
        ce_out = held_out_ce[name]
        if len(ce_in) != len(ce_out):
            raise ValueError(f"replicate count mismatch for {name}")
        mean, lo, hi = t_ci(np.asarray(ce_in) - np.asarray(ce_out))
        out[name] = {"gap_mean": mean, "gap_lo": lo, "gap_hi": hi}
    return out
