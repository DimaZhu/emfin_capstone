"""Mean-reverting equity scenario law: algebra, calibration guards, simulation."""
import copy

import numpy as np
import pytest

from emfin_v2.mean_reversion import (MODEL, settings, phi_weekly, loadings,
                                     permanent_covariance, fad_returns,
                                     variance_ratio, describe)
from emfin_v2.innovations import log_gross_moment, describe as innovations_describe
from emfin_v2.default_run import load_config, validate_config, setup, draw_paths

PARAMS = dict(half_life_years=2.0, variance_share=0.40)


def test_settings_validation():
    assert settings(dict(mean_reversion=PARAMS)) == PARAMS
    assert settings(dict()) == dict(half_life_years=2.0, variance_share=0.40)
    for bad in [dict(half_life_years=0), dict(half_life_years=11),
                dict(variance_share=0), dict(variance_share=1),
                dict(variance_share=float('nan')), dict(unknown=1)]:
        with pytest.raises(ValueError):
            settings(dict(mean_reversion=bad))


def test_algebra_exact_unconditional_moments():
    # realistic weekly-like covariance: two equities (corr .76), gold, treasury
    sd0 = np.array([.025, .031, .024, .009])
    r = np.array([[1, .76, .1, -.05], [.76, 1, .15, .0], [.1, .15, 1, .3], [-.05, .0, .3, 1]])
    cov = np.outer(sd0, sd0) * r
    members = [0, 1]
    p = settings(dict(mean_reversion=PARAMS))
    phi = phi_weekly(p)
    w = loadings(cov, members, p)
    perm = permanent_covariance(cov, members, p)
    # Fad weekly return covariance is w w' * 2(1-phi); permanent + fad == cov.
    fad = np.outer(w, w) * 2.0 * (1.0 - phi)
    np.testing.assert_allclose(perm + fad, cov, rtol=1e-12, atol=1e-15)
    # Each equity asset's fad share of its own variance is exactly the setting.
    for i in members:
        assert w[i] ** 2 * 2.0 * (1.0 - phi) == pytest.approx(
            p['variance_share'] * cov[i, i], rel=1e-12)
    assert w[2] == 0 and w[3] == 0
    assert np.linalg.eigvalsh(perm).min() > 0


def test_variance_ratio_shape_and_limits():
    vr = variance_ratio(PARAMS, [1, 52, 260, 416, 1560])
    assert vr[0] == pytest.approx(1.0)
    assert np.all(np.diff(vr) < 0)                       # strictly mean-reverting
    assert vr[-1] > 1.0 - PARAMS['variance_share']       # never below the floor
    # long-horizon limit tends to the permanent share
    assert variance_ratio(PARAMS, [52 * 200])[0] == pytest.approx(0.6, abs=0.01)
    with pytest.raises(ValueError):
        variance_ratio(PARAMS, [0])


def test_fad_stationarity_and_reversal_sign():
    rng = np.random.default_rng(11)
    fr = fad_returns(rng, 40000, 8, PARAMS)
    assert fr.mean() == pytest.approx(0., abs=0.01)
    lag1 = np.corrcoef(fr[:, :-1].ravel(), fr[:, 1:].ravel())[0, 1]
    assert -0.05 < lag1 < 0                              # reversals, not momentum
    # fad variance matches the algebra: Var(fr) = 2(1-phi)
    phi = phi_weekly(PARAMS)
    assert fr.var() == pytest.approx(2 * (1 - phi), rel=0.02)


def test_psd_guard_and_moment_rejection():
    rng = np.random.default_rng(4)
    u = rng.normal(size=(2, 2))
    cov = u @ u.T * 0.01 + np.eye(2) * 1e-4              # near-singular equity block
    with pytest.raises(ValueError, match='not PSD'):
        permanent_covariance(cov, [0, 1], dict(half_life_years=2.0, variance_share=0.98))
    with pytest.raises(ValueError, match='path-dependent mean reversion'):
        log_gross_moment(dict(scenario_model=MODEL), [0], [[1]], [1])
    d = describe(dict(scenario_model=MODEL))
    assert 'finite' in d['price_exponential_moments'] and d['sources']
    assert innovations_describe(dict(scenario_model=MODEL))['model'] == MODEL


def test_integrated_draw_matches_iid_weekly_moments_but_reverts():
    c = load_config()
    assert c['scenario_model'] == 'gaussian_scale_mixture'
    fit = setup(c)
    _, mu, cov = fit
    members = c['asset_layout']['factor_indices']['equity']
    n, seed = 2000, 77123
    base = draw_paths(c, fit, n, seed)
    cc = copy.deepcopy(c)
    cc['scenario_model'] = MODEL
    cc['mean_reversion'] = dict(PARAMS)
    cc = validate_config(cc)
    mr = draw_paths(cc, fit, n, seed)
    assert mr.mean_reversion_diagnostics is not None
    assert not np.array_equal(base[0], mr[0])            # genuinely different paths
    # weekly log returns of the first equity member from price relatives
    rb = np.diff(np.log(base[0][:, :, members[0]]), axis=1)
    rm = np.diff(np.log(mr[0][:, :, members[0]]), axis=1)
    assert rm.mean() == pytest.approx(mu[members[0]], abs=3e-4)
    assert rm.var() == pytest.approx(cov[members[0], members[0]], rel=0.06)
    # iid base shows no weekly autocorrelation; the MR law is negative
    ac = lambda x: np.corrcoef(x[:, :-1].ravel(), x[:, 1:].ravel())[0, 1]
    assert abs(ac(rb)) < 0.02
    assert -0.05 < ac(rm) < -0.0002
    np.testing.assert_allclose(base[4], mr[4])           # money-market growth untouched


def test_integrated_five_year_variance_ratio_matches_formula():
    c = load_config()
    c['horizon_weeks'] = 260
    c['recurring_payout'] = None
    c['liabilities'] = [dict(name='none', week=260, amount=0.)]   # variance check only
    c = validate_config(c)
    fit = setup(c)
    _, _, cov = fit
    members = c['asset_layout']['factor_indices']['equity']
    n, seed = 2000, 88123
    cc = copy.deepcopy(c)
    cc['scenario_model'] = MODEL
    cc['mean_reversion'] = dict(PARAMS)
    cc = validate_config(cc)
    mr = draw_paths(cc, fit, n, seed)
    i = members[0]
    five_year = np.log(mr[0][:, -1, i] / mr[0][:, 0, i])
    analytic_var = 260 * cov[i][i] * variance_ratio(PARAMS, [260])[0]
    assert five_year.var() == pytest.approx(analytic_var, rel=0.10)
    base = draw_paths(c, fit, n, seed)
    base_five_year = np.log(base[0][:, -1, i] / base[0][:, 0, i])
    assert base_five_year.var() == pytest.approx(260 * cov[i][i], rel=0.10)
    assert five_year.var() < base_five_year.var()


def test_determinism_and_registry_guard():
    c = load_config()
    cc = copy.deepcopy(c)
    cc['scenario_model'] = MODEL
    cc = validate_config(cc)
    fit = setup(c)
    a = draw_paths(cc, fit, 30, 123)
    np.testing.assert_array_equal(a[0], draw_paths(cc, fit, 30, 123)[0])
    legacy = {k: v for k, v in cc.items() if k != 'asset_registry'}
    legacy['liquidity_haircuts'] = [0.] * 6
    with pytest.raises(ValueError, match='registry adapter'):
        validate_config(legacy)
