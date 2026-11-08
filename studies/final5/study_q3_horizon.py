"""FINAL-5, question 3 (owner ask 8 Nov 12:20): investment horizon
5 vs 10/15/20/30 years - how the answer changes.

Fresh confirmation of the 4th-edition/new-model horizon sweep, which was
single-law, fitted-carry only and showed a non-monotonic safe share
(20y at the 10% floor). This run repeats the sweep under the round-2
discipline: BOTH carry views (fitted / current quotes), dual-law judging
(mixture + fhs_ewma), fresh seed family 20261109 disjoint from all earlier
studies. Risky sleeve proportions are the frozen round-2 1y sleeves per view.

Per (view, horizon): dual-law mix search (lowest safe share passing both
laws), plus the view's frozen round-2 recommended mix re-judged at that
horizon ("hold the 10y answer"). $250k/month throughout; only 12 months
are owner-confirmed - the rest is a labeled sensitivity. The 15% terminal
loss limit sits at the END of each horizon (owner nuance 10:23).
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common5 import (S, save, load, f5_config, f5_fit, f5_draws, dual_mix_search,
                     judge_frozen, FRESH_SEED)

YEARS = [5, 10, 15, 20, 30]
R2 = Path('studies/round2/results/round2_dual_law.json')


def main():
    r = load('final5_horizon.json')
    r.setdefault('meta', dict(
        label='FINAL-5 Q3: horizon sweep 5/10/15/20/30y, both carry views, dual-law judging. '
              'Fresh seed family %d, disjoint from 20261107/20261108 families.' % FRESH_SEED,
        fresh_seed=FRESH_SEED, years=YEARS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        prop = r2[view]['sleeve']['proportions']
        frozen = r2[view]['dual']['weights']
        vent = r.setdefault(view, {})
        for years in YEARS:
            key = f'{years}y'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = f5_config(view=view, weeks=52 * years, months=12 * years)
            fit = f5_fit(c)
            tag = f'f5_h{52 * years}_{view}'
            primary, fifth = f5_draws(c, fit, tag)
            search = dual_mix_search(c, primary, fifth, prop,
                                     label=f'FINAL-5 {view} view, {years}y horizon, dual-law, seed {FRESH_SEED}')
            hold = judge_frozen(c, primary, fifth, frozen,
                                label=f'frozen round-2 {view} recommended mix held at {years}y')
            vent[key] = dict(years=years, months=12 * years,
                             total_paid=12 * years * 250000.0,
                             search=search, hold_10y_mix=hold,
                             seconds=time.perf_counter() - t0)
            save('final5_horizon.json', r)
            print(view, key, 'safe=', search.get('chosen_safe'),
                  'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
                  '| held10y pass=', hold['final_pass'],
                  'CE=%.1fM' % (hold.get('common_cara_ledger_ce', 0) / 1e6),
                  '(%.0fs)' % vent[key]['seconds'], flush=True)
    save('final5_horizon.json', r)


if __name__ == '__main__':
    main()
