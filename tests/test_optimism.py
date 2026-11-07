"""Tests for toolbox/optimism.py."""

import numpy as np
import pytest

from emfin_v2.toolbox import optimism


def test_t_ci_contains_mean_and_shrinks_with_n():
    rng = np.random.default_rng(1)
    v = rng.standard_normal(30) + 5.0
    mean, lo, hi = optimism.t_ci(v)
    assert lo < mean < hi
    _, lo2, hi2 = optimism.t_ci(np.concatenate([v, rng.standard_normal(970) + 5.0]))
    assert (hi2 - lo2) < (hi - lo)


def test_control_method_has_zero_gap():
    # a method that fits nothing: in-sample and held-out CEs from the same
    # distribution - the CI must cover zero
    rng = np.random.default_rng(2)
    ce_in = {"1/N": rng.standard_normal(12) * 100 + 1e6}
    ce_out = {"1/N": rng.standard_normal(12) * 100 + 1e6}
    gaps = optimism.optimism_gaps(ce_in, ce_out)
    assert gaps["1/N"]["gap_lo"] < 0 < gaps["1/N"]["gap_hi"]


def test_deterministic_gap_is_tight():
    ce_in = {"x": np.full(10, 1_000_000.0)}
    ce_out = {"x": np.full(10, 990_000.0)}
    g = optimism.optimism_gaps(ce_in, ce_out)["x"]
    assert g["gap_mean"] == pytest.approx(10_000.0)
    assert g["gap_hi"] - g["gap_lo"] < 1e-6


def test_mismatched_methods_raise():
    with pytest.raises(ValueError):
        optimism.optimism_gaps({"a": np.ones(3)}, {"b": np.ones(3)})
