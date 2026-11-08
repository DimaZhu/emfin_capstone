"""Charts for the final five-question report. Pure rendering of frozen results."""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report6_data import assemble

FIGS = Path(__file__).resolve().parent / 'figs6'
FIGS.mkdir(exist_ok=True)

NAVY = '#0d1b2e'; TEAL = '#0e7c6b'; AMBER = '#b26a00'; GRAY = '#5b6b7a'; RED = '#b00020'
LINE = '#c9d4de'
plt.rcParams.update({'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.edgecolor': LINE, 'grid.color': '#e4eaf0', 'axes.grid': True,
                     'grid.linewidth': 0.7, 'font.family': 'DejaVu Sans'})

YEARS = [5, 10, 15, 20, 30]
KEYS = [f'{y}y' for y in YEARS]


def fig_horizon(d):
    h5, old = d['h5'], d['charts']['horizon']
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.2))

    for view, col, lab in (('fitted', TEAL, 'fitted carry, five laws (fresh)'),
                           ('current_quotes', NAVY, 'current quotes, five laws (fresh)')):
        safe = [h5[view][k]['search'].get('chosen_safe') for k in KEYS]
        safe = [s * 100 if s is not None else np.nan for s in safe]
        ax.plot(YEARS, safe, 'o-', color=col, lw=2, ms=5, label=lab)
    oldsafe = [old[k]['chosen_safe'] * 100 for k in KEYS]
    ax.plot(YEARS, oldsafe, 's--', color=GRAY, lw=1.4, ms=4.5,
            label='earlier single-law sweep (different seeds)')
    ax.set_xlabel('Horizon (years)')
    ax.set_ylabel('Minimum validated T-bill share (%)')
    ax.set_ylim(0, 80)
    ax.legend(fontsize=8.2, frameon=False, loc='upper left')
    ax.set_title('Longer horizon => more bills, but the exact\nminimum wiggles across seed families', fontsize=10)

    for view, col, lab in (('fitted', TEAL, 'fitted view'), ('current_quotes', NAVY, 'current-quotes view')):
        ok, bad = [], []
        for x, k in zip(YEARS, KEYS):
            hd = h5[view][k]['hold_10y_mix']
            (ok if hd['final_pass'] else bad).append((x, hd['common_cara_ledger_ce'] / 1e6))
        if ok:
            ax2.scatter([p[0] for p in ok], [p[1] for p in ok], color=col, marker='o', s=42,
                        label=f'{lab}: passes' if view == 'fitted' else None)
        if bad:
            ax2.scatter([p[0] for p in bad], [p[1] for p in bad], color=col, marker='x', s=52,
                        linewidths=2.2,
                        label=f'{lab}: fails the regime law' if view == 'fitted' else None)
    ax2.set_xlabel('Horizon the 10-year mix is simply held to (years)')
    ax2.set_ylabel('Score ($M, not comparable across horizons)')
    ax2.set_title('Just holding the 10-year answer:\npasses to ~15y, fails the regime law at 20y+', fontsize=10)
    h, l = ax2.get_legend_handles_labels()
    ax2.legend(h[:2] + [plt.Line2D([], [], marker='o', ls='', color=GRAY),
                        plt.Line2D([], [], marker='x', ls='', color=GRAY)],
               ['passes both laws', 'fails the regime law', 'teal=fitted view, navy=current quotes'],
               fontsize=8.2, frameon=False, loc='upper left')
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_horizon.png', dpi=190, bbox_inches='tight')


def fig_inperiod(d):
    q4 = d['q4']
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.0))
    cmls = [0.05, 0.10, 0.15, 0.25, 0.40, 0.60]
    xs = [c * 100 for c in cmls]
    for view, col, lab in (('fitted', TEAL, 'fitted view'), ('current_quotes', NAVY, 'current-quotes view')):
        ce = [q4[view][f'{c:.2f}']['common_cara_ledger_ce'] / 1e6 for c in cmls]
        ax.plot(xs, ce, 'o-', color=col, lw=2, ms=5, label=lab)
    ax.axvline(40, color=AMBER, lw=1.2, ls=':')
    ax.text(40.8, ax.get_ylim()[0] + 0.4, 'your 40%', color=AMBER, fontsize=8.6, rotation=90, va='bottom')
    ax.set_xlabel('Any-point (in-period) loss cap (%)')
    ax.set_ylabel('Score ($M)')
    ax.set_title('What tightening the in-period cap costs\n(10y, terminal limit fixed at 15%, fresh seeds)', fontsize=10)
    ax.legend(fontsize=8.6, frameon=False)

    fix6 = d['fix6']['cells']
    cml_rows = [0.15, 0.25, 0.40, 0.60, 1.00]
    loss_cols = [0.05, 0.10, 0.15, 0.25, 0.40, 0.60]
    Z = np.full((len(cml_rows), len(loss_cols)), np.nan)
    for i, cml in enumerate(cml_rows):
        for j, loss in enumerate(loss_cols):
            cell = fix6.get(f'cml{cml:.2f}_loss{loss:.2f}', {})
            if cell.get('common_cara_ledger_ce'):
                Z[i, j] = cell['common_cara_ledger_ce'] / 1e6
    im = ax2.imshow(Z, cmap='Greens', aspect='auto', origin='lower')
    ax2.set_xticks(range(len(loss_cols)), [f'{v:.0%}' for v in loss_cols])
    ax2.set_yticks(range(len(cml_rows)), [f'{v:.0%}' for v in cml_rows])
    ax2.set_xlabel('Terminal loss limit')
    ax2.set_ylabel('Any-point cap')
    ax2.grid(False)
    for i in range(len(cml_rows)):
        for j in range(len(loss_cols)):
            if not np.isnan(Z[i, j]):
                ax2.text(j, i, f'{Z[i, j]:.0f}', ha='center', va='center', fontsize=8.2,
                         color='white' if Z[i, j] > np.nanmax(Z) * 0.75 else NAVY)
    j15, i40 = loss_cols.index(0.15), cml_rows.index(0.40)
    ax2.add_patch(plt.Rectangle((j15 - .5, i40 - .5), 1, 1, fill=False, edgecolor=AMBER, lw=2.2))
    ax2.set_title('Both limits together: score ($M) per cell.\nBox = your defaults (earlier seed family)', fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_inperiod.png', dpi=190, bbox_inches='tight')


def fig_utility(d):
    u = d['charts']['utilities']
    names = [('cara', 'CARA\n(surplus)'), ('crra_gross', 'CRRA\n(gross wealth)'),
             ('hara_payment_floor', 'HARA\n(payment floor)'), ('kinked_shortfall', 'Kinked\nshortfall')]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.2, 3.8), gridspec_kw={'width_ratios': [1.25, 1]})
    ce = [u[k]['common_cara_ledger_ce'] / 1e6 for k, _ in names]
    safe = [u[k]['chosen_safe'] * 100 for k, _ in names]
    cols = [TEAL, NAVY, NAVY, AMBER]
    ax.bar(range(4), ce, color=cols, width=0.62)
    for i, (v, s) in enumerate(zip(ce, safe)):
        ax.text(i, v + 0.15, f'${v:.1f}M\n{s:.0f}% bills', ha='center', fontsize=8.8, color=NAVY)
    ax.set_xticks(range(4), [n for _, n in names], fontsize=9)
    ax.set_ylim(109.5, 111.8)
    ax.set_ylabel('Score ($M, common CARA ledger)')
    ax.set_title('Same universe, same limits, 10y:\nthe utility flavor moves the answer by ~0.5%', fontsize=10)
    # Q2 panel: rebalancing, 1y with fees (frozen numbers from the dynamic study)
    laws = ['IID', 'Bounded', 'Drift -2pp', 'Drift -2pp\n+ vol x1.2']
    monthly = [98.217254, 98.209127, 97.945954, 97.949082]
    annual = [98.246273, 98.241122, 97.961745, 97.964012]
    x = np.arange(4)
    ax2.bar(x - 0.18, monthly, width=0.36, color=GRAY, label='monthly')
    ax2.bar(x + 0.18, annual, width=0.36, color=TEAL, label='annual / hold')
    for xi, (m, a) in enumerate(zip(monthly, annual)):
        ax2.text(xi + 0.18, a + 0.004, f'+{(a - m) * 1000:.0f}k', ha='center', fontsize=8, color=TEAL)
    ax2.set_xticks(x, laws, fontsize=8.2)
    ax2.set_ylim(97.88, 98.30)
    ax2.set_ylabel('Score ($M)')
    ax2.set_title('Rebalancing, 1y with 5bp fees:\nannual wins, by ~15-32k on a 98M score', fontsize=10)
    ax2.legend(fontsize=8.4, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=2)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_utility_freq.png', dpi=190, bbox_inches='tight')


def fig_benchmarks(d):
    b = d['charts']['benchmarks']
    rows = [('clever (validated mix)', 'clever\n(validated mix)'),
            ('reserve payouts, rest risky', 'reserve payouts,\nrest risky'),
            ('equal weight (1/N)', 'equal weight\n(1/N)'),
            ('all T-bills + property', 'all T-bills\n+ property'),
            ('60/40-style (60% stocks, 30% bills)', '60/40-style')]
    fig, ax = plt.subplots(figsize=(9.6, 4.0))
    ce = [b[k]['common_cara_ledger_ce'] / 1e6 for k, _ in rows]
    ok = [b[k]['validation_pass'] and b[k]['final_pass'] for k, _ in rows]
    cols = [TEAL if o else RED for o in ok]
    ax.bar(range(len(rows)), ce, color=cols, width=0.6)
    for i, (v, o) in enumerate(zip(ce, ok)):
        ax.text(i, v + 0.4, f'${v:.1f}M', ha='center', fontsize=9, color=NAVY)
        ax.text(i, 85.7, 'passes' if o else 'fails the\nsafety judge', ha='center', fontsize=8,
                color='white', fontweight='bold')
    ax.set_xticks(range(len(rows)), [n for _, n in rows], fontsize=9)
    ax.set_ylim(85, 115)
    ax.set_ylabel('Score ($M, shared final paths)')
    ax.set_title('Clever vs simple, 10y new model: simple mixes can score higher -\nbut they do not pass the same safety judge', fontsize=10.5)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_benchmarks.png', dpi=190, bbox_inches='tight')


def main():
    d = assemble()
    fig_horizon(d)
    fig_inperiod(d)
    fig_utility(d)
    fig_benchmarks(d)
    print('figures written to', FIGS)


if __name__ == '__main__':
    main()
