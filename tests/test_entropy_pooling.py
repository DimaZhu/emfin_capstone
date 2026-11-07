"""Entropy pooling: baseline reduction, exactness of views, sequential
priority semantics, inconsistency detection, and a brute-force primal
cross-check of the dual solver."""

import numpy as np
import pytest
from scipy import optimize

from emfin_capstone.toolbox import entropy_pooling as ep


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
