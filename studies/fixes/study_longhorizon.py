"""Fix 4: true long-horizon optimization instead of 1y-proportion screens
(open point 4: the 10-30y results fixed the risky sleeve at 1-year optimizer
proportions and searched only the safe share; the true long-horizon optimum
could look different).

Method: run the SAME cvxpy multi-period solve the 1y sleeve uses, but directly
on the 10-year training draws (520 weeks, 120 payout dates). Check size
stability at n=100/200/400 scenarios. Then feed the 10y-derived risky sleeve
proportions into the frozen validation discipline (same draws, same mix
search, same independent final judge) and compare the validated portfolio and
score against the 1y-proportion base.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import S, save, load


def solve_at(c, fit, n):
    dr = S.draw_paths(c, fit, n, c['seed'])
    p, ps = S.probabilities(c, dr[0], dr.re_price_logs)
    t0 = time.perf_counter()
    raw, status = S.solve(c, dr, p, ps, 1.)
    dt = time.perf_counter() - t0
    ids = c['asset_layout']['ids']
    if raw is None:
        return dict(n=n, seconds=dt, status=status.get('kind'), reason=status.get('reason'))
    w = {a: float(raw[i] / c['wealth']) for i, a in enumerate(ids)}
    return dict(n=n, seconds=dt, status=status.get('kind'), weights=w)


def main():
    r = load('fix4_longhorizon.json')
    r.setdefault('meta', dict(
        label='LABELED STUDY (owner ask 8 Nov 11:05, open point 4): true 10y optimization. '
              'Same solver, budgets and draws family as the 1y sleeve; only the horizon changes.'))
    c = S.nm_config()
    fit = S.setup(c)
    solves = r.setdefault('solves', {})
    # n=400 exceeds this box's per-run compute budget and the engine's own
    # solver time caps (CLARABEL cap, SCS fallback); 100 vs 200 is the
    # scenario-noise check. Labeled limitation.
    r['meta']['solve_size_note'] = ('n=400 not run: exceeds sandbox compute and the engine solver '
                                    'time caps; n=100 vs n=200 used as the scenario-noise check.')
    for n in (100, 200):
        key = str(n)
        if key not in solves:
            solves[key] = solve_at(c, fit, n)
            save('fix4_longhorizon.json', r)
        s = solves[key]
        print('solve n=%s %s %.1fs' % (key, s['status'], s['seconds']),
              {k: round(v, 3) for k, v in (s.get('weights') or {}).items() if v > 1e-4}, flush=True)
    # sleeve proportions from the largest successful solve
    big = solves.get('200') if solves.get('200', {}).get('weights') else solves.get('100')
    ids = c['asset_layout']['ids']
    mins, fixed = S.holding_bounds(c, len(ids))
    fixed = {int(k): v for k, v in fixed.items()}
    safe_idx = ids.index('tbill')
    w = big['weights']
    risky = {a: w[a] for i, a in enumerate(ids)
             if i != safe_idx and i not in fixed and mins[i] == 0 and a != 'cash' and w[a] > 1e-6}
    tot = sum(risky.values())
    prop = {k: v / tot for k, v in risky.items()}
    r['sleeve_10y'] = dict(proportions=prop, safe_share_raw=w['tbill'], source_n=big['n'])
    if 'mix_10y_sleeve' not in r:
        val, vp, fin, fp = S.get_draws(c, fit, 'h520')
        t0 = time.perf_counter()
        res = S.mix_search(c, val, vp, fin, fp, prop,
                           label='10y-solve sleeve proportions (fix 4), frozen validation discipline')
        res['seconds'] = time.perf_counter() - t0
        r['mix_10y_sleeve'] = res
        save('fix4_longhorizon.json', r)
    m = r['mix_10y_sleeve']
    print('10y sleeve -> safe=', m.get('chosen_safe'),
          'CE=%.1fM' % (m.get('common_cara_ledger_ce', 0) / 1e6), m.get('weights'), flush=True)


if __name__ == '__main__':
    main()
