"""Charts for the 5th-edition report. Pure rendering of frozen results."""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report5_data import assemble

FIGS = Path(__file__).resolve().parent / 'figs5'
FIGS.mkdir(exist_ok=True)

NAVY = '#0d1b2e'; TEAL = '#0e7c6b'; AMBER = '#b26a00'; GRAY = '#5b6b7a'; RED = '#b00020'
LINE = '#c9d4de'
plt.rcParams.update({'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.edgecolor': LINE, 'grid.color': '#e4eaf0', 'axes.grid': True,
                     'grid.linewidth': 0.7, 'font.family': 'DejaVu Sans'})

NAMES = {'tbill': 'T-bills', 'treasury': 'IEF 7-10y', 'us_equity': 'US stocks',
         'em_equity': 'EM stocks', 'gold': 'Gold', 'tips': 'TIPS',
         'cash': 'Cash 0%', 'sg_property': 'SG property'}
ORDER = ['tbill', 'treasury', 'tips', 'us_equity', 'em_equity', 'gold', 'cash', 'sg_property']
COLORS = {'tbill': '#7fb3d5', 'treasury': '#2e5f8a', 'tips': '#4fe3c1', 'us_equity': '#c0392b',
          'em_equity': '#e67e22', 'gold': '#b26a00', 'cash': '#c9d4de', 'sg_property': '#5b6b7a'}


def weights_of(entry):
    return entry['weights']


def fig_mixes(d):
    rows = [('Previous default\n(shrunk history, old judge)', d['base']['weights'])]
    for view, lab in (('fitted', 'Using shrunk history\n(five laws)'), ('current_quotes', 'Using today\'s bill yields\n(five laws)')):
        e = d['dual'][view]['dual']
        if e.get('weights'):
            rows.append((lab, e['weights']))
    if d['mix10'].get('fresh_sleeve_dual', {}).get('weights'):
        rows.append(('True 10y sleeve\n(fresh, five laws)', d['mix10']['fresh_sleeve_dual']['weights']))
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    y = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    for k in ORDER:
        vals = np.array([w.get(k, 0) * 100 for _, w in rows])
        ax.barh(y, vals, left=left, color=COLORS[k], label=NAMES[k], height=0.62)
        for yi, v, l in zip(y, vals, left):
            if v >= 4:
                ax.text(l + v / 2, yi, f'{v:.0f}', ha='center', va='center', fontsize=8.4,
                        color='white' if k in ('treasury', 'us_equity', 'sg_property') else NAVY)
        left += vals
    ax.set_yticks(y, [r[0] for r in rows], fontsize=9.5)
    ax.set_xlabel('Share of the $100M (%)')
    ax.set_xlim(0, 100)
    ax.legend(ncol=4, fontsize=8.6, frameon=False, loc='upper center', bbox_to_anchor=(0.5, 1.16))
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_mixes.png', dpi=190, bbox_inches='tight')
    plt.close(fig)


def fig_nominal_vs_real(d):
    labs, nom, real = [], [], []
    for view, lab in (('fitted', 'Using shrunk history'), ('current_quotes', "Using today's bill yields")):
        e = d['dual'][view]['dual']
        if not e.get('weights'):
            continue
        labs.append(lab)
        nom.append(e['common_cara_ledger_ce'] / 1e6)
        real.append(d['real']['real_repricing'][view]['common_cara_ledger_ce'] / 1e6)
    x = np.arange(len(labs))
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    b1 = ax.bar(x - 0.19, nom, width=0.36, color=NAVY, label='Nominal score (dollars as they arrive)')
    b2 = ax.bar(x + 0.19, real, width=0.36, color=AMBER, label='Real score (in today\'s dollars)')
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f'${b.get_height():.0f}M',
                ha='center', fontsize=9.5)
    ax.set_xticks(x, labs)
    ax.set_ylabel('Score, $M (certainty equivalent)')
    ax.set_ylim(0, max(nom) * 1.18)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_nominal_vs_real.png', dpi=190, bbox_inches='tight')
    plt.close(fig)


def fig_stability(d):
    solves = d['fresh']['solves']
    fix4prop = d['fix4']['sleeve_10y']['proportions']
    props = [('old random draws\n(n=200, fix 4)', fix4prop)]
    for n in ('100', '200', '400'):
        s = solves.get(n)
        if s and s.get('weights'):
            # sleeve proportions of the risky part
            ids = ['us_equity', 'em_equity', 'gold', 'treasury', 'tips']
            w = s['weights']
            risky = {a: w.get(a, 0) for a in ids}
            tot = sum(v for v in risky.values() if v > 1e-6)
            risky = {a: (v if v > 1e-6 else 0) / tot for a, v in risky.items()}
            props.append((f'fresh draws, n={n}', risky))
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    x = np.arange(len(props))
    width = 0.15
    for i, a in enumerate(['us_equity', 'gold', 'treasury', 'tips']):
        vals = [p[1].get(a, 0) * 100 for p in props]
        ax.bar(x + (i - 1.5) * width, vals, width=width, color=COLORS[a], label=NAMES[a])
        for xi, v in zip(x, vals):
            ax.text(xi + (i - 1.5) * width, v + 1.2, f'{v:.0f}', ha='center', fontsize=8)
    ax.set_xticks(x, [p[0] for p in props], fontsize=9)
    ax.set_ylabel('Share of the risky sleeve (%)')
    ax.legend(frameon=False, ncol=4, fontsize=8.6)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_stability.png', dpi=190, bbox_inches='tight')
    plt.close(fig)


def fig_limit_cost(d):
    cells = d['fix6']['cells']
    rows = []
    for key, cell in cells.items():
        if not key.startswith('cml0.40_'):
            continue
        loss = float(key.split('loss')[1])
        ce = cell.get('common_cara_ledger_ce')
        if ce:
            rows.append((loss * 100, ce / 1e6))
    rows.sort()
    fig, ax = plt.subplots(figsize=(6.4, 3.7))
    xs, ys = zip(*rows)
    ax.plot(xs, ys, '-o', color=NAVY)
    for xv, yv in rows:
        ax.text(xv, yv + 0.35, f'${yv:.1f}M', ha='center', fontsize=8.6)
    ax.set_xlabel('Worst end-of-plan loss allowed (%)')
    ax.set_ylabel('Score at 10 years, $M')
    ax.axvline(15, color=AMBER, lw=1, ls='--')
    ax.text(15.6, min(ys), 'your current\n15% limit', color=AMBER, fontsize=8.6)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_limit_cost.png', dpi=190, bbox_inches='tight')
    plt.close(fig)


def main():
    d = assemble()
    fig_mixes(d)
    fig_nominal_vs_real(d)
    fig_stability(d)
    try:
        fig_limit_cost(d)
    except Exception as e:
        print('limit-cost figure skipped:', e)
    print('figures written:', [p.name for p in FIGS.glob('*.png')])


if __name__ == '__main__':
    main()
