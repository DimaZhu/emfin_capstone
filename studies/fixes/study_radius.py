"""Fix 2: the Wasserstein model-miss radius (open point 2: the radius is a
manual 2e-5 with no calibration behind it - buffer 0.04% of wealth, cosmetic).

Two parts:
  refit_instability  radius calibrated from refit instability: stationary
                     block bootstrap refits of the same fit_frame machinery,
                     each refit's draw set matched against the base draw set
                     under the declared max_path cost (chebyshev on flattened
                     price+funding paths, same geometry as
                     radius_calibration.balanced_distances). Radius = q90 of
                     the cross-set assignment distances. A within-base
                     half-split gives the simulation noise floor for scale.
  radius_grid        the frozen 10y pipeline (same draws, same sleeve, same
                     judge) re-run at radius values from 0 up to multiples of
                     the calibrated radius: chosen safe share and CE vs radius,
                     and where the budgets become infeasible. Every radius is a
                     labeled sensitivity; no engine default is changed.

Reference: the existing past-empirical calibrate() is 52-week-only; its value
is reported for scale at the 1y sleeve config.
"""
import sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import S, save, load
from emfin_v2.historical_simulation import stationary_indices
from emfin_v2.registry_runtime import fit_frame
from emfin_v2.radius_calibration import balanced_distances
from emfin_v2.toolbox.wasserstein import penalty
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

N_PATHS = 64
N_REFITS = 8
MEAN_BLOCK = 52


def path_blocks(draw):
    paths, funding = draw[0], draw.funding_paths
    return np.array([np.r_[paths[i].ravel(), funding[i].ravel()] for i in range(len(paths))])


def cross_distance(a, b):
    d = cdist(a, b, metric='chebyshev')
    i, j = linear_sum_assignment(d)
    return float(d[i, j].mean())


def main():
    r = load('fix2_radius.json')
    r.setdefault('meta', dict(
        label='LABELED STUDY (owner ask 8 Nov 11:05, open point 2): model-miss radius calibration.',
        geometry='declared max_path cost: chebyshev over flattened price+funding path coordinates',
        n_paths=N_PATHS, n_refits=N_REFITS, mean_block_weeks=MEAN_BLOCK))
    c = S.nm_config()
    fit = S.setup(c)
    frame, mu, cov = fit
    import json
    base_prop = json.loads(
        Path('studies/tbill/results/study_tips_charts.json').read_text())['sleeve_cara']['proportions']

    if 'refit_instability' not in r:
        t0 = time.perf_counter()
        base_draw = S.draw_paths(c, fit, N_PATHS, c['seed'] + 5000)
        base_blocks = path_blocks(base_draw)
        noise_floor = balanced_distances(base_blocks, repetitions=32)
        rows = []
        for b in range(N_REFITS):
            idx = stationary_indices(len(frame), 1, len(frame), MEAN_BLOCK, c['seed'] + 6000 + b)[0]
            frame_b = frame.iloc[idx].reset_index(drop=True)
            import copy
            cb = copy.deepcopy(c)
            fit_b = fit_frame(cb, frame_b)
            draw_b = S.draw_paths(c, fit_b, N_PATHS, c['seed'] + 7000 + b)
            d = cross_distance(base_blocks, path_blocks(draw_b))
            rows.append(dict(refit=b, cross_distance=d,
                             mu_shift_annual=float(np.abs((fit_b[1] - mu) * 52).max())))
            save('fix2_radius.json', r)  # checkpoint meta at least
            print('refit', b, 'cross', round(d, 4), flush=True)
        dists = sorted(row['cross_distance'] for row in rows)
        radius = float(np.quantile(dists, .9, method='inverted_cdf'))
        r['refit_instability'] = dict(
            rows=rows, radius_q90=radius,
            noise_floor_median=float(np.median(noise_floor)),
            noise_floor_q90=float(np.quantile(noise_floor, .9)),
            current_manual_radius=c['wasserstein_radius'],
            buffer_fraction_at_calibrated=float(
                penalty(np.ones(len(c['asset_layout']['ids'])) / len(c['asset_layout']['ids']),
                        radius, c['confidence'], metric=c.get('wasserstein_metric', 'legacy_l1'))),
            note='q90 of refit-vs-base cross distances; property channel constant across refits '
                 '(URA calibration, labeled); shrinkage/mean policy identical to production fit.',
            seconds=time.perf_counter() - t0)
        save('fix2_radius.json', r)
        print('refit instability radius:', radius, flush=True)

    if 'past_empirical_52w' not in r:
        try:
            c1 = S.nm_config(one_year_sleeve=True)
            from emfin_v2.radius_calibration import calibrate
            cal = calibrate(c1, S.setup(c1)[0])
            r['past_empirical_52w'] = {k: v for k, v in cal.items() if k in
                                       ('available', 'radius', 'reason', 'budget_conflict',
                                        'unavoidable_funding_buffer_dollars', 'smallest_funding_budget')}
        except Exception as e:  # labeled: reference only
            r['past_empirical_52w'] = dict(available=False, reason=f'{type(e).__name__}: {e}')
        save('fix2_radius.json', r)
        print('past-empirical 52w:', r['past_empirical_52w'].get('radius'), flush=True)

    cal_radius = r.get('refit_instability', {}).get('radius_q90')
    grid_radii = [0.0, c['wasserstein_radius'], 2.5e-5, 3e-5, 4e-5, 5e-5, 7.5e-5, 1e-4, 1e-3, 1e-2, 0.1]
    if cal_radius:
        grid_radii += [cal_radius * m for m in (0.5, 1.0, 2.0, 4.0)]
    grid_radii = sorted(set(round(float(x), 8) for x in grid_radii))
    r.setdefault('radius_grid', dict(label='frozen 10y pipeline at labeled radius sensitivities '
                                           '(fix 2): same draws/sleeve/judge, only the model-miss '
                                           'buffer radius changes',
                                     base_portfolio_safe=0.375, runs=[]))
    done = {run['radius'] for run in r['radius_grid']['runs']}
    val_cache = {}
    for rad in grid_radii:
        if rad in done:
            continue
        t0 = time.perf_counter()
        cr = S.nm_config()
        cr['wasserstein_radius'] = rad
        cr['label'] += f' LABELED SENSITIVITY (fix 2 radius grid): wasserstein_radius={rad}.'
        if 'd' not in val_cache:
            val_cache['d'] = S.get_draws(cr, fit, 'h520')
        val, vp, fin, fp = val_cache['d']
        res = S.mix_search(cr, val, vp, fin, fp, base_prop,
                           label=f'fix-2 radius grid, radius={rad}')
        # also judge the frozen base portfolio (37.5% bills) at this radius
        mix, ids = S.mix_fn(cr, base_prop)
        base_verdict = S.evaluate(cr, fin, mix(0.375) * cr['wealth'],
                                  [x[0] for x in fp], [x[1] for x in fp])
        run = dict(radius=rad, chosen_safe=res.get('chosen_safe'),
                   ce=res.get('common_cara_ledger_ce'),
                   base_portfolio_passes=base_verdict['overall_pass'],
                   base_portfolio_breaches=base_verdict.get('breaches'),
                   note=res.get('note'), seconds=time.perf_counter() - t0)
        r['radius_grid']['runs'].append(run)
        save('fix2_radius.json', r)
        print('radius', rad, '-> safe', run['chosen_safe'], 'base passes', run['base_portfolio_passes'],
              flush=True)

    print('radius study done', flush=True)


if __name__ == '__main__':
    main()
