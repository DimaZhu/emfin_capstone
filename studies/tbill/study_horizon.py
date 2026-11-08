"""Labeled long-horizon sensitivity (Tijs Q2): 10/20/30 years at $250k/month.

NOT the confirmed case: only 12 months x $250k is confirmed. The optimizer's
cvxpy solve is priced for one year, so this screen judges fixed candidate
mixes on fresh simulated futures (same evaluate() judge, same ledger) instead
of re-optimizing per horizon. Candidates:
  anchor      90% safe asset (cash or T-bills) + 10% property
  validated1y the frozen one-year validated mix (per registry)
  step30/50/70 safe-asset share 70/50/30%, risky remainder split pro rata
                following the one-year optimizer's risky proportions, 10% property
Nominal model (no inflation indexation); multi-year paths use the same
iid-week mixture law - the clustering caveat grows with horizon and is stated.
"""
from pathlib import Path
import json, sys, time
import numpy as np
from emfin_v2.default_run import validate_config, setup, draw_paths, probabilities, holding_bounds
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from emfin_v2.utilities import native_ce

sys.path.insert(0, 'studies/tbill')
from study_tbill import provision


def schedule(months, amount=250000.0, first=4, spacing=52 / 12):
    return [dict(name=f'Monthly payment {i+1} (labeled sensitivity)', week=round(first + i * spacing),
                 amount=amount, schedule='recurring', month=i + 1) for i in range(months)]


def screen(config_path, anchor_id, years, months, weeks):
    c = json.loads(Path(config_path).read_text())
    c['horizon_weeks'] = weeks
    c['recurring_payout'] = None
    c.pop('one_off_liabilities', None)
    c['liabilities'] = schedule(months)
    c['funding_mode'] = 'pay_all_99'
    c = validate_config(c)
    fit = setup(c)
    d = len(c['asset_names'])
    validation = [draw_paths(c, fit, 200, c['seed'] + 1000 + j) for j in range(4)]
    vp = [probabilities(c, v[0], v.re_price_logs) for v in validation]
    final = [draw_paths(c, fit, 400, c['seed'] + 10000 + j) for j in range(4)]
    fp = [probabilities(c, x[0], x.re_price_logs) for x in final]

    mins, fixed = holding_bounds(c, d)
    prop = fixed.get(str(c['asset_layout']['property_indices'][0]), 0.1)
    safe_idx = c['asset_layout']['ids'].index(anchor_id) if anchor_id else c['cash_index']
    risky_idx = [i for i in range(d) if i != safe_idx and i not in fixed and mins[i] == 0]
    # one-year optimizer's risky proportions (from the frozen raw solutions),
    # keyed by registry asset id; the safe asset itself is excluded.
    if anchor_id:
        risky_prop = {'us_equity': 0.1255, 'gold': 0.1127, 'treasury': 0.2409, 'em_equity': 0.0}
    else:
        risky_prop = {'us_equity': 0.1832, 'em_equity': 0.0, 'gold': 0.0, 'treasury': 0.3613}
    names = c['asset_names']
    ids = c['asset_layout']['ids']

    def mix(safe_share):
        w = np.zeros(d)
        w[safe_idx] = safe_share
        for i, v in fixed.items():
            w[i] = v
        rem = 1 - safe_share - sum(fixed.values())
        tot = sum(risky_prop.get(ids[i], 0) for i in risky_idx)
        if tot <= 0:
            raise ValueError('risky proportions missing for registry')
        for i in risky_idx:
            w[i] = rem * risky_prop.get(ids[i], 0) / tot
        assert abs(w.sum() - 1.0) < 1e-9, f'mix must sum to 1, got {w.sum()}'
        return w

    candidates = {
        'anchor(90% safe)': mix(0.9 - 0),
        'step70': mix(0.7), 'step50': mix(0.5), 'step30': mix(0.3),
    }
    # correct anchor: 90% safe + 10% property
    a = np.zeros(d)
    a[safe_idx] = 0.9
    for i, v in fixed.items():
        a[i] = v
    a[safe_idx] += 1 - a.sum()
    candidates['anchor(90% safe)'] = a

    rows = []
    for label, w in candidates.items():
        a = w * c['wealth']
        v = evaluate(c, validation, a, [x[0] for x in vp], [x[1] for x in vp])
        verdict = evaluate(c, final, a, [x[0] for x in fp], [x[1] for x in fp])
        audits = [cash_first(c, x, a) for x in final]
        x = np.concatenate([z['terminal_net'] for z in audits])
        L = np.concatenate([provision(z) for z in final])
        common = native_ce('cara', x + L, x, np.full(len(x), 1 / len(x)), c['wealth'], c['risk_tolerance'], L)
        rows.append(dict(label=label, weights=w.tolist(),
                         validation_pass=bool(v['overall_pass']), validation_breaches=v.get('breaches'),
                         final_pass=bool(verdict['overall_pass']), final_breaches=verdict.get('breaches'),
                         common_cara_ledger_ce=common['ce'],
                         terminal_median=float(np.median(x)), terminal_q05=float(np.quantile(x, .05)),
                         funded=float(np.mean([z['funded'].mean() for z in audits])),
                         largest_unpaid=max(float(z['payment_shortfalls'].max()) for z in audits)))
    return dict(years=years, months=months, total_paid=months * 250000.0, assets=names, rows=rows)


def main():
    out = {}
    for years, months, weeks in ((10, 120, 520), (20, 240, 1040), (30, 360, 1560)):
        for name, anchor in (('baseline', None), ('tbill', 'tbill')):
            t0 = time.perf_counter()
            try:
                r = screen(f'studies/tbill/config_{name}.json', anchor, years, months, weeks)
            except Exception as e:
                r = dict(error=str(e)[:300])
            r['seconds'] = time.perf_counter() - t0
            out[f'horizon{years}y_{name}'] = r
            print(years, name, '%.0fs' % r['seconds'], flush=True)
            for row in r.get('rows', []):
                print('  %-18s val=%-5s final=%-5s CE=%8.1fM funded=%.3f q05=%.1fM med=%.1fM' % (
                    row['label'], row['validation_pass'], row['final_pass'],
                    row['common_cara_ledger_ce'] / 1e6, row['funded'],
                    row['terminal_q05'] / 1e6, row['terminal_median'] / 1e6), flush=True)
    full = json.load(open('studies/tbill/results/study_tbill.json'))
    full['results'].update(out)
    json.dump(full, open('studies/tbill/results/study_tbill.json', 'w'), indent=1, default=str)
    print('saved')


if __name__ == '__main__':
    main()
