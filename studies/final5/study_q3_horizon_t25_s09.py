"""FINAL-5 follow-up (owner ask 8 Nov ~13:05 SGT, "Sure!" to the agent's
offer): re-run the 25% terminal-loss horizon sweep on the SAME seed family
as the 15% run (20261109), so ONLY the limit changes (15% -> 25%) and the
seed-family noise flagged in the t25 run (seed 20261110) drops out.

Identical draws: same seed family, same draw tags (f5_h*) and the same
f5_draws pipeline as studies/final5/study_q3_horizon.py. Draws and the
carry fit are loss-independent (verified in study_tips_charts.py:
draw_paths / probabilities / setup do not read loss_budget or cml_budget),
so every difference vs results/final5_horizon.json is the limit.

Everything else unchanged: BOTH carry views, dual-law judging (mixture +
fhs_ewma), frozen round-2 sleeves, $250k/month (12 months owner-confirmed;
longer payouts are a labeled sensitivity), 40% any-point cap, 20%
per-payment tail, model-miss buffer untouched.

Comparison bases: results/final5_horizon.json (15% limit, seed 20261109)
and results/final5_horizon_t25.json (25% limit, seed 20261110).
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
SEED = 20261109          # SAME family as the 15% run: identical draws, only the limit changes
LOSS = 0.25              # owner 8 Nov 12:42 SGT: terminal limit 25% at horizon end
RESULT = 'final5_horizon_t25_s09.json'


def t25_config(view='fitted', **kw):
    c = S.nm_config(loss=LOSS, **kw)
    c['seed'] = SEED
    c['carry_view'] = view
    c['label'] += (' FINAL-5 T25-S09 (owner ask 8 Nov 12:42 + 13:05 SGT): terminal-loss '
                   'limit 25%% (was 15%%) at each horizon end, on the SAME seed family %d '
                   'as the 15%% run - isolates the limit change; carry view %s; '
                   'dual-law judging (mixture + %s). All other limits unchanged.'
                   % (SEED, view, common5.FIFTH_LAW))
    return c


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 T25-S09: horizon sweep 5/10/15/20/30y, terminal-loss limit 25%% at '
               'each horizon end (owner 8 Nov 12:42 SGT), SAME seed family %d as the 15%% '
               'run (owner 13:05 SGT "Sure!"), both carry views, dual-law judging. Only the '
               'limit differs from final5_horizon.json.' % SEED),
        seed_family=SEED, terminal_loss_limit=LOSS, years=YEARS,
        same_draws_as='studies/final5/results/final5_horizon.json',
        comparison=('studies/final5/results/final5_horizon.json',
                    'studies/final5/results/final5_horizon_t25.json')))
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
            tag = f'f5_h{52 * years}_{view}'
            primary, fifth = common5.f5_draws(c, fit, tag)
            search = dual_mix_search(c, primary, fifth, prop,
                                     label=f'FINAL-5 T25-S09 {view} view, {years}y horizon, '
                                           f'dual-law, seed {SEED} (same draws as 15% run), '
                                           f'terminal 25%')
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
