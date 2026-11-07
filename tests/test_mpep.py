"""Tests for toolbox/mpep.py - Multi-Period (Sequential) Entropy Pooling.

Synthetic geometric paths; checks per-horizon views bind at their own
horizon, the cross-horizon ripple the article predicts, ML/CML indicator
constraints, and the tail-count search.
"""

import numpy as np
import pytest

from emfin_v2.toolbox import mpep


def _paths(n=3000, steps=6, assets=2, seed=7):
    rng = np.random.default_rng(seed)
    corr = np.array([[1.0, 0.6], [0.6, 1.0]])
    chol = np.linalg.cholesky(corr)
    z = rng.standard_normal((n, steps, assets)) @ chol.T
    drift, vol = np.array([0.01, 0.004]), np.array([0.05, 0.03])
    logr = drift + vol * z
    prices0 = np.array([100.0, 50.0])
    return prices0 * np.exp(np.cumsum(logr, axis=1)), prices0


def test_mean_view_binds_at_its_horizon():
    paths, p0 = _paths()
    prior_mean = paths[:, -1, 0].mean()
    target = prior_mean * 1.05
    res = mpep.mpep(paths, [mpep.MPView(kind="mean", instrument=0, horizon=5, value=target)],
                    initial_prices=p0)
    assert res.achieved["mean_0"] == pytest.approx(target, rel=1e-3)


def test_cross_horizon_ripple():
    # a terminal mean view lifts intermediate horizons too (path persistence)
    paths, p0 = _paths()
    res = mpep.mpep(paths, [mpep.MPView(kind="mean", instrument=0, horizon=5,
                                        value=paths[:, -1, 0].mean() * 1.05)],
                    initial_prices=p0)
    q = res.posterior_probs
    mid_post = paths[:, 2, 0] @ q
    mid_prior = paths[:, 2, 0].mean()
    assert mid_post > mid_prior * 1.01


def test_other_horizon_means_not_pinned():
    # fixing the terminal mean must NOT pin the mid-horizon mean to its prior
    paths, p0 = _paths()
    res = mpep.mpep(paths, [mpep.MPView(kind="mean", instrument=0, horizon=5,
                                        value=paths[:, -1, 0].mean() * 1.05)],
                    initial_prices=p0)
    q = res.posterior_probs
    assert not np.isclose(paths[:, 2, 0] @ q, paths[:, 2, 0].mean(), rtol=1e-3)


def test_vol_view_around_updated_mean():
    paths, p0 = _paths()
    prior_vol = paths[:, -1, 1].std()
    target = prior_vol * 1.5
    res = mpep.mpep(paths, [mpep.MPView(kind="vol", instrument=1, horizon=5, value=target)],
                    initial_prices=p0)
    assert res.achieved["vol_1"] == pytest.approx(target, rel=0.05)


def test_ml_view_caps_exceedance_mass():
    paths, p0 = _paths()
    losses = mpep.max_path_loss(paths[:, :, 0], p0[0])
    v_ml = float(np.quantile(losses, 0.90))  # prior exceedance mass 10% -> cap at 5%
    res = mpep.mpep(paths, [mpep.MPView(kind="ml", instrument=0, value=v_ml,
                                        alpha=0.95, sense="le")],
                    initial_prices=p0)
    q = res.posterior_probs
    assert q[losses >= v_ml].sum() <= 0.05 + 1e-3


def test_cml_view_stresses_tail_and_search_finds_count():
    paths, p0 = _paths(n=1500)
    losses = mpep.max_path_loss(paths[:, :, 0], p0[0])
    prior_cml = mpep.cml_of_paths(losses, np.full(1500, 1 / 1500), 0.90)
    target = prior_cml * 1.15  # stress: 90%-CML at least 15% worse than prior
    views = [mpep.MPView(kind="cml", instrument=0, value=target, alpha=0.90, sense="ge",
                         name="cml_stress")]
    res = mpep.mpep(paths, views, initial_prices=p0, cml_search=True)
    assert res.cml_tail_counts["cml_stress"] >= 2
    assert res.achieved["cml_stress"] >= target * 0.98  # discrete-path approximation
    assert res.relative_entropy > 0


def test_posterior_sums_to_one_and_is_positive():
    paths, p0 = _paths(n=500)
    res = mpep.mpep(paths, [mpep.MPView(kind="mean", instrument=0, horizon=5,
                                        value=paths[:, -1, 0].mean())],
                    initial_prices=p0)
    assert res.posterior_probs.sum() == pytest.approx(1.0)
    assert (res.posterior_probs > 0).all()


def test_stack_paths_layout():
    paths = np.arange(2 * 3 * 2, dtype=float).reshape(2, 3, 2)
    x = mpep.stack_paths(paths)
    assert x.shape == (2, 6)
    # column i*H + h holds asset i at step h
    assert x[0, 0 * 3 + 1] == paths[0, 1, 0]
    assert x[1, 1 * 3 + 2] == paths[1, 2, 1]


def test_multiple_cml_views_solve_jointly():
    paths,p0=_paths(n=400)
    views=[]
    for j in range(2):
        losses=mpep.max_path_loss(paths[:,:,j],p0[j])
        target=mpep.cml_of_paths(losses,np.full(400,1/400),.9)*1.05
        views.append(mpep.MPView('cml',j,value=target,sense='ge',alpha=.9,name=f'tail{j}'))
    result=mpep.mpep(paths,views,p0)
    assert len(result.cml_tail_counts)==2
    for view in views:
        assert result.achieved[view.name] >= view.value-1e-4


def test_invalid_kind_is_rejected_not_silently_ignored():
    paths,p0=_paths(n=50)
    with pytest.raises(ValueError):
        mpep.mpep(paths,[mpep.MPView('typo',0)],p0)
