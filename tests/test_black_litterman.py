import numpy as np
import pytest

from emfin_v2.toolbox import black_litterman as bl


@pytest.fixture()
def market():
    sigma = np.array([[0.04, 0.01, 0.005], [0.01, 0.03, 0.004], [0.005, 0.004, 0.02]])
    w = np.array([0.6, 0.3, 0.1])
    return sigma, w, bl.equilibrium_prior(sigma, w, 2.5)


def test_view_at_prior_leaves_mean_unchanged(market):
    sigma, w, pi = market
    m, _ = bl.posterior(sigma, pi, np.array([[1.0, 0, 0]]), np.array([pi[0]]), tau=0.05)
    np.testing.assert_allclose(m, pi, atol=1e-10)


def test_confident_view_pulls_mean_to_it(market):
    sigma, w, pi = market
    m, _ = bl.posterior(sigma, pi, np.array([[1.0, 0, 0]]), np.array([0.10]),
                        tau=0.05, omega=np.array([[1e-6]]))
    assert m[0] == pytest.approx(0.10, abs=1e-3)


def test_vague_view_moves_mean_partway(market):
    sigma, w, pi = market
    m, _ = bl.posterior(sigma, pi, np.array([[1.0, 0, 0]]), np.array([0.10]), tau=0.05)
    assert pi[0] < m[0] < 0.10  # interpolation, not adoption


def test_relative_view_moves_spread(market):
    sigma, w, pi = market
    # asset 2 outperforms asset 0 by 5%
    m, _ = bl.posterior(sigma, pi, np.array([[-1.0, 0, 1.0]]), np.array([0.05]),
                        tau=0.05, omega=np.array([[1e-6]]))
    assert (m[2] - m[0]) == pytest.approx(0.05, abs=1e-3)


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        bl.equilibrium_prior(np.eye(2), np.array([0.5, 0.4]), 2.5)
