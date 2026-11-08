"""LABELED SENSITIVITY (Tijs, 8 Nov 09:52 + steering 09:54): which asset adds
the most diversification, tested in the engine - not a rules-of-thumb list.

Universe: the T-bill registry (VTI/VWO/GLD/IEF/tbill anchor/cash/property 10%
fixed) plus ONE candidate at a time: TIP, TLT, AGG, VNQ, DBC, DBMF (Yahoo
adjusted-close total return, manifests in studies/tbill/data/candidates/).

Method (frozen validation discipline, same as the 10y matrix study):
  1. One-year raw optimizer solve on the expanded universe gives the risky
     sleeve proportions including the candidate (same source as the matrix
     study's frozen proportions). If the 1y optimizer allocates <0.5% of the
     sleeve to the candidate, an exploratory tilt is used instead: candidate
     gets 10% of the sleeve, the rest scaled down proportionally - labeled.
  2. Ten-year mix search over safe (T-bill) share 10-90% in 2.5% steps, at
     TWO caps: cml_budget 6% (current strict) and 40% (owner's new default),
     loss_budget 15% both. Candidates judged on 4x200 shared fresh validation
     paths, selection verified on 4x400 independent final paths with the
     one-step-safer walk-back. Draws are shared across caps within a universe.
  3. Reported: chosen safe share, full weights, CARA CE on final paths,
     median and 5% leftover after all 120 x $250k payments, model-implied
     expected annual return, funded status, final-judge verdict.
  4. Control = the same procedure on the registry without any addition
     (includes the loss-budget binding check at the new 40% default: the mix
     search re-run at loss_budget 40%; equal safe share => not binding).

Short-history caveat: weekly_returns fits on the COMMON window, so DBMF
(2019-05+) truncates the whole fit to 2019+ (no 2008, no 2011, no 2013);
DBC truncates to 2006-02. Labeled where it applies.
"""
from pathlib import Path
import json, sys, time
import numpy as np
from emfin_v2.default_run import validate_config, setup, draw_paths, probabilities, holding_bounds, solve
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from emfin_v2.utilities import native_ce

sys.path.insert(0, 'studies/tbill')
from study_tbill import provision
from study_horizon import schedule

OUT = Path('studies/tbill/results/study_diversification.json')
BASE = 'studies/tbill/config_tbill.json'
DATADIR = Path('studies/tbill/data/candidates').resolve()
YEARS, MONTHS, WEEKS = 10, 120, 520
SAFE_GRID = np.round(np.arange(0.10, 0.9001, 0.025), 4)
CAPS = [0.06, 0.40]
WINDOW_CTRL = {'control_w2006': '2006-02-06', 'control_w2019': '2019-05-08'}

CANDS = {
    'control': None,
    'control_w2006': None,
    'control_w2019': None,
    'tips': dict(ticker='TIP', name='US TIPS', asset_class='tips', haircut=0.0005),
    'long_treasury': dict(ticker='TLT', name='US 20+yr Treasuries', asset_class='treasury_long', haircut=0.0005),
    'agg_bond': dict(ticker='AGG', name='US aggregate bonds', asset_class='agg_bond', haircut=0.0005),
    'reits': dict(ticker='VNQ', name='US REITs', asset_class='reits', haircut=0.0015),
    'commodities': dict(ticker='DBC', name='Broad commodities', asset_class='commodities', haircut=0.0015),
    'managed_futures': dict(ticker='DBMF', name='Managed futures', asset_class='managed_futures', haircut=0.002),
}


def build_config(cand_id, cml, loss, weeks=WEEKS):
    c = json.loads(Path(BASE).read_text())
    if cand_id in WINDOW_CTRL:
        tag = cand_id.replace('control_', '')
        for a in ['us_equity', 'em_equity', 'gold', 'treasury', 'tbill']:
            c['history_manifests'][a] = str(DATADIR / f'{a}-{tag}-manifest.json')
        c['label'] += f' LABELED WINDOW CONTROL: all histories truncated to >={WINDOW_CTRL[cand_id]} to match the short-history candidate window.'
    if CANDS[cand_id]:
        spec = CANDS[cand_id]
        entry = dict(enabled=True, currency='USD', return_model='etf_total_return', liquidity='listed',
                     minimum_weight=0.0, mean_view=False, factors=[], cash=False, id=cand_id,
                     ticker=spec['ticker'], name=spec['name'], asset_class=spec['asset_class'],
                     haircut=spec['haircut'],
                     source=dict(kind='yahoo_adjusted_close', url=f"https://finance.yahoo.com/quote/{spec['ticker']}/history/",
                                 status='private research, owner-accepted terms risk (7 Nov 2026)', redistribution='not_cleared'))
        assets = c['asset_registry']['assets']
        pos = next(i for i, a in enumerate(assets) if a['id'] == 'treasury') + 1
        assets.insert(pos, entry)
        c['history_manifests'][cand_id] = str(DATADIR / f'{cand_id}-manifest.json')
    c['horizon_weeks'] = weeks
    if weeks == WEEKS:
        c['recurring_payout'] = None
        c['liabilities'] = schedule(MONTHS)
    c['funding_mode'] = 'pay_all_99'
    c['cml_budget'] = cml
    c['loss_budget'] = loss
    c['label'] += (f' LABELED DIVERSIFICATION SENSITIVITY: +{cand_id}, {weeks//52}y horizon, '
                   f'cml_budget={cml:.0%}, loss_budget={loss:.0%}.')
    return validate_config(c)


def sleeve_proportions(cand_id):
    """1y raw optimizer on the expanded universe -> risky sleeve proportions."""
    c = build_config(cand_id, 0.06, 0.15, weeks=52)
    fit = setup(c)
    dr = draw_paths(c, fit, 100, c['seed'])
    p, ps = probabilities(c, dr[0], dr.re_price_logs)
    raw, status = solve(c, dr, p, ps, 1.)
    ids = c['asset_layout']['ids']
    mins, fixed = holding_bounds(c, len(ids))
    safe_idx = ids.index('tbill')
    risky = {}
    for i, a in enumerate(ids):
        if i == safe_idx or i in fixed or mins[i] > 0 or a == 'cash':
            continue
        w = float(raw[i] / c['wealth'])
        if w > 1e-6:
            risky[a] = w
    return risky, status.get('kind'), float(raw[safe_idx] / c['wealth'])


def run_universe(cand_id):
    t0 = time.perf_counter()
    risky, kind, raw_safe = sleeve_proportions(cand_id)
    tot = sum(risky.values())
    prop = {k: v / tot for k, v in risky.items()}
    tilted = False
    if CANDS[cand_id] and prop.get(cand_id, 0) < 0.005:
        prop = {k: v * 0.9 for k, v in prop.items()}
        prop[cand_id] = 0.10
        tilted = True
    c0 = build_config(cand_id, 0.06, 0.15)
    fit = setup(c0)
    ids = c0['asset_layout']['ids']
    d = len(ids)
    mins, fixed = holding_bounds(c0, d)
    safe_idx = ids.index('tbill')
    risky_idx = [i for i in range(d) if i != safe_idx and i not in fixed and mins[i] == 0 and ids[i] != 'cash']

    def mix(safe_share):
        w = np.zeros(d)
        w[safe_idx] = safe_share
        for i, v in fixed.items():
            w[i] = v
        rem = 1 - safe_share - sum(fixed.values())
        for i in risky_idx:
            w[i] = rem * prop.get(ids[i], 0)
        assert abs(w.sum() - 1.0) < 1e-9
        return w

    validation = [draw_paths(c0, fit, 200, c0['seed'] + 1000 + j) for j in range(4)]
    vp = [probabilities(c0, v[0], v.re_price_logs) for v in validation]
    final = [draw_paths(c0, fit, 400, c0['seed'] + 10000 + j) for j in range(4)]
    fp = [probabilities(c0, x[0], x.re_price_logs) for x in final]
    train = draw_paths(c0, fit, 800, c0['seed'] + 555)
    wk = train[0][:, 1:, :] / train[0][:, :-1, :] - 1.0
    exp_annual = ((1 + wk.mean(axis=(0, 1))) ** 52 - 1).tolist()

    def cell(cml, loss):
        c = build_config(cand_id, cml, loss)
        chosen = None
        for s in SAFE_GRID:
            a = mix(float(s)) * c['wealth']
            v = evaluate(c, validation, a, [x[0] for x in vp], [x[1] for x in vp])
            if v['overall_pass']:
                chosen = float(s)
                break
        if chosen is None:
            return dict(chosen_safe=None, note='no candidate mix passes validation')
        s = chosen
        pick = None
        while s <= 0.9001:
            a = mix(float(s)) * c['wealth']
            verdict = evaluate(c, final, a, [x[0] for x in fp], [x[1] for x in fp])
            if verdict['overall_pass']:
                pick = (float(s), verdict)
                break
            s = round(s + 0.025, 4)
        if pick is None:
            return dict(chosen_safe=None, note='fails independent final judge even at 90% safe')
        s, verdict = pick
        a = mix(s) * c['wealth']
        audits = [cash_first(c, x, a) for x in final]
        x = np.concatenate([z['terminal_net'] for z in audits])
        L = np.concatenate([provision(z) for z in final])
        common = native_ce('cara', x + L, x, np.full(len(x), 1 / len(x)), c['wealth'], c['risk_tolerance'], L)
        w = (a / c['wealth']).tolist()
        return dict(chosen_safe=s, validation_selected_safe=chosen,
                    weights={n: round(wi, 4) for n, wi in zip(ids, w)},
                    expected_annual_return=float(np.dot(w, exp_annual)),
                    common_cara_ledger_ce=common['ce'],
                    terminal_median=float(np.median(x)), terminal_q05=float(np.quantile(x, .05)),
                    prob_end_below_start=float(np.mean(x < 0)),
                    funded=float(np.mean([z['funded'].mean() for z in audits])),
                    largest_unpaid=max(float(z['payment_shortfalls'].max()) for z in audits),
                    final_pass=True, final_breaches=verdict.get('breaches'))

    out = dict(sleeve_proportions_1y_optimizer={k: round(v, 4) for k, v in prop.items()},
               optimizer_safe_share_1y=raw_safe, exploratory_tilt=tilted,
               cells={f'cml{int(c*100)}': cell(c, 0.15) for c in CAPS},
               seconds=time.perf_counter() - t0)
    if cand_id in ('control', 'control_w2006', 'control_w2019'):
        c15 = out['cells']['cml40']['chosen_safe']
        loose = cell(0.40, 0.40)
        out['loss_budget_binding_check'] = dict(
            safe_at_loss15=c15, safe_at_loss40=loose['chosen_safe'],
            binding=loose['chosen_safe'] != c15)
    return out


def main():
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    for cand_id in CANDS:
        if cand_id in results:
            print('skip', cand_id, flush=True)
            continue
        results[cand_id] = run_universe(cand_id)
        OUT.write_text(json.dumps(results, default=str, indent=1))
        r = results[cand_id]
        for cap, cellr in r['cells'].items():
            cs = cellr.get('chosen_safe')
            print('%s %s -> safe=%s CE=%s' % (cand_id, cap,
                  f'{cs:.3f}' if cs else 'NONE',
                  f"{cellr.get('common_cara_ledger_ce', 0)/1e6:.1f}M" if cs else '-'), flush=True)
        print('%s done %.0fs' % (cand_id, r['seconds']), flush=True)


if __name__ == '__main__':
    main()
