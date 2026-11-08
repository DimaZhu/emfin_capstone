"""UIF item 4 (owner ask 8 Nov 2026 17:09 SGT): fees, no tax - "include fees
(especially since this effects rebalancing)".

Two layers, all labeled sensitivities on the frozen round-2 mixes, owner
defaults, dual-law draws (seed family 20261109; 10y band on 20261111):

A. Execution-policy layer. simulate_fees (common_uif) re-runs the final5
   policy dial - cash_first (never rebalances), annual_rebal, threshold_10,
   glide_annual - under fee tiers:
     trade0     no added fees (current labeled state: sell haircuts 5-20bp only)
     trade10    +10bp on every trade (rebalance buys+sells, payout liquidations)
     trade25    +25bp on every trade (conservative)
     trade10+aum25  +10bp trades and +0.25%/yr holding fee on listed sleeves
     trade10+aum50  +10bp trades and +0.50%/yr holding fee on listed sleeves
   Metrics: terminal tail upper bound (same statistic as final5 policies),
   funded fraction, turnover, mean total fees, terminal median/q05.
   Horizons 10/20/30y, both carry views.

B. Holding-fee drag on the safe-share search (10y): fitted weekly log means
   of ALL listed sleeves (incl. tbill - a bill fund also charges) reduced by
   0.25%/yr and 0.50%/yr, then the full dual-law mix search. This covers
   holding fees only; trading fees are a policy-layer effect, not a
   buy-hold-mark effect, and the judge never rebalances (disclosed).

No tax anywhere, per the owner instruction.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'final5'))
import common_uif as U
from common_uif import S, common5
from study_q3_rebalance import terminal_tail, frozen_vector

R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'uif4_fees.json'
TIERS = dict(trade0=dict(fee_trade=0.0, fee_aum_annual=0.0),
             trade10=dict(fee_trade=0.001, fee_aum_annual=0.0),
             trade25=dict(fee_trade=0.0025, fee_aum_annual=0.0),
             trade10_aum25=dict(fee_trade=0.001, fee_aum_annual=0.0025),
             trade10_aum50=dict(fee_trade=0.001, fee_aum_annual=0.005))
POLICIES = ['cash_first', 'annual_rebal', 'threshold_10', 'glide_annual']


def main():
    r = U.load(RESULT)
    r.setdefault('meta', dict(
        label=('UIF item 4 (owner ask 8 Nov 17:09 SGT): fees, no tax. Execution-policy layer: '
               'trading fee tiers 0/10/25bp and holding fees 0/0.25/0.50%%/yr on listed '
               'sleeves, on top of the existing 5-20bp sell haircuts; frozen round-2 mixes; '
               'policies cash_first/annual_rebal/threshold_10/glide_annual; 10/20/30y. '
               'Search layer: 0.25/0.50%%/yr mean drag on all listed sleeves, 10y dual-law '
               'search. Labeled sensitivity; engine unchanged.').replace('%%', '%'),
        tiers={k: v for k, v in TIERS.items()}, policies=POLICIES))
    r2 = json.loads(R2.read_text())
    h15 = json.loads(Path('studies/final5/results/final5_horizon.json').read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        static = {int(y): h15[view][f'{y}y']['search'].get('chosen_safe') for y in (10, 20, 30)}
        s10 = static[10]
        for years in (10, 20, 30):
            seeds = (U.SEED_BASE, U.SEED_BAND) if years == 10 else (U.SEED_BASE,)
            for seed in seeds:
                key = f'{years}y_s{seed}'
                if key in vent:
                    continue
                t0 = time.perf_counter()
                c = U.uif_config(view=view, seed=seed, weeks=52 * years, months=12 * years)
                fit = U.uif_fit(c)
                _, (_, _, fin2, fp2) = U.fresh_draws(c, fit)
                w0, ids = frozen_vector(c, r2[view]['dual']['weights'])
                cell = dict(years=years, seed=seed,
                            weights={i: round(float(w), 4) for i, w in zip(ids, w0)},
                            glide=(static[years], s10), policies={})
                for tier, fees in TIERS.items():
                    for pol in POLICIES:
                        glide = (static[years], s10) if pol == 'glide_annual' else None
                        pay = [U.simulate_fees(c, d, w0, pol, glide, **fees) for d in fin2]
                        wp = [z['net_wealth_paths'][:, -1] for z in pay]
                        tt = terminal_tail(c, fin2, fp2, w0, wp)
                        cell['policies'][f'{pol}|{tier}'] = dict(
                            terminal_ru=tt['terminal_ru'], q05=tt['q05'], median=tt['median'],
                            funded=float(np.mean([z['funded'].mean() for z in pay])),
                            turnover=float(np.mean([z['turnover'].mean() for z in pay])),
                            total_fees=float(np.mean([z['total_fees'].mean() for z in pay])),
                            total_fees_median=float(np.median(np.concatenate([z['total_fees'] for z in pay]))))
                cell['seconds'] = time.perf_counter() - t0
                vent[key] = cell
                U.save(RESULT, r)
                print(view, key, '(%.0fs)' % cell['seconds'], flush=True)
        # B. holding-fee drag on the 10y search
        for drag in (0.0025, 0.005):
            key = f'10y_search_drag{drag:.4f}'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = U.uif_config(view=view, seed=U.SEED_BASE, weeks=520, months=120)
            fit = U.uif_fit(c)
            frame, mu, cov = fit
            n_liquid = len(c['liquidity_haircuts'])
            mu_d = mu.copy()
            mu_d[:n_liquid] -= drag / 52
            fit_d = (frame, mu_d, cov)
            c['label'] += (' UIF4 LABELED: holding-fee drag %.2f%%/yr subtracted from ALL '
                           'listed-sleeve fitted means (incl. tbill); trading fees excluded '
                           '(policy-layer effect).' % (drag * 100))
            primary, fifth = U.fresh_draws(c, fit_d)
            prop = r2[view]['sleeve']['proportions']
            search = common5.dual_mix_search(c, primary, fifth, prop,
                                             label=f'UIF4 holding-fee drag {drag:.2%}/yr, 10y dual-law')
            vent[key] = dict(drag_annual=drag, chosen_safe=search.get('chosen_safe'),
                             validation_selected_safe=search.get('validation_selected_safe'),
                             note=search.get('note'),
                             ce=search.get('common_cara_ledger_ce'),
                             seconds=time.perf_counter() - t0)
            U.save(RESULT, r)
            print(view, key, 'safe=', search.get('chosen_safe'), flush=True)
    U.save(RESULT, r)


if __name__ == '__main__':
    main()
