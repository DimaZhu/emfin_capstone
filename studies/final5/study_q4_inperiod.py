"""FINAL-5, question 4 (owner ask 8 Nov 12:20): the in-period (any-point) loss
limit - how tightening/loosening it changes the answer.

Fresh confirmation of the new-model cml sweep (seed 20261107, single-law,
fitted carry). This run: 10y horizon, terminal loss limit fixed at the owner
default 15%, any-point cap swept over 5/10/15/25/40/60%, BOTH carry views,
dual-law judging, fresh seed family 20261109. Same frozen round-2 1y sleeves.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common5 import (S, save, load, f5_config, f5_fit, f5_draws, dual_mix_search,
                     FRESH_SEED)

CMLS = [0.05, 0.10, 0.15, 0.25, 0.40, 0.60]
R2 = Path('studies/round2/results/round2_dual_law.json')


def main():
    r = load('final5_inperiod.json')
    r.setdefault('meta', dict(
        label=f'FINAL-5 Q4: any-point (in-period) loss cap sweep at 10y, terminal 15% fixed, '
              f'both carry views, dual-law judging. Fresh seed family {FRESH_SEED}.',
        fresh_seed=FRESH_SEED, cmls=CMLS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        prop = r2[view]['sleeve']['proportions']
        vent = r.setdefault(view, {})
        for cml in CMLS:
            key = f'{cml:.2f}'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = f5_config(view=view, weeks=520, months=120, cml=cml, loss=0.15)
            fit = f5_fit(c)
            tag = f'f5_h520_{view}'  # same horizon: reuse the Q3 draws
            primary, fifth = f5_draws(c, fit, tag)
            res = dual_mix_search(c, primary, fifth, prop,
                                  label=f'FINAL-5 {view}, 10y, any-point cap {cml:.0%}, terminal 15%, dual-law')
            res['seconds'] = time.perf_counter() - t0
            vent[key] = res
            save('final5_inperiod.json', r)
            print(view, 'cml=%.2f' % cml, 'safe=', res.get('chosen_safe'),
                  'CE=%.2fM' % (res.get('common_cara_ledger_ce', 0) / 1e6),
                  '(%.0fs)' % res['seconds'], flush=True)
    save('final5_inperiod.json', r)


if __name__ == '__main__':
    main()
