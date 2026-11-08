"""Sensitivity section (owner ask 8 Nov 13:12 SGT): Stage 4 - seed-noise band.
Repeats the key cells on a THIRD seed family (20261111, disjoint from
20261109/20261110) so the report can show which differences are real and
which are draw noise: full horizon sweep at 15% and 25% terminal (both carry
views) plus the policy cells at 20/30y. New draws generate on first use and
are shared across both limits (draws are loss-independent).
Checkpointed per cell in results/final5_sens_seeds.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, save, load, f5_fit, dual_mix_search, judge_frozen
from study_sens_policies import simulate_policy
from study_q3_rebalance import terminal_tail, frozen_vector

R2 = Path('studies/round2/results/round2_dual_law.json')
H15 = Path('studies/final5/results/final5_horizon.json')
RESULT = 'final5_sens_seeds.json'
YEARS = [5, 10, 15, 20, 30]
LOSSES = [0.15, 0.25]
SEED = 20261111


def cfg(view='fitted', **kw):
    c = S.nm_config(**kw)
    c['seed'] = SEED
    c['carry_view'] = view
    c['label'] += (' FINAL-5 SENS seed band (owner ask 8 Nov 13:12 SGT): seed family %d '
                   '(third family, disjoint from 20261109/20261110); carry view %s; dual-law.'
                   % (SEED, view))
    return c


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 SENS stage 4: seed-noise band on seed family %d - horizon sweep at '
               '15%%/25%% terminal plus 20/30y policy cells, both carry views, dual-law. '
               'Compares against final5_horizon.json / final5_horizon_t25_s09.json (20261109) '
               'and final5_horizon_t25.json (20261110).' % SEED),
        seed_family=SEED, years=YEARS, losses=LOSSES))
    r2 = json.loads(R2.read_text())
    h15 = json.loads(H15.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        prop = r2[view]['sleeve']['proportions']
        frozen = r2[view]['dual']['weights']
        for years in YEARS:
            for loss in LOSSES:
                key = f'{years}y_t{loss:.2f}'
                if key in vent:
                    continue
                t0 = time.perf_counter()
                c = cfg(view=view, weeks=52 * years, months=12 * years, loss=loss)
                fit = f5_fit(c)
                tag = f'f5s11_h{52 * years}_{view}'
                primary, fifth = common5.f5_draws(c, fit, tag)
                search = dual_mix_search(c, primary, fifth, prop,
                                         label=f'FINAL-5 SENS seed {SEED} {view}, {years}y, '
                                               f'terminal {loss:.0%}, dual-law')
                hold = judge_frozen(c, primary, fifth, frozen,
                                    label=f'frozen round-2 {view} mix at {years}y, terminal {loss:.0%}, '
                                          f'seed {SEED}')
                vent[key] = dict(years=years, loss=loss, search=search, hold_10y_mix=hold,
                                 seconds=time.perf_counter() - t0)
                save(RESULT, r)
                print(view, key, 'safe=', search.get('chosen_safe'),
                      'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
                      '| held10y pass=', hold['final_pass'],
                      '(%.0fs)' % vent[key]['seconds'], flush=True)
        # policy cells at 20/30y on the same seed-20261111 draws
        static = {int(y): h15[view][f'{y}y']['search'].get('chosen_safe') for y in (20, 30)}
        s10 = h15[view]['10y']['search'].get('chosen_safe')
        for years in (20, 30):
            key = f'{years}y_policies'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = cfg(view=view, weeks=52 * years, months=12 * years, loss=0.15)
            fit = f5_fit(c)
            tag = f'f5s11_h{52 * years}_{view}'
            _, (_, _, fin2, fp2) = common5.f5_draws(c, fit, tag)
            w0, ids = frozen_vector(c, r2[view]['dual']['weights'])
            a = w0 * c['wealth']
            cell = dict(years=years, view=view, glide=(static[years], s10))
            bh = [(d[0] @ a)[:, -1] for d in fin2]
            cell['buy_hold_mark'] = terminal_tail(c, fin2, fp2, w0, bh)
            for pol in ('cash_first', 'annual_rebal', 'threshold_10', 'glide_annual'):
                glide = (static[years], s10) if pol == 'glide_annual' else None
                pay = [simulate_policy(c, d, w0, pol, glide) for d in fin2]
                wp = [z['net_wealth_paths'][:, -1] for z in pay]
                tt = terminal_tail(c, fin2, fp2, w0, wp)
                tt['funded'] = float(np.mean([z['funded'].mean() for z in pay]))
                cell[pol] = tt
            cell['seconds'] = time.perf_counter() - t0
            vent[key] = cell
            save(RESULT, r)
            print(view, key, {p: round(cell[p]['terminal_ru'], 3) for p in
                              ('buy_hold_mark', 'cash_first', 'annual_rebal',
                               'threshold_10', 'glide_annual')}, flush=True)
    save(RESULT, r)


if __name__ == '__main__':
    main()
