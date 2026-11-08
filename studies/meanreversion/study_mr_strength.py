"""MR scenario: calibration strength sensitivity (weak/strong vs central) at
10y and 30y, fitted carry view, seed 20261109. Shows how much of the MR
effect survives halving or 1.5x-ing the declared reversion. Also records the
analytic variance-ratio table for all three calibrations."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_mr
from common_mr import f5_fit, dual_mix_search, judge_frozen, mr_config, mr_draws, save_mr, load_mr
from emfin_v2.mean_reversion import variance_ratio

YEARS = [10, 30]
R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'mr_strength.json'


def main():
    r = load_mr(RESULT)
    r.setdefault('meta', dict(
        label=('MR scenario: calibration strength (weak/central/strong) at 10/30y, fitted '
               'view, seed 20261109, dual-law. Central cells mirrored from mr_horizon.json.'),
        calibrations=common_mr.CALIBRATIONS))
    r.setdefault('variance_ratio', {
        name: {f'{y}y': round(float(v), 4) for y, v in
               zip([1, 3, 5, 8, 15, 30], variance_ratio(p, [52 * y for y in [1, 3, 5, 8, 15, 30]]))}
        for name, p in common_mr.CALIBRATIONS.items()})
    r2 = json.loads(R2.read_text())
    view = 'fitted'
    prop = r2[view]['sleeve']['proportions']
    frozen = r2[view]['dual']['weights']
    for mr in ('weak', 'strong'):
        vent = r.setdefault(mr, {})
        for years in YEARS:
            key = f'{years}y'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = mr_config(view=view, seed=20261109, mr=mr, weeks=52 * years, months=12 * years)
            fit = f5_fit(c)
            tag = f'mr{mr}_h{52 * years}_{view}'
            primary, fifth = mr_draws(c, fit, tag)
            search = dual_mix_search(c, primary, fifth, prop,
                                     label=f'MR {mr} {view}, {years}y, dual-law')
            hold = judge_frozen(c, primary, fifth, frozen,
                                label=f'frozen round-2 {view} mix at {years}y under MR {mr}')
            vent[key] = dict(years=years, search=search, hold_10y_mix=hold,
                             seconds=time.perf_counter() - t0)
            save_mr(RESULT, r)
            print(mr, key, 'safe=', search.get('chosen_safe'),
                  'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
                  '(%.0fs)' % vent[key]['seconds'], flush=True)
    save_mr(RESULT, r)


if __name__ == '__main__':
    main()
