"""Fix 1: bootstrap/regime market model vs the iid Gaussian scale mixture
(open point 1: the default law draws independent weeks - no volatility
clustering - and equity tails thinner than the sample; VTI sample excess
kurtosis 9.1 vs 1.69 in the model).

Method: the engine's declared EWMA filtered historical simulation variant
(scenario_model='fhs_ewma', emfin_v2/historical_simulation.py: EWMA-filtered
standardized residuals, joint row resampling, forecast-variance recursion,
no future row in any volatility estimate) as a fifth scenario law. Same fit,
same seeds, same frozen validation discipline; only the scenario law changes.

Answers:
  diag     does FHS actually add clustering? squared-return ACF of history vs
           mixture paths vs FHS paths (us_equity column)
  fhs_frozen_sleeve   mix search under FHS draws, base CARA sleeve frozen
  fhs_own_sleeve      sleeve re-solved on 1y FHS draws, then mix search
  cross_base_on_fhs   the validated base portfolio judged on FHS final paths
  cross_fhs_on_mix    the FHS-chosen portfolio judged on mixture final paths
"""
import sys, time, json
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import S, save, load

LAGS = (1, 2, 4, 8, 13)


def sq_acf(x, lags=LAGS):
    """Mean across paths of the lag-k autocorrelation of squared weekly log returns.

    Accepts price paths (last axis steps) or raw return series; callers say which.
    """
    x = np.asarray(x, float)
    if x.ndim == 3:  # (n, h, d) prices -> per-path log returns
        x = np.log(x[:, 1:, :] / x[:, :-1, :])
    elif x.ndim == 2:  # (n, h) prices -> per-path log returns
        x = np.log(x[:, 1:] / x[:, :-1])
    if x.ndim == 1:
        x = x[None, :]
    sq = x ** 2
    sq = sq - sq.mean(axis=1, keepdims=True)
    den = (sq ** 2).mean(axis=1)
    out = {}
    for k in lags:
        num = (sq[:, k:] * sq[:, :-k]).mean(axis=1)
        out[k] = float(np.mean(num / np.maximum(den, 1e-30)))
    return out


def variant_config(model, **kw):
    c = S.nm_config(**kw)
    c['scenario_model'] = model
    c['label'] += (f' LABELED SCENARIO-LAW VARIANT (owner ask 8 Nov 11:05, open point 1): '
                   f'{model} replaces the iid Gaussian scale mixture. Same fit, seeds and '
                   'validation discipline.')
    return c


def fhs_config(**kw):
    return variant_config('fhs_ewma', **kw)


def variant_sleeve(model):
    c = variant_config(model, one_year_sleeve=True)
    fit = S.setup(c)
    dr = S.draw_paths(c, fit, 100, c['seed'])
    p, ps = S.probabilities(c, dr[0], dr.re_price_logs)
    raw, status = S.solve(c, dr, p, ps, 1.)
    ids = c['asset_layout']['ids']
    mins, fixed = S.holding_bounds(c, len(ids))
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
    return {k: v / tot for k, v in risky.items()}, float(raw[safe_idx] / c['wealth']), status.get('kind')


def run_variant(model, r):
    """Full fix-1 battery for one scenario law."""
    cv = variant_config(model)
    fit = S.setup(cv)
    vv, vpv, fv, fpv = S.get_draws(cv, fit, f'h520_{model}')
    c = S.nm_config()
    fit0 = S.setup(c)
    val, vp, fin, fp = S.get_draws(c, fit0, 'h520')
    ids = c['asset_layout']['ids']
    base_prop = json.loads(Path('studies/tbill/results/study_tips_charts.json').read_text())['sleeve_cara']['proportions']
    key = f'{model}_frozen_sleeve'
    if key not in r:
        t0 = time.perf_counter()
        res = S.mix_search(cv, vv, vpv, fv, fpv, base_prop,
                           label=f'{model} law, base CARA sleeve frozen (fix 1)')
        res['seconds'] = time.perf_counter() - t0
        r[key] = res
        save('fix1_market_model.json', r)
        print(key, 'safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    key = f'{model}_own_sleeve'
    if key not in r:
        prop, raw_safe, kind = variant_sleeve(model)
        t0 = time.perf_counter()
        res = S.mix_search(cv, vv, vpv, fv, fpv, prop,
                           label=f'{model} law, sleeve re-solved on 1y {model} draws (fix 1)')
        res['seconds'] = time.perf_counter() - t0
        res['sleeve_proportions'] = prop
        res['sleeve_safe_share_1y'] = raw_safe
        res['sleeve_status'] = kind
        r[key] = res
        save('fix1_market_model.json', r)
        print(key, 'safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), prop, flush=True)
    key = f'cross_base_on_{model}'
    if key not in r:
        base_w = json_base_weights()
        a = np.array([base_w[i] for i in ids]) * c['wealth']
        v = S.evaluate(cv, fv, a, [x[0] for x in fpv], [x[1] for x in fpv])
        row = dict(final_pass=bool(v['overall_pass']), final_breaches=v.get('breaches'))
        row.update(S.score_final(cv, fv, fpv, a))
        r[key] = row
        save('fix1_market_model.json', r)
        print(key, 'pass=', row['final_pass'], row.get('final_breaches'), flush=True)
    key = f'cross_{model}_on_mix'
    own = r.get(f'{model}_own_sleeve', {})
    if key not in r and own.get('weights'):
        # exact reconstruction from chosen safe share + sleeve (the stored
        # weights dict is 4dp reporting-rounded and fails exact holdings checks)
        mix, _ = S.mix_fn(c, own['sleeve_proportions'])
        a = mix(float(own['chosen_safe'])) * c['wealth']
        v = S.evaluate(c, fin, a, [x[0] for x in fp], [x[1] for x in fp])
        row = dict(final_pass=bool(v['overall_pass']), final_breaches=v.get('breaches'))
        row.update(S.score_final(c, fin, fp, a))
        r[key] = row
        save('fix1_market_model.json', r)
        print(key, 'pass=', row['final_pass'], row.get('final_breaches'), flush=True)
    # diagnostics for this law
    dkey = f'diag_{model}'
    if dkey not in r:
        eq = 0
        paths = np.concatenate([d[0][:, :, eq] for d in fv])
        rets = np.log(paths[:, 1:] / paths[:, :-1])
        r[dkey] = dict(sq_acf=sq_acf(paths), us_equity_ann_vol=float(rets.std() * np.sqrt(52)))
        save('fix1_market_model.json', r)


def main():
    r = load('fix1_market_model.json')
    r.setdefault('meta', dict(label='LABELED STUDY (owner ask 8 Nov 11:05, open point 1): '
                                   'bootstrap/regime market model (fhs_ewma) vs iid mixture.'))
    # --- diagnostics ---
    if 'diag' not in r or 'us_equity_ann_vol' not in r.get('diag', {}):
        c = S.nm_config()
        frame, mu, cov = S.setup(c)
        eq = list(frame.columns).index('us_equity')
        hist = frame.to_numpy()[:, eq]
        val, vp, fin, fp = S.get_draws(c, (frame, mu, cov), 'h520')
        mix_paths = np.concatenate([d[0][:, :, eq] for d in fin])
        cf = fhs_config()
        vf, vpf, ff, fpf = S.get_draws(cf, (frame, mu, cov), 'h520_fhs')
        fhs_paths = np.concatenate([d[0][:, :, eq] for d in ff])
        def ann_vol(paths):
            rets = np.log(paths[:, 1:] / paths[:, :-1])
            return float(rets.std() * np.sqrt(52))
        hist_vol = float(hist.std() * np.sqrt(52))
        ids = c['asset_layout']['ids']
        per_asset_vol = {}
        for j, name in enumerate(ids):
            hm = np.concatenate([d[0][:, :, j] for d in fin])
            hf = np.concatenate([d[0][:, :, j] for d in ff])
            per_asset_vol[name] = dict(mixture=ann_vol(hm), fhs=ann_vol(hf))
        r['diag'] = dict(history=sq_acf(hist), mixture=sq_acf(mix_paths), fhs=sq_acf(fhs_paths),
                         us_equity_ann_vol=dict(history=hist_vol, mixture=ann_vol(mix_paths),
                                                fhs=ann_vol(fhs_paths)),
                         per_asset_ann_vol=per_asset_vol,
                         note='squared weekly log-return autocorrelation, us_equity; '
                              'history is one long series, models averaged over 1600 final paths')
        save('fix1_market_model.json', r)
        print('diag', r['diag'], flush=True)
    # --- per-law batteries (draws cached on disk; results cached in the JSON) ---
    for model in ('fhs_ewma', 'bounded_ewma_mixture'):
        run_variant(model, r)
    print('market model study done', flush=True)


def json_base_weights():
    import json
    base = json.loads(Path('studies/tbill/results/study_tips_charts.json').read_text())
    return base['base']['weights']


if __name__ == '__main__':
    main()
