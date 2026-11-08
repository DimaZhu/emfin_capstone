"""MR scenario diagnostics: does the implemented law deliver the declared
mean reversion? Analytic variance ratios vs simulated ones, weekly return
autocorrelation, and the unconditional weekly mean/covariance match against
the fitted iid moments (must be exact by construction). Fast; no judging."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_mr
from common_mr import S, f5_fit, mr_config, save_mr, load_mr
from emfin_v2.mean_reversion import variance_ratio

YEARS = [1, 3, 5, 8, 15, 30]
RESULT = 'mr_diagnostics.json'


def simulated_vr(fit, members, c_mr, weeks=416, n=2000, seed=991):
    """8-year equity variance ratio from MR draws vs iid draws (same seed)."""
    import copy
    h = c_mr['horizon_weeks']
    assert h == weeks
    i = members[0]
    mr = S.draw_paths(c_mr, fit, n, seed)
    c_iid = copy.deepcopy(c_mr)
    c_iid['scenario_model'] = 'gaussian_scale_mixture'
    c_iid.pop('mean_reversion', None)
    iid = S.draw_paths(c_iid, fit, n, seed)
    ret = lambda d: np.log(d[0][:, -1, i] / d[0][:, 0, i]).var()
    return float(ret(mr) / ret(iid))


def main():
    r = load_mr(RESULT)
    r.setdefault('meta', dict(label=('MR scenario diagnostics: analytic vs simulated variance '
                                     'ratios, weekly autocorrelation, unconditional weekly '
                                     'moment match. Central calibration, fitted view, seed 20261109.')))
    c = mr_config(view='fitted', seed=20261109)
    fit = f5_fit(c)
    _, mu, cov = fit
    members = c['asset_layout']['factor_indices']['equity']

    r['analytic_variance_ratio'] = {
        name: {f'{y}y': round(float(v), 4)
               for y, v in zip(YEARS, variance_ratio(p, [52 * y for y in YEARS]))}
        for name, p in common_mr.CALIBRATIONS.items()}

    # weekly moments + autocorrelation from one long MR draw set
    d = S.draw_paths(c, fit, 2000, 991)
    i = members[0]
    rm = np.diff(np.log(d[0][:, :, i]), axis=1)
    r['weekly'] = dict(
        mean=float(rm.mean()), fitted_mean=float(mu[i]),
        variance=float(rm.var()), fitted_variance=float(cov[i, i]),
        lag1_autocorr=float(np.corrcoef(rm[:, :-1].ravel(), rm[:, 1:].ravel())[0, 1]))
    c_iid = mr_config(view='fitted', seed=20261109)
    c_iid['scenario_model'] = 'gaussian_scale_mixture'
    c_iid.pop('mean_reversion', None)
    b = S.draw_paths(c_iid, fit, 2000, 991)
    rb = np.diff(np.log(b[0][:, :, i]), axis=1)
    r['weekly']['iid_lag1_autocorr'] = float(np.corrcoef(rb[:, :-1].ravel(), rb[:, 1:].ravel())[0, 1])

    c8 = mr_config(view='fitted', seed=20261109, weeks=416, months=96)
    fit8 = f5_fit(c8)
    r['simulated_variance_ratio_8y'] = dict(
        value=simulated_vr(fit8, members, c8),
        analytic=round(float(variance_ratio(common_mr.CALIBRATIONS['central'], [416])[0]), 4),
        note='Monte Carlo ratio of 8y equity log-return variances (MR / iid), 2000 paths each.')
    save_mr(RESULT, r)
    print(json.dumps(r, indent=1)[:1500])


if __name__ == '__main__':
    main()
