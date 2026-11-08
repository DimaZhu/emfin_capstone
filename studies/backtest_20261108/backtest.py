"""Walk-forward historical backtest: proposed engine vs cash, 1/N, min-var, shrunk MV.

Design (docs/NEXT_RESEARCH_PLAN.md; owner approval "Yes, a and b", WhatsApp
8 Nov 2026 19:06 +08; owner steering 19:13 +08: include SG property from the
project's own URA series, private use):

- Universe: the model's own actual registry: VTI/VWO/GLD/IEF total return,
  fixed-rate cash account, and Singapore URA private-residential property
  (quarterly index, 45-day release lag, holding_mode fixed at 10% per the
  placeholder client case) with SGD/USD from the committed Fed H.10 series.
  Property is realized at quarterly index granularity with the engine's own
  cash_and_mark convention (rent/sale rules exactly as configured). The URA
  index is a transaction price index: no realized weekly property tails,
  rent, or execution beyond the model's own conventions. This is labelled
  throughout as an index-level property path, not a tradable property return.
- 78 non-overlapping 13-week folds, first decision at training week 104
  (expanding window, strict past-only refit per fold: liquid moments via
  registry_runtime.fit_frame on rows before the decision date; property
  calibration via real_estate history_end pinned to the decision date).
- Per fold the proposed model is re-fit and re-solved at full default scale
  (train_scenarios=1000, horizon 520w, validation 3x4000, calibration grid,
  multiplier grid), replicating default_run.run()'s selection exactly.
- Realized 13-week windows are accounted through the engine's executable
  cash-first ledger (emfin_v2.ledger.cash_first): identical assets, haircuts,
  payout schedule (weeks 4/8/13, $250k) and constraints.
- Stationary reference wealth: each fold is solved at config wealth ($100M,
  risk_tolerance $10M); realized outcomes compound offline per method.
  Chained-wealth resolving is future work (recorded limitation).
- Checkpointed stage machine (solve -> select -> realized). Built for a
  GitHub Actions runner: the engine's solver policy (CLARABEL 60s cap, SCS
  60s fallback cap) makes one solve take up to ~2 minutes, which exceeds the
  local sandbox's per-call limit.

No confidence/significance claims beyond descriptive paired differences: the
fold count (78) bounds what can be said.
"""
import sys, json, time, argparse, copy, csv, calendar
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
RESULTS = Path(__file__).resolve().parent / 'results'
STATE = RESULTS / 'state.json'
TMP = RESULTS / 'tmp'

FOLD = 13
TRAIN_MIN = 104
BASE_SEED = 20261108
METHODS = ['proposed', 'cash', '1/N', 'min_var', 'shrunk_MV']


def build_config():
    from emfin_v2.default_run import load_config
    from emfin_v2.registry_runtime import configure
    c = load_config(ROOT / 'emfin_v2/resources/configs/default.json')
    c = configure(c, c['asset_registry'])
    return c


def fold_config(c, decision_date):
    """Per-fold config: property calibration sees only data released by the decision date."""
    cf = copy.deepcopy(c)
    cf['real_estate']['history_end'] = str(decision_date)
    return cf


def full_frame(c):
    """Weekly liquid log returns plus the FX factor column, full committed range."""
    from emfin_v2.asset_history import weekly_returns
    from emfin_v2.fx import weekly_factor, COLUMN
    frame = weekly_returns(c['asset_registry'], c['history_manifests'], c.get('history_end'))
    fx, meta = weekly_factor(frame.index, c['fx'].get('manifest'))
    frame[COLUMN] = fx
    return frame


def fold_starts(n_weeks):
    out = []
    t0 = TRAIN_MIN
    while t0 + FOLD <= n_weeks:
        out.append(t0)
        t0 += FOLD
    return out


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {'fold': 0, 'mult_index': 0, 'stage': 'solve', 'done': []}


def save_state(s):
    STATE.write_text(json.dumps(s, indent=1) + '\n')


def stage_solve(c, frame, starts):
    from emfin_v2.default_run import solve, probabilities, draw_paths
    from emfin_v2.registry_runtime import fit_frame
    s = load_state()
    k, mi = s['fold'], s['mult_index']
    t0 = starts[k]
    mult = sorted(c['multiplier_grid'], reverse=True)[mi]
    cf = fold_config(c, frame.index[t0])
    fitted = fit_frame(cf, frame.iloc[:t0])
    draw = draw_paths(cf, fitted, cf['train_scenarios'], BASE_SEED + k)
    q, qs = probabilities(cf, draw[0], getattr(draw, 're_price_logs', None))
    t_start = time.perf_counter()
    a, diag = solve(cf, draw, q, qs, mult)
    rec = {'stage': 'solve', 'fold': k, 'mult': mult, 'diag': diag,
           'solve_seconds': round(time.perf_counter() - t_start, 2)}
    if a is not None:
        np.savez(TMP / f'fold_{k:03d}_solve_{mi}.npz', a=a)
    (TMP / f'fold_{k:03d}_solve_{mi}.json').write_text(json.dumps(rec, default=str, indent=1))
    s['stage'] = 'select'
    save_state(s)
    return f"solve fold={k} mult={mult} kind={diag.get('kind')} ok={a is not None} secs={rec['solve_seconds']}"


def stage_select(c, frame, starts):
    """Validation scoring + cash-mix calibration, replicating default_run.run()."""
    from emfin_v2.default_run import (probabilities, draw_paths, metrics,
                                      interval, dro_buffer, holding_bounds)
    from emfin_v2.registry_runtime import fit_frame
    from emfin_v2.real_estate import funding_paths
    from emfin_v2.contracts import accumulated_requirement
    s = load_state()
    k, mi = s['fold'], s['mult_index']
    t0 = starts[k]
    cf = fold_config(c, frame.index[t0])
    fitted = fit_frame(cf, frame.iloc[:t0])
    draw = draw_paths(cf, fitted, cf['train_scenarios'], BASE_SEED + k)
    d = draw[0].shape[2]
    mins, fixed = holding_bounds(cf, d)
    mult = sorted(cf['multiplier_grid'], reverse=True)[mi]
    npz = TMP / f'fold_{k:03d}_solve_{mi}.npz'
    a = np.load(npz)['a'] if npz.exists() else None
    chosen = None
    calibration = []
    cash_safe = None
    if a is not None:
        anchor_index = cf['cash_index']
        cash = np.zeros(d); cash[anchor_index] = cf['wealth']
        cash_safe = True
        for kk, step in enumerate(draw[2]):
            need = accumulated_requirement(draw[1], draw[2], draw[4], kk)
            cash_safe &= bool(np.maximum(need - funding_paths(draw)[:, step - 1] @ cash, 0).max()
                              + dro_buffer(cf, cash) <= cf['funding_budget_fraction'] * mult * draw[3][kk])
        cash_safe &= bool(np.maximum(0, 1 - draw[0] @ cash / cf['wealth']).max()
                          + dro_buffer(cf, cash, False) / cf['wealth'] <= min(cf['cml_budget'], cf['loss_budget']))
        if np.any(mins[np.arange(d) != cf['cash_index']] > 0) or any(i != cf['cash_index'] and v > 0 for i, v in fixed.items()):
            cash_safe = False
        grid = cf.get('cash_mix_grid', [1., .75, .5, .25, 0.]) if cash_safe else [1.]
        validation = [draw_paths(cf, fitted, cf['validation_scenarios'], BASE_SEED + 100000 + 1000 * k + j)
                      for j in range(cf['validation_seeds'])]
        validation_measures = [probabilities(cf, v[0], getattr(v, 're_price_logs', None)) for v in validation]
        validation_stress = [p[1] for p in validation_measures]
        from emfin_v2.multi_law import all_laws, draw_extra_splits, measures as law_measures
        laws = all_laws(cf)
        extra_validation = draw_extra_splits(cf, fitted, laws, 'validation') if len(laws) > 1 else {}
        extra_validation_measures = {law: law_measures(cf, vd) for law, vd in extra_validation.items()}
        budgets = draw[3] * cf['funding_budget_fraction']
        for risky_fraction in grid:
            candidate = risky_fraction * a + (1 - risky_fraction) * cash
            ci = interval([metrics(cf, v, candidate)[0] for v in validation])
            stress_ci = interval([metrics(cf, v, candidate, ps)[0] for v, ps in zip(validation, validation_stress)])
            passed = bool(np.all(np.maximum(ci['high'], stress_ci['high']) + dro_buffer(cf, candidate) <= budgets))
            law_pass = {}
            for law, vd in extra_validation.items():
                vn, vs = extra_validation_measures[law]
                ci_law = interval([metrics(cf, v, candidate)[0] for v in vd])
                stress_ci_law = interval([metrics(cf, v, candidate, ps)[0] for v, ps in zip(vd, vs)])
                ok_law = bool(np.all(np.maximum(ci_law['high'], stress_ci_law['high']) + dro_buffer(cf, candidate) <= budgets))
                law_pass[law] = ok_law
                passed = bool(passed and ok_law)
            calibration.append(dict(multiplier=mult, risky_fraction=risky_fraction,
                                    gap_cvar_high=ci['high'], stressed_gap_cvar_high=stress_ci['high'],
                                    law_pass=law_pass, passed=passed))
            if passed and chosen is None:
                chosen = candidate.copy()
                if cf['funding_mode'] != 'pay_all_99':
                    break
    rec = {'fold': k, 'mult': mult, 'cash_safe': cash_safe,
           'calibration': calibration, 'chosen': chosen is not None}
    if chosen is not None:
        np.savez(TMP / f'fold_{k:03d}_chosen.npz', chosen=chosen)
        rec['risky_fraction'] = None
        for row in calibration:
            if row['passed']:
                rec['risky_fraction'] = row['risky_fraction']
                break
        s['stage'] = 'realized'
    elif mi + 1 < len(cf['multiplier_grid']):
        s['mult_index'] = mi + 1
        s['stage'] = 'solve'
    else:
        rec['proposed_unavailable'] = True
        s['stage'] = 'realized'
    (TMP / f'fold_{k:03d}_select.json').write_text(json.dumps(rec, default=str, indent=1))
    save_state(s)
    return f"select fold={k} mult={mult} chosen={chosen is not None} next={s['stage']}"


def property_realized(c, window_index, growth):
    """URA quarterly index marks + engine rent/sale convention for the realized window.

    index_at() sees only releases on or before each day (45-day lag), matching
    radius_calibration.calibrate's block construction. FX path is the realized
    relative spot change over the window, same convention as scenario draws.
    """
    from emfin_v2.singapore import ROOT as SG_ROOT
    from emfin_v2.real_estate import cash_and_mark
    re = c['real_estate']
    quarter = []
    with (SG_ROOT / 'ura_private_residential_quarterly.csv').open() as f:
        for row in csv.DictReader(f):
            if row['property_type'] == re['sg_property_type']:
                year = int(row['quarter'][:4]); month = int(row['quarter'][-1]) * 3
                quarter.append((date(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=45),
                                float(row['index'])))
    quarter.sort()

    def index_at(day):
        vals = [v for release, v in quarter if release <= pd.Timestamp(day).date()]
        if not vals:
            raise ValueError('no released URA index before ' + str(day))
        return vals[-1]

    initial = index_at(window_index[0] - pd.Timedelta(days=7))
    local = np.array([[index_at(day) / initial for day in window_index]])
    return local


def realized_window(frame, c, t0):
    """Realized 13-week ScenarioDraw with the engine's haircut/payout/property conventions."""
    from emfin_v2.real_estate import ScenarioDraw, cash_and_mark
    from emfin_v2.fx import COLUMN
    window = frame.iloc[t0:t0 + FOLD]
    liquid_cols = [col for col in frame.columns if col != COLUMN]
    gross = np.exp(np.cumsum(window[liquid_cols].to_numpy(), axis=0))  # (13, 5)
    hair = np.asarray(c['liquidity_haircuts'], float)
    paths_l = gross * (1 - hair)
    growth = gross[:, c['cash_index']][None].copy()  # (1, 13)
    fx_path = np.exp(np.cumsum(window[COLUMN].to_numpy()))[None]  # (1, 13)
    local = property_realized(c, window.index, growth)
    mark, spendable = cash_and_mark(local, growth, c['real_estate'], fx_paths=fx_path)
    paths = np.concatenate([paths_l[None], mark[:, :, None]], axis=2)
    funding = np.concatenate([paths_l[None], spendable[:, :, None]], axis=2)
    liab = [l for l in c['liabilities'] if l['week'] <= FOLD]
    steps = np.array([l['week'] for l in liab], int)
    bases = np.array([l['amount'] for l in liab], float)
    amounts = np.broadcast_to(bases, (1, len(bases))).copy()
    return ScenarioDraw((paths, amounts, steps, bases, growth), funding), window


def stage_realized(c, frame, starts):
    from emfin_v2.default_run import draw_paths, holding_bounds
    from emfin_v2.registry_runtime import fit_frame
    from emfin_v2.toolbox import benchmark
    from emfin_v2.ledger import cash_first
    import cvxpy as cp
    s = load_state()
    k = s['fold']
    t0 = starts[k]
    cf = fold_config(c, frame.index[t0])
    fitted = fit_frame(cf, frame.iloc[:t0])
    draw = draw_paths(cf, fitted, cf['train_scenarios'], BASE_SEED + k)
    d = draw[0].shape[2]
    mins, fixed = holding_bounds(cf, d)
    wealth = cf['wealth']
    allocs = {}
    ch = TMP / f'fold_{k:03d}_chosen.npz'
    if ch.exists():
        allocs['proposed'] = np.load(ch)['chosen']
    else:
        allocs['proposed'] = None  # no calibration candidate passed at any multiplier
    cash_v = np.zeros(d); cash_v[cf['cash_index']] = wealth
    allocs['cash'] = cash_v
    equal = np.zeros(d)
    for i, v in fixed.items():
        equal[i] = v
    free = [i for i in range(d) if i not in fixed]
    remaining = 1 - sum(fixed.values())
    while free:
        share = remaining / len(free)
        locked = {i for i in free if mins[i] > share}
        if not locked:
            for i in free:
                equal[i] = share
            break
        for i in locked:
            equal[i] = mins[i]
        remaining -= mins[i]
        free = [i for i in free if i not in locked]
    allocs['1/N'] = equal * wealth
    term = draw[0][:, -1]  # (n, d) terminal gross incl. haircuts
    allocs['shrunk_MV'] = benchmark.mean_variance_allocation(
        term.mean(0), np.cov(term.T), np.ones(d), wealth, cf['risk_tolerance'],
        minimum_weights=mins, fixed_weights=fixed)
    w = cp.Variable(d)
    sigma = np.cov(term.T)
    constraints = [cp.sum(w) == 1, w >= mins]
    for i, v in fixed.items():
        constraints.append(w[i] == v)
    prob = cp.Problem(cp.Minimize(cp.quad_form(w, sigma + 1e-12 * np.eye(d))), constraints)
    prob.solve(solver='CLARABEL')
    allocs['min_var'] = None if w.value is None else np.maximum(np.asarray(w.value).ravel(), 0) * wealth
    rd, window = realized_window(frame, cf, t0)
    marks = rd[0][0]  # (13, d) realized unit marks incl. haircuts and property
    prev = {}
    pw = TMP / 'prev_weights.json'
    if pw.exists():
        prev = json.loads(pw.read_text())
    new_prev = {}
    per_method = {}
    for name, a in allocs.items():
        if a is None:
            per_method[name] = {'available': False}
            continue
        r = cash_first(cf, rd, a)
        wf = a / wealth
        port = marks @ wf  # asset-value path, ratio to reference wealth
        drift = wf * marks[-1]
        drift = drift / drift.sum()
        new_prev[name] = drift.tolist()
        turnover = None
        if name in prev:
            turnover = float(np.abs(wf - np.asarray(prev[name])).sum())
        per_method[name] = {
            'available': True,
            'weights': (a / wealth).tolist(),
            'funded': bool(r['funded'][0]),
            'payment_shortfalls_dollars': r['payment_shortfalls'][0].tolist(),
            'terminal_unpaid_dollars': float(r['terminal_unpaid'][0]),
            'terminal_net_dollars': float(r['terminal_net'][0]),
            'realized_window_return': float(r['terminal_net'][0] / wealth - 1),
            'max_path_loss': float(np.maximum(0, 1 - port).max()),
            'min_net_wealth_ratio': float(r['net_wealth_paths'][0].min() / wealth),
            'turnover': turnover,
        }
    (TMP / 'prev_weights.json').write_text(json.dumps(new_prev))
    solvers = []
    for mi in range(s['mult_index'] + 1):
        p = TMP / f'fold_{k:03d}_solve_{mi}.json'
        if p.exists():
            solvers.append(json.loads(p.read_text()))
    sel = json.loads((TMP / f'fold_{k:03d}_select.json').read_text())
    rec = {
        'fold': k, 'decision_date': str(frame.index[t0].date()),
        'train_weeks': t0, 'train_start': str(frame.index[0].date()),
        'train_end': str(frame.index[t0 - 1].date()),
        'window_start': str(window.index[0].date()), 'window_end': str(window.index[-1].date()),
        'solves': solvers,
        'selection': {kk: vv for kk, vv in sel.items() if kk != 'calibration'},
        'calibration': sel.get('calibration'),
        'methods': per_method,
        'seeds': {'train': BASE_SEED + k, 'validation_base': BASE_SEED + 100000 + 1000 * k},
        'property_note': 'Realized property marks from URA quarterly price index (45-day release lag), engine cash_and_mark rent/sale convention; quarterly index granularity, not a tradable weekly property return.',
    }
    (RESULTS / f'fold_{k:03d}.json').write_text(json.dumps(rec, default=str, indent=1))
    s['done'].append(k)
    s['fold'] = k + 1
    s['mult_index'] = 0
    s['stage'] = 'solve'
    save_state(s)
    return f"realized fold={k} done={len(s['done'])}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-seconds', type=float, default=1500)
    args = ap.parse_args()
    t_start = time.perf_counter()
    c = build_config()
    frame = full_frame(c)
    starts = fold_starts(len(frame))
    print(f'{len(starts)} folds over {len(frame)} weeks', flush=True)
    while True:
        s = load_state()
        if s['fold'] >= len(starts):
            print('ALL FOLDS COMPLETE')
            return
        stage = s['stage']
        need = 300 if stage == 'solve' else 120
        if time.perf_counter() - t_start + need > args.max_seconds:
            print(f"time budget reached at fold={s['fold']} stage={stage}", flush=True)
            return
        try:
            if stage == 'solve':
                msg = stage_solve(c, frame, starts)
            elif stage == 'select':
                msg = stage_select(c, frame, starts)
            else:
                msg = stage_realized(c, frame, starts)
        except Exception as err:
            # Record the failure with its fold and keep the stage for retry/inspection.
            s = load_state()
            (RESULTS / f'error_fold_{s["fold"]:03d}_{s["stage"]}.json').write_text(json.dumps(
                {'fold': s['fold'], 'stage': s['stage'], 'mult_index': s['mult_index'],
                 'error': repr(err)}, indent=1))
            raise
        print(msg, flush=True)


if __name__ == '__main__':
    main()
