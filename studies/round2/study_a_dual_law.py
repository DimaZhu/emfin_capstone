"""Round 2, items A+B: the regime/bootstrap fifth law in the judge, and the
current-quotes carry as a second default view - one pipeline, two views.

Owner plan (WhatsApp 8 Nov 11:36, approved 11:37). Everything on the fresh
seed family 20261108 (training, validation, final, and the fifth law's own
draws are all disjoint from earlier studies).

Per view (fitted carry, current-quotes carry):
  sleeve    1y CARA optimizer sleeve on that view's fit
  single    mix search judged on the mixture law only (reference)
  dual      mix search judged on mixture + fhs_ewma (the new discipline)
"""
import sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import (S, save, load, fresh_config, fresh_fit, dual_draws,
                     dual_mix_search, FIFTH_LAW, FRESH_SEED)


def sleeve_1y(c10, fit10):
    """1y CARA optimizer sleeve (52-week config, same as the frozen discipline),
    on the fresh seed and this view's carry override."""
    c = fresh_config(view=c10.get('carry_view', 'fitted'), one_year_sleeve=True)
    fit = fresh_fit(c)
    dr = S.draw_paths(c, fit, 100, c['seed'])
    p, ps = S.probabilities(c, dr[0], dr.re_price_logs)
    raw, status = S.solve(c, dr, p, ps, 1.)
    ids = c['asset_layout']['ids']
    mins, fixed = S.holding_bounds(c, len(ids))
    fixed = {int(k): v for k, v in fixed.items()}
    safe_idx = ids.index('tbill')
    risky = {}
    for i, a in enumerate(ids):
        if i == safe_idx or i in fixed or mins[i] > 0 or a == 'cash':
            continue
        w = float(raw[i] / c['wealth'])
        if w > 1e-6:
            risky[a] = w
    tot = sum(risky.values())
    return {k: v / tot for k, v in risky.items()}, float(raw[safe_idx] / c['wealth']), status.get('kind')


def run_view(view, r):
    c = fresh_config(view=view)
    fit = fresh_fit(c)
    tag = 'r2_h520' if view == 'fitted' else 'r2_h520_curr'
    primary, fifth = dual_draws(c, fit, tag)
    key = f'{view}'
    entry = r.setdefault(key, {})
    if 'sleeve' not in entry:
        prop, raw_safe, kind = sleeve_1y(c, fit)
        entry['sleeve'] = dict(proportions=prop, raw_safe_share=raw_safe, status=kind)
        save('round2_dual_law.json', r)
    prop = entry['sleeve']['proportions']
    label = ('ROUND 2 %s view, 1y CARA sleeve on fresh seed %d' % (view, FRESH_SEED))
    if 'single' not in entry:
        t0 = time.perf_counter()
        val, vp, fin, fp = primary
        res = S.mix_search(c, val, vp, fin, fp, prop, label=label + ' (single-law reference)')
        res['seconds'] = time.perf_counter() - t0
        entry['single'] = res
        save('round2_dual_law.json', r)
        print(view, 'single safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'dual' not in entry:
        t0 = time.perf_counter()
        res = dual_mix_search(c, primary, fifth, prop, label=label + ' (dual-law: mixture + %s)' % FIFTH_LAW)
        res['seconds'] = time.perf_counter() - t0
        if 'fifth_law_final' in res:
            res['fifth_law_score'] = res.pop('fifth_law_final')['ce']
        entry['dual'] = res
        save('round2_dual_law.json', r)
        print(view, 'dual safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)


def main():
    r = load('round2_dual_law.json')
    r.setdefault('meta', dict(
        label='ROUND 2 STUDY (owner plan 8 Nov 11:37): fhs_ewma regime/bootstrap variant as a '
              'fifth judging law; current-quotes carry as second default view. Fresh seed family.',
        fresh_seed=FRESH_SEED, fifth_law=FIFTH_LAW))
    for view in ('fitted', 'current_quotes'):
        run_view(view, r)
    save('round2_dual_law.json', r)


if __name__ == '__main__':
    main()
