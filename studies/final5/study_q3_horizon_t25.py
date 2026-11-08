"""FINAL-5 follow-up (owner ask 8 Nov 12:42 SGT): horizon sweep with the
terminal-loss limit set to 25% instead of 15%, tested at the END of each
horizon (5/10/15/20/30y). Owner's words: "Scale it with Horizon and push it
everywhere to 25% instead", clarified "No I meant depending on the test at
the end of the investment horizon" - read as: 25% terminal-loss limit at
each horizon's end; every other limit unchanged (40% any-point cap, 20%
per-payment tail, model-miss buffer untouched).

Same discipline as studies/final5/study_q3_horizon.py (15% run, seed family
20261109): BOTH carry views (fitted / current quotes), dual-law judging
(mixture + fhs_ewma), risky sleeve proportions frozen at the round-2 1y
sleeves per view, $250k/month throughout (only 12 months owner-confirmed;
longer payouts are a labeled sensitivity). Fresh seed family 20261110,
disjoint from 20261107 / 20261108 / 20261109.

The 15% results in results/final5_horizon.json are the comparison base;
nothing in the 15% machinery is changed.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, save, load, f5_fit, dual_mix_search, judge_frozen

YEARS = [5, 10, 15, 20, 30]
R2 = Path('studies/round2/results/round2_dual_law.json')
SEED = 20261110          # fresh family, disjoint from 20261107/08/09
LOSS = 0.25              # owner 8 Nov 12:42 SGT: terminal limit 25% at horizon end
RESULT = 'final5_horizon_t25.json'


def t25_config(view='fitted', **kw):
    c = S.nm_config(loss=LOSS, **kw)
    c['seed'] = SEED
    c['carry_view'] = view
    c['label'] += (' FINAL-5 T25 (owner ask 8 Nov 12:42 SGT): terminal-loss limit 25%% '
                   '(was 15%%) at each horizon end; seed family %d; carry view %s; '
                   'dual-law judging (mixture + %s). All other limits unchanged.'
                   % (SEED, view, common5.FIFTH_LAW))
    return c


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 T25: horizon sweep 5/10/15/20/30y, terminal-loss limit 25%% at each '
               'horizon end (owner 8 Nov 12:42 SGT), both carry views, dual-law judging. '
               'Fresh seed family %d, disjoint from 20261107/20261108/20261109. Comparison '
               'base: final5_horizon.json (15%% limit, seed family 20261109).' % SEED),
        fresh_seed=SEED, terminal_loss_limit=LOSS, years=YEARS,
        comparison='studies/final5/results/final5_horizon.json'))
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
            c = t25_config(view=view, weeks=52 * years, months=12 * years)
            fit = f5_fit(c)
            tag = f'f5t25_h{52 * years}_{view}'
            primary, fifth = common5.f5_draws(c, fit, tag)
            search = dual_mix_search(c, primary, fifth, prop,
                                     label=f'FINAL-5 T25 {view} view, {years}y horizon, '
                                           f'dual-law, seed {SEED}, terminal 25%')
            hold = judge_frozen(c, primary, fifth, frozen,
                                label=f'frozen round-2 {view} recommended mix held at {years}y '
                                      f'under 25% terminal')
            vent[key] = dict(years=years, months=12 * years,
                             total_paid=12 * years * 250000.0,
                             search=search, hold_10y_mix=hold,
                             seconds=time.perf_counter() - t0)
            save(RESULT, r)
            print(view, key, 'safe=', search.get('chosen_safe'),
                  'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
                  '| held10y pass=', hold['final_pass'],
                  'CE=%.1fM' % (hold.get('common_cara_ledger_ce', 0) / 1e6),
                  '(%.0fs)' % vent[key]['seconds'], flush=True)
    save(RESULT, r)


if __name__ == '__main__':
    main()
