"""Empirical, regime-aware judging.

The parametric judge (fresh Gaussian/Student-t draws around the estimated
moments) is the right benchmark for a parametric truth, but BY
CONSTRUCTION it cannot reward a better prior: FFR/TSDR/shrinkage tilts
only add estimation noise under it.  This module provides the complement:
judge scenarios resampled from REAL history through the empirical Markov
chain (toolbox/tsdr.py with flat per-state vectors - no time decay, so
the judge is the empirical process itself, not the prior).  Regime
persistence and fat tails present in history are therefore present in the
judging.

Honest label, always printed with the table: the empirical judge OVERLAPS
the estimation window, so it is an in-sample-overlapping evaluation -
valid for relative comparison between allocations (all face the same
judge) and for tail realism, NOT a substitute for true out-of-sample
evaluation (the walk-forward cross-validation provides that).
"""

from __future__ import annotations

import numpy as np

from emfin_capstone.toolbox import tsdr

FLAT_HALF_LIFE = 1e12  # effectively no time decay: judge = empirical process


def empirical_horizon_invariants(invariants: np.ndarray, states: np.ndarray,
                                 n_scenarios: int, n_steps: int, initial_state: int,
                                 seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Summed horizon invariants from the empirical Markov chain.

    Returns (horizon invariants (n_scenarios, n_assets), entered_high mask
    (n_scenarios,)) where the mask marks paths that visited the highest
    state at least once - the regime split for the judge table.
    """
    pv = tsdr.state_probability_vectors(states, half_life=FLAT_HALF_LIFE)
    paths, state_paths = tsdr.resample_invariant_paths(
        invariants, states, pv, n_scenarios, n_steps, initial_state, seed)
    high_label = pv.shape[0] - 1
    entered_high = (state_paths == high_label).any(axis=1) \
        if high_label > 0 else np.zeros(n_scenarios, dtype=bool)
    return paths.sum(axis=1), entered_high
