"""FINAL-5 follow-up (owner question 8 Nov 12:50 SGT): "you can rebalance
yearly, right?" - what the horizon study actually judges, and how annual
rebalancing changes the 20y/30y terminal tail under the regime law
(fhs_ewma), fitted and current-quotes carry views, frozen round-2 mix.

Three policies on the SAME regime-law final draws (4x400, seed family
20261110, shared with the T25 horizon run):
  buy_hold_mark  - what evaluate()'s Held-out terminal-loss tail measures:
                   the frozen mix marked to market (paths @ a). Payouts are
                   NOT deducted here; they live in the funding checks.
  cash_first     - the executable policy audit (ledger twin): cash first,
                   then proportional liquidation; no rebalancing.
  annual_rebal   - cash_first + rebalance to the starting liquid target
                   every 52 weeks (study_tips_charts.simulate, labeled:
                   buys at net unit values, no buy-side cost).

Terminal tail statistic identical to judge_sim: common_tail of terminal
loss per batch over reference/nominal/stressed measures (common hull),
Bonferroni Student-t upper across 4 batches, plus the Wasserstein market
buffer; compared against the 15% (old) and 25% (new) terminal limits.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, f5_fit
from study_q3_horizon_t25 import t25_config
from emfin_v2.evaluation import common_tail
from emfin_v2.toolbox.wasserstein import penalty

R2 = Path('studies/round2/results/round2_dual_law.json')
OUT = Path('studies/final5/results/final5_rebalance_2030.json')


def terminal_tail(c, fin, fp, w0, wealth_paths):
    """evaluate()-identical upper bound on terminal loss for supplied terminal wealth.

    Per batch: common_tail per measure (reference/nominal/stressed) plus the
    common-hull value; Bonferroni Student-t across the FULL check family
    ((n_dates + 2) * 4 measures), exactly as evaluate() computes it; plus the
    Wasserstein market buffer. upper = max over measures.
    """
    n_batches = len(fin)
    n_dates = len(fin[0][2])
    per_batch = []
    for wp, d, (q, qs) in zip(wealth_paths, fin, fp):
        measures = np.array([np.full(len(d[0]), 1 / len(d[0])), q, qs])
        loss = 1 - np.asarray(wp, float) / c['wealth']
        per_batch.append([common_tail(loss, [p], c['confidence'], False) for p in measures]
                         + [common_tail(loss, measures, c['confidence'], False)])
    x = np.asarray(per_batch)
    crit = tdist.ppf(1 - .05 / ((n_dates + 2) * 4), n_batches - 1)
    high = x.mean(0) + crit * x.std(0, ddof=1) / np.sqrt(n_batches)
    names = ['reference', 'nominal', 'stressed', 'common_hull']
    buf = float(penalty(np.asarray(w0, float), c.get('wasserstein_radius', 0),
                        c['confidence'], metric=c.get('wasserstein_metric', 'legacy_l1')))
    upper = float(high.max() + buf)
    return dict(terminal_ru=upper, measure_upper={k: float(v + buf) for k, v in zip(names, high)},
                buffer=buf,
                q05=float(np.quantile(np.concatenate([w for w in wealth_paths]), .05)),
                median=float(np.median(np.concatenate([w for w in wealth_paths]))))


def frozen_vector(c, weights):
    ids = c['asset_layout']['ids']
    a = np.array([weights.get(i, 0.0) for i in ids], float)
    safe_idx = ids.index('tbill') if 'tbill' in ids else int(c['cash_index'])
    a[safe_idx] += 1.0 - a.sum()
    assert abs(a.sum() - 1.0) < 1e-12
    return a, ids


def main():
    r2 = json.loads(R2.read_text())
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    out['meta'] = dict(
        label=('Rebalancing check (owner 8 Nov 12:50 SGT): 20y/30y, regime law fhs_ewma, '
               'frozen round-2 mixes, seed family 20261110 (shared with T25 horizon run). '
               'buy_hold_mark = what the terminal-loss judge measures; cash_first = executed '
               'policy audit twin; annual_rebal = rebalance to target every 52 weeks (labeled '
               'sensitivity: no buy-side cost).'),
        limits=dict(old=0.15, new=0.25))
    for view in ('fitted', 'current_quotes'):
        for years in (20, 30):
            key = f'{view}_{years}y'
            if key in out:
                continue
            c = t25_config(view=view, weeks=52 * years, months=12 * years)
            fit = f5_fit(c)
            tag = f'f5t25_h{52 * years}_{view}'
            _, (_, _, fin2, fp2) = common5.f5_draws(c, fit, tag)
            w0, ids = frozen_vector(c, r2[view]['dual']['weights'])
            a = w0 * c['wealth']
            cell = dict(years=years, view=view, weights={i: round(float(w), 4) for i, w in zip(ids, w0)})
            # 1) buy-and-hold mark-to-market (the judged terminal metric)
            bh = [(d[0] @ a)[:, -1] for d in fin2]
            cell['buy_hold_mark'] = terminal_tail(c, fin2, fp2, w0, bh)
            # 2) executed policies via the labeled rebalance simulator
            for label, weeks in [('cash_first', None), ('annual_rebal', 52)]:
                pay = [S.simulate(c, d, w0, weeks, payouts=True) for d in fin2]
                wp = [z['net_wealth_paths'][:, -1] for z in pay]
                tt = terminal_tail(c, fin2, fp2, w0, wp)
                tt['funded'] = float(np.mean([z['funded'].mean() for z in pay]))
                tt['turnover_mean'] = float(np.mean([z['turnover'].mean() for z in pay]))
                cell[label] = tt
            out[key] = cell
            OUT.write_text(json.dumps(out, default=str, indent=1))
            print(key, flush=True)
            for pol in ('buy_hold_mark', 'cash_first', 'annual_rebal'):
                v = cell[pol]
                print('  %-14s termRU=%.3f (pass15=%s pass25=%s) q05=%.1fM med=%.1fM'
                      % (pol, v['terminal_ru'], v['terminal_ru'] <= 0.15, v['terminal_ru'] <= 0.25,
                         v['q05'] / 1e6, v['median'] / 1e6), flush=True)
    OUT.write_text(json.dumps(out, default=str, indent=1))


if __name__ == '__main__':
    main()
