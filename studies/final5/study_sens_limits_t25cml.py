"""Sensitivity section (owner ask 8 Nov 13:51 SGT - joint sensitivities):
Stage 1b - the two loss limits TOGETHER: in-period cap sweep (5/15/25%) with
the terminal limit at 25% (the base grid swept caps at 15% terminal). Shows
how the two limits interact: which one binds at each combination.
10/20/30y, both carry views, dual-law judging, same seed family 20261109,
same draws (tag f5_h{weeks}_{view}). Checkpointed per cell in
results/final5_sens_limits_t25cml.json.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, save, load, f5_fit, dual_mix_search, judge_frozen

R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'final5_sens_limits_t25cml.json'
YEARS = [10, 20, 30]
CMLS = [0.05, 0.15, 0.25]
LOSS = 0.25
SEED = 20261109


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 SENS stage 1b (owner ask 8 Nov 13:51 SGT): joint loss limits - '
               'any-point cap 5/15/25%% at terminal limit 25%%, 10/20/30y, both carry views, '
               'dual-law, seed family %d (same draws as the base grid).' % SEED),
        seed_family=SEED, years=YEARS, cmls=CMLS, terminal_loss=LOSS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        prop = r2[view]['sleeve']['proportions']
        frozen = r2[view]['dual']['weights']
        for years in YEARS:
            for cml in CMLS:
                key = f'{years}y_c{cml:.2f}'
                if key in vent:
                    continue
                t0 = time.perf_counter()
                c = S.nm_config(weeks=52 * years, months=12 * years, loss=LOSS, cml=cml)
                c['seed'] = SEED
                c['carry_view'] = view
                c['label'] += (' FINAL-5 SENS joint limits (owner ask 8 Nov 13:51 SGT): terminal '
                               '25%%, any-point %.0f%%, seed family %d, carry view %s, dual-law.'
                               % (cml, SEED, view))
                fit = f5_fit(c)
                tag = f'f5_h{52 * years}_{view}'
                primary, fifth = common5.f5_draws(c, fit, tag)
                search = dual_mix_search(c, primary, fifth, prop,
                                         label=f'FINAL-5 SENS {view}, {years}y, terminal 25%, '
                                               f'any-point {cml:.0%}, dual-law')
                hold = judge_frozen(c, primary, fifth, frozen,
                                    label=f'frozen round-2 {view} mix at {years}y, terminal 25%, '
                                          f'any-point {cml:.0%}')
                vent[key] = dict(years=years, loss=LOSS, cml=cml,
                                 search=search, hold_10y_mix=hold,
                                 seconds=time.perf_counter() - t0)
                save(RESULT, r)
                print(view, key, 'safe=', search.get('chosen_safe'),
                      'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
                      '| held10y pass=', hold['final_pass'],
                      '(%.0fs)' % vent[key]['seconds'], flush=True)
    save(RESULT, r)


if __name__ == '__main__':
    main()
