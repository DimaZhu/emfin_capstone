"""Sensitivity section (owner ask 8 Nov 13:12 SGT): comprehensive dials, no
assumed limits baked in. Stage 1: the two loss limits swept wide, per horizon.

Dial 2 - terminal loss limit at horizon end: 5/35/50% (15% in final5_horizon.json
         and 25% in final5_horizon_t25_s09.json already exist on the SAME seed
         family 20261109 - reused, not rerun).
Dial 3 - in-period (any-point) cap: 5/15/25% at every horizon (40% is the base
         in final5_horizon.json; 10y-only sweep in final5_inperiod.json).

Same-draws discipline: draws are loss/cml-independent (verified in
study_tips_charts.py: draw_paths / probabilities / setup do not read
loss_budget or cml_budget), so all cells reuse the seed-20261109 draws tagged
f5_h{weeks}_{view}; every difference inside a (view, horizon) column is the
dial alone. BOTH carry views, dual-law judging (mixture + fhs_ewma), frozen
round-2 sleeves, $250k/month (12 months owner-confirmed; longer payouts are a
labeled sensitivity), model-miss buffer untouched.

Checkpointed per cell in results/final5_sens_limits.json - safe to resume.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, save, load, f5_fit, dual_mix_search, judge_frozen

YEARS = [5, 10, 15, 20, 30]
TERMINAL_LOSSES = [0.05, 0.35, 0.50]       # 0.15 and 0.25 already on this seed family
CMLS = [0.05, 0.15, 0.25]                  # 0.40 is the base run; q4 swept 10y only
R2 = Path('studies/round2/results/round2_dual_law.json')
SEED = 20261109
RESULT = 'final5_sens_limits.json'


def cfg(view='fitted', **kw):
    c = S.nm_config(**kw)
    c['seed'] = SEED
    c['carry_view'] = view
    c['label'] += (' FINAL-5 SENS (owner ask 8 Nov 13:12 SGT): limit dials on seed family '
                   '%d (same draws as the 15%%/25%% horizon runs); carry view %s; dual-law '
                   'judging (mixture + %s).' % (SEED, view, common5.FIFTH_LAW))
    return c


def run_cell(r, r2, vent, view, years, key, loss, cml):
    if key in vent:
        return
    t0 = time.perf_counter()
    c = cfg(view=view, weeks=52 * years, months=12 * years, loss=loss, cml=cml)
    fit = f5_fit(c)
    tag = f'f5_h{52 * years}_{view}'
    primary, fifth = common5.f5_draws(c, fit, tag)
    prop = r2[view]['sleeve']['proportions']
    frozen = r2[view]['dual']['weights']
    search = dual_mix_search(c, primary, fifth, prop,
                             label=f'FINAL-5 SENS {view}, {years}y, terminal {loss:.0%}, '
                                   f'any-point {cml:.0%}, dual-law, seed {SEED}')
    hold = judge_frozen(c, primary, fifth, frozen,
                        label=f'frozen round-2 {view} mix held at {years}y, '
                              f'terminal {loss:.0%}, any-point {cml:.0%}')
    vent[key] = dict(years=years, loss=loss, cml=cml,
                     search=search, hold_10y_mix=hold,
                     seconds=time.perf_counter() - t0)
    save(RESULT, r)
    print(view, key, 'safe=', search.get('chosen_safe'),
          'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6),
          '| held10y pass=', hold['final_pass'],
          '(%.0fs)' % vent[key]['seconds'], flush=True)


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 SENS stage 1 (owner ask 8 Nov 13:12 SGT): terminal loss limit and '
               'in-period cap swept wide per horizon, same seed family %d as the 15%%/25%% '
               'runs, both carry views, dual-law judging. 15%%/25%% terminal cells and the '
               '40%% any-point base live in final5_horizon.json / final5_horizon_t25_s09.json.'
               % SEED),
        seed_family=SEED, years=YEARS, terminal_losses=TERMINAL_LOSSES, cmls=CMLS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        for years in YEARS:
            for loss in TERMINAL_LOSSES:
                run_cell(r, r2, vent, view, years, f'{years}y_t{loss:.2f}', loss, 0.40)
            for cml in CMLS:
                run_cell(r, r2, vent, view, years, f'{years}y_c{cml:.2f}', 0.15, cml)
    save(RESULT, r)


if __name__ == '__main__':
    main()
