"""MR scenario, headline question: the horizon effect under mean reversion.

Mirrors studies/final5/study_q3_horizon.py cell-for-cell (5/10/15/20/30y,
both carry views, dual-law judging, frozen round-2 sleeves, $250k/month) but
with the mean-reverting law as primary. Seed families 20261109 and 20261111
so every cell has a frozen iid comparison cell in final5_horizon.json and
final5_sens_seeds.json. Checkpointed per cell; safe to resume.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_mr
from common_mr import f5_fit, dual_mix_search, judge_frozen, mr_config, mr_draws, save_mr, load_mr

YEARS = [5, 10, 15, 20, 30]
SEEDS = [20261109, 20261111]
R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'mr_horizon.json'


def main():
    r = load_mr(RESULT)
    r.setdefault('meta', dict(
        label=('MR scenario: horizon sweep 5/10/15/20/30y under the mean-reverting equity '
               'law (central calibration), both carry views, dual-law judging (MR + fhs_ewma), '
               'seed families 20261109 + 20261111. Comparison bases: final5_horizon.json '
               '(20261109) and final5_sens_seeds.json (20261111).'),
        calibrations=common_mr.CALIBRATIONS, years=YEARS, seeds=SEEDS))
    r2 = json.loads(R2.read_text())
    for seed in SEEDS:
        for view in ('fitted', 'current_quotes'):
            prop = r2[view]['sleeve']['proportions']
            frozen = r2[view]['dual']['weights']
            vent = r.setdefault(f'{view}_s{seed}', {})
            for years in YEARS:
                key = f'{years}y'
                if key in vent:
                    continue
                t0 = time.perf_counter()
                c = mr_config(view=view, seed=seed, weeks=52 * years, months=12 * years)
                fit = f5_fit(c)
                tag = f'mr{seed % 100}_h{52 * years}_{view}'
                primary, fifth = mr_draws(c, fit, tag)
                search = dual_mix_search(c, primary, fifth, prop,
                                         label=f'MR central {view}, {years}y, seed {seed}, dual-law')
                hold = judge_frozen(c, primary, fifth, frozen,
                                    label=f'frozen round-2 {view} mix held at {years}y under MR')
                vent[key] = dict(years=years, months=12 * years,
                                 total_paid=12 * years * 250000.0,
                                 search=search, hold_10y_mix=hold,
                                 seconds=time.perf_counter() - t0)
                save_mr(RESULT, r)
                print(seed, view, key, 'safe=', search.get('chosen_safe'),
                      'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
                      '| held10y pass=', hold['final_pass'],
                      '(%.0fs)' % vent[key]['seconds'], flush=True)
    save_mr(RESULT, r)


if __name__ == '__main__':
    main()
