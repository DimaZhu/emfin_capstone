"""Sensitivity section (owner ask 8 Nov 13:12 SGT + glide-path "Yes" 13:19):
Stage 2 - execution policy dial. Does HOW you run the portfolio (never
rebalance / annual / threshold / time-varying glide target) substitute for a
safer mix? Same seed family 20261109, same draws (tag f5_h{weeks}_{view}) and
same terminal-tail statistic as the horizon and limit studies, so all policy
numbers sit on the stage-1 grid's draws. BOTH carry views, horizons 10/20/30y,
$250k/month, frozen round-2 mixes as the static starting point.

Policies per (view, horizon):
  buy_hold_mark  - the judged terminal metric: frozen mix marked to market.
  cash_first     - executed policy, never rebalances.
  annual_rebal   - rebalance to the frozen target every 52 weeks.
  threshold_10   - rebalance only when the risky drift vs target exceeds 10pp.
  glide_annual   - annual rebalance to a TIME-VARYING target: bill share
                   declines linearly from the validated static share at this
                   horizon (final5_horizon.json, 15% terminal) to the validated
                   10y share. This is the glide path rebalancing alone cannot
                   produce (owner question 13:18 SGT).
Checkpointed per cell in results/final5_sens_policies.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import S, save, load, f5_fit
from study_q3_rebalance import terminal_tail, frozen_vector

R2 = Path('studies/round2/results/round2_dual_law.json')
H15 = Path('studies/final5/results/final5_horizon.json')
RESULT = 'final5_sens_policies.json'
YEARS = [10, 20, 30]


def simulate_policy(c, draw, w0, policy, glide=None):
    """cash_first twin with rebalancing variants. Mirrors S.simulate;
    glide=(s_start, s_end) makes the liquid bill target decline linearly."""
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
    funded = np.zeros((n, amounts.shape[1]))

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
        # safe asset gets share s of liquid wealth; the rest pro-rata per base
        out = base.copy()
        other = out.sum() - out[safe_pos]
        out = out / other * (1 - s)
        out[safe_pos] = s
        return out

    arrears = np.zeros(n)
    shortfalls = np.zeros_like(amounts)
    for t in range(h):
        ratio = growth[:, t] / (growth[:, t - 1] if t else 1.)
        cash *= ratio
        arrears *= ratio
        do_rebal = False
        if policy in ('annual_rebal', 'glide_annual') and t % 52 == 0:
            do_rebal = True
        elif policy == 'threshold_10':
            px = prices[:, t]
            vals = units[:, liquid] * px[:, liquid]
            total = cash + vals.sum(1)
            cur = np.concatenate([cash[:, None], vals], 1) / total[:, None]
            drift = np.abs(cur - base[None, :]).max(1)
            if drift.max() > 0.10:
                do_rebal = True
        if do_rebal and policy not in ('cash_first', 'buy_hold_mark'):
            tgt = target_at(t)
            px = prices[:, t]
            vals = units[:, liquid] * px[:, liquid]
            total = cash + vals.sum(1)
            desired = total[:, None] * tgt[None, :]
            dv = desired[:, 1:] - vals
            turnover += (np.abs(dv).sum(1) + np.abs(desired[:, 0] - cash)) / 2
            units[:, liquid] = desired[:, 1:] / px[:, liquid]
            cash = desired[:, 0]
        for k in np.flatnonzero(steps == t + 1):
            due = amounts[:, k] + arrears
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
    return dict(net_wealth_paths=wealth, turnover=turnover,
                funded=np.all(shortfalls <= 1e-6, axis=1))


def main():
    r2 = json.loads(R2.read_text())
    h15 = json.loads(H15.read_text())
    out = load(RESULT)
    out.setdefault('meta', dict(
        label=('FINAL-5 SENS stage 2 (owner ask 8 Nov 13:12 + glide "Yes" 13:19 SGT): policy '
               'dial at 10/20/30y, seed family 20261109 (same draws as the limit studies), '
               'both carry views. buy_hold_mark = judged metric; cash_first/annual_rebal/'
               'threshold_10/glide_annual = executed policies. Glide target: validated static '
               'bill share at horizon H declining linearly to the validated 10y share '
               '(final5_horizon.json, 15% terminal).'),
        years=YEARS,
        policies=['buy_hold_mark', 'cash_first', 'annual_rebal', 'threshold_10', 'glide_annual']))
    for view in ('fitted', 'current_quotes'):
        vent = out.setdefault(view, {})
        static = {int(y): h15[view][f'{y}y']['search'].get('chosen_safe') for y in YEARS}
        s10 = h15[view]['10y']['search'].get('chosen_safe')
        for years in YEARS:
            key = f'{years}y'
            if key in vent:
                continue
            t0 = time.perf_counter()
            c = common5.f5_config(view=view, weeks=52 * years, months=12 * years)
            fit = f5_fit(c)
            tag = f'f5_h{52 * years}_{view}'
            _, (_, _, fin2, fp2) = common5.f5_draws(c, fit, tag)
            w0, ids = frozen_vector(c, r2[view]['dual']['weights'])
            a = w0 * c['wealth']
            cell = dict(years=years, view=view,
                        weights={i: round(float(w), 4) for i, w in zip(ids, w0)},
                        glide=(static[years], s10))
            bh = [(d[0] @ a)[:, -1] for d in fin2]
            cell['buy_hold_mark'] = terminal_tail(c, fin2, fp2, w0, bh)
            for pol in ('cash_first', 'annual_rebal', 'threshold_10', 'glide_annual'):
                glide = (static[years], s10) if pol == 'glide_annual' else None
                pay = [simulate_policy(c, d, w0, pol, glide) for d in fin2]
                wp = [z['net_wealth_paths'][:, -1] for z in pay]
                tt = terminal_tail(c, fin2, fp2, w0, wp)
                tt['funded'] = float(np.mean([z['funded'].mean() for z in pay]))
                tt['turnover_mean'] = float(np.mean([z['turnover'].mean() for z in pay]))
                cell[pol] = tt
                print(view, key, pol, 'termRU=%.3f funded=%.3f' % (tt['terminal_ru'], tt['funded']), flush=True)
            cell['seconds'] = time.perf_counter() - t0
            vent[key] = cell
            save(RESULT, out)
    save(RESULT, out)


if __name__ == '__main__':
    main()
