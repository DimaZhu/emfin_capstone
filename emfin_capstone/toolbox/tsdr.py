"""Time- and State-Dependent Resampling (TSDR) path generation.

Kristensen & Vorobets (2025), "Time- and State-Dependent Resampling"
(SSRN 5117589; public summary at antonvorobets.substack.com/p/
time-and-state-dependent-resampling).  The full definitions PDF is
access-gated and the accompanying code is GPL-3.0 (fortitudo.tech) -
NEITHER was consulted.  This module implements the construction from the
public descriptions: several weighted probability vectors (one per state)
governed by an implicit Markov chain, combining exponential time decay
with a crisp state classification (the FFR special case; the MPEP case
study uses the 25%/90% quantiles and half-life tau = T/2, mirrored here
as defaults).

Construction (all from public sources):
* classify the state variable into low/mid/high states by quantiles;
* per-state probability vector p_k over historical observation times,
  proportional to (exponential time decay) x (state indicator);
* path generation: conditional on the current state k, draw a historical
  time t ~ p_k, emit the FOLLOWING week's invariant, and move to the
  state realized at t+1 - the empirical successor.  The chain on
  (state, invariant) is Markov by construction with a stationary distribution when initialized in an invariant
  state distribution. An arbitrary initial state is not strictly stationary;
  decay-weighted transitions need not preserve the raw empirical marginal.

Contrast with toolbox/ffr.py: FFR computes ONE state-conditioned weight
vector for moment estimation / one-shot bootstrap.  TSDR generates PATHS
step by step, so the time-series dependence (vol regime transitions)
survives into the simulated paths instead of being averaged out.
"""

from __future__ import annotations

import numpy as np

from emfin_capstone.toolbox import ffr

STATE_NAMES = ("low", "mid", "high")


def state_labels(state_var: np.ndarray, quantiles: tuple[float, float] = (0.25, 0.90)) -> np.ndarray:
    """Classify a state series into 0=low / 1=mid / 2=high by quantiles."""
    s = np.asarray(state_var, dtype=float)
    if s.ndim != 1 or len(s) < 10:
        raise ValueError("state_var must be a 1-D series with at least 10 observations")
    q_lo, q_hi = np.quantile(s, quantiles)
    return np.digitize(s, [q_lo, q_hi]).astype(int)


def state_probability_vectors(states: np.ndarray, half_life: float) -> np.ndarray:
    """(K, T) array of per-state probability vectors.

    p_k[t] ∝ time_decay[t] * 1[states[t] == k] - the crisp-conditioning FFR
    special case.  A state with no observations raises (the classification
    above cannot produce one for the mid state, but extreme inputs can).
    """
    st = np.asarray(states, dtype=int)
    decay = ffr.time_decay_weights(len(st), half_life)
    k_states = int(st.max()) + 1
    out = np.zeros((k_states, len(st)))
    for k in range(k_states):
        w = decay * (st == k)
        if w.sum() <= 0:
            raise ValueError(f"state {k} has no observations to resample from")
        out[k] = w / w.sum()
    return out


def resample_invariant_paths(invariants: np.ndarray, states: np.ndarray,
                             prob_vectors: np.ndarray, n_scenarios: int, n_steps: int,
                             initial_state: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Markov-chain resampling of weekly invariants into paths.

    Conditional on the current state k, draw t ~ p_k over times with a
    valid successor, emit invariants[t + 1], and transition to
    states[t + 1].  Returns (weekly invariant paths (S, H, I), state
    paths (S, H) of the state ENTERED at each step).
    """
    inv = np.asarray(invariants, dtype=float)
    st = np.asarray(states, dtype=int)
    pv = np.asarray(prob_vectors, dtype=float)
    if len(inv) != len(st) or pv.shape[1] != len(st):
        raise ValueError("invariants, states and probability vectors must share the time axis")
    valid = np.arange(len(st) - 1)  # need a successor at t+1
    rng = np.random.default_rng(seed)
    s, i = n_scenarios, inv.shape[1]
    paths = np.empty((s, n_steps, i))
    state_paths = np.empty((s, n_steps), dtype=int)
    current = np.full(s, int(initial_state), dtype=int)
    for h in range(n_steps):
        previous = current.copy()
        for k in np.unique(previous):
            rows = np.where(previous == k)[0]
            p_k = pv[k][valid]
            p_k = p_k / p_k.sum()
            draws = rng.choice(valid, size=len(rows), p=p_k)
            paths[rows, h] = inv[draws + 1]
            current[rows] = st[draws + 1]
        state_paths[:, h] = current
    return paths, state_paths
