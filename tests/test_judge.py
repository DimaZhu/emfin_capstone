"""Tests for toolbox/judge.py - empirical, regime-aware judge sampler."""

import numpy as np
import pytest

from emfin_capstone.toolbox import judge, tsdr


def _history(n=600, seed=4):
    rng = np.random.default_rng(seed)
    state_var = np.abs(rng.standard_normal(n).cumsum() * 0.02 + 0.01)
    labels = tsdr.state_labels(state_var)
    vols = np.where(labels == 2, 0.06, 0.02)
    inv = rng.standard_normal((n, 2)) * vols[:, None]
    return inv, labels


def test_shapes_and_determinism():
    inv, labels = _history()
    a, mask_a = judge.empirical_horizon_invariants(inv, labels, 500, 13, 1, seed=7)
    b, mask_b = judge.empirical_horizon_invariants(inv, labels, 500, 13, 1, seed=7)
    assert a.shape == (500, 2) and mask_a.shape == (500,)
    assert np.array_equal(a, b) and np.array_equal(mask_a, mask_b)


def test_horizon_invariant_is_sum_of_weekly():
    inv, labels = _history()
    h, _ = judge.empirical_horizon_invariants(inv, labels, 200, 13, 1, seed=9)
    # 13 weekly invariants of sd ~0.02-0.06 sum to sd ~ sqrt(13)*0.04 ~ 0.14
    assert 0.05 < h[:, 0].std() < 0.4


def test_regime_split_is_informative():
    inv, labels = _history()
    _, mask = judge.empirical_horizon_invariants(inv, labels, 4000, 13, 1, seed=11)
    assert 0.01 < mask.mean() < 0.99  # some paths enter high vol, not all
    h, mask2 = judge.empirical_horizon_invariants(inv, labels, 4000, 13, 2, seed=11)
    # starting IN the high state, more paths visit it
    assert mask2.mean() > mask.mean()


def test_high_regime_paths_have_fatter_tails():
    inv, labels = _history()
    h, mask = judge.empirical_horizon_invariants(inv, labels, 8000, 13, 1, seed=13)
    assert h[mask, 0].std() > h[~mask, 0].std()
