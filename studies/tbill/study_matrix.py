"""LABELED SENSITIVITY (Tijs, 8 Nov 09:36): loss-limit matrix at a 10-year horizon.

Grid over the two loss budgets, both loosened from the current (strictest) values:
  rows: cml_budget  (any-point cumulative loss cap; default 0.06) -> 6/8/10/15/20/30%
  cols: loss_budget (horizon-end loss cap;     default 0.15) -> 15/20/25/30/40%
Horizon 10 years (520 weeks), $250k/month x 120 payments (only 12 months are
confirmed by the owner; the 120-month schedule is a labeled sensitivity),
$100M, T-bill registry with anchor_asset_id='tbill', property fixed at 10%.

Method (frozen validation discipline, adapted to long horizon):
  The engine's cvxpy optimizer is priced for one year, so - as in the 4th
  edition's horizon screens - each cell runs a MIX SEARCH instead: candidates
  are blends of the safe anchor (T-bills) with a risky sleeve whose composition
  is frozen at the one-year raw optimizer's proportions (VTI 0.1255, GLD 0.1127,
  IEF 0.2409; EM 0), property fixed at 10%. Safe share spans 10%..90% in 2.5%
  steps. All candidates are judged on the SAME fresh validation paths
  (4 batches x 200, seeds seed+1000..1003); the chosen mix is the lowest safe
  share passing the full validation judge at the cell's budgets, then verified
  on independent final paths (4 batches x 400, seeds seed+10000..10003); if it
  fails there, the search walks one grid step safer until the final judge
  passes. Cells where no candidate passes validation say so.

  Validation/final draws are generated ONCE (budgets do not enter the draw
  law) and shared across cells, so every cell is judged on identical futures.

Reported per cell: chosen weights (safe share), CARA certainty equivalent on
final paths (same ledger convention as the unified report), median and 5%
leftover after all $30M of payouts, model-implied expected annual return,
funded status, independent final-check verdict, and the binding check (first
breach of the next more aggressive mix).
"""
from pathlib import Path
import copy, json, sys, time
import numpy as np
from emfin_v2.default_run import validate_config, setup, draw_paths, probabilities, holding_bounds
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from emfin_v2.utilities import native_ce

sys.path.insert(0, 'studies/tbill')
from study_tbill import provision
from study_horizon import schedule

OUT = Path('studies/tbill/results/study_matrix.json')
BASE = 'studies/tbill/config_tbill.json'
CML_CAPS = [0.06, 0.08, 0.10, 0.15, 0.20, 0.30]
LOSS_CAPS = [0.15, 0.20, 0.25, 0.30, 0.40]
SAFE_GRID = np.round(np.arange(0.10, 0.9001, 0.025), 4)
RISKY_PROP = {'us_equity': 0.1255, 'gold': 0.1127, 'treasury': 0.2409, 'em_equity': 0.0}
YEARS, MONTHS, WEEKS = 10, 120, 520


def load_cell_config(cml, loss):
    c = json.loads(Path(BASE).read_text())
    c['horizon_weeks'] = WEEKS
    c['recurring_payout'] = None
    c.pop('one_off_liabilities', None)
    c['liabilities'] = schedule(MONTHS)
    c['funding_mode'] = 'pay_all_99'
    c['cml_budget'] = cml
    c['loss_budget'] = loss
    c['label'] = (c['label'] + f' LABELED MATRIX SENSITIVITY: 10-year horizon, '
                  f'cml_budget={cml:.0%} (default 6%), loss_budget={loss:.0%} (default 15%).')
    return validate_config(c)


def main():
    t_start = time.perf_counter()
    c0 = load_cell_config(0.06, 0.15)
    fit = setup(c0)
    d = len(c0['asset_names'])
    names = c0['asset_names']
    ids = c0['asset_layout']['ids']
    mins, fixed = holding_bounds(c0, d)
    safe_idx = ids.index('tbill')
    risky_idx = [i for i in range(d) if i != safe_idx and i not in fixed and mins[i] == 0]
    tot = sum(RISKY_PROP.get(ids[i], 0) for i in risky_idx)

    def mix(safe_share):
        w = np.zeros(d)
        w[safe_idx] = safe_share
        for i, v in fixed.items():
            w[i] = v
        rem = 1 - safe_share - sum(fixed.values())
        for i in risky_idx:
            w[i] = rem * RISKY_PROP.get(ids[i], 0) / tot
        assert abs(w.sum() - 1.0) < 1e-9
        return w

    print('drawing shared path sets...', flush=True)
    validation = [draw_paths(c0, fit, 200, c0['seed'] + 1000 + j) for j in range(4)]
    vp = [probabilities(c0, v[0], v.re_price_logs) for v in validation]
    final = [draw_paths(c0, fit, 400, c0['seed'] + 10000 + j) for j in range(4)]
    fp = [probabilities(c0, x[0], x.re_price_logs) for x in final]
    # model-implied per-asset expected annual return from a large fitted draw
    train = draw_paths(c0, fit, 800, c0['seed'] + 555)
    wk = train[0][:, 1:, :] / train[0][:, :-1, :] - 1.0
    exp_annual = ((1 + wk.mean(axis=(0, 1))) ** 52 - 1).tolist()
    print('draws done %.0fs' % (time.perf_counter() - t_start), flush=True)

    results = {}
    if OUT.exists():
        results = json.loads(OUT.read_text()).get('cells', {})

    def score(c, a):
        audits = [cash_first(c, x, a) for x in final]
        x = np.concatenate([z['terminal_net'] for z in audits])
        L = np.concatenate([provision(z) for z in final])
        common = native_ce('cara', x + L, x, np.full(len(x), 1 / len(x)), c['wealth'], c['risk_tolerance'], L)
        return dict(common_cara_ledger_ce=common['ce'],
                    terminal_median=float(np.median(x)), terminal_q05=float(np.quantile(x, .05)),
                    funded=float(np.mean([z['funded'].mean() for z in audits])),
                    largest_unpaid=max(float(z['payment_shortfalls'].max()) for z in audits))

    for cml in CML_CAPS:
        for loss in LOSS_CAPS:
            key = f'cml{int(cml*100)}_loss{int(loss*100)}'
            if key in results:
                print('skip', key, flush=True)
                continue
            t0 = time.perf_counter()
            c = load_cell_config(cml, loss)
            trials = []
            chosen = None
            for s in SAFE_GRID:
                a = mix(float(s)) * c['wealth']
                v = evaluate(c, validation, a, [x[0] for x in vp], [x[1] for x in vp])
                trials.append(dict(safe=float(s), passed=bool(v['overall_pass']), breaches=v.get('breaches')))
                if chosen is None and v['overall_pass']:
                    chosen = float(s)
            cell = dict(cml_budget=cml, loss_budget=loss, trials=trials)
            if chosen is None:
                cell.update(chosen_safe=None, note='no candidate mix passes the validation judge at these limits')
            else:
                # walk from chosen to safer until the independent final judge passes
                pick = None
                s = chosen
                while s <= 0.9001:
                    a = mix(float(s)) * c['wealth']
                    verdict = evaluate(c, final, a, [x[0] for x in fp], [x[1] for x in fp])
                    if verdict['overall_pass']:
                        pick = (float(s), verdict)
                        break
                    s = round(s + 0.025, 4)
                if pick is None:
                    cell.update(chosen_safe=None,
                                note='validation-passing mixes fail the independent final judge even at 90% safe')
                else:
                    s, verdict = pick
                    a = mix(s) * c['wealth']
                    sc = score(c, a)
                    w = (a / c['wealth']).tolist()
                    # binding check: first breach of the next more aggressive mix (validation)
                    riskier = [t for t in trials if t['safe'] < chosen and not t['passed']]
                    binding = None
                    if riskier:
                        binding = max(riskier, key=lambda t: t['safe'])['breaches']
                    cell.update(chosen_safe=s, validation_selected_safe=chosen,
                                final_walk_steps=round((s - chosen) / 0.025),
                                weights={n: round(wi, 4) for n, wi in zip(names, w)},
                                expected_annual_return=float(np.dot(w, exp_annual)),
                                final_pass=True, final_breaches=verdict.get('breaches'),
                                binding_check_next_riskier=binding, **sc)
            cell['seconds'] = time.perf_counter() - t0
            results[key] = cell
            OUT.write_text(json.dumps(dict(seconds=time.perf_counter() - t_start, assets=names,
                                           expected_annual_return_by_asset=dict(zip(names, exp_annual)),
                                           safe_grid=list(map(float, SAFE_GRID)), cells=results),
                                      default=str, indent=1))
            cs = cell.get('chosen_safe')
            print('%s -> safe=%s CE=%s walk=%s (%.0fs)' % (
                key, f'{cs:.3f}' if cs else 'NONE',
                f"{cell.get('common_cara_ledger_ce', 0)/1e6:.1f}M" if cs else '-',
                cell.get('final_walk_steps', '-'), cell['seconds']), flush=True)

    print('MATRIX TOTAL seconds %.1f' % (time.perf_counter() - t_start), flush=True)


if __name__ == '__main__':
    main()
