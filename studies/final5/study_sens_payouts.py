"""Sensitivity section (owner ask 8 Nov 13:12 SGT): Stage 3 - payout dial.
How much monthly spending can the portfolio carry at 10/20/30y? Payout
50k/100k per month (250k is the base in final5_horizon.json), both carry
views, dual-law judging, same seed family 20261109 and same price draws
(tag f5_h{weeks}_{view}); amounts scale with the payout exactly as
study_tips_charts.sec_payout does at 10y (radius scaled with payout size).
Checkpointed per cell in results/final5_sens_payouts.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, save, load, f5_fit, dual_mix_search, judge_frozen

R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'final5_sens_payouts.json'
YEARS = [10, 20, 30]
PAYOUTS = [50000.0, 100000.0]
SEED = 20261109


def scaled_draws(c, fit, tag, scale):
    """f5_draws with amounts scaled by payout ratio (price paths shared)."""
    val, vp, fin, fp = S.get_draws(c, fit, tag, payout_scale=scale)
    f = common5.DRAW_DIR / f'{tag}_{common5.FIFTH_LAW}.npz'
    z = np.load(f, allow_pickle=False)  # guaranteed cached by stage 1
    val2, fin2 = common5._unpack(z, 'v', 4), common5._unpack(z, 'f', 4)
    if scale != 1.0:
        def sc(ds):
            out = []
            for d in ds:
                out.append(common5.ScenarioDraw((d[0], d[1] * scale, d[2], d[3] * scale, d[4]),
                                                d.funding_paths, d.re_price_logs))
            return out
        val2, fin2 = sc(val2), sc(fin2)
    vp2 = [S.probabilities(c, v[0], v.re_price_logs) for v in val2]
    fp2 = [S.probabilities(c, x[0], x.re_price_logs) for x in fin2]
    return (val, vp, fin, fp), (val2, vp2, fin2, fp2)


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 SENS stage 3 (owner ask 8 Nov 13:12 SGT): payout 50k/100k per month '
               'at 10/20/30y, both carry views, dual-law judging, seed family %d, price draws '
               'shared with the limit studies (amounts scaled, radius scaled with payout, '
               'sec_payout precedent). 250k cells live in final5_horizon.json.' % SEED),
        seed_family=SEED, years=YEARS, payouts=PAYOUTS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        prop = r2[view]['sleeve']['proportions']
        frozen = r2[view]['dual']['weights']
        for years in YEARS:
            for monthly in PAYOUTS:
                key = f'{years}y_p{int(monthly/1000)}k'
                if key in vent:
                    continue
                t0 = time.perf_counter()
                scale = monthly / 250000.0
                c = S.nm_config(weeks=52 * years, months=12 * years, payout=monthly,
                                radius_scale=scale)
                c['seed'] = SEED
                c['carry_view'] = view
                c['label'] += (' FINAL-5 SENS payout (owner ask 8 Nov 13:12 SGT): $%dk/month, '
                               'seed family %d, carry view %s, dual-law.' % (monthly / 1000, SEED, view))
                fit = f5_fit(c)
                tag = f'f5_h{52 * years}_{view}'
                primary, fifth = scaled_draws(c, fit, tag, scale)
                search = dual_mix_search(c, primary, fifth, prop,
                                         label=f'FINAL-5 SENS {view}, {years}y, ${monthly/1000:.0f}k/month, dual-law')
                hold = judge_frozen(c, primary, fifth, frozen,
                                    label=f'frozen round-2 {view} mix at {years}y, ${monthly/1000:.0f}k/month')
                vent[key] = dict(years=years, monthly=monthly,
                                 total_paid=12 * years * monthly,
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
