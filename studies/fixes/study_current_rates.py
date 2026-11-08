"""Fix 5: full re-run at current market rates as a second default view
(open point 5: fitted estimation window quietly drives the answer; fitted
bill carry 1.81%/yr vs today's quote).

Method: identical pipeline as the base new-model run, except the fitted
weekly log means of the three safe listed assets are replaced by current
market quotes (5 Nov 2026, FRED/H.15):
  tbill    <- DGS3MO 4.17% (3-month constant maturity)
  treasury <- DGS10  4.84% (10-year constant maturity; IEF is a 7-10y roll,
              labeled simplification: expected log return = current yield,
              i.e. no average rate change, no roll/term-premium adjustment)
  tips     <- DFII10 2.60% real + 2.24% breakeven (= DGS10 - DFII10) = 4.84%
              nominal; labeled the same way
Volatilities, correlations and all other moments stay as fitted on the full
history (labeled). Equity/gold/property means unchanged. The 1y sleeve solve
and the 10y study both see the override.
"""
import sys, time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import S, save, full_pipeline

RATES = dict(dgs3mo=0.0417, dgs10=0.0484, dfii10=0.0260, asof='2026-11-05',
             source='FRED H.15 daily (DGS3MO/DGS10/DFII10), fetched 8 Nov 2026')


def current_rate_fit(c, fit):
    frame, mu, cov = fit
    ids = list(frame.columns)
    mu = mu.copy()
    breakeven = RATES['dgs10'] - RATES['dfii10']
    targets = dict(tbill=RATES['dgs3mo'], treasury=RATES['dgs10'],
                   tips=RATES['dfii10'] + breakeven)
    for name, annual in targets.items():
        mu[ids.index(name)] = np.log1p(annual) / 52
    return frame, mu, cov


def main():
    label = ('SECOND DEFAULT VIEW (owner ask 8 Nov 11:05, open point 5): safe-asset carry at '
             'current market quotes %(asof)s - 3M bill %(dgs3mo)s, 10y %(dgs10)s, 10y TIPS real '
             '%(dfii10)s - replacing the fitted-window carry. Labeled simplifications: IEF/TIP '
             'expected log return set to current yield (no roll/term-premium model); vols, '
             'correlations, risky means unchanged from full-history fit.' % RATES)
    t0 = time.perf_counter()
    c, fit, draws, res = full_pipeline('h520_curr', label, fit_override=current_rate_fit)
    res['seconds_total'] = time.perf_counter() - t0
    res['rates'] = RATES
    out = load_result = {'meta': dict(label=label, rates=RATES), 'current_rates': res}
    save('fix5_current_rates.json', out)
    print('safe=', res.get('chosen_safe'), 'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6),
          'weights=', res.get('weights'), flush=True)


if __name__ == '__main__':
    main()
