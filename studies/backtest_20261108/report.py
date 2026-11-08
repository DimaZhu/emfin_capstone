"""Aggregate walk-forward folds into summary tables, figures and REPORT.md.

Run after backtest.py completes (or any time for partial results). Reads
results/part_*/fold_*.json (partitioned runner), writes results/summary.json,
figs/*.png and REPORT.md.

Reporting discipline (docs/NEXT_RESEARCH_PLAN.md): realized funding deficits,
tail loss with sample counts, terminal surplus, turnover, and paired
differences against benchmarks. No confidence or significance claims beyond
what 78 non-overlapping folds support; standard errors are descriptive.
"""
import sys, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RESULTS = HERE / 'results'
FIGS = HERE / 'figs'
METHODS = ['proposed', 'cash', '1/N', 'min_var', 'shrunk_MV']


def load_folds():
    folds = []
    for p in sorted(RESULTS.glob('part_*/fold_*.json')):
        folds.append(json.loads(p.read_text()))
    return folds


def aggregate(folds):
    per = {m: [] for m in METHODS}
    for f in folds:
        for m in METHODS:
            rec = f['methods'].get(m)
            if not rec or not rec.get('available'):
                per[m].append(None)
                continue
            per[m].append(rec)
    out = {'n_folds': len(folds), 'methods': {}}
    for m in METHODS:
        vals = [r for r in per[m] if r]
        if not vals:
            out['methods'][m] = {'available': False}
            continue
        rets = np.array([r['realized_window_return'] for r in vals])
        short = np.array([max(r['payment_shortfalls_dollars'] + [0.0]) for r in vals])
        unfunded = sum(1 for r in vals if not r['funded'])
        losses = np.array([r['max_path_loss'] for r in vals])
        turns = np.array([r['turnover'] for r in vals if r['turnover'] is not None])
        wealth_rel = float(np.prod(1 + rets))
        out['methods'][m] = dict(
            available=True, n=len(vals),
            wealth_relative_over_backtest=wealth_rel,
            annualized_return=float((wealth_rel ** (52 / (13 * len(vals))) - 1)),
            mean_window_return=float(rets.mean()),
            std_window_return=float(rets.std(ddof=1)),
            min_window_return=float(rets.min()),
            max_path_loss_median=float(np.median(losses)),
            max_path_loss_worst=float(losses.max()),
            folds_with_unfunded_payout=unfunded,
            total_unpaid_dollars=float(sum(sum(r['payment_shortfalls_dollars']) for r in vals)),
            largest_fold_shortfall_dollars=float(short.max()),
            mean_turnover_per_fold=float(turns.mean()) if len(turns) else None,
        )
    # paired differences vs proposed (descriptive, paired by fold)
    base = per['proposed']
    paired = {}
    for m in METHODS:
        if m == 'proposed':
            continue
        diffs = []
        for rb, rm in zip(base, per[m]):
            if rb and rm:
                diffs.append(rb['realized_window_return'] - rm['realized_window_return'])
        if diffs:
            d = np.array(diffs)
            paired[m] = dict(n=len(d), mean_diff_window_return=float(d.mean()),
                             se=float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else None)
    out['paired_vs_proposed'] = paired
    # solver health
    solves = []
    for f in folds:
        for s in f.get('solves', []):
            solves.append(s)
    kinds = {}
    for s in solves:
        k = s.get('diag', {}).get('kind', '?')
        kinds[k] = kinds.get(k, 0) + 1
    out['solver'] = dict(n_solves=len(solves), kinds=kinds,
                         solve_seconds_median=float(np.median([s.get('solve_seconds', np.nan) for s in solves])) if solves else None,
                         mults_used=sorted({s.get('mult') for s in solves}))
    unavailable = [f['fold'] for f in folds if not f['methods'].get('proposed', {}).get('available')]
    out['proposed_unavailable_folds'] = unavailable
    # Sensitivity: count abstention folds as earning the cash-account window
    # return (what a declined client would plausibly hold) instead of skipping.
    if unavailable and out['methods'].get('cash', {}).get('available'):
        cash_rets = {f['fold']: f['methods']['cash']['realized_window_return'] for f in folds
                     if f['methods'].get('cash', {}).get('available')}
        w = 1.0
        for f in folds:
            rec = f['methods'].get('proposed', {})
            if rec.get('available'):
                w *= 1 + rec['realized_window_return']
            else:
                w *= 1 + cash_rets.get(f['fold'], 0.0)
        out['proposed_wealth_relative_abstention_as_cash'] = float(w)
    return out, per


def make_figures(folds, per):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    FIGS.mkdir(exist_ok=True)
    dates = [f['decision_date'] for f in folds]
    x = np.arange(len(folds))

    # 1. chained wealth relative per method. The proposed model has folds
    # where calibration declined every candidate; compound those as cash
    # (the abstention-as-cash sensitivity in REPORT.md) so its line shows.
    cash_rets = {f['fold']: f['methods']['cash']['realized_window_return'] for f in folds
                 if f['methods'].get('cash', {}).get('available')}
    fig, ax = plt.subplots(figsize=(10, 5))
    abst_pts = []
    for m in METHODS:
        vals = per[m]
        w, wi = 1.0, []
        ok = True
        for i, v in enumerate(vals):
            if not v:
                if m == 'proposed':
                    w *= 1 + cash_rets.get(folds[i]['fold'], 0.0)
                    wi.append(w)
                    abst_pts.append((i, w))
                    continue
                ok = False
                break
            w *= 1 + v['realized_window_return']
            wi.append(w)
        if ok:
            label = m if m != 'proposed' else 'proposed (abstentions as cash)'
            ax.plot(x, wi, label=label, linewidth=2 if m == 'proposed' else 1)
    if abst_pts:
        ax.scatter([p[0] for p in abst_pts], [p[1] for p in abst_pts],
                   marker='x', color='black', zorder=5, label='proposed abstention fold')
    ax.set_title('Walk-forward chained wealth relative (reference-wealth folds, compounded offline)')
    ax.set_xlabel('fold (13-week steps, 2007-03 to 2026-08)')
    ax.set_ylabel('wealth relative')
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / 'wealth_relative.png', dpi=130)
    plt.close(fig)

    # 2. funding shortfall dollars per fold
    fig, ax = plt.subplots(figsize=(10, 4))
    width = 0.15
    for i, m in enumerate(METHODS):
        vals = [max((v['payment_shortfalls_dollars'] + [0.0])) if v else np.nan for v in per[m]]
        ax.bar(x + i * width, vals, width=width, label=m)
    ax.set_title('Largest unpaid payout per 13-week fold (dollars; engine cash-first ledger on realized paths)')
    ax.set_xlabel('fold')
    ax.set_ylabel('largest shortfall ($)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / 'funding_shortfalls.png', dpi=130)
    plt.close(fig)

    # 3. realized window returns scatter, proposed vs benchmarks
    fig, ax = plt.subplots(figsize=(10, 5))
    for m in METHODS:
        vals = [v['realized_window_return'] if v else np.nan for v in per[m]]
        ax.plot(x, vals, '.', label=m, markersize=4)
    ax.axhline(0, color='k', linewidth=0.5)
    ax.set_title('Realized 13-week window returns by method')
    ax.set_xlabel('fold')
    ax.set_ylabel('window return')
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / 'window_returns.png', dpi=130)
    plt.close(fig)
    return ['wealth_relative.png', 'funding_shortfalls.png', 'window_returns.png']


def write_report(folds, summary, figs):
    L = []
    L.append('# Walk-forward historical backtest (2007-2026)')
    L.append('')
    L.append('First true chronological out-of-sample evaluation of the engine: 78 non-overlapping')
    L.append('13-week folds, decisions 2007-03-16 to 2026-05-22; every fold re-fit strictly on past')
    L.append('data and re-solved at full default scale; realized outcomes accounted through the')
    L.append('engine cash-first ledger with identical assets, haircuts, payouts (3 x $250k per fold)')
    L.append('and constraints. Property included via the URA quarterly index at the fixed 10%')
    L.append('placeholder holding (index granularity; not a tradable weekly property return).')
    L.append('')
    L.append(f"Folds completed: {summary['n_folds']} of 78.")
    L.append('')
    L.append('## Headline table')
    L.append('')
    L.append('| method | wealth relative | annualized | worst fold | folds with unpaid $ | total unpaid $ | mean turnover |')
    L.append('|---|---|---|---|---|---|---|')
    for m in METHODS:
        s = summary['methods'].get(m, {})
        if not s.get('available'):
            L.append(f'| {m} | n/a | | | | | |')
            continue
        L.append(f"| {m} | {s['wealth_relative_over_backtest']:.3f} | {s['annualized_return']:.2%} | "
                 f"{s['min_window_return']:.2%} | {s['folds_with_unfunded_payout']} | "
                 f"${s['total_unpaid_dollars']:,.0f} | "
                 + (f"{s['mean_turnover_per_fold']:.2f}" if s['mean_turnover_per_fold'] is not None else 'n/a') + ' |')
    L.append('')
    L.append('## Paired differences vs proposed (per-fold realized window return)')
    L.append('')
    for m, p in summary.get('paired_vs_proposed', {}).items():
        se = f" +/- {p['se']:.4f} (descriptive SE)" if p['se'] is not None else ''
        L.append(f"- proposed minus {m}: {p['mean_diff_window_return']:+.4f} per fold{se}, n={p['n']}")
    L.append('')
    sv = summary['solver']
    L.append(f"## Solver health: {sv['n_solves']} solves, kinds {sv['kinds']}, "
             f"median {sv['solve_seconds_median']}s, multipliers used {sv['mults_used']}")
    if summary['proposed_unavailable_folds']:
        L.append(f"Folds where no proposed allocation passed: {summary['proposed_unavailable_folds']}")
        if 'proposed_wealth_relative_abstention_as_cash' in summary:
            L.append(f"Proposed wealth relative counting abstention folds as cash: "
                     f"{summary['proposed_wealth_relative_abstention_as_cash']:.3f} "
                     f"(headline {summary['methods']['proposed']['wealth_relative_over_backtest']:.3f} skips those folds).")
    L.append('')
    L.append('## Caveats')
    L.append('')
    L.append('- Folds are solved at stationary reference wealth ($100M / $10M risk tolerance);')
    L.append('  wealth relatives compound offline. Chained-wealth re-solving is future work.')
    L.append('- 78 folds bound what can be said: paired differences are descriptive, no')
    L.append('  significance claims. Early folds have ~2 years of training data.')
    L.append('- Property marks: quarterly URA index, 45-day release lag; engine rent/sale')
    L.append('  conventions. No weekly property tails are observed or claimed.')
    L.append('- Cash account is the registry fixed-rate account in both model and realized')
    L.append('  paths (identical-investable-assets rule).')
    L.append('')
    L.append('Figures: ' + ', '.join(f'figs/{f}' for f in figs))
    (HERE / 'REPORT.md').write_text('\n'.join(L) + '\n')


def main():
    folds = load_folds()
    if not folds:
        print('no folds yet')
        return
    summary, per = aggregate(folds)
    (RESULTS / 'summary.json').write_text(json.dumps(summary, indent=1, default=str) + '\n')
    figs = make_figures(folds, per)
    write_report(folds, summary, figs)
    print(json.dumps({m: summary['methods'][m] for m in METHODS if summary['methods'].get(m, {}).get('available')},
                     indent=1, default=str)[:3000])


if __name__ == '__main__':
    main()
