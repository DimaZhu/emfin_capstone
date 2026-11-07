"""Entropy pooling: baseline reduction, exactness of views, sequential
priority semantics, inconsistency detection, and a brute-force primal
cross-check of the dual solver."""

import numpy as np
import pytest
from scipy import optimize

from emfin_v2.toolbox import entropy_pooling as ep


@pytest.fixture()
def scenarios():
    rng = np.random.default_rng(0)
    return rng.normal(0.001, 0.02, size=(5000, 3))


def test_no_views_returns_prior_exactly(scenarios):
    n = len(scenarios)
    result = ep.joint_entropy_pooling(n, [])
    assert result.kl_divergence == 0.0
    np.testing.assert_allclose(result.posterior_probs, 1 / n)
    result_seq = ep.sequential_entropy_pooling(n, [])
    np.testing.assert_allclose(result_seq.posterior_probs, 1 / n)


def test_mean_view_hits_target(scenarios):
    view = ep.mean_view(scenarios, 0, 0.005)
    result = ep.joint_entropy_pooling(len(scenarios), [view])
    assert result.per_view_achieved[0][0] == pytest.approx(0.005, abs=1e-8)
    assert result.kl_divergence > 0
    assert result.posterior_probs.sum() == pytest.approx(1.0)
    assert (result.posterior_probs > 0).all()


def test_joint_mean_and_vol_views_both_hold(scenarios):
    views = [
        ep.mean_view(scenarios, 0, 0.005),
        ep.volatility_view(scenarios, 0, 0.03, pin_mean=0.005),
    ]
    result = ep.joint_entropy_pooling(len(scenarios), views)
    q = result.posterior_probs
    assert q @ scenarios[:, 0] == pytest.approx(0.005, abs=1e-8)
    std = np.sqrt(q @ scenarios[:, 0] ** 2 - (q @ scenarios[:, 0]) ** 2)
    assert std == pytest.approx(0.03, abs=1e-8)
    # Effective number of scenarios drops but stays meaningful
    assert 1 < result.effective_n_scenarios < len(scenarios)


def test_sequential_later_view_overrides_earlier(scenarios):
    early = ep.mean_view(scenarios, 0, 0.005, name="early")
    late = ep.mean_view(scenarios, 0, -0.002, name="late")
    result = ep.sequential_entropy_pooling(len(scenarios), [early, late])
    # The last view holds exactly; the earlier one is violated (and visible)
    assert result.per_view_achieved[1][0] == pytest.approx(-0.002, abs=1e-8)
    assert result.per_view_achieved[0][0] != pytest.approx(0.005, abs=1e-4)


def test_joint_inconsistent_views_raise(scenarios):
    views = [ep.mean_view(scenarios, 0, 0.005), ep.mean_view(scenarios, 0, -0.002)]
    with pytest.raises(RuntimeError, match="not satisfied|did not converge"):
        ep.joint_entropy_pooling(len(scenarios), views)


def test_dual_matches_brute_force_primal():
    """Small-N cross-check: minimize KL directly under the constraint."""
    rng = np.random.default_rng(7)
    n = 200
    x = rng.normal(0.0, 1.0, size=(n, 1))
    target = 0.3
    view = ep.View(features=x, target=[target])
    result = ep.joint_entropy_pooling(n, [view])
    q_dual = result.posterior_probs

    def kl(q):
        return q @ np.log(q * n)

    cons = [{"type": "eq", "fun": lambda q: q.sum() - 1},
            {"type": "eq", "fun": lambda q: q @ x.ravel() - target}]
    res = optimize.minimize(kl, np.full(n, 1 / n), jac="2-point",
                            constraints=cons, method="SLSQP",
                            options={"maxiter": 500, "ftol": 1e-12})
    assert res.success
    np.testing.assert_allclose(q_dual, res.x, atol=1e-5)


def test_probs_must_be_positive(scenarios):
    with pytest.raises(ValueError, match="strictly positive"):
        ep.joint_entropy_pooling(
            len(scenarios), [ep.mean_view(scenarios, 0, 0.0)],
            prior_probs=np.concatenate([[0.0], np.full(len(scenarios) - 1, 1.0)]),
        )


# ---------------------------------------------------------------------------
# Inequality views, moment views, confidence blending, package cross-check
# ---------------------------------------------------------------------------

def test_volatility_cap_binds_at_boundary(scenarios):
    # Prior vol is 0.02; cap at 0.015 must bind: posterior std == 0.015.
    cap = ep.volatility_cap(scenarios, 0, 0.015)
    result = ep.joint_entropy_pooling(len(scenarios), [cap])
    q = result.posterior_probs
    std = np.sqrt(q @ scenarios[:, 0] ** 2 - (q @ scenarios[:, 0]) ** 2)
    assert std <= 0.015 + 1e-8  # the cap holds
    assert std == pytest.approx(0.015, abs=1e-4)  # and it binds
    assert result.kl_divergence > 0


def test_volatility_cap_nonbinding_leaves_prior(scenarios):
    # Prior vol is 0.02; cap at 0.05 never binds: posterior stays the prior.
    cap = ep.volatility_cap(scenarios, 0, 0.05)
    result = ep.joint_entropy_pooling(len(scenarios), [cap])
    np.testing.assert_allclose(result.posterior_probs, 1 / len(scenarios), atol=1e-10)
    assert result.kl_divergence == pytest.approx(0.0, abs=1e-12)


def test_mean_floor_ge_sense(scenarios):
    floor = ep.mean_floor(scenarios, 0, 0.005)
    result = ep.joint_entropy_pooling(len(scenarios), [floor])
    assert result.per_view_achieved[0][0] == pytest.approx(0.005, abs=1e-8)


def test_relative_mean_view(scenarios):
    # Rank column 1 at least 0.004 above column 2.
    view = ep.relative_mean_view(scenarios, 1, 2, min_spread=0.004)
    result = ep.joint_entropy_pooling(len(scenarios), [view])
    q = result.posterior_probs
    assert q @ scenarios[:, 1] - q @ scenarios[:, 2] == pytest.approx(0.004, abs=1e-6)


def test_joint_mean_equality_and_vol_cap_hold_together(scenarios):
    # Equality and inequality pooled in one dual: both must hold exactly.
    views = [
        ep.mean_view(scenarios, 0, 0.005),
        ep.volatility_cap(scenarios, 0, 0.015, pin_mean=0.005),
    ]
    result = ep.joint_entropy_pooling(len(scenarios), views)
    q = result.posterior_probs
    assert q @ scenarios[:, 0] == pytest.approx(0.005, abs=1e-8)
    std = np.sqrt(q @ scenarios[:, 0] ** 2 - 0.005**2)
    assert std <= 0.015 + 1e-8
    assert std == pytest.approx(0.015, abs=1e-4)  # the cap binds


def test_moment_views_hit_targets(scenarios):
    x = scenarios[:, 0]
    m, s = x.mean(), x.std()
    views = [
        ep.skewness_view(scenarios, 0, -0.75, pin_mean=m, pin_vol=s),
        ep.kurtosis_view(scenarios, 0, 3.5, pin_mean=m, pin_vol=s, sense="ge"),
    ]
    result = ep.joint_entropy_pooling(len(scenarios), views)
    q = result.posterior_probs
    assert q @ ((x - m) / s) ** 3 == pytest.approx(-0.75, abs=1e-6)
    assert q @ ((x - m) / s) ** 4 >= 3.5 - 1e-8


def test_correlation_view(scenarios):
    view = ep.correlation_view(scenarios, 1, 2, 0.5)
    result = ep.joint_entropy_pooling(len(scenarios), [view])
    q = result.posterior_probs
    x, y = scenarios[:, 1], scenarios[:, 2]
    cov = q @ ((x - x.mean()) * (y - y.mean()))
    assert cov / (x.std() * y.std()) == pytest.approx(0.5, abs=1e-6)


def test_sequential_mixed_eq_and_ineq(scenarios):
    early = ep.mean_view(scenarios, 0, 0.005, name="early mean")
    late = ep.volatility_cap(scenarios, 0, 0.015, pin_mean=0.005, name="late cap")
    result = ep.sequential_entropy_pooling(len(scenarios), [early, late])
    q = result.posterior_probs
    std = np.sqrt(q @ scenarios[:, 0] ** 2 - (q @ scenarios[:, 0]) ** 2)
    assert std <= 0.015 + 1e-8  # the cap holds after the sequence


def test_inconsistent_inequalities_raise(scenarios):
    views = [ep.mean_floor(scenarios, 0, 0.05), ep.mean_cap(scenarios, 0, -0.05)]
    with pytest.raises(RuntimeError, match="not satisfied|did not converge|failed"):
        ep.joint_entropy_pooling(len(scenarios), views)


def test_confidence_blending(scenarios):
    view = ep.mean_view(scenarios, 0, 0.005)
    n = len(scenarios)
    prior_mean = scenarios[:, 0].mean()
    full = ep.joint_entropy_pooling(n, [view], confidence=1.0)
    half = ep.joint_entropy_pooling(n, [view], confidence=0.5)
    zero = ep.joint_entropy_pooling(n, [view], confidence=0.0)
    # c = 0: posterior is the prior exactly
    np.testing.assert_allclose(zero.posterior_probs, 1 / n)
    # c = 0.5: achieved mean is the midpoint of prior and view target
    assert half.per_view_achieved[0][0] == pytest.approx((prior_mean + 0.005) / 2, abs=1e-8)
    # KL grows monotonically with confidence
    assert zero.kl_divergence < half.kl_divergence < full.kl_divergence
    with pytest.raises(ValueError, match="confidence"):
        ep.joint_entropy_pooling(n, [view], confidence=1.5)


def test_ens_ratio_consistency(scenarios):
    view = ep.mean_view(scenarios, 0, 0.005)
    result = ep.joint_entropy_pooling(len(scenarios), [view])
    assert result.effective_n_scenarios_ratio == pytest.approx(
        result.effective_n_scenarios / len(scenarios), rel=1e-12
    )
    assert 0 < result.effective_n_scenarios_ratio < 1


def test_crosscheck_against_fortitudo_bsd_package(scenarios):
    """Our dual solver must reproduce the reference EP implementation.

    Cross-check against Fortitudo Technologies' BSD-3-Clause "entropy-pooling"
    package (the same algorithm, independently coded) on a joint problem with
    equality (mean) and inequality (vol cap) constraints.
    """
    pytest.importorskip("entropy_pooling", reason="BSD reference package not installed")
    import entropy_pooling as ref

    n = len(scenarios)
    x = scenarios[:, 0]
    m = x.mean()
    p = np.full((n, 1), 1 / n)
    A = np.vstack((np.ones((1, n)), x[np.newaxis, :]))
    b = np.array([[1.0], [0.005]])
    G = ((x - 0.005) ** 2)[np.newaxis, :]
    h = np.array([[0.015**2]])
    q_ref = ref.ep(p, A, b, G, h).ravel()

    views = [ep.mean_view(scenarios, 0, 0.005), ep.volatility_cap(scenarios, 0, 0.015, pin_mean=0.005)]
    q_ours = ep.joint_entropy_pooling(n, views).posterior_probs

    assert q_ref @ x == pytest.approx(0.005, abs=1e-6)  # reference is sane
    np.testing.assert_allclose(q_ours, q_ref, atol=1e-6)
