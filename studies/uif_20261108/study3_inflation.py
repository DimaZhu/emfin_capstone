"""UIF item 3 (owner ask 8 Nov 2026 17:09 SGT): inflation-linked payouts.

Base rule stays what it is: $250k/month NOMINAL, judged on nominal dollars.
This study asks the owner's question: if the payout instead GROWS with CPI,
how do the validated safe share and scores move, and what is the real value
of the current nominal payout?

Inflation model (declared): iid monthly log-changes ~ N(mu, sd), fitted on
BLS CPI-U all-items NSA monthly, Jan 1996 - Dec 2025 (359 changes; Oct 2025
missing, dropped): annual mean 2.52%, monthly-change sd 0.357%. Own RNG
stream at +777000, independent of market draws - no CPI/asset linkage is
modeled, so the TIPS sleeve can only help through its real-rate carry, not
through a modeled CPI correlation (declared limitation; property drift is
also not indexed). Tail budget bases scale with the EXPECTED index (the 20%
allowance tracks the expected payment; fixed nominal budget dollars would be
stricter - disclosed in results).

Cells: 10y and 20y, fitted and current_quotes, nominal vs CPI-indexed,
dual-law search, seed family 20261109; 10y repeated on 20261111 for the seed
band. Plus an exploratory sleeve variant at 10y/fitted: treasury sleeve
split 50/50 treasury/TIPS in the risky proportions (TIPS is otherwise never
selected by the frozen proportions - labeled).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_uif as U
from common_uif import S, common5

R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'uif3_inflation.json'
MU_M, SD_M = 0.00207, 0.00357  # fitted BLS CPI-U NSA 1996-2025 monthly log-changes
INFL_SEED_OFFSET = 777000


def cell(c, fit, prop, mode, label):
    """Dual-law search with nominal or CPI-indexed payouts on shared price paths."""
    primary, fifth = U.fresh_draws(c, fit)
    if mode == 'indexed':
        months = c['horizon_weeks'] * 12 // 52 + 1
        idx_val = U.monthly_inflation_index(200, months, MU_M, SD_M, c['seed'] + INFL_SEED_OFFSET)
        idx_fin = U.monthly_inflation_index(400, months, MU_M, SD_M,
                                            c['seed'] + INFL_SEED_OFFSET + 5000)
        idx_mean = np.exp(np.arange(1, months + 1) * MU_M)
        val, vp, fin, fp = primary
        val2, vp2, fin2, fp2 = fifth
        primary = (U.rebase_budgets(U.index_payouts(val, idx_val), idx_mean), vp,
                   U.rebase_budgets(U.index_payouts(fin, idx_fin), idx_mean), fp)
        fifth = (U.rebase_budgets(U.index_payouts(val2, idx_val), idx_mean), vp2,
                 U.rebase_budgets(U.index_payouts(fin2, idx_fin), idx_mean), fp2)
        index_info = dict(mean_index_10y=float(np.exp(120 * MU_M)),
                          q05_index_10y=float(np.exp(120 * MU_M - 1.645 * SD_M * np.sqrt(120))),
                          q95_index_10y=float(np.exp(120 * MU_M + 1.645 * SD_M * np.sqrt(120))))
    else:
        index_info = None
    search = common5.dual_mix_search(c, primary, fifth, prop, label=label)
    out = dict(chosen_safe=search.get('chosen_safe'),
               validation_selected_safe=search.get('validation_selected_safe'),
               note=search.get('note'),
               ce=search.get('common_cara_ledger_ce'),
               fifth_ce=(search.get('fifth_law_score') or {}).get('common_cara_ledger_ce'),
               terminal_q05=search.get('terminal_q05'),
               funded=search.get('funded'),
               weights=search.get('weights'))
    if index_info:
        out['index'] = index_info
    return out


def main():
    r = U.load(RESULT)
    r.setdefault('meta', dict(
        label=('UIF item 3 (owner ask 8 Nov 17:09 SGT): CPI-indexed vs nominal $250k/month. '
               'iid monthly CPI log-changes fitted on BLS CPI-U NSA 1996-2025 (mean 2.52%/yr, '
               'sd 0.357%/mo); independent of market draws; tail budgets scale with the '
               'expected index; nominal rule unchanged. Dual-law, owner defaults.'),
        inflation_model=dict(mu_monthly=MU_M, sd_monthly=SD_M,
                             source='BLS public API CUUR0000SA0, Jan 1996 - Dec 2025, NSA',
                             fetched='8 Nov 2026')))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        prop = r2[view]['sleeve']['proportions']
        vent = r.setdefault(view, {})
        for years in (10, 20):
            for seed in ((U.SEED_BASE, U.SEED_BAND) if years == 10 else (U.SEED_BASE,)):
                for mode in ('nominal', 'indexed'):
                    key = f'{years}y_{mode}_s{seed}'
                    if key in vent:
                        continue
                    t0 = time.perf_counter()
                    c = U.uif_config(view=view, seed=seed, weeks=52 * years, months=12 * years)
                    fit = U.uif_fit(c)
                    out = cell(c, fit, prop, mode, f'UIF3 {view} {years}y {mode} s{seed}')
                    out['seconds'] = time.perf_counter() - t0
                    vent[key] = out
                    U.save(RESULT, r)
                    print(view, key, 'safe=', out['chosen_safe'],
                          'CE=%.1fM' % ((out['ce'] or 0) / 1e6), flush=True)
        # exploratory TIPS sleeve variant, 10y fitted-view proportions only
        if view == 'fitted' and '10y_indexed_tips_sleeve' not in vent:
            prop_tips = dict(prop)
            half = prop_tips.get('treasury', 0) / 2
            prop_tips['treasury'] = half
            prop_tips['tips'] = half
            c = U.uif_config(view=view, seed=U.SEED_BASE, weeks=520, months=120)
            fit = U.uif_fit(c)
            out = cell(c, fit, prop_tips, 'indexed',
                       'UIF3 LABELED EXPLORATORY: treasury sleeve split 50/50 treasury/TIPS, '
                       '10y fitted indexed')
            vent['10y_indexed_tips_sleeve'] = out
            U.save(RESULT, r)
            print(view, '10y_indexed_tips_sleeve', 'safe=', out['chosen_safe'], flush=True)
    U.save(RESULT, r)


if __name__ == '__main__':
    main()
