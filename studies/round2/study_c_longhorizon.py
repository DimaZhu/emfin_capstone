"""Round 2, item C: true 10y sleeve on FRESH paths, larger scenario counts.

Owner plan (WhatsApp 8 Nov 11:36, approved 11:37): re-validate the true 10y
sleeve on fresh paths with more scenarios than fix 4's n=100/200 where
feasible. Fresh seed family (20261108) disjoint from fix 4's (20261107):
fresh training draws for the solve AND fresh validation/final judges.

Answers:
  solves      10y cvxpy solves at n=100/200/400 on fresh training paths:
              weights, solver status, seconds (scenario-noise stability vs
              fix 4 and across n)
  stability   pairwise L1 distance between sleeve proportions
  mix         dual-law mix search (mixture + fhs_ewma) for the largest-n
              sleeve, judged on fresh validation and fresh final draws
"""
import sys, time, json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies' / 'tbill'))
sys.path.insert(0, str(ROOT / 'studies' / 'fixes'))
import study_tips_charts as S  # noqa: E402

RESULTS = Path(__file__).resolve().parent / 'results'
RESULTS.mkdir(exist_ok=True)
FRESH_SEED = 20261108


def save(name, data):
    (RESULTS / name).write_text(json.dumps(data, default=str, indent=1))


def load(name):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def fresh_config(**kw):
    c = S.nm_config(**kw)
    c['seed'] = FRESH_SEED
    c['label'] += (' ROUND 2 (owner plan 8 Nov 11:37): fresh seed family %d - training, '
                   'validation and final paths all disjoint from earlier studies.' % FRESH_SEED)
    return c


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


def sleeve_from(c, w):
    ids = c['asset_layout']['ids']
    mins, fixed = S.holding_bounds(c, len(ids))
    fixed = {int(k): v for k, v in fixed.items()}
    safe_idx = ids.index('tbill')
    risky = {a: w[a] for i, a in enumerate(ids)
             if i != safe_idx and i not in fixed and mins[i] == 0 and a != 'cash' and w[a] > 1e-6}
    tot = sum(risky.values())
    return {k: v / tot for k, v in risky.items()}


def main():
    r = load('round2_longhorizon_fresh.json')
    r.setdefault('meta', dict(
        label='ROUND 2 STUDY (owner plan 8 Nov 11:37): true 10y sleeve re-validation on fresh '
              'paths. Fresh seed family 20261108 for training, validation and final draws. '
              'n=400 attempted (fix 4 labeled it out of reach); if infeasible, labeled.',
        fresh_seed=FRESH_SEED))
    c = fresh_config()
    fit = S.setup(c)
    solves = r.setdefault('solves', {})
    for n in (100, 200, 400):
        key = str(n)
        if key not in solves:
            solves[key] = solve_at(c, fit, n)
            save('round2_longhorizon_fresh.json', r)
        s = solves[key]
        print('solve n=%s %s %.1fs' % (key, s['status'], s['seconds']),
              {k: round(v, 3) for k, v in (s.get('weights') or {}).items() if v > 1e-4}, flush=True)
    ok = {int(k): v for k, v in solves.items() if v.get('weights')}
    # stability: pairwise L1 on sleeve proportions, plus fix4's n=200 sleeve
    props = {n: sleeve_from(c, v['weights']) for n, v in ok.items()}
    fix4 = json.loads(Path('studies/fixes/results/fix4_longhorizon.json').read_text())
    fix4_prop = fix4['sleeve_10y']['proportions']
    names = sorted(set().union(*[set(p) for p in props.values()], set(fix4_prop)))
    def vec(p):
        return np.array([p.get(a, 0.0) for a in names])
    stab = {}
    keys = list(props) + ['fix4_n200']
    vecs = {**{n: vec(p) for n, p in props.items()}, 'fix4_n200': vec(fix4_prop)}
    for i in range(len(keys)):
        for j in range(i):
            stab['%s_vs_%s' % (keys[i], keys[j])] = float(np.abs(vecs[keys[i]] - vecs[keys[j]]).sum())
    r['stability'] = dict(assets=names, sleeve_L1=stab,
                          proportions={str(k): v for k, v in props.items()})
    r['sleeve_10y_fresh'] = dict(proportions=props[max(ok)], source_n=max(ok),
                                 safe_share_raw=ok[max(ok)]['weights']['tbill'])
    save('round2_longhorizon_fresh.json', r)
    print('stability L1:', {k: round(v, 3) for k, v in stab.items()}, flush=True)


if __name__ == '__main__':
    main()
