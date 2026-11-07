"""Audit tests: discrete-scenario alpha-CVaR leftover-mass handling.

Research item 4 (Tail Risk Mathematics, May 2026): when (1-alpha) * N is
not an integer, the atom straddling the tail boundary must enter CVaR with
FRACTIONAL weight.  Dropping it biases CVaR low; rounding up biases it
high.  These tests pin the exact behavior against the Rockafellar &
Uryasev (2002) variational identity, which needs no counting convention.
"""

import numpy as np
import pytest

from emfin_v2.toolbox import mpep, risk_stats


def _ru_cvar(losses: np.ndarray, c: float) -> float:
    """Rockafellar-Uryasev identity: CVaR = min_eta eta + E[max(L-eta,0)]/(1-c)."""
    l = np.sort(np.asarray(losses, dtype=float))
    etas = np.concatenate([[l[0] - 1e-9], l, [l[-1] + 1e-9]])
    vals = etas + np.maximum(l[:, None] - etas[None, :], 0).mean(axis=0) / (1 - c)
    return float(vals.min())


def test_fractional_atom_matches_ru_identity():
    rng = np.random.default_rng(42)
    for n, c in [(7, 0.9), (101, 0.95), (1000, 0.99), (33, 0.975)]:
        losses = rng.standard_normal(n) * 3 + 1
        assert risk_stats.empirical_cvar(losses, c) == pytest.approx(_ru_cvar(losses, c), rel=1e-8)


def test_straddling_atom_gets_fractional_weight():
    # N=7, c=0.9: tail mass 0.7 - the worst atom enters with weight 0.7, not 1.0
    losses = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 10.0])
    assert risk_stats.empirical_cvar(losses, 0.9) == pytest.approx(10.0)
    # drop-the-leftover would give 10 too (tail=0 atoms + ... ) - use a case
    # where truncation errs: N=7, c=0.8: tail 1.4 atoms -> worst + 0.4*second
    losses = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 10.0])
    expected = (10.0 + 0.4 * 5.0) / 1.4
    assert risk_stats.empirical_cvar(losses, 0.8) == pytest.approx(expected)
    # naive truncation int((1-c)N)=1 would give 10.0 - measurably wrong
    assert expected != pytest.approx(10.0)


def test_cvar_dominates_var_and_is_monotone_in_c():
    rng = np.random.default_rng(7)
    losses = rng.standard_normal(500)
    for c in (0.90, 0.95, 0.99):
        assert risk_stats.empirical_cvar(losses, c) >= risk_stats.empirical_var(losses, c)
    cvars = [risk_stats.empirical_cvar(losses, c) for c in (0.80, 0.90, 0.95, 0.99)]
    assert all(b >= a for a, b in zip(cvars, cvars[1:]))


def test_weighted_cml_reduces_to_fractional_cvar_under_uniform_weights():
    rng = np.random.default_rng(11)
    losses = np.abs(rng.standard_normal(997))  # odd count forces leftover mass
    uniform = np.full(997, 1 / 997)
    assert mpep.cml_of_paths(losses, uniform, 0.95) == pytest.approx(
        risk_stats.empirical_cvar(losses, 0.95), rel=1e-10)


def test_strict_variant_still_raises_on_noninteger_tail():
    from emfin_v2.toolbox import scenario_market
    with pytest.raises(Exception):
        scenario_market.empirical_cvar(np.arange(7.0), 0.9)  # (1-c)N = 0.7
    # and agrees with the fractional version where it is defined
    losses = np.arange(100.0)
    assert scenario_market.empirical_cvar(losses, 0.95) == pytest.approx(
        risk_stats.empirical_cvar(losses, 0.95))
