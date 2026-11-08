"""Round 2, real-terms repricing: what the round-2 recommended portfolios
promise in today's dollars (fix-3 machinery on the fresh seed family).

For each carry view (fitted, current-quotes) the dual-law recommended mix is
judged and scored on fresh CPI-deflated draws: TIPS as a real instrument
(mean-inflation deflated; current-quotes view drift-corrected to the 2.60%
DFII10 real yield), payouts inflation-indexed. Labeled: inflation independent
of assets; 15% terminal and 40% any-point limits read in real dollars.
"""
import sys, json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fixes'))

from common2 import S, save, load, FRESH_SEED  # noqa: E402
import study_real_terms as R  # noqa: E402


def real_setup(view):
    c = R.real_config()
    c['seed'] = FRESH_SEED
    c['label'] += ' ROUND 2 (owner plan 8 Nov 11:37): fresh seed family.'
    if view == 'fitted':
        fit = S.setup(c)
        val, vp, fin, fp = R.make_real_draws(c, fit, 'r2_h520_rtipsdef')
    else:
        fit = R.current_rate_fit_nominal_only(c, S.setup(c))
        val, vp, fin, fp = R.make_real_draws(c, fit, 'r2_h520_curr_rtips', tips_real_drift=0.026)
    return c, (val, vp, fin, fp)


def reprice(view, weights, r, mix_spec=None):
    c, (val, vp, fin, fp) = real_setup(view)
    ids = c['asset_layout']['ids']
    if mix_spec is not None:
        # exact reconstruction from safe share + sleeve proportions (rounded
        # weight dicts would nudge the fixed 10% property holding off target)
        prop, safe = mix_spec
        mix, ids = S.mix_fn(c, prop)
        a = mix(float(safe)) * c['wealth']
        weights = {n: round(float(wi), 6) for n, wi in zip(ids, a / c['wealth'])}
    else:
        a = np.array([weights.get(i, 0.0) for i in ids], float)
        a = a / a.sum() * c['wealth']
    v = S.evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
    row = dict(view=view, weights=weights, final_pass=bool(v['overall_pass']),
               final_breaches=v.get('breaches'))
    row.update(S.score_final(c, fin, fp, a))
    r.setdefault('real_repricing', {})[view] = row
    save('round2_real_repricing.json', r)
    print(view, 'real judge pass=', row['final_pass'], 'real CE=%.1fM' % (row['common_cara_ledger_ce'] / 1e6),
          'q05=%.1fM' % (row['terminal_q05'] / 1e6), 'breaches=', row['final_breaches'], flush=True)


def main():
    r = load('round2_real_repricing.json')
    r.setdefault('meta', dict(
        label='ROUND 2 STUDY (owner plan 8 Nov 11:37): real-terms repricing of the dual-law '
              'recommended mixes on fresh CPI-deflated draws. Fix-3 machinery, fresh seed family.',
        fresh_seed=FRESH_SEED))
    dual = json.loads((Path(__file__).resolve().parent / 'results' / 'round2_dual_law.json').read_text())
    for view in ('fitted', 'current_quotes'):
        if view in r.get('real_repricing', {}):
            continue
        rec = dual[view]['dual']
        if not rec.get('chosen_safe'):
            print(view, 'no dual-law recommendation to reprice', flush=True)
            continue
        prop = dual[view]['sleeve']['proportions']
        reprice(view, rec['weights'], r, mix_spec=(prop, rec['chosen_safe']))


if __name__ == '__main__':
    main()
