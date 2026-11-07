"""Tests for toolbox/tsdr.py - Time- and State-Dependent Resampling."""

import numpy as np
import pytest

from emfin_capstone.toolbox import tsdr


def _history(n=800, seed=3):
    """Two-regime history: high-vol state has 3x the vol of the low state."""
    rng = np.random.default_rng(seed)
    state_var = np.abs(rng.standard_normal(n).cumsum() * 0.02 + 0.01)
    labels = tsdr.state_labels(state_var)
    vols = np.where(labels == 2, 0.06, 0.02)
    inv = rng.standard_normal((n, 2)) * vols[:, None]
    return inv, state_var, labels


def test_state_labels_partition():
    labels = tsdr.state_labels(np.arange(100, dtype=float))
    assert set(labels) == {0, 1, 2}
    assert (labels[:25] == 0).all() and (labels[90:] == 2).all()


def test_probability_vectors_normalize_and_concentrate():
    _, _, labels = _history()
    pv = tsdr.state_probability_vectors(labels, half_life=200.0)
    assert pv.shape == (3, len(labels))
    assert np.allclose(pv.sum(axis=1), 1.0)
    for k in range(3):  # crisp conditioning: mass only on own state
        assert pv[k][labels != k].sum() == 0.0


def test_resampled_paths_inherit_state_dependence():
    inv, state_var, labels = _history()
    pv = tsdr.state_probability_vectors(labels, half_life=10_000.0)  # no decay
    paths, state_paths = tsdr.resample_invariant_paths(
        inv, labels, pv, n_scenarios=4000, n_steps=1, initial_state=2, seed=5)
    # starting in the high-vol state, step-1 invariants should be high-vol
    assert paths[:, 0, 0].std() > 0.045
    paths_lo, _ = tsdr.resample_invariant_paths(
        inv, labels, pv, n_scenarios=4000, n_steps=1, initial_state=0, seed=5)
    assert paths_lo[:, 0, 0].std() < 0.03


def test_stationarity_state_dependence_fades_with_horizon():
    # the article's headline property: initial-state dependence disappears
    # on long horizons (stationarity of the chain)
    inv, state_var, labels = _history()
    pv = tsdr.state_probability_vectors(labels, half_life=10_000.0)
    hi, _ = tsdr.resample_invariant_paths(inv, labels, pv, 6000, 52, initial_state=2, seed=9)
    lo, _ = tsdr.resample_invariant_paths(inv, labels, pv, 6000, 52, initial_state=0, seed=9)
    early_gap = abs(hi[:, 0, 0].std() - lo[:, 0, 0].std())
    late_gap = abs(hi[:, -1, 0].std() - lo[:, -1, 0].std())
    assert late_gap < early_gap
    assert late_gap < 0.01


def test_markov_transition_follows_empirical_successor():
    inv, state_var, labels = _history()
    pv = tsdr.state_probability_vectors(labels, half_life=10_000.0)
    _, state_paths = tsdr.resample_invariant_paths(inv, labels, pv, 4000, 30, initial_state=1, seed=11)
    # empirical transition matrix from history
    emp = np.zeros((3, 3))
    for t in range(len(labels) - 1):
        emp[labels[t], labels[t + 1]] += 1
    emp /= emp.sum(axis=1, keepdims=True)
    # simulated one-step transitions from the mid state
    trans = state_paths[:, 0]
    sim = np.array([(trans == k).mean() for k in range(3)])
    assert np.allclose(sim, emp[1], atol=0.03)


def test_empty_state_raises():
    labels = np.zeros(20, dtype=int)  # only state 0 present; ask for state 2 vector
    pv = tsdr.state_probability_vectors(labels, half_life=5.0)
    assert pv.shape == (1, 20)  # no empty rows created


def test_each_path_transitions_exactly_once_per_step():
    # Deterministic successor 0->1->2->0. An in-place grouped update would
    # mistakenly advance the first group three times in one step.
    labels=np.array([0,1,2,0])
    inv=np.arange(4.)[:,None]
    pv=np.array([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]])
    paths, states=tsdr.resample_invariant_paths(inv,labels,pv,20,3,0,7)
    np.testing.assert_array_equal(states, np.tile([1,2,0],(20,1)))
    np.testing.assert_array_equal(paths[:,:,0], np.tile([1.,2.,3.],(20,1)))
