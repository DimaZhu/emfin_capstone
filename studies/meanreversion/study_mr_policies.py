"""MR scenario: execution-policy dial under mean reversion. Mirrors
studies/final5/study_sens_policies.py (buy-and-hold mark, cash-first, annual
rebalance, 10pp threshold, glide) at 10/20/30y, both views, seed 20261109,
MR final draws shared with mr_horizon.json. Checkpointed per cell."""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'final5'))
import common_mr
from common_mr import f5_fit, mr_config, mr_draws, save_mr, load_mr
from study_sens_policies import simulate_policy
from study_q3_rebalance import terminal_tail, frozen_vector

R2 = Path('studies/round2/results/round2_dual_law.json')
MR_H = Path(__file__).resolve().parent / 'results' / 'mr_horizon.json'
RESULT = 'mr_sens_policies.json'
YEARS = [10, 20, 30]


def main():
    r = load_mr(RESULT)
    r.setdefault('meta', dict(
        label=('MR scenario: execution policies (buy-hold mark, cash-first, annual rebalance, '
               '10pp threshold, glide) under the MR law (central) at 10/20/30y, both views, '
               'seed 20261109. Comparison base: final5_sens_policies.json.'),
        years=YEARS))
    r2 = json.loads(R2.read_text())
    mr_h = json.loads(MR_H.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        h = mr_h[f'{view}_s20261109']
        static = {int(y): h[f'{y}y']['search'].get('chosen_safe') for y in YEARS}
        s10 = h['10y']['search'].get('chosen_safe')
        for years in YEARS:
            key = f'{years}y'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = mr_config(view=view, seed=20261109, weeks=52 * years, months=12 * years)
            fit = f5_fit(c)
            tag = f'mr09_h{52 * years}_{view}'
            (_, _, fin, fp), _ = mr_draws(c, fit, tag)
            w0, ids = frozen_vector(c, r2[view]['dual']['weights'])
            a = w0 * c['wealth']
            cell = dict(years=years, view=view, glide=(static[years], s10))
            bh = [(d[0] @ a)[:, -1] for d in fin]
            cell['buy_hold_mark'] = terminal_tail(c, fin, fp, w0, bh)
            for pol in ('cash_first', 'annual_rebal', 'threshold_10', 'glide_annual'):
                glide = (static[years], s10) if pol == 'glide_annual' else None
                pay = [simulate_policy(c, d, w0, pol, glide) for d in fin]
                wp = [z['net_wealth_paths'][:, -1] for z in pay]
                tt = terminal_tail(c, fin, fp, w0, wp)
                tt['funded'] = float(np.mean([z['funded'].mean() for z in pay]))
                cell[pol] = tt
            cell['seconds'] = time.perf_counter() - t0
            vent[key] = cell
            save_mr(RESULT, r)
            print(view, key, {p: round(cell[p]['terminal_ru'], 3) for p in
                              ('buy_hold_mark', 'cash_first', 'annual_rebal',
                               'threshold_10', 'glide_annual')}, flush=True)
    save_mr(RESULT, r)


if __name__ == '__main__':
    main()
