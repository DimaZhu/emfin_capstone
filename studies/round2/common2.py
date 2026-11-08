"""Round-2 shared helpers (owner plan 8 Nov 2026 11:37): dual-law judging.

Primary law = gaussian_scale_mixture (engine default). Fifth law = fhs_ewma
(the engine's declared EWMA filtered historical simulation regime/bootstrap
variant), promoted into the judge by the same plan. Same fit, budgets, seeds
family and frozen discipline as studies/tbill and studies/fixes; extra-law
draws use offset +500000 so no seed is shared with the primary law.

Study tier (unchanged): validation 4x200, final 4x400.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies' / 'tbill'))
sys.path.insert(0, str(ROOT / 'studies' / 'fixes'))

import study_tips_charts as S  # noqa: E402
from emfin_v2.evaluation import evaluate  # noqa: E402
from emfin_v2.current_rates import apply_carry_view  # noqa: E402

RESULTS = Path(__file__).resolve().parent / 'results'
RESULTS.mkdir(exist_ok=True)
DRAW_DIR = Path('/tmp/round2_draws')
DRAW_DIR.mkdir(exist_ok=True)
FRESH_SEED = 20261108
FIFTH_LAW = 'fhs_ewma'
LAW_OFFSET = 500000


def save(name, data):
    (RESULTS / name).write_text(json.dumps(data, default=str, indent=1))


def load(name):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def fresh_config(view='fitted', **kw):
    c = S.nm_config(**kw)
    c['seed'] = FRESH_SEED
    c['carry_view'] = view
    c['label'] += (' ROUND 2 (owner plan 8 Nov 11:37): fresh seed family %d; carry view %s; '
                   'dual-law judging (mixture + %s).' % (FRESH_SEED, view, FIFTH_LAW))
    return c


def fresh_fit(c):
    fit = S.setup(c)
    if c.get('carry_view', 'fitted') != 'fitted':
        fit = apply_carry_view(c, fit)
    return fit


def _unpack(z, prefix, count):
    from emfin_v2.real_estate import ScenarioDraw
    out = []
    for j in range(count):
        out.append(ScenarioDraw((z[f'{prefix}{j}_prices'], z[f'{prefix}{j}_amounts'],
                                 z[f'{prefix}{j}_steps'], z[f'{prefix}{j}_bases'],
                                 z[f'{prefix}{j}_growth']),
                                z[f'{prefix}{j}_funding'], z[f'{prefix}{j}_relog']))
    return out


def dual_draws(c, fit, tag):
    """Primary (mixture) and fifth-law (fhs_ewma) validation/final splits, cached."""
    val, vp, fin, fp = S.get_draws(c, fit, tag)
    f = DRAW_DIR / f'{tag}_{FIFTH_LAW}.npz'
    if f.exists():
        z = np.load(f, allow_pickle=False)
        val2, fin2 = _unpack(z, 'v', 4), _unpack(z, 'f', 4)
    else:
        import copy
        cc = copy.deepcopy(c)
        cc['scenario_model'] = FIFTH_LAW
        val2 = [S.draw_paths(cc, fit, 200, c['seed'] + 1000 + LAW_OFFSET + j) for j in range(4)]
        fin2 = [S.draw_paths(cc, fit, 400, c['seed'] + 10000 + LAW_OFFSET + j) for j in range(4)]
        blob = {}
        for prefix, draws in (('v', val2), ('f', fin2)):
            for j, d in enumerate(draws):
                blob[f'{prefix}{j}_prices'] = d[0]
                blob[f'{prefix}{j}_amounts'] = d[1]
                blob[f'{prefix}{j}_steps'] = d[2]
                blob[f'{prefix}{j}_bases'] = d[3]
                blob[f'{prefix}{j}_growth'] = d[4]
                blob[f'{prefix}{j}_funding'] = d.funding_paths
                blob[f'{prefix}{j}_relog'] = d.re_price_logs
        np.savez(f, **blob)
    vp2 = [S.probabilities(c, v[0], v.re_price_logs) for v in val2]
    fp2 = [S.probabilities(c, x[0], x.re_price_logs) for x in fin2]
    return (val, vp, fin, fp), (val2, vp2, fin2, fp2)


def judge(c, splits, a):
    val, vp, fin, fp = splits
    v = evaluate(c, val, a, [x[0] for x in vp], [x[1] for x in vp])
    f = evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
    return v, f


def dual_mix_search(c, primary, fifth, prop, label=''):
    """Lowest safe share passing validation under BOTH laws, then one-step-safer
    walk-back on the final judge of BOTH laws. Score on the primary final set."""
    mix, ids = S.mix_fn(c, prop)
    per_law_val = []
    chosen = None
    for s in S.SAFE_GRID:
        a = mix(float(s)) * c['wealth']
        v1, _ = judge(c, primary, a)
        if not v1['overall_pass']:
            per_law_val.append((float(s), 'mixture', v1['breaches'][:2]))
            continue
        v2, _ = judge(c, fifth, a)
        if not v2['overall_pass']:
            per_law_val.append((float(s), FIFTH_LAW, v2['breaches'][:2]))
            continue
        chosen = float(s)
        break
    if chosen is None:
        return dict(chosen_safe=None, note='no candidate mix passes dual-law validation', label=label,
                    validation_failures=per_law_val[:6])
    s = chosen
    pick = None
    while s <= 0.9001:
        a = mix(float(s)) * c['wealth']
        _, f1 = judge(c, primary, a)
        _, f2 = judge(c, fifth, a)
        if f1['overall_pass'] and f2['overall_pass']:
            pick = (float(s), f1, f2)
            break
        s = round(s + 0.025, 4)
    if pick is None:
        return dict(chosen_safe=None, validation_selected_safe=chosen,
                    note='fails dual-law final judge even at 90% safe', label=label)
    s, f1, f2 = pick
    a = mix(s) * c['wealth']
    out = dict(chosen_safe=s, validation_selected_safe=chosen,
               weights={n: round(float(wi), 4) for n, wi in zip(ids, a / c['wealth'])},
               final_pass=True, final_breaches= f1.get('breaches'),
               fifth_law_final_breaches=f2.get('breaches'), label=label)
    out.update(S.score_final(c, primary[2], primary[3], a))
    out['fifth_law_final'] = dict(
        terminal_median=None,
        ce=S.score_final(c, fifth[2], fifth[3], a))
    return out
