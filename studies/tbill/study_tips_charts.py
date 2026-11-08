"""NEW MODEL study (Tijs, WhatsApp 8 Nov 2026 10:17): TIPS added - the only
universe change ("Only add TIPS now") - under the owner's new defaults
(10y horizon, cml_budget 0.40, loss_budget 0.15 kept, $250k/month x120 labeled
beyond the confirmed year). Owner nuance (10:23, relayed by main): at other
horizons the 15% terminal loss limit moves to the END of that horizon.

Produces the numbers for the chart pack:
  base      validated portfolio under the new model (mix search, frozen
            validation discipline, identical to study_diversification.py)
  utilities CARA / CRRA / HARA / kinked-shortfall: separate 1y optimizer
            sleeve proportions per utility, then the same constraint-driven
            mix search; scored native + common CARA on shared final paths
  cml       in-period (any-point) cap sweep at loss_budget 15%, shared draws
  bench     clever (validated mix) vs simple baselines on shared final paths
  rebal     rebalancing frequency (never/12/6/3/1 months), custom labeled
            rebalance ledger (dynamic_policy.execute requires exactly 4 risky
            sleeves; the new universe has 6, so a purpose-built simulator
            mirrors cash_first and adds rebalancing-to-target)
  horizon   5/10/15/20/30 years; terminal 15% loss limit at horizon end
  payout    $50k/$100k/$250k per month at 10y (identical price paths:
            deterministic liabilities do not consume RNG; same seeds)

All sections: labeled sensitivity, private research, nominal dollars.
"""
from pathlib import Path
import copy, json, sys, time
import numpy as np

sys.path.insert(0, 'studies/tbill')
from emfin_v2.default_run import validate_config, setup, draw_paths, probabilities, holding_bounds, solve
from emfin_v2.evaluation import evaluate, common_tail
from emfin_v2.ledger import cash_first
from emfin_v2.utilities import native_ce
from emfin_v2.real_estate import ScenarioDraw
from study_tbill import provision
from study_horizon import schedule

BASE = 'studies/tbill/config_tbill.json'
OUT = Path('studies/tbill/results/study_tips_charts.json')
DRAW_DIR = Path('/tmp/tips_draws')
DRAW_DIR.mkdir(exist_ok=True)
SEED = 20261107
SAFE_GRID = np.round(np.arange(0.10, 0.9001, 0.025), 4)
KINDS = ['cara', 'crra_gross', 'hara_payment_floor', 'kinked_shortfall']


def nm_config(weeks=520, months=120, cml=0.40, loss=0.15, payout=250000.0,
              objective=None, one_year_sleeve=False, radius_scale=1.0):
    """New-model config: T-bill registry + TIPS, owner defaults. Labeled."""
    c = json.loads(Path(BASE).read_text())
    root = Path('.').resolve()
    for k in list(c['history_manifests']):
        c['history_manifests'][k] = str(root / 'emfin_v2/resources/data/actual_etfs'
                                        / Path(c['history_manifests'][k]).name)
    assets = c['asset_registry']['assets']
    if not any(a['id'] == 'tips' for a in assets):
        entry = dict(enabled=True, currency='USD', return_model='etf_total_return',
                     liquidity='listed', minimum_weight=0.0, mean_view=False, factors=[],
                     cash=False, id='tips', ticker='TIP', name='US TIPS', asset_class='tips',
                     haircut=0.0005,
                     source=dict(kind='yahoo_adjusted_close',
                                 url='https://finance.yahoo.com/quote/TIP/history/',
                                 status='private research, owner-accepted terms risk (7 Nov 2026)',
                                 redistribution='not_cleared'))
        pos = next(i for i, a in enumerate(assets) if a['id'] == 'treasury') + 1
        assets.insert(pos, entry)
    c['history_manifests']['tips'] = str(root / 'studies/tbill/data/candidates/tips-manifest.json')
    c['anchor_asset_id'] = 'tbill'
    if one_year_sleeve:
        c['cml_budget'] = 0.06
        c['loss_budget'] = 0.15
        # keep the config's own 12-month recurring payout and 52-week horizon
    else:
        c['horizon_weeks'] = weeks
        c['recurring_payout'] = None
        c.pop('one_off_liabilities', None)
        c['liabilities'] = schedule(months, payout)
        c['cml_budget'] = cml
        c['loss_budget'] = loss
    if objective:
        c['objective_kind'] = objective
    if radius_scale != 1.0:
        c['wasserstein_radius'] *= radius_scale
        c['label'] += (f' LABELED SENSITIVITY: model-miss buffer scaled x{radius_scale:.2f} (keeps its '
                       'confirmed-250k share, 80%, of the 20%-of-payment allowance; 4th-edition '
                       'section 13 precedent). No budget loosened.')
    c['funding_mode'] = 'pay_all_99'
    c['label'] += (' NEW MODEL (owner, WhatsApp 8 Nov 2026 10:17): TIPS added, the only universe '
                   'change; 10y/40%-cap/15%-terminal-loss owner defaults (09:54 + 10:17).')
    return validate_config(c)


def get_draws(c, fit, tag, payout_scale=1.0):
    """Load or draw validation (4x200) and final (4x400) sets; deterministic in (config, seed)."""
    f = DRAW_DIR / f'{tag}.npz'
    if f.exists():
        z = np.load(f, allow_pickle=False)

        def unpack(prefix, count):
            out = []
            for j in range(count):
                steps = z[f'{prefix}{j}_steps']
                out.append(ScenarioDraw((z[f'{prefix}{j}_prices'], z[f'{prefix}{j}_amounts'],
                                         steps, z[f'{prefix}{j}_bases'], z[f'{prefix}{j}_growth']),
                                        z[f'{prefix}{j}_funding'], z[f'{prefix}{j}_relog']))
            return out
        val, fin = unpack('v', 4), unpack('f', 4)
    else:
        val = [draw_paths(c, fit, 200, c['seed'] + 1000 + j) for j in range(4)]
        fin = [draw_paths(c, fit, 400, c['seed'] + 10000 + j) for j in range(4)]
        blob = {}
        for prefix, draws in (('v', val), ('f', fin)):
            for j, d in enumerate(draws):
                blob[f'{prefix}{j}_prices'] = d[0]
                blob[f'{prefix}{j}_amounts'] = d[1]
                blob[f'{prefix}{j}_steps'] = d[2]
                blob[f'{prefix}{j}_bases'] = d[3]
                blob[f'{prefix}{j}_growth'] = d[4]
                blob[f'{prefix}{j}_funding'] = d.funding_paths
                blob[f'{prefix}{j}_relog'] = d.re_price_logs
        np.savez(f, **blob)
    if payout_scale != 1.0:
        def scaled(draws):
            out = []
            for d in draws:
                out.append(ScenarioDraw((d[0], d[1] * payout_scale, d[2], d[3] * payout_scale, d[4]),
                                        d.funding_paths, d.re_price_logs))
            return out
        val, fin = scaled(val), scaled(fin)
    vp = [probabilities(c, v[0], v.re_price_logs) for v in val]
    fp = [probabilities(c, x[0], x.re_price_logs) for x in fin]
    return val, vp, fin, fp


def mix_fn(c, prop):
    ids = c['asset_layout']['ids']
    d = len(ids)
    mins, fixed = holding_bounds(c, d)
    fixed = {int(k): v for k, v in fixed.items()}
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
    return mix, ids


def sleeve_proportions(objective='cara'):
    """1y raw optimizer on the new universe -> risky sleeve proportions."""
    c = nm_config(one_year_sleeve=True, objective=objective)
    fit = setup(c)
    dr = draw_paths(c, fit, 100, c['seed'])
    p, ps = probabilities(c, dr[0], dr.re_price_logs)
    raw, status = solve(c, dr, p, ps, 1.)
    ids = c['asset_layout']['ids']
    mins, fixed = holding_bounds(c, len(ids))
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
    return ({k: v / tot for k, v in risky.items()}, float(raw[safe_idx] / c['wealth']),
            status.get('kind'))


def score_final(c, fin, fp, a):
    audits = [cash_first(c, x, a) for x in fin]
    x = np.concatenate([z['terminal_net'] for z in audits])
    L = np.concatenate([provision(z) for z in fin])
    common = native_ce('cara', x + L, x, np.full(len(x), 1 / len(x)), c['wealth'], c['risk_tolerance'], L)
    return dict(common_cara_ledger_ce=common['ce'],
                terminal_median=float(np.median(x)), terminal_q05=float(np.quantile(x, .05)),
                terminal_q95=float(np.quantile(x, .95)),
                prob_end_below_start=float(np.mean(x < 0)),
                funded=float(np.mean([z['funded'].mean() for z in audits])),
                largest_unpaid=max(float(z['payment_shortfalls'].max()) for z in audits),
                total_paid=float(sum(z[3].sum() for z in fin[:1])))


def mix_search(c, val, vp, fin, fp, prop, label=''):
    """Lowest safe share passing validation, then one-step-safer walk-back on final."""
    mix, ids = mix_fn(c, prop)
    chosen = None
    for s in SAFE_GRID:
        a = mix(float(s)) * c['wealth']
        v = evaluate(c, val, a, [x[0] for x in vp], [x[1] for x in vp])
        if v['overall_pass']:
            chosen = float(s)
            break
    if chosen is None:
        return dict(chosen_safe=None, note='no candidate mix passes validation', label=label)
    s = chosen
    pick = None
    while s <= 0.9001:
        a = mix(float(s)) * c['wealth']
        verdict = evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
        if verdict['overall_pass']:
            pick = (float(s), verdict)
            break
        s = round(s + 0.025, 4)
    if pick is None:
        return dict(chosen_safe=None, note='fails independent final judge even at 90% safe', label=label)
    s, verdict = pick
    a = mix(s) * c['wealth']
    out = dict(chosen_safe=s, validation_selected_safe=chosen,
               weights={n: round(float(wi), 4) for n, wi in zip(ids, a / c['wealth'])},
               final_pass=True, final_breaches=verdict.get('breaches'), label=label)
    out.update(score_final(c, fin, fp, a))
    return out


def expected_returns(c, fit):
    train = draw_paths(c, fit, 800, c['seed'] + 555)
    wk = train[0][:, 1:, :] / train[0][:, :-1, :] - 1.0
    return ((1 + wk.mean(axis=(0, 1))) ** 52 - 1).tolist()


# ---------------- rebalancing simulator (labeled sensitivity) ----------------

def simulate(c, draw, w0, rebalance_weeks=None, payouts=True):
    """cash_first twin + rebalancing to target among cash+listed sleeves.

    Sells use the same haircut-netted unit values as cash_first; buys at the
    same values (no buy-side cost - labeled). Property never traded.
    """
    paths, amounts, steps, bases, growth = draw
    prices = np.asarray(paths, float)
    n, h, d = prices.shape
    cash_ix = c['cash_index']
    prop_ix = c.get('asset_layout', {}).get('property_indices', [])
    liquid = [i for i in range(d) if i != cash_ix and i not in prop_ix]
    a = np.asarray(w0, float) * c['wealth']
    units = np.broadcast_to(a, (n, d)).copy()
    units[:, cash_ix] = 0.
    cash = np.full(n, a[cash_ix])
    arrears = np.zeros(n)
    shortfalls = np.zeros_like(amounts)
    wealth = np.zeros((n, h))
    turnover = np.zeros(n)
    rebal = set()
    if rebalance_weeks:
        rebal = set(range(0, h, int(rebalance_weeks)))
    target_liq = np.array([a[i] for i in [cash_ix] + liquid])
    target_liq = target_liq / target_liq.sum()
    amts = amounts if payouts else np.zeros_like(amounts)
    for t in range(h):
        ratio = growth[:, t] / (growth[:, t - 1] if t else 1.)
        cash *= ratio
        arrears *= ratio
        if t in rebal:
            px = prices[:, t]
            vals = units[:, liquid] * px[:, liquid]
            total = cash + vals.sum(1)
            desired = total[:, None] * target_liq[None, :]
            desired_cash = desired[:, 0]
            desired_vals = desired[:, 1:]
            dv = desired_vals - vals
            trade = np.abs(dv).sum(1) + np.abs(desired_cash - cash)
            turnover += trade / 2
            units[:, liquid] = desired_vals / px[:, liquid]
            cash = desired_cash
        for k in np.flatnonzero(steps == t + 1):
            due = amts[:, k] + arrears
            need = np.maximum(due - cash, 0.)
            available = prices[:, t, liquid] * units[:, liquid]
            total = available.sum(1)
            fraction = np.minimum(1., np.divide(need, total, out=np.zeros(n), where=total > 0))
            liquidation = available * fraction[:, None]
            units[:, liquid] *= 1 - fraction[:, None]
            cash += liquidation.sum(1)
            payment = np.minimum(cash, due)
            cash -= payment
            arrears = due - payment
            shortfalls[:, k] = arrears
        wealth[:, t] = (cash + (prices[:, t, liquid] * units[:, liquid]).sum(1)
                        + prices[:, t, prop_ix] @ a[prop_ix] - arrears)
    return dict(net_wealth_paths=wealth, payment_shortfalls=shortfalls,
                terminal_net=wealth[:, -1], funded=np.all(shortfalls <= 1e-6, axis=1),
                turnover=turnover)


def judge_sim(c, sims, fin, fp, w0):
    """Judge-style stats on simulated paths: funding, any-point (cml) and terminal
    loss measured on the no-payout shadow run, budgets as in evaluate()."""
    from scipy.stats import t as tdist
    from emfin_v2.toolbox.wasserstein import penalty
    wealth = c['wealth']
    keys = []
    per_batch = []
    for sim, shad, d, (q, qs) in zip(sims['pay'], sims['shadow'], fin, fp):
        measures = np.array([np.full(len(d[0]), 1 / len(d[0])), q, qs])
        losses = []
        for i, step in enumerate(d[2]):
            losses.append(sim['payment_shortfalls'][:, i] / wealth)
        wp = shad['net_wealth_paths'] / wealth
        losses.append(np.maximum(0, 1 - wp).max(1))     # any-point loss vs start
        losses.append(1 - wp[:, -1])                     # terminal loss
        per_batch.append([common_tail(x, measures, c['confidence'], k < len(losses) - 1)
                          for k, x in enumerate(losses)])
    x = np.asarray(per_batch)
    crit = tdist.ppf(1 - .05 / (x.shape[1] * 1), len(fin) - 1)
    high = x.mean(0) + crit * x.std(0, ddof=1) / np.sqrt(len(fin))
    buffer = penalty(np.asarray(w0, float), c.get('wasserstein_radius', 0), c['confidence'],
                     metric=c.get('wasserstein_metric', 'legacy_l1'))
    n_dates = len(fin[0][2])
    checks = []
    worst = 0.0
    for k in range(n_dates + 2):
        funding = k < n_dates
        limit = (fin[0][3][k] * c['funding_budget_fraction'] / wealth if funding
                 else c['cml_budget'] if k == n_dates else c['loss_budget'])
        val = float(high[k] + buffer)
        ok = val <= limit
        worst = max(worst, val - limit)
        checks.append(ok)
    return dict(overall_pass=bool(all(checks)), worst_margin=float(worst),
                cml_ru=float(high[-2] + buffer), terminal_ru=float(high[-1] + buffer),
                max_funding_ru=float(high[:n_dates].max() + buffer) if n_dates else 0.0)


def run_rebal(c, fin, fp, w0):
    out = {}
    for label, weeks in [('never (buy & hold)', None), ('every 12 months', 52),
                         ('every 6 months', 26), ('every 3 months', 13), ('every month', 4)]:
        pay = [simulate(c, d, w0, weeks, payouts=True) for d in fin]
        shadow = [simulate(c, d, w0, weeks, payouts=False) for d in fin]
        j = judge_sim(c, dict(pay=pay, shadow=shadow), fin, fp, w0)
        x = np.concatenate([z['terminal_net'] for z in pay])
        L = np.concatenate([provision(z) for z in fin])
        common = native_ce('cara', x + L, x, np.full(len(x), 1 / len(x)), c['wealth'],
                           c['risk_tolerance'], L)
        out[label] = dict(rebalance_weeks=weeks, judge=j,
                          common_cara_ledger_ce=common['ce'],
                          terminal_median=float(np.median(x)), terminal_q05=float(np.quantile(x, .05)),
                          funded=float(np.mean([z['funded'].mean() for z in pay])),
                          turnover_mean=float(np.mean([z['turnover'].mean() for z in pay])))
        print('  rebal %-20s pass=%s CE=%.1fM q05=%.1fM' %
              (label, j['overall_pass'], common['ce'] / 1e6, np.quantile(x, .05) / 1e6), flush=True)
    return out


# ---------------- sections ----------------

def load_results():
    return json.loads(OUT.read_text()) if OUT.exists() else {}


def save_results(r):
    OUT.write_text(json.dumps(r, default=str, indent=1))


def sec_fit():
    c = nm_config()
    t0 = time.perf_counter()
    fit = setup(c)
    get_draws(c, fit, 'h520')
    r = load_results()
    r['meta'] = dict(seed=SEED, fit_seconds=time.perf_counter() - t0,
                     history=c.get('history_evidence', {}).get('first_week'),
                     history_last=c.get('history_evidence', {}).get('last_week'),
                     assets=c['asset_layout']['ids'])
    save_results(r)
    print('fit+draws done %.0fs' % (time.perf_counter() - t0), r['meta']['assets'], flush=True)


def sec_base():
    c = nm_config()
    fit = setup(c)
    val, vp, fin, fp = get_draws(c, fit, 'h520')
    prop, raw_safe, kind = sleeve_proportions('cara')
    r = load_results()
    r['sleeve_cara'] = dict(proportions=prop, optimizer_safe_share=raw_safe, status=kind)
    r['expected_annual_return_per_asset'] = dict(zip(c['asset_layout']['ids'], expected_returns(c, fit)))
    t0 = time.perf_counter()
    r['base'] = mix_search(c, val, vp, fin, fp, prop, label='new model, owner defaults')
    r['base']['seconds'] = time.perf_counter() - t0
    w = r['base'].get('weights')
    if w:
        er = r['expected_annual_return_per_asset']
        r['base']['expected_annual_return'] = float(sum(w[i] * er[i] for i in c['asset_layout']['ids']))
    save_results(r)
    print('base:', json.dumps(r['base'], default=str)[:600], flush=True)


def sec_utilities():
    c = nm_config()
    fit = setup(c)
    val, vp, fin, fp = get_draws(c, fit, 'h520')
    r = load_results()
    r.setdefault('utilities', {})
    for kind in KINDS:
        if kind in r['utilities']:
            print('skip', kind, flush=True)
            continue
        t0 = time.perf_counter()
        prop, raw_safe, status = sleeve_proportions(kind)
        res = mix_search(c, val, vp, fin, fp, prop, label=f'utility={kind}')
        if res.get('chosen_safe') is not None:
            mix, ids = mix_fn(c, prop)
            a = mix(res['chosen_safe']) * c['wealth']
            audits = [cash_first(c, x, a) for x in fin]
            x = np.concatenate([z['terminal_net'] for z in audits])
            L = np.concatenate([provision(z) for z in fin])
            gross = np.concatenate([d[0][:, -1] @ a for d in fin])
            q = np.concatenate([np.full(len(d[0]), 1 / len(d[0])) / 4 for d in fin])
            native = native_ce(kind, gross, gross - L, q, c['wealth'], c['risk_tolerance'], L)
            res['native_ce'] = native['ce']
        res['sleeve_proportions'] = prop
        res['optimizer_safe_share_1y'] = raw_safe
        res['seconds'] = time.perf_counter() - t0
        r['utilities'][kind] = res
        save_results(r)
        print('utility', kind, 'safe=', res.get('chosen_safe'), 'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)


def sec_cml():
    fit = None
    r = load_results()
    r.setdefault('cml_sweep', {})
    prop = r['sleeve_cara']['proportions']
    for cap in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
        key = f'{cap:.2f}'
        if key in r['cml_sweep']:
            print('skip', key, flush=True)
            continue
        c = nm_config(cml=cap, loss=0.15)
        if fit is None:
            fit = setup(c)
        val, vp, fin, fp = get_draws(c, fit, 'h520')
        t0 = time.perf_counter()
        r['cml_sweep'][key] = mix_search(c, val, vp, fin, fp, prop, label=f'cml={cap:.0%}, loss=15%')
        r['cml_sweep'][key]['seconds'] = time.perf_counter() - t0
        save_results(r)
        print('cml', key, '->', r['cml_sweep'][key].get('chosen_safe'), flush=True)
    # binding check: same cap, loss limit relaxed to 40%
    if 'binding_loss40' not in r['cml_sweep']:
        c = nm_config(cml=0.40, loss=0.40)
        if fit is None:
            fit = setup(c)
        val, vp, fin, fp = get_draws(c, fit, 'h520')
        r['cml_sweep']['binding_loss40'] = mix_search(c, val, vp, fin, fp, prop, label='cml=40%, loss=40% (binding check)')
        save_results(r)
        print('binding check done', flush=True)


def sec_bench():
    c = nm_config()
    fit = setup(c)
    val, vp, fin, fp = get_draws(c, fit, 'h520')
    r = load_results()
    prop = r['sleeve_cara']['proportions']
    mix, ids = mix_fn(c, prop)
    d = len(ids)
    mins, fixed = holding_bounds(c, d)
    fixed = {int(k): v for k, v in fixed.items()}
    propw = sum(fixed.values())

    def w_of(pairs):
        w = np.zeros(d)
        for name, v in pairs.items():
            w[ids.index(name)] = v
        return w

    clever = np.array([r['base']['weights'][i] for i in ids])
    risky_names = [i for i in ids if i not in ('tbill', 'cash', 'sg_property')]
    eq = np.zeros(d)
    free = 1 - propw
    for i in range(d):
        if ids[i] in risky_names + ['tbill']:
            eq[i] = free / (len(risky_names) + 1)
    for i, v in fixed.items():
        eq[i] = v
    reserve_share = min(0.30, sum(c_l['amount'] for c_l in c['liabilities']) / c['wealth'])
    reserve = np.zeros(d)
    reserve[ids.index('tbill')] = reserve_share
    rem = 1 - propw - reserve_share
    for name in risky_names:
        reserve[ids.index(name)] = rem * prop.get(name, 0)
    for i, v in fixed.items():
        reserve[i] = v
    candidates = {
        'clever (validated mix)': clever,
        'all T-bills + property': mix(0.90),
        '60/40-style (60% stocks, 30% bills)': w_of({'us_equity': 0.60, 'tbill': 0.30, 'sg_property': 0.10}),
        'equal weight (1/N)': eq,
        'reserve payouts, rest risky': reserve,
    }
    rows = {}
    for label, w in candidates.items():
        a = w * c['wealth']
        v = evaluate(c, val, a, [x[0] for x in vp], [x[1] for x in vp])
        verdict = evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
        row = dict(weights={n: round(float(wi), 4) for n, wi in zip(ids, w)},
                   validation_pass=bool(v['overall_pass']), final_pass=bool(verdict['overall_pass']),
                   final_breaches=verdict.get('breaches'))
        row.update(score_final(c, fin, fp, a))
        rows[label] = row
        print('bench %-38s val=%s final=%s CE=%.1fM' %
              (label, row['validation_pass'], row['final_pass'], row['common_cara_ledger_ce'] / 1e6), flush=True)
    r['benchmarks'] = rows
    save_results(r)


def sec_rebal():
    c = nm_config()
    fit = setup(c)
    val, vp, fin, fp = get_draws(c, fit, 'h520')
    r = load_results()
    ids = c['asset_layout']['ids']
    w0 = np.array([r['base']['weights'][i] for i in ids])
    t0 = time.perf_counter()
    r['rebalancing'] = run_rebal(c, fin, fp, w0)
    r['rebalancing_seconds'] = time.perf_counter() - t0
    save_results(r)


def sec_horizon(which):
    r = load_results()
    prop = r['sleeve_cara']['proportions']
    r.setdefault('horizon', {})
    for years in which:
        key = f'{years}y'
        if key in r['horizon']:
            print('skip', key, flush=True)
            continue
        weeks, months = 52 * years, 12 * years
        c = nm_config(weeks=weeks, months=months, cml=0.40, loss=0.15)
        fit = setup(c)
        tag = f'h{weeks}'
        val, vp, fin, fp = get_draws(c, fit, tag)
        t0 = time.perf_counter()
        res = mix_search(c, val, vp, fin, fp, prop,
                         label=f'{years}y horizon, 15% terminal loss limit at year {years} (owner 10:23)')
        res['seconds'] = time.perf_counter() - t0
        res['years'] = years
        res['total_paid'] = months * 250000.0
        r['horizon'][key] = res
        save_results(r)
        print('horizon', key, 'safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)


def sec_payout():
    r = load_results()
    prop = r['sleeve_cara']['proportions']
    r.setdefault('payout', {})
    for monthly in [50000.0, 100000.0, 250000.0]:
        key = f'{int(monthly/1000)}k'
        if key in r['payout']:
            print('skip', key, flush=True)
            continue
        c = nm_config(payout=monthly, radius_scale=monthly / 250000.0)
        fit = setup(c)
        # identical price paths across payout levels by construction (same seeds);
        # amounts scale with the payout size.
        val, vp, fin, fp = get_draws(c, fit, 'h520', payout_scale=monthly / 250000.0)
        t0 = time.perf_counter()
        res = mix_search(c, val, vp, fin, fp, prop, label=f'${int(monthly/1000)}k/month x120')
        res['seconds'] = time.perf_counter() - t0
        res['monthly'] = monthly
        r['payout'][key] = res
        save_results(r)
        print('payout', key, 'safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)


if __name__ == '__main__':
    which = sys.argv[1]
    rest = sys.argv[2:]
    dict(fit=sec_fit, base=sec_base, utilities=sec_utilities, cml=sec_cml,
         bench=sec_bench, rebal=sec_rebal, payout=sec_payout)[which]() if which != 'horizon' \
        else sec_horizon([int(x) for x in rest])
