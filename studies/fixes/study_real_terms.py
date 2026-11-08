"""Fix 3: real terms (open point 3: everything is nominal - payouts, returns
and the 15% limit are all in today's dollars; "loss vs start" mechanically
loses its teeth past ~20 years).

Method: deflate every nominal scenario path by a stochastic CPI path, so the
whole frozen pipeline (validation, judge, mix search, ledger) runs in today's
dollars. Payouts become inflation-indexed by construction (a constant
$250k/month in real terms - the owner's real case). TIPS automatically become
the real safe asset (TIP nominal total return deflated by realized CPI);
T-bills become a real asset with carry = nominal bill return minus realized
inflation. Singapore property: URA quarterly log returns deflated by CPI and
fed through the engine's own calibration_returns_override, so the property
drift/vol and its entropy-pooling view are consistent in real terms.

Inflation scenarios: stationary block bootstrap (mean block 36 months) of
historical monthly log changes of US CPIAUCSL (FRED, 1947-01 to 2026-09,
seasonally adjusted), monthly draws spread evenly over 52/12 weeks per month.
Independent of asset scenarios (labeled simplification: no inflation-asset
correlation; TIPS inflation beta is mechanical via deflation, not estimated).

Sections:
  real_frozen_sleeve        mix search on real draws, base sleeve frozen
  real_own_sleeve           sleeve re-solved on 1y real draws, then mix search
  real_peak_to_trough       same, but the any-point cap judged on peak-to-trough
                            drawdown instead of loss-vs-start (custom judge,
                            labeled) - answers "a limit that keeps biting"
  real_current_rates        real terms x fix-5 current-rate carry (second
                            default view candidate)
  cross_base_on_real        the nominal base portfolio judged on real draws:
                            what the nominal answer really promises in today's
                            dollars
"""
import sys, time, json
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import S, save, load
from emfin_v2.historical_simulation import stationary_indices
from emfin_v2.evaluation import common_tail
from emfin_v2.toolbox.wasserstein import penalty
from emfin_v2.real_estate import ScenarioDraw

CPI_CSV = '/tmp/cpi.csv'
MEAN_BLOCK_MONTHS = 36


def cpi_monthly_changes():
    df = pd.read_csv(CPI_CSV)
    cpi = pd.to_numeric(df['CPIAUCSL'], errors='coerce').dropna().to_numpy(float)
    return np.diff(np.log(cpi))


def inflation_paths(n, weeks, seed):
    """(n, weeks) weekly log-inflation paths: stationary bootstrap of monthly
    log-CPI changes, each month spread over its weeks."""
    ch = cpi_monthly_changes()
    months = int(np.ceil(weeks * 12 / 52)) + 1
    idx = stationary_indices(len(ch), n, months, MEAN_BLOCK_MONTHS, seed)
    monthly = ch[idx]  # (n, months)
    week_of_month = np.minimum((np.arange(weeks) * 12 // 52), months - 1)
    return monthly[:, week_of_month] * 12 / 52  # spread each month's change evenly over its weeks


def real_config(fit_override=None, **kw):
    """Base config; property stays on its nominal URA calibration and every
    path (property included) is deflated post-hoc by the CPI path. The RE
    entropy-pooling view target is reduced by the mean bootstrap inflation
    drift in probabilities_real, keeping the view consistent in real terms.
    """
    c = S.nm_config(**kw)
    from emfin_v2.default_run import validate_config
    c = validate_config(c)
    c['label'] += (' LABELED REAL-TERMS VARIANT (owner ask 8 Nov 11:05, open point 3): all paths '
                   'deflated by bootstrapped CPI paths; payouts inflation-indexed (constant real); '
                   'limits read in today-dollars. Inflation independent of assets (labeled).')
    return c


def make_real_draws(c, fit, tag, tips_real_drift=None):
    """Real-terms validation/final draw sets, cached like study_tips_charts.get_draws.

    TIPS are modeled as a REAL instrument: their column is deflated by the
    deterministic mean-inflation path, not by the simulated CPI path. Deflating
    by the simulated path would be wrong: TIPS principal compensates realized
    inflation, so TIPS real returns are driven by real yields, and the bootstrap
    draws TIP nominal returns independently of the simulated inflation path -
    dividing by it would turn TIPS back into a nominal bond in high-inflation
    states (found mid-study, fixed). All genuinely nominal columns (bills,
    treasury, equity, gold, property) are deflated by the simulated CPI path.

    tips_real_drift: if set (annual real yield, e.g. 0.026 for DFII10 5 Nov 2026),
    the TIPS real paths are drift-corrected so their mean real log drift equals
    the current real yield (current-rates treatment, fix 5 x fix 3).
    """
    f = S.DRAW_DIR / f'{tag}_real.npz'
    if f.exists():
        z = np.load(f, allow_pickle=False)

        def unpack(prefix, count):
            out = []
            for j in range(count):
                out.append(ScenarioDraw((z[f'{prefix}{j}_prices'], z[f'{prefix}{j}_amounts'],
                                         z[f'{prefix}{j}_steps'], z[f'{prefix}{j}_bases'],
                                         z[f'{prefix}{j}_growth']),
                                        z[f'{prefix}{j}_funding'], z[f'{prefix}{j}_relog']))
            return out
        val, fin = unpack('v', 4), unpack('f', 4)
    else:
        blob = {}
        infl_stats = {}
        for prefix, count, n, seed0 in (('v', 4, 200, c['seed'] + 1000), ('f', 4, 400, c['seed'] + 10000)):
            for j in range(count):
                d = S.draw_paths(c, fit, n, seed0 + j)
                infl = inflation_paths(n, c['horizon_weeks'], seed0 + 777 + j)
                D = np.exp(np.cumsum(infl, axis=1))
                paths = d[0] / D[:, :, None]
                growth = d[4] / D
                funding = d.funding_paths / D[:, :, None]
                relog = d.re_price_logs - np.log(D)
                tips_j = c['asset_layout']['ids'].index('tips')
                mean_weekly = cpi_monthly_changes().mean() * 12 / 52
                d_mean = np.exp(mean_weekly * np.arange(paths.shape[1]))[None, :]
                paths[:, :, tips_j] = d[0][:, :, tips_j] / d_mean
                funding[:, :, tips_j] = d.funding_paths[:, :, tips_j] / d_mean
                if tips_real_drift is not None:
                    col = paths[:, :, tips_j]
                    realized = float(np.log(col[:, 1:] / col[:, :-1]).mean())
                    corr = np.log1p(tips_real_drift) / 52 - realized
                    scale = np.exp(corr * np.arange(paths.shape[1]))[None, :]
                    paths[:, :, tips_j] = col * scale
                    funding[:, :, tips_j] = funding[:, :, tips_j] * scale
                if prefix == 'f' and j == 0:
                    infl_stats = dict(mean_annual=float(infl.mean() * 52),
                                      p05_annual=float(np.quantile(infl.mean(1) * 52, .05)),
                                      p95_annual=float(np.quantile(infl.mean(1) * 52, .95)))
                blob[f'{prefix}{j}_prices'] = paths
                blob[f'{prefix}{j}_amounts'] = d[1]
                blob[f'{prefix}{j}_steps'] = d[2]
                blob[f'{prefix}{j}_bases'] = d[3]
                blob[f'{prefix}{j}_growth'] = growth
                blob[f'{prefix}{j}_funding'] = funding
                blob[f'{prefix}{j}_relog'] = relog
        np.savez(f, **blob)
        (S.DRAW_DIR / f'{tag}_real_infl.json').write_text(json.dumps(infl_stats, indent=1))
        z = np.load(f, allow_pickle=False)

        def unpack(prefix, count):
            out = []
            for j in range(count):
                out.append(ScenarioDraw((z[f'{prefix}{j}_prices'], z[f'{prefix}{j}_amounts'],
                                         z[f'{prefix}{j}_steps'], z[f'{prefix}{j}_bases'],
                                         z[f'{prefix}{j}_growth']),
                                        z[f'{prefix}{j}_funding'], z[f'{prefix}{j}_relog']))
            return out
        val, fin = unpack('v', 4), unpack('f', 4)
    vp = [probabilities_real(c, v[0], v.re_price_logs) for v in val]
    fp = [probabilities_real(c, x[0], x.re_price_logs) for x in fin]
    return val, vp, fin, fp


def probabilities_real(c, paths, re_price_logs):
    """probabilities() equivalent for this config (no relative views, single RE
    forward view): joint entropy pooling from the uniform prior directly.
    The sequential-EP pipeline zeros some posterior atoms on deflated paths,
    which the strict-positive joint pooling rejects; with one view the joint
    projection from uniform IS the sequential projection, so this is an
    equivalent route, not a changed posterior. Labeled.
    """
    from emfin_v2.toolbox import entropy_pooling as ep
    n = len(paths)
    uniform = np.full(n, 1 / n)
    members = c['view_instruments']
    from emfin_v2.real_estate import calibration
    infl_mean = float(cpi_monthly_changes().mean()) * 12  # annual log-inflation drift, full CPI sample
    target = (calibration(c['real_estate'])['forward_log_drift'] - infl_mean) * c['horizon_weeks'] / 52
    re_view = ep.View(np.asarray(re_price_logs)[:, -1], [target], name='Forward RE price view')
    q = ep.joint_entropy_pooling(n, [re_view], prior_probs=uniform).posterior_probs
    loss = np.maximum(0, 1 - paths[:, :, members].mean(2)).max(1)
    stress_target = float(loss @ q + c['stress_mean_path_loss_increment'])
    qs = ep.joint_entropy_pooling(n, [ep.View(loss, [stress_target], sense='ge'), re_view],
                                  prior_probs=q).posterior_probs
    return q, qs


# ---------- peak-to-trough judge (labeled variant of evaluation.evaluate) ----------

def evaluate_peak(c, draws, allocation, nominal, stressed):
    """evaluate() with the any-point slot measured as peak-to-trough drawdown
    on the no-payout wealth path, instead of max loss vs starting wealth.
    Funding dates and terminal slots unchanged. Read-only judge, same
    finite-envelope and t-bound discipline, same Wasserstein buffer.
    """
    from emfin_v2.default_run import holding_bounds
    from emfin_v2.real_estate import funding_paths
    from scipy.stats import t as tdist
    a = np.asarray(allocation, float)
    wealth = c['wealth']
    w = a / wealth
    mins, fixed = holding_bounds(c, len(a))
    tol = 1e-7
    checks_hold = [abs(w.sum() - 1) <= tol, max(0., -w.min()) <= tol,
                   max(0., float(np.max(mins - w))) <= tol]
    checks_hold += [abs(w[i] - v) <= tol for i, v in fixed.items()]
    names = ['Fully invested', 'No shorting', 'Minimum holdings residual'] + \
            [f'Fixed holding {i}' for i in fixed]
    n_dates = len(draws[0][2])
    batches = []
    for draw, q, qs in zip(draws, nominal, stressed):
        paths, amounts, steps, bases, growth = draw
        measures = np.array([np.full(len(paths), 1 / len(paths)), q, qs])
        values = paths @ a / wealth
        spendable = funding_paths(draw) @ a
        losses = []
        for i, step in enumerate(steps):
            required = amounts[:, i].copy()
            for j, prior in enumerate(steps):
                if prior < step or (prior == step and j < i):
                    required += amounts[:, j] * growth[:, step - 1] / growth[:, prior - 1]
            losses.append(np.maximum(required - spendable[:, step - 1], 0) / wealth)
        runmax = np.maximum.accumulate(values, axis=1)
        losses.append((1 - values / runmax).max(1))       # peak-to-trough drawdown
        losses.append(1 - values[:, -1])                  # terminal loss vs start
        batches.append([[common_tail(x, [p], c['confidence'], k != len(losses) - 1)[0] if False else
                         common_tail(x, [p], c['confidence'], k != len(losses) - 1) for p in measures] +
                        [common_tail(x, measures, c['confidence'], k != len(losses) - 1)]
                        for k, x in enumerate(losses)])
    x = np.asarray(batches)
    familysize = x.shape[1] * x.shape[2]
    critical = tdist.ppf(1 - .05 / familysize, len(draws) - 1)
    mean = x.mean(0)
    high = mean + critical * x.std(0, ddof=1) / np.sqrt(len(draws))
    market_buffer = penalty(w, c.get('wasserstein_radius', 0), c['confidence'],
                            metric=c.get('wasserstein_metric', 'legacy_l1'))
    funding_buffer = penalty(w, c.get('wasserstein_radius', 0), c['confidence'],
                             c.get('wasserstein_liability_scale', .01),
                             metric=c.get('wasserstein_metric', 'legacy_l1'))
    checks = list(checks_hold)
    worst = 0.0
    for k in range(n_dates + 2):
        funding = k < n_dates
        scale = wealth if funding else 1.
        limit = draws[0][3][k] * c['funding_budget_fraction'] if funding else \
            c['cml_budget'] if k == n_dates else c['loss_budget']
        buffer = (funding_buffer if funding else market_buffer) * scale
        val = float(high[k, 3] * scale + buffer)   # common hull envelope
        checks.append(val <= limit)
        worst = max(worst, val - limit)
    return dict(overall_pass=bool(all(checks)),
                holding_names=names, holding_pass=checks_hold,
                worst_margin=float(worst), peak_to_trough=True)


def mix_search_peak(c, val, vp, fin, fp, prop, label=''):
    mix, ids = S.mix_fn(c, prop)
    chosen = None
    for s in S.SAFE_GRID:
        a = mix(float(s)) * c['wealth']
        if evaluate_peak(c, val, a, [x[0] for x in vp], [x[1] for x in vp])['overall_pass']:
            chosen = float(s)
            break
    if chosen is None:
        return dict(chosen_safe=None, note='no candidate mix passes validation (peak-to-trough)', label=label)
    s = chosen
    pick = None
    while s <= 0.9001:
        a = mix(float(s)) * c['wealth']
        verdict = evaluate_peak(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
        if verdict['overall_pass']:
            pick = (float(s), verdict)
            break
        s = round(s + 0.025, 4)
    if pick is None:
        return dict(chosen_safe=None, note='fails final judge even at 90% safe (peak-to-trough)', label=label)
    s, verdict = pick
    a = mix(s) * c['wealth']
    out = dict(chosen_safe=s, validation_selected_safe=chosen,
               weights={n: round(float(wi), 4) for n, wi in zip(ids, a / c['wealth'])},
               final_pass=True, label=label, judge='peak_to_trough_anypoint')
    out.update(S.score_final(c, fin, fp, a))
    return out


def mix_fn_anchor(c, prop, anchor_id):
    """mix_fn with a chosen safe anchor (real terms: TIPS are the real safe
    asset; nominal bills are not - they carry full inflation-regime risk)."""
    ids = c['asset_layout']['ids']
    d = len(ids)
    mins, fixed = S.holding_bounds(c, d)
    fixed = {int(k): v for k, v in fixed.items()}
    safe_idx = ids.index(anchor_id)
    risky_idx = [i for i in range(d) if i != safe_idx and i not in fixed and mins[i] == 0 and ids[i] != 'cash']

    def mix(safe_share):
        w = np.zeros(d)
        w[safe_idx] = safe_share
        for i, v in fixed.items():
            w[i] = v
        rem = 1 - safe_share - sum(fixed.values())
        for i in risky_idx:
            w[i] = rem * prop.get(ids[i], 0)
        return w
    return mix, ids


# anchor cannot exceed 1 - fixed holdings (property is fixed at 10%): grid ends at 0.9
ANCHOR_GRID = list(S.SAFE_GRID)


def mix_search_anchor(c, val, vp, fin, fp, prop, anchor_id, label=''):
    mix, ids = mix_fn_anchor(c, prop, anchor_id)
    chosen = None
    for s in ANCHOR_GRID:
        a = mix(float(s)) * c['wealth']
        if S.evaluate(c, val, a, [x[0] for x in vp], [x[1] for x in vp])['overall_pass']:
            chosen = float(s)
            break
    if chosen is None:
        return dict(chosen_safe=None, note=f'no candidate mix passes validation (anchor={anchor_id})', label=label)
    s = chosen
    pick = None
    while s <= ANCHOR_GRID[-1] + 1e-9:
        a = mix(float(s)) * c['wealth']
        verdict = S.evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
        if verdict['overall_pass']:
            pick = (float(s), verdict)
            break
        s = round(s + 0.025, 4)
    if pick is None:
        return dict(chosen_safe=None, note=f'fails final judge even at {ANCHOR_GRID[-1]} safe (anchor={anchor_id})', label=label)
    s, verdict = pick
    a = mix(s) * c['wealth']
    out = dict(chosen_safe=s, validation_selected_safe=chosen, anchor=anchor_id,
               weights={n: round(float(wi), 4) for n, wi in zip(ids, a / c['wealth'])},
               final_pass=True, final_breaches=verdict.get('breaches'), label=label)
    out.update(S.score_final(c, fin, fp, a))
    return out



def current_rate_fit_nominal_only(c, fit):
    """current_rate_fit without the tips override: TIPS current-rates treatment
    is the real-space drift correction in make_real_draws (tips_real_drift)."""
    frame, mu, cov = fit
    ids = list(frame.columns)
    mu = mu.copy()
    for name, annual in dict(tbill=0.0417, treasury=0.0484).items():
        mu[ids.index(name)] = np.log1p(annual) / 52
    return frame, mu, cov


RTIPS_TAG = 'h520_curr_rtips2'


def real_current_setup(c_base):
    cr = real_config()
    fitc = current_rate_fit_nominal_only(cr, S.setup(cr))
    return cr, fitc, make_real_draws(cr, fitc, RTIPS_TAG, tips_real_drift=0.026)


def main():
    r = load('fix3_real_terms.json')
    r.setdefault('meta', dict(label='LABELED STUDY (owner ask 8 Nov 11:05, open point 3): real terms.',
                              inflation_model=f'stationary bootstrap of monthly log CPIAUCSL changes, '
                                              f'mean block {MEAN_BLOCK_MONTHS} months, 1947-2026, '
                                              'independent of asset paths (labeled simplification)'))
    c = real_config()
    fit = S.setup(c)
    val, vp, fin, fp = make_real_draws(c, fit, 'h520_rtipsdef')
    infl_file = S.DRAW_DIR / 'h520_rtipsdef_real_infl.json'
    if infl_file.exists():
        r['meta']['inflation_paths'] = json.loads(infl_file.read_text())
    base_prop = json.loads(Path('studies/tbill/results/study_tips_charts.json').read_text())['sleeve_cara']['proportions']
    if 'real_frozen_sleeve' not in r:
        t0 = time.perf_counter()
        res = S.mix_search(c, val, vp, fin, fp, base_prop, label='real terms, base sleeve frozen (fix 3)')
        res['seconds'] = time.perf_counter() - t0
        r['real_frozen_sleeve'] = res
        save('fix3_real_terms.json', r)
        print('real frozen: safe=', res.get('chosen_safe'),
              'CE=%.1fM real' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'real_own_sleeve' not in r:
        # Sleeve from the TRUE 10y solve on real draws (fix-4 approach). The 1y
        # real solve is infeasible: at 1y the any-point budget is 6% and the
        # fixed 10% property sleeve alone exhausts it in the stressed envelope
        # once property drift is deflated (labeled finding, see report).
        dr = S.draw_paths(c, fit, 100, c['seed'])
        infl = inflation_paths(100, c['horizon_weeks'], c['seed'] + 777)
        D = np.exp(np.cumsum(infl, axis=1))
        real_paths = dr[0] / D[:, :, None]
        real_funding = dr.funding_paths / D[:, :, None]
        tj = c['asset_layout']['ids'].index('tips')
        d_mean = np.exp(cpi_monthly_changes().mean() * 12 / 52 * np.arange(real_paths.shape[1]))[None, :]
        real_paths[:, :, tj] = dr[0][:, :, tj] / d_mean
        real_funding[:, :, tj] = dr.funding_paths[:, :, tj] / d_mean
        dr_real = ScenarioDraw((real_paths, dr[1], dr[2], dr[3], dr[4] / D),
                               real_funding, dr.re_price_logs - np.log(D))
        p, ps = probabilities_real(c, dr_real[0], dr_real.re_price_logs)
        t0s = time.perf_counter()
        raw, status = S.solve(c, dr_real, p, ps, 1.)
        r['real_solve_10y'] = dict(status=status.get('kind'), reason=status.get('reason'),
                                   seconds=time.perf_counter() - t0s)
        ids = c['asset_layout']['ids']
        mins, fixed = S.holding_bounds(c, len(ids))
        fixed = {int(k): v for k, v in fixed.items()}
        safe_idx = ids.index('tbill')
        if raw is None:
            r['real_own_sleeve'] = dict(chosen_safe=None, note='10y real solve unavailable: '
                                        + str(status.get('kind')), sleeve_status=status.get('kind'))
            save('fix3_real_terms.json', r)
            print('real 10y solve unavailable:', status.get('kind'), flush=True)
        else:
            risky = {}
            for i, a_ in enumerate(ids):
                if i == safe_idx or i in fixed or mins[i] > 0 or a_ == 'cash':
                    continue
                w = float(raw[i] / c['wealth'])
                if w > 1e-6:
                    risky[a_] = w
            tot = sum(risky.values())
            prop = {k: v / tot for k, v in risky.items()}
            t0 = time.perf_counter()
            res = S.mix_search(c, val, vp, fin, fp, prop,
                               label='real terms, sleeve from true 10y real solve (fix 3+4)')
            res['seconds'] = time.perf_counter() - t0
            res['sleeve_proportions'] = prop
            res['sleeve_safe_share_10y_raw'] = float(raw[safe_idx] / c['wealth'])
            res['sleeve_status'] = status.get('kind')
            r['real_own_sleeve'] = res
            save('fix3_real_terms.json', r)
            print('real own sleeve: safe=', res.get('chosen_safe'),
                  'CE=%.1fM real' % (res.get('common_cara_ledger_ce', 0) / 1e6), prop, flush=True)
    if 'real_peak_to_trough' not in r:
        prop = base_prop  # frozen base sleeve; the real-terms 10y solve was infeasible (see real_solve_10y)
        t0 = time.perf_counter()
        res = mix_search_peak(c, val, vp, fin, fp, prop,
                              label='real terms + peak-to-trough any-point limit, frozen base sleeve (fix 3, labeled custom judge)')
        res['seconds'] = time.perf_counter() - t0
        res['sleeve_proportions'] = prop
        r['real_peak_to_trough'] = res
        save('fix3_real_terms.json', r)
        print('real peak-to-trough: safe=', res.get('chosen_safe'),
              'CE=%.1fM real' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'real_current_rates' not in r:
        cr, fitc, (valc, vpc, finc, fpc) = real_current_setup(c)
        # sleeve: true 10y real solve at current rates if feasible, else frozen base sleeve
        propc = base_prop
        srcc = 'frozen base sleeve (10y real current-rates solve unavailable)'
        drc = S.draw_paths(cr, fitc, 100, cr['seed'])
        inflc = inflation_paths(100, cr['horizon_weeks'], cr['seed'] + 777)
        Dc = np.exp(np.cumsum(inflc, axis=1))
        drc_real = ScenarioDraw((drc[0] / Dc[:, :, None], drc[1], drc[2], drc[3], drc[4] / Dc),
                                drc.funding_paths / Dc[:, :, None], drc.re_price_logs - np.log(Dc))
        pc, psc = probabilities_real(cr, drc_real[0], drc_real.re_price_logs)
        t0s = time.perf_counter()
        rawc, statusc = S.solve(cr, drc_real, pc, psc, 1.)
        r['real_current_rates_solve_10y'] = dict(status=statusc.get('kind'),
                                                 reason=statusc.get('reason'),
                                                 seconds=time.perf_counter() - t0s)
        if rawc is not None:
            idsc = cr['asset_layout']['ids']
            minsc, fixedc = S.holding_bounds(cr, len(idsc))
            fixedc = {int(k): v for k, v in fixedc.items()}
            safe_idxc = idsc.index('tbill')
            riskyc = {a_: float(rawc[i] / cr['wealth']) for i, a_ in enumerate(idsc)
                      if i != safe_idxc and i not in fixedc and minsc[i] == 0 and a_ != 'cash'
                      and rawc[i] / cr['wealth'] > 1e-6}
            totc = sum(riskyc.values())
            propc = {k: v / totc for k, v in riskyc.items()}
            srcc = 'true 10y real solve at current rates'
        t0 = time.perf_counter()
        res = S.mix_search(cr, valc, vpc, finc, fpc, propc,
                           label='real terms x current rates (fixes 3+5), second default view candidate')
        res['seconds'] = time.perf_counter() - t0
        res['sleeve_proportions'] = propc
        res['sleeve_source'] = srcc
        r['real_current_rates'] = res
        save('fix3_real_terms.json', r)
        print('real x current rates: safe=', res.get('chosen_safe'),
              'CE=%.1fM real' % (res.get('common_cara_ledger_ce', 0) / 1e6), srcc, flush=True)
    # TIPS-anchored real mixes: nominal bills are not a real safe asset.
    if 'real_tips_anchor_curr' not in r:
        cr, fitc, (valc, vpc, finc, fpc) = real_current_setup(c)
        prop = r.get('real_current_rates', {}).get('sleeve_proportions') or base_prop
        # treasury stays in the risky sleeve; TIPS becomes the anchor, so remove
        # tips from the sleeve proportions if present and renormalize
        prop = {k: v for k, v in prop.items() if k != 'tips'}
        tot = sum(prop.values())
        prop = {k: v / tot for k, v in prop.items()}
        t0 = time.perf_counter()
        res = mix_search_anchor(cr, valc, vpc, finc, fpc, prop, 'tips',
                                label='real terms x current rates, TIPS-anchored safe share (fix 3: TIPS is the real safe asset)')
        res['seconds'] = time.perf_counter() - t0
        res['sleeve_proportions'] = prop
        r['real_tips_anchor_curr'] = res
        save('fix3_real_terms.json', r)
        print('real x curr, TIPS anchor: safe=', res.get('chosen_safe'),
              'CE=%.1fM real' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'real_tips_anchor_fitted' not in r:
        prop = {k: v for k, v in base_prop.items() if k != 'tips'}
        tot = sum(prop.values())
        prop = {k: v / tot for k, v in prop.items()}
        t0 = time.perf_counter()
        res = mix_search_anchor(c, val, vp, fin, fp, prop, 'tips',
                                label='real terms, fitted means, TIPS-anchored safe share (fix 3)')
        res['seconds'] = time.perf_counter() - t0
        res['sleeve_proportions'] = prop
        r['real_tips_anchor_fitted'] = res
        save('fix3_real_terms.json', r)
        print('real fitted, TIPS anchor: safe=', res.get('chosen_safe'),
              'CE=%.1fM real' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'judge_raw_solve_curr' not in r:
        cr, fitc, (valc, vpc, finc, fpc) = real_current_setup(c)
        drc = S.draw_paths(cr, fitc, 100, cr['seed'])
        inflc = inflation_paths(100, cr['horizon_weeks'], cr['seed'] + 777)
        Dc = np.exp(np.cumsum(inflc, axis=1))
        drc_real = ScenarioDraw((drc[0] / Dc[:, :, None], drc[1], drc[2], drc[3], drc[4] / Dc),
                                drc.funding_paths / Dc[:, :, None], drc.re_price_logs - np.log(Dc))
        pc, psc = probabilities_real(cr, drc_real[0], drc_real.re_price_logs)
        rawc, statusc = S.solve(cr, drc_real, pc, psc, 1.)
        ids = cr['asset_layout']['ids']
        if rawc is not None:
            v1 = S.evaluate(cr, valc, rawc, [x[0] for x in vpc], [x[1] for x in vpc])
            v2 = S.evaluate(cr, finc, rawc, [x[0] for x in fpc], [x[1] for x in fpc])
            row = dict(raw_weights={a: round(float(rawc[i] / cr['wealth']), 4) for i, a in enumerate(ids)},
                       validation_pass=bool(v1['overall_pass']), final_pass=bool(v2['overall_pass']),
                       final_breaches=v2.get('breaches'))
            row.update(S.score_final(cr, finc, fpc, rawc))
            r['judge_raw_solve_curr'] = row
            save('fix3_real_terms.json', r)
            print('raw 10y real/curr solve judged: val=', row['validation_pass'],
                  'final=', row['final_pass'], row.get('final_breaches'), flush=True)
    if 'cross_base_on_real' not in r:
        base_w = json.loads(Path('studies/tbill/results/study_tips_charts.json').read_text())['base']['weights']
        ids = c['asset_layout']['ids']
        a = np.array([base_w[i] for i in ids])
        a = a / a.sum() * c['wealth']
        v = S.evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
        row = dict(final_pass=bool(v['overall_pass']), final_breaches=v.get('breaches'))
        row.update(S.score_final(c, fin, fp, a))
        r['cross_base_on_real'] = row
        save('fix3_real_terms.json', r)
        print('nominal base on real draws: pass=', row['final_pass'],
              'real CE=%.1fM' % (row['common_cara_ledger_ce'] / 1e6),
              'P(end below start)=%.3f' % row['prob_end_below_start'], flush=True)
    if 'real_feasible_limits' not in r:
        # Fix 3 payoff: no static mix passes the nominal-calibrated budgets in
        # real terms. Find the TIGHTEST budgets at which the best real
        # candidate (90% TIPS anchor at current rates, property fixed 10%)
        # passes the same judge unchanged: scan (any-point cap, terminal
        # limit) pairs. Answers "how tight can a real limit be".
        t0 = time.perf_counter()
        cr, fitc, (valc, vpc, finc, fpc) = real_current_setup(c)
        prop = r.get('real_current_rates', {}).get('sleeve_proportions') or base_prop
        mix, ids = mix_fn_anchor(cr, prop, 'tips')
        a = mix(0.9) * cr['wealth']
        grid = []
        for cml in (0.40, 0.45, 0.50, 0.55, 0.60):
            for loss in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45):
                cc = dict(cr); cc['cml_budget'] = cml; cc['loss_budget'] = loss
                vv = S.evaluate(cc, valc, a, [x[0] for x in vpc], [x[1] for x in vpc])
                vf = S.evaluate(cc, finc, a, [x[0] for x in fpc], [x[1] for x in fpc])
                grid.append(dict(anypoint_cap=cml, terminal_limit=loss,
                                 validation_pass=vv['overall_pass'], final_pass=vf['overall_pass'],
                                 breaches=vf.get('breaches')))
        feas = [g for g in grid if g['final_pass'] and g['validation_pass']]
        best = min(feas, key=lambda g: (g['terminal_limit'], g['anypoint_cap'])) if feas else None
        out = dict(label='fix 3: tightest real-terms budgets passing the unchanged judge, '
                         '90% TIPS anchor at current rates (property fixed 10%)',
                   grid=grid, tightest=best, seconds=time.perf_counter() - t0)
        if best is not None:
            cc = dict(cr); cc['cml_budget'] = best['anypoint_cap']; cc['loss_budget'] = best['terminal_limit']
            out['weights'] = {n: round(float(wi), 4) for n, wi in zip(ids, a / cr['wealth'])}
            out.update(S.score_final(cc, finc, fpc, a))
        r['real_feasible_limits'] = out
        save('fix3_real_terms.json', r)
        print('real feasible limits: tightest=', best, flush=True)
    print('real terms study done', flush=True)


if __name__ == '__main__':
    main()
