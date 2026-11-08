"""T-bill study: frozen-pipeline replica of the validated selection, parameterized.

Replicates the exact machinery of experiments/utility_comparison.py that
produced the frozen validated portfolio (fraction grid toward the safe anchor,
first candidate passing the final all-risk judge on validation paths, then
common CARA ledger CE on disjoint final paths), for:
  - the bundled baseline registry (control; must reproduce cash 0.76385 /
    CE $98,252,660 for the cara/3M-monthly case), and
  - the T-bill registry with anchor_asset_id='tbill'.

Every variant is a labeled sensitivity: the config dict carries the same
frozen defaults unless a variant overrides one named knob at a time.
"""
from pathlib import Path
import copy, json, time
import numpy as np
from emfin_v2.default_run import validate_config, setup, draw_paths, probabilities, solve
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from emfin_v2.utilities import native_ce
from emfin_v2.default_run import holding_bounds

ROOT = Path('studies/tbill/results')
SEED = 20261107


def provision(draw):
    return sum(draw[1][:, i] * draw[4][:, -1] / draw[4][:, step - 1] for i, step in enumerate(draw[2]))


def anchor_vector(c, d, anchor_id=None):
    mins, fixed = holding_bounds(c, d)
    anchor = mins.copy()
    for i, v in fixed.items():
        anchor[i] = v
    if anchor_id is None:
        idx = c['cash_index']
    else:
        ids = c['asset_layout']['ids']
        idx = ids.index(anchor_id)
    anchor[idx] += 1 - anchor.sum()
    return anchor


def run_frozen(config_path, anchor_id=None, tag=''):
    """One frozen selection: raw solve, blend grid, judge on validation, score on final."""
    c = validate_config(json.loads(Path(config_path).read_text()))
    c['funding_mode'] = 'pay_all_99'
    c = validate_config(c)
    fit = setup(c)
    dr = draw_paths(c, fit, 100, c['seed'])
    p, ps = probabilities(c, dr[0], dr.re_price_logs)
    validation = [draw_paths(c, fit, 200, c['seed'] + 1000 + j) for j in range(4)]
    vp = [probabilities(c, v[0], v.re_price_logs) for v in validation]
    d = dr[0].shape[2]
    anchor = anchor_vector(c, d, anchor_id) * c['wealth']

    raw, status = solve(c, dr, p, ps, 1.)
    out = dict(tag=tag, status_kind=status.get('kind'), trials=[], selected=None)
    if status.get('kind') != 'optimized':
        out['error'] = 'raw optimizer not optimal: ' + str(status)
        return out
    candidates = [('raw', None, raw)]
    for fraction in [1., .75, .5, .25, 0.]:
        candidates.append(('blend', fraction, fraction * raw + (1 - fraction) * anchor))
    chosen = None
    for kind, fraction, a in candidates:
        v = evaluate(c, validation, a, [x[0] for x in vp], [x[1] for x in vp])
        out['trials'].append(dict(kind=kind, fraction=fraction, passed=bool(v['overall_pass']),
                                  breaches=v.get('breaches'),
                                  weights=(a / c['wealth']).tolist()))
        if kind == 'blend' and v['overall_pass'] and chosen is None:
            chosen = (fraction, a)
    if chosen is None:
        out['error'] = 'no blend candidate passed validation'
        return out
    fraction, a = chosen
    final = [draw_paths(c, fit, 400, c['seed'] + 10000 + j) for j in range(4)]
    fp = [probabilities(c, x[0], x.re_price_logs) for x in final]
    verdict = evaluate(c, final, a, [x[0] for x in fp], [x[1] for x in fp])
    audits = [cash_first(c, x, a) for x in final]
    x = np.concatenate([z['terminal_net'] for z in audits])
    L = np.concatenate([provision(z) for z in final])
    ref = np.full(len(x), 1 / len(x))
    common = native_ce('cara', x + L, x, ref, c['wealth'], c['risk_tolerance'], L)
    out['selected'] = dict(
        fraction=fraction, weights=(a / c['wealth']).tolist(),
        anchor_weight=float(a[(c['asset_layout']['ids'].index(anchor_id) if anchor_id else c['cash_index'])] / c['wealth']),
        validation_pass=True, final_verdict=verdict,
        common_cara_ledger_ce=common['ce'], ledger_net_mean=float(x.mean()),
        ledger_quantiles=np.quantile(x, [.05, .5, .95]).tolist(),
        largest_unpaid=max(float(z['payment_shortfalls'].max()) for z in audits),
        funded=float(np.mean([z['funded'].mean() for z in audits])))
    # raw scored the same way for the before/after delta
    audits_r = [cash_first(c, z, raw) for z in final]
    xr = np.concatenate([z['terminal_net'] for z in audits_r])
    Lr = np.concatenate([provision(z) for z in final])
    common_r = native_ce('cara', xr + Lr, xr, np.full(len(xr), 1 / len(xr)), c['wealth'], c['risk_tolerance'], Lr)
    out['raw_scored'] = dict(weights=(raw / c['wealth']).tolist(), common_cara_ledger_ce=common_r['ce'],
                             final_verdict=evaluate(c, final, raw, [q[0] for q in fp], [q[1] for q in fp]))
    out['assets'] = c['asset_names']
    return out


def variant_config(base_path, out_path, **overrides):
    c = json.loads(Path(base_path).read_text())
    for k, v in overrides.items():
        if k == 'payout_amount':
            c['recurring_payout']['amount'] = v
        elif k == 'payout_months':
            c['recurring_payout']['months'] = v
        else:
            c[k] = v
    Path(out_path).write_text(json.dumps(c, indent=1))
    return out_path


def main():
    t0 = time.perf_counter()
    ROOT.mkdir(parents=True, exist_ok=True)
    results = {}

    # 1. Control: reproduce the frozen validated selection exactly.
    results['control_baseline'] = run_frozen('studies/tbill/config_baseline.json', None, 'control')
    sel = results['control_baseline'].get('selected') or {}
    print('CONTROL cash=%.5f CE=%.2f (target 0.76385 / 98252659.99)'
          % (sel.get('anchor_weight', -1), sel.get('common_cara_ledger_ce', -1)), flush=True)

    # 2. T-bill registry, anchor=tbill, same everything else.
    results['tbill_anchor'] = run_frozen('studies/tbill/config_tbill.json', 'tbill', 'tbill_anchor')
    sel = results['tbill_anchor'].get('selected') or {}
    print('TBILL  tbillw=%.5f CE=%.2f' % (sel.get('anchor_weight', -1), sel.get('common_cara_ledger_ce', -1)), flush=True)

    # 2b. T-bill in the universe but anchor kept at cash (isolate the anchor change).
    results['tbill_cash_anchor'] = run_frozen('studies/tbill/config_tbill.json', None, 'tbill_cash_anchor')

    # 3. Payout levels 50/100/250k (125k added: refusal boundary). Labeled:
    #    at <200k the fixed model-miss buffer exceeds 20% of the payment, so the
    #    engine declines; the sensitivity scales the W1 radius so the buffer keeps
    #    its 250k ratio (80% of the allowance). No budget loosened.
    for amount in [50000, 100000, 125000, 250000]:
        for name, anchor in (('baseline', None), ('tbill', 'tbill')):
            base = f'studies/tbill/config_{name}.json'
            vc = variant_config(base, f'studies/tbill/config_tmp_p{amount}_{name}.json',
                                payout_amount=amount)
            try:
                r = run_frozen(vc, anchor, f'payout{amount}_{name}')
            except ValueError as exc:
                r = dict(tag=f'payout{amount}_{name}', refused=True, reason=str(exc)[:300])
                if amount < 200000:
                    # labeled scaled-buffer sensitivity: buffer keeps its 250k share (80%)
                    # of the 20%-of-payment allowance
                    scale = amount / 250000.0
                    c0 = json.loads(Path(base).read_text())
                    c0['recurring_payout']['amount'] = amount
                    c0['wasserstein_radius'] = c0['wasserstein_radius'] * scale
                    c0['label'] = c0['label'] + f' LABELED SENSITIVITY: model-miss buffer scaled x{scale:.2f} to keep 80% of the payment allowance (same ratio as the confirmed $250k case). No budget loosened.'
                    Path(vc).write_text(json.dumps(c0, indent=1))
                    try:
                        r = run_frozen(vc, anchor, f'payout{amount}_{name}_scaledbuffer')
                        r['scaled_buffer'] = scale
                    except ValueError as exc2:
                        r = dict(tag=f'payout{amount}_{name}_scaledbuffer', refused=True, reason=str(exc2)[:300])
            results[f'payout{amount}_{name}'] = r
            print('payout', amount, name, 'done', flush=True)

    # 4. Loss-limit vs cash share: vary the path-loss cap (default 0.15).
    for cap in [0.10, 0.15, 0.20, 0.30]:
        for name, anchor in (('baseline', None), ('tbill', 'tbill')):
            vc = variant_config(f'studies/tbill/config_{name}.json',
                                f'studies/tbill/config_tmp_loss{int(cap*100)}_{name}.json',
                                loss_budget=cap)
            vc_obj = json.loads(Path(vc).read_text())
            vc_obj['label'] = vc_obj['label'] + f' LABELED SENSITIVITY: path-loss cap {cap:.0%} (default 15%).'
            Path(vc).write_text(json.dumps(vc_obj, indent=1))
            results[f'losscap{int(cap*100)}_{name}'] = run_frozen(vc, anchor, f'losscap{cap}_{name}')
            print('losscap', cap, name, 'done', flush=True)

    # 5. Cumulative-loss cap companion sweep (default 0.06).
    for cap in [0.03, 0.06, 0.10]:
        for name, anchor in (('baseline', None), ('tbill', 'tbill')):
            vc = variant_config(f'studies/tbill/config_{name}.json',
                                f'studies/tbill/config_tmp_cml{int(cap*100)}_{name}.json',
                                cml_budget=cap)
            vc_obj = json.loads(Path(vc).read_text())
            vc_obj['label'] = vc_obj['label'] + f' LABELED SENSITIVITY: cumulative-loss cap {cap:.0%} (default 6%).'
            Path(vc).write_text(json.dumps(vc_obj, indent=1))
            results[f'cmlcap{int(cap*100)}_{name}'] = run_frozen(vc, anchor, f'cmlcap{cap}_{name}')
            print('cmlcap', cap, name, 'done', flush=True)

    def default(o):
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    (ROOT / 'study_tbill.json').write_text(json.dumps(
        dict(seconds=time.perf_counter() - t0, results=results), default=default, indent=1))
    print('TOTAL seconds %.1f' % (time.perf_counter() - t0), flush=True)


if __name__ == '__main__':
    main()
