"""UIF studies (owner ask 8 Nov 2026 17:09 SGT, relayed by main): items
1 (estimation uncertainty), 3 (inflation-linked payouts), 4 (fees, no tax).

Shared helpers. Judging discipline identical to final5/round2: primary
gaussian_scale_mixture law + fhs_ewma fifth law, validation 4x200, final
4x400, fifth-law draws at offset +500000, SAFE_GRID 2.5pp steps, dual-law
mix search (lowest safe share passing BOTH laws, one-step-safer walk-back
on the final judge of BOTH laws). No engine defaults change; every cell is
a labeled sensitivity. Draws are generated fresh per cell (no /tmp cache
reuse across refits: each refit has its own law).
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies' / 'tbill'))
sys.path.insert(0, str(ROOT / 'studies' / 'round2'))
sys.path.insert(0, str(ROOT / 'studies' / 'final5'))

import study_tips_charts as S  # noqa: E402
import common5  # noqa: E402
from emfin_v2.current_rates import apply_carry_view  # noqa: E402
from emfin_v2.real_estate import ScenarioDraw  # noqa: E402
from emfin_v2.registry_runtime import fit_frame  # noqa: E402

RESULTS = Path(__file__).resolve().parent / 'results'
RESULTS.mkdir(exist_ok=True)
FIFTH_LAW = common5.FIFTH_LAW
LAW_OFFSET = common5.LAW_OFFSET
SEED_BASE = 20261109   # same family as final5: direct comparability
SEED_BAND = 20261111   # seed-noise band family (as final5_sens_seeds)


def save(name, data):
    (RESULTS / name).write_text(json.dumps(data, default=str, indent=1))


def load(name):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def uif_config(view='fitted', seed=SEED_BASE, **kw):
    c = S.nm_config(**kw)
    c['seed'] = seed
    c['carry_view'] = view
    c['label'] += (' UIF (owner ask 8 Nov 17:09 SGT): estimation-uncertainty / inflation / fees '
                   'studies; seed family %d; carry view %s; dual-law.' % (seed, view))
    return c


def uif_fit(c):
    fit = S.setup(c)
    if c.get('carry_view', 'fitted') != 'fitted':
        fit = apply_carry_view(c, fit)
    return fit


def fresh_draws(c, fit):
    """common5.f5_draws without the /tmp cache (refit laws must not share tags)."""
    val = [S.draw_paths(c, fit, 200, c['seed'] + 1000 + j) for j in range(4)]
    fin = [S.draw_paths(c, fit, 400, c['seed'] + 10000 + j) for j in range(4)]
    cc = copy.deepcopy(c)
    cc['scenario_model'] = FIFTH_LAW
    val2 = [S.draw_paths(cc, fit, 200, c['seed'] + 1000 + LAW_OFFSET + j) for j in range(4)]
    fin2 = [S.draw_paths(cc, fit, 400, c['seed'] + 10000 + LAW_OFFSET + j) for j in range(4)]
    vp = [S.probabilities(c, v[0], v.re_price_logs) for v in val]
    fp = [S.probabilities(c, x[0], x.re_price_logs) for x in fin]
    vp2 = [S.probabilities(c, v[0], v.re_price_logs) for v in val2]
    fp2 = [S.probabilities(c, x[0], x.re_price_logs) for x in fin2]
    return (val, vp, fin, fp), (val2, vp2, fin2, fp2)


def block_bootstrap_indices(T, B, block, seed):
    """Circular block bootstrap row indices, B resamples of length T."""
    rng = np.random.default_rng(seed)
    out = np.empty((B, T), dtype=int)
    n_starts = T - block + 1
    for b in range(B):
        idx = []
        while len(idx) < T:
            s = int(rng.integers(0, n_starts))
            idx.extend(range(s, s + block))
        out[b] = np.array(idx[:T])
    return out


def refit_on_rows(c, frame, rows):
    """Refit all listed moments on the supplied (resampled) frame rows."""
    c2 = copy.deepcopy(c)
    fit_b = fit_frame(c2, frame.iloc[rows].reset_index(drop=True))
    if c2.get('carry_view', 'fitted') != 'fitted':
        fit_b = apply_carry_view(c2, fit_b)
    return c2, fit_b


def annual_moments(fit):
    """Annualized fitted log drift and vol per asset."""
    frame, mu, cov = fit
    ids = list(frame.columns)
    return dict(ids=ids,
                drift={i: float(mu[k] * 52) for k, i in enumerate(ids)},
                vol={i: float(np.sqrt(cov[k, k] * 52)) for k, i in enumerate(ids)})


# ---------------- inflation indexing (item 3) ----------------

def monthly_inflation_index(n, months, mu_m, sd_m, seed):
    """Per-path cumulative CPI index at month-ends 1..months. iid monthly
    log-changes ~ N(mu_m, sd_m) fitted on BLS CPI-U NSA 1996-2025 (declared).
    Independent of market draws (own RNG stream)."""
    rng = np.random.default_rng(seed)
    shocks = rng.normal(mu_m, sd_m, size=(n, months))
    return np.exp(np.cumsum(shocks, axis=1))


def index_payouts(draws, index):
    """Replace per-path payment amounts by base x CPI index at the payment
    month. steps are week numbers; payment k falls in month
    ceil(week*12/52). bases stay nominal (budget dollars disclosed)."""
    out = []
    for d in draws:
        paths, amounts, steps, bases, growth = d
        n = paths.shape[0]
        new_amounts = np.empty_like(amounts)
        for k, w in enumerate(steps):
            month = min(int(np.ceil(w * 12 / 52)), index.shape[1])
            new_amounts[:, k] = bases[k] * index[:, month - 1]
        out.append(ScenarioDraw((paths, new_amounts, steps, bases, growth),
                                d.funding_paths, d.re_price_logs))
    return out


def rebase_budgets(draws, index_mean):
    """Scale the per-payment tail budget bases by the EXPECTED index, so the
    20% allowance tracks the expected payment size (declared choice; the
    alternative - fixed nominal budget dollars - is stricter at long horizon)."""
    out = []
    for d in draws:
        paths, amounts, steps, bases, growth = d
        new_bases = bases.copy()
        for k, w in enumerate(steps):
            month = min(int(np.ceil(w * 12 / 52)), len(index_mean))
            new_bases[k] = bases[k] * index_mean[month - 1]
        out.append(ScenarioDraw((paths, amounts, steps, new_bases, growth),
                                d.funding_paths, d.re_price_logs))
    return out


# ---------------- fee-augmented policy simulator (item 4) ----------------

def simulate_fees(c, draw, w0, policy, glide=None, fee_trade=0.0, fee_aum_annual=0.0):
    """study_sens_policies.simulate_policy twin + explicit fee layer (labeled
    sensitivity; engine unchanged):

    fee_trade      proportional cost on every trade: rebalancing buys AND
                   sells, and payout-liquidation sales (sales are grossed up
                   so proceeds net of the fee cover the amount due).
                   This sits ON TOP of the per-asset sell haircuts already in
                   the judged model (5-20bp).
    fee_aum_annual annual holding fee on listed liquid sleeves (not cash,
                   not property), accrued weekly and settled at the next
                   payment liquidation / rebalance / horizon end by pro-rata
                   sale - the fee always leaves the portfolio in cash terms.

    Policies identical to simulate_policy: cash_first (never rebalances),
    annual_rebal, threshold_10, glide_annual (glide=(s_start,s_end)).
    """
    paths, amounts, steps, bases, growth = draw
    prices = np.asarray(paths, float)
    n, h, d = prices.shape
    cash_ix = c['cash_index']
    prop_ix = c.get('asset_layout', {}).get('property_indices', [])
    liquid = [i for i in range(d) if i != cash_ix and i not in prop_ix]
    ids = c['asset_layout']['ids']
    safe_idx = ids.index('tbill') if 'tbill' in ids else cash_ix
    a = np.asarray(w0, float) * c['wealth']
    units = np.broadcast_to(a, (n, d)).copy()
    units[:, cash_ix] = 0.
    cash = np.full(n, a[cash_ix])
    wealth = np.zeros((n, h))
    turnover = np.zeros(n)
    fees = np.zeros(n)
    accrued = np.zeros(n)

    cols = [cash_ix] + liquid
    base = np.array([a[i] for i in cols], float)
    base = base / base.sum()
    safe_pos = cols.index(safe_idx)

    def target_at(t):
        if glide is None:
            return base
        s0, s1 = glide
        frac = t / max(h - 1, 1)
        s = s0 + (s1 - s0) * frac
        out = base.copy()
        other = out.sum() - out[safe_pos]
        out = out / other * (1 - s)
        out[safe_pos] = s
        return out

    def settle_accrued(px):
        """Settle accrued holding fees by pro-rata sale of liquid sleeves."""
        nonlocal accrued, fees
        vals = units[:, liquid] * px[:, liquid]
        total = vals.sum(1)
        pay = np.minimum(accrued, total)
        frac = np.divide(pay, total, out=np.zeros(n), where=total > 0)
        units[:, liquid] *= 1 - frac[:, None]
        fees += pay
        accrued -= pay

    arrears = np.zeros(n)
    shortfalls = np.zeros_like(amounts)
    for t in range(h):
        ratio = growth[:, t] / (growth[:, t - 1] if t else 1.)
        cash *= ratio
        arrears *= ratio
        px = prices[:, t]
        vals = units[:, liquid] * px[:, liquid]
        if fee_aum_annual:
            accrued += fee_aum_annual / 52 * vals.sum(1)
        do_rebal = False
        if policy in ('annual_rebal', 'glide_annual') and t % 52 == 0:
            do_rebal = True
        elif policy == 'threshold_10':
            total = cash + vals.sum(1)
            cur = np.concatenate([cash[:, None], vals], 1) / total[:, None]
            drift = np.abs(cur - base[None, :]).max(1)
            if drift.max() > 0.10:
                do_rebal = True
        if do_rebal and policy not in ('cash_first', 'buy_hold_mark'):
            tgt = target_at(t)
            total = cash + vals.sum(1)
            desired = total[:, None] * tgt[None, :]
            dv = desired[:, 1:] - vals
            turnover += (np.abs(dv).sum(1) + np.abs(desired[:, 0] - cash)) / 2
            fee_t = fee_trade * (np.abs(dv).sum(1) + np.abs(desired[:, 0] - cash))
            units[:, liquid] = desired[:, 1:] / px[:, liquid]
            cash = desired[:, 0] - fee_t
            fees += fee_t
            # if the fee pushed cash below zero, settle the overflow pro-rata
            neg = np.maximum(-cash, 0.)
            if neg.max() > 0:
                vals = units[:, liquid] * px[:, liquid]
                total = vals.sum(1)
                frac = np.divide(neg, total, out=np.zeros(n), where=total > 0)
                units[:, liquid] *= 1 - frac[:, None]
                cash += neg
            if fee_aum_annual:
                settle_accrued(px)
        for k in np.flatnonzero(steps == t + 1):
            if fee_aum_annual:
                settle_accrued(px)  # fees are sold for first; funding checks stay on client payments
            due = amounts[:, k] + arrears
            need = np.maximum(due - cash, 0.)
            available = px[:, liquid] * units[:, liquid]
            total = available.sum(1)
            # gross up the sale so proceeds net of the trading fee cover the need
            gross_need = need / max(1.0 - fee_trade, 1e-9)
            fraction = np.minimum(1., np.divide(gross_need, total, out=np.zeros(n), where=total > 0))
            liquidation = available * fraction[:, None]
            units[:, liquid] *= 1 - fraction[:, None]
            proceeds = liquidation.sum(1)
            fee_t = fee_trade * proceeds
            fees += fee_t
            cash += proceeds - fee_t
            payment = np.minimum(cash, due)
            cash -= payment
            arrears = due - payment
            shortfalls[:, k] = arrears
        wealth[:, t] = (cash + (px[:, liquid] * units[:, liquid]).sum(1)
                        + px[:, prop_ix] @ a[prop_ix] - arrears)
    if fee_aum_annual:
        settle_accrued(prices[:, -1])
        wealth[:, -1] = (cash + (prices[:, -1][:, liquid] * units[:, liquid]).sum(1)
                         + prices[:, -1][:, prop_ix] @ a[prop_ix] - arrears)
    return dict(net_wealth_paths=wealth, turnover=turnover,
                funded=np.all(shortfalls <= 1e-6, axis=1),
                payment_shortfalls=shortfalls, total_fees=fees)


def dual_mix_search_fast(c, primary, fifth, prop, label=''):
    """Same answer as common5.dual_mix_search (identical 2.5pp SAFE_GRID and
    identical chosen safe share), ~2x fewer evaluate() calls: coarse 5pp scan
    to bracket the first validation pass, then the intervening 2.5pp step,
    then the same one-step-safer final walk-back. Search-only speedup; the
    judging discipline is unchanged."""
    val, vp, fin, fp = primary
    val2, vp2, fin2, fp2 = fifth
    mix, ids = S.mix_fn(c, prop)
    per_law_val = []

    def val_pass(s):
        a = mix(float(s)) * c['wealth']
        v1, _ = common5.judge(c, primary, a)
        if not v1['overall_pass']:
            per_law_val.append((float(s), 'mixture', v1['breaches'][:2]))
            return False
        v2, _ = common5.judge(c, fifth, a)
        if not v2['overall_pass']:
            per_law_val.append((float(s), FIFTH_LAW, v2['breaches'][:2]))
            return False
        return True

    grid = [float(s) for s in S.SAFE_GRID]
    coarse = grid[::2]
    if grid[-1] not in coarse:
        coarse.append(grid[-1])
    bracket = None
    for s in coarse:
        if val_pass(s):
            bracket = s
            break
    if bracket is None:
        return dict(chosen_safe=None, note='no candidate mix passes dual-law validation',
                    label=label, validation_failures=per_law_val[:6])
    lo = max(grid[0], round(bracket - 0.05, 4))
    chosen = bracket
    s = lo
    while s < bracket:
        if s not in coarse[:-1] or s > lo:
            if val_pass(s):
                chosen = s
                break
        s = round(s + 0.025, 4)
    else:
        chosen = bracket
    s = chosen
    pick = None
    while s <= 0.9001:
        a = mix(float(s)) * c['wealth']
        _, f1 = common5.judge(c, primary, a)
        _, f2 = common5.judge(c, fifth, a)
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
               final_pass=True, final_breaches=f1.get('breaches'),
               fifth_law_final_breaches=f2.get('breaches'), label=label)
    out.update(S.score_final(c, primary[2], primary[3], a))
    out['fifth_law_score'] = S.score_final(c, fifth[2], fifth[3], a)
    return out
