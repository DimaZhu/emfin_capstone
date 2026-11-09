"""Offline chained-wealth analysis of the walk-forward backtest: no new solves.

Motivation (design review, 9 Nov 2026; owner approval "Ok. Go!" 10:30 +08):
the full chained-wealth re-solve (studies/backtest_chained_20261109) re-solves
every fold at the method's compounded wealth. That state-dependence only
matters if wealth moves far from the $100M reference. This study answers the
chained question from the reference-wealth study's OWN fold records
(studies/backtest_20261108/results/part_*/fold_*.json), at zero solver cost:

1. Offline chaining: each method's per-fold realized window return is
   decomposed into a gross asset return (window return + the reference payout
   drag 750k/$100M = 0.75%; payouts land in weeks 4/8/13, the add-back treats
   them as fold-end - approximation error ~0.002%/fold) and re-chained with
   ABSOLUTE payouts: W <- W*(1+g) - $750k per fold.
2. Stationary bootstrap (Politis & Romano 1994, JASA 89:1303): 5,000
   resampled 78-fold sequences (geometric block lengths, mean 4 folds = 1
   year, fold indices resampled jointly across methods so cross-method
   dependence is kept), each chained the same way. Gives the distribution of
   chained outcomes instead of the single realized path.

Abstention treatment: in the reference study the 9 folds where no calibration
candidate passed record proposed as unavailable. Here those folds earn the
registry cash account return (0% placeholder - an OVERSTATEMENT of the cost of
abstaining; the T-bill fallback is implemented on the chained branch). Results
are therefore slightly conservative for the proposed method.

What this study does NOT capture: state-dependent re-solving (risk_tolerance =
10% of chained wealth vs fixed $10M). The realized-path result below shows the
proposed method's wealth stays within [99.0, 112.2]M, so its risk tolerance
would wander only ~$9.9-11.2M vs $10M and decisions would barely move - the
reason the full chained run is deferred.

Also computed: paired per-fold differences vs proposed BOTH ways (excluding
the 9 abstention folds, as in the reference report, and including them with
proposed earning the cash return), because the exclusion flatters the
proposed method (1/N averaged +1.71% in those 9 quarters).

Deterministic: numpy default_rng(20261109), 5,000 replications.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / 'studies/backtest_20261108/results'
HERE = Path(__file__).resolve().parent
METHODS = ['proposed', 'cash', '1/N', 'min_var', 'shrunk_MV']
PAYOUT = 750_000.0   # 3 x $250k per 13-week fold
REF = 1e8
DRAG_REF = PAYOUT / REF  # 0.75% per fold at reference wealth
N_BOOT = 5000
MEAN_BLOCK = 4         # folds (~1 year)
SEED = 20261109


def load_folds():
    folds = [json.loads(p.read_text()) for p in sorted(V1.glob('part_*/fold_*.json'))]
    folds.sort(key=lambda f: f['fold'])
    assert len(folds) == 78 and [f['fold'] for f in folds] == list(range(78))
    return folds


def gross_returns(folds):
    """Per-method per-fold gross asset-window returns (payout drag added back).
    Abstain/unavailable folds -> 0 (registry cash account, 0% placeholder)."""
    g = {m: [] for m in METHODS}
    for f in folds:
        for m in METHODS:
            rec = f['methods'].get(m, {})
            if rec.get('available'):
                g[m].append(rec['realized_window_return'] + DRAG_REF)
            else:
                g[m].append(0.0)
    return {m: np.array(v) for m, v in g.items()}


def chain(seq, payout=PAYOUT):
    W = REF
    path = [W]
    for x in seq:
        W = W * (1 + x) - payout
        path.append(W)
    return W, np.array(path)


def paired(folds):
    """Paired per-fold differences vs proposed, both abstention treatments."""
    out = {}
    for m in METHODS:
        if m == 'proposed':
            continue
        excl, incl = [], []
        for f in folds:
            rec = f['methods'].get('proposed', {})
            rm = f['methods'][m]['realized_window_return']
            if rec.get('available'):
                excl.append(rec['realized_window_return'] - rm)
                incl.append(rec['realized_window_return'] - rm)
            else:
                incl.append(-DRAG_REF - rm)  # proposed as cash
        e, i = np.array(excl), np.array(incl)
        out[m] = dict(
            excluding_abstentions=dict(n=len(e), mean_diff=float(e.mean()),
                                       se=float(e.std(ddof=1) / np.sqrt(len(e)))),
            including_abstentions_as_cash=dict(n=len(i), mean_diff=float(i.mean()),
                                               se=float(i.std(ddof=1) / np.sqrt(len(i)))),
        )
    return out


def stationary_bootstrap(G):
    rng = np.random.default_rng(SEED)
    T = G[METHODS[0]].shape[0]
    p = 1.0 / MEAN_BLOCK
    terms = np.zeros((N_BOOT, len(METHODS)))
    mins = np.zeros((N_BOOT, len(METHODS)))
    for b in range(N_BOOT):
        idx = []
        i = rng.integers(T)
        while len(idx) < T:
            if rng.random() < p:
                i = rng.integers(T)
            else:
                i = (i + 1) % T
            idx.append(i)
        idx = np.array(idx[:T])
        for j, m in enumerate(METHODS):
            W, path = chain(G[m][idx])
            terms[b, j] = W / REF
            mins[b, j] = path.min() / REF
    return terms, mins


def main():
    folds = load_folds()
    g = gross_returns(folds)
    abst = [f['fold'] for f in folds if not f['methods'].get('proposed', {}).get('available')]
    abst_dates = [folds[k]['decision_date'] for k in abst]

    chained = {}
    paths = {}
    for m in METHODS:
        W, path = chain(g[m])
        paths[m] = path
        chained[m] = dict(terminal_wealth_dollars=float(W),
                          terminal_relative=float(W / REF),
                          min_wealth_dollars=float(path.min()),
                          max_payout_ratio_per_fold=float(PAYOUT / path.min()))

    terms, mins = stationary_bootstrap(g)
    boot = {}
    for j, m in enumerate(METHODS):
        q = np.quantile(terms[:, j], [0.05, 0.5, 0.95])
        boot[m] = dict(terminal_q05=float(q[0]), terminal_q50=float(q[1]),
                       terminal_q95=float(q[2]),
                       p_min_wealth_below_075=float((mins[:, j] < 0.75).mean()))
    p_beat = {m: float((terms[:, 0] > terms[:, j]).mean())
              for j, m in enumerate(METHODS) if m != 'proposed'}

    abst_other = {}
    for m in METHODS:
        if m == 'proposed':
            continue
        rs = [folds[k]['methods'][m]['realized_window_return'] for k in abst]
        abst_other[m] = float(np.mean(rs))

    out = dict(
        design=__doc__.split('\n\n')[1],
        payout_per_fold_dollars=PAYOUT, reference_wealth_dollars=REF,
        abstention_folds=abst, abstention_decision_dates=abst_dates,
        abstention_treatment='proposed earns the 0% registry cash account (conservative)',
        methods_mean_return_in_abstention_folds=abst_other,
        offline_chained=chained,
        paired_vs_proposed=paired(folds),
        bootstrap=dict(seed=SEED, n_replications=N_BOOT, mean_block_folds=MEAN_BLOCK,
                       per_method=boot, p_proposed_terminal_exceeds=p_beat),
    )
    (HERE / 'results').mkdir(exist_ok=True)
    (HERE / 'results/summary.json').write_text(json.dumps(out, indent=1) + '\n')

    # Figure: left = offline chained wealth paths; right = bootstrap terminal
    # relative distribution (q05/q50/q95) per method.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    (HERE / 'figs').mkdir(exist_ok=True)
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(13, 5))
    x = np.arange(79) / 4  # years
    for m in METHODS:
        axl.plot(x, paths[m] / 1e6, label=m, linewidth=2 if m == 'proposed' else 1)
    axl.scatter([(k + 1) / 4 for k in abst],
                [paths['proposed'][k + 1] / 1e6 for k in abst],
                marker='x', color='black', zorder=5, label='proposed abstention fold')
    axl.axhline(100, color='grey', linewidth=0.5)
    axl.set_xlabel('years since Mar 2007')
    axl.set_ylabel('wealth, $M (start $100M, $750k payouts per quarter)')
    axl.set_title('Offline chained wealth, realized path 2007-2026\n'
                  '(v1 fold returns, absolute payouts; abstentions at 0% cash)')
    axl.legend(fontsize=8)
    for j, m in enumerate(METHODS):
        b = boot[m]
        axr.plot([j, j], [b['terminal_q05'], b['terminal_q95']], color='C0')
        axr.plot(j, b['terminal_q50'], marker='o', color='C0')
        axr.plot(j, chained[m]['terminal_relative'], marker='s', color='black', markersize=5)
    axr.plot([], [], color='C0', marker='o', label='bootstrap q05/q50/q95 (5,000 sequences)')
    axr.plot([], [], color='black', marker='s', linestyle='none', label='realized path (left panel)')
    axr.axhline(1.0, color='grey', linewidth=0.5)
    axr.set_xticks(range(len(METHODS)))
    axr.set_xticklabels(METHODS, fontsize=8)
    axr.set_ylabel('terminal wealth relative to $100M')
    axr.set_title('Stationary bootstrap of chained terminal wealth\n'
                  '(resampled 78-fold sequences, mean block 4 folds)')
    axr.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(HERE / 'figs/offline_chained.png', dpi=150)
    print(json.dumps({m: chained[m]['terminal_relative'] for m in METHODS}, indent=1))
    print('P(proposed terminal > other):', p_beat)


if __name__ == '__main__':
    main()
