"""MR scenario: loss-limit dials under mean reversion. Mirrors
studies/final5/study_sens_limits.py (terminal 5/35/50%, any-point 5/15/25%,
5 horizons, both views, seed 20261109) with the MR law as primary; draws
shared with mr_horizon.json cells. Checkpointed per cell."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_mr
from common_mr import f5_fit, dual_mix_search, judge_frozen, mr_config, mr_draws, save_mr, load_mr

YEARS = [5, 10, 15, 20, 30]
TERMINAL_LOSSES = [0.05, 0.35, 0.50]
CMLS = [0.05, 0.15, 0.25]
R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'mr_sens_limits.json'


def run_cell(r, r2, vent, view, years, key, loss, cml):
    if key in vent:
        return
    t0 = time.perf_counter()
    c = mr_config(view=view, seed=20261109, weeks=52 * years, months=12 * years,
                  loss=loss, cml=cml)
    fit = f5_fit(c)
    tag = f'mr09_h{52 * years}_{view}'
    primary, fifth = mr_draws(c, fit, tag)
    prop = r2[view]['sleeve']['proportions']
    frozen = r2[view]['dual']['weights']
    search = dual_mix_search(c, primary, fifth, prop,
                             label=f'MR central {view}, {years}y, terminal {loss:.0%}, any-point {cml:.0%}')
    hold = judge_frozen(c, primary, fifth, frozen,
                        label=f'frozen round-2 {view} mix at {years}y under MR, terminal {loss:.0%}, cml {cml:.0%}')
    vent[key] = dict(years=years, loss=loss, cml=cml, search=search, hold_10y_mix=hold,
                     seconds=time.perf_counter() - t0)
    save_mr(RESULT, r)
    print(view, key, 'safe=', search.get('chosen_safe'),
          'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6), flush=True)


def main():
    r = load_mr(RESULT)
    r.setdefault('meta', dict(
        label=('MR scenario: terminal loss limit and any-point cap swept per horizon under '
               'the MR law (central), both views, seed 20261109. 15%/40% base cells live in '
               'mr_horizon.json. Comparison base: final5_sens_limits.json.'),
        years=YEARS, terminal_losses=TERMINAL_LOSSES, cmls=CMLS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        for years in YEARS:
            for loss in TERMINAL_LOSSES:
                run_cell(r, r2, vent, view, years, f'{years}y_t{loss:.2f}', loss, 0.40)
            for cml in CMLS:
                run_cell(r, r2, vent, view, years, f'{years}y_c{cml:.2f}', 0.15, cml)
    save_mr(RESULT, r)


if __name__ == '__main__':
    main()
