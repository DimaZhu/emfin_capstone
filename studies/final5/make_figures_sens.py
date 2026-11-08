"""Charts for the sensitivity-and-trade-offs chapter. Pure rendering of
frozen results into figs6/ (run after the sens studies)."""
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
plt.rcParams.update({'font.size': 10.5, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.edgecolor': '#e4eaf0', 'grid.color': '#e4eaf0', 'axes.grid': True,
                     'grid.linewidth': 0.7, 'font.family': 'DejaVu Sans'})
TEAL, NAVY, GRAY, RED = '#0f7b6c', '#1f3864', '#8a8f98', '#b23a3a'
YEARS = [5, 10, 15, 20, 30]
KEYS = [f'{y}y' for y in YEARS]


def _safe(cell):
    s = cell['search'].get('chosen_safe')
    return s * 100 if s is not None else np.nan


def fig_sens_terminal(d):
    h5, sl, t25 = d['h5'], d['sl'], d['t25']
    losses = [0.05, 0.15, 0.25, 0.35, 0.50]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9), sharey=True)
    for ax, view, lab in ((axes[0], 'fitted', 'fitted carry'), (axes[1], 'current_quotes', "today's quotes")):
        grid = np.full((len(losses), len(YEARS)), np.nan)
        for i, L in enumerate(losses):
            for j, k in enumerate(KEYS):
                if L == 0.15:
                    cell = h5[view][k]
                elif L == 0.25:
                    cell = t25[view][k]
                else:
                    cell = sl[view].get(f'{k}_t{L:.2f}')
                if cell:
                    grid[i, j] = _safe(cell)
        im = ax.imshow(grid, cmap='viridis_r', vmin=0, vmax=90, aspect='auto')
        ax.set_xticks(range(len(YEARS)), [f'{y}y' for y in YEARS])
        ax.set_yticks(range(len(losses)), [f'{int(L*100)}%' for L in losses])
        ax.set_xlabel('Horizon')
        ax.set_title(f'Minimum validated bill share (%)\n{lab}', fontsize=10)
        for i in range(len(losses)):
            for j in range(len(YEARS)):
                if not np.isnan(grid[i, j]):
                    ax.text(j, i, f'{grid[i, j]:.0f}', ha='center', va='center', fontsize=8,
                            color='white' if grid[i, j] > 45 else 'black')
    axes[0].set_ylabel('Terminal loss limit')
    fig.colorbar(im, ax=axes, shrink=0.85, label='bill share (%)')
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_sens_terminal.png', dpi=170)
    plt.close(fig)


def fig_sens_caps(d):
    h5, sl = d['h5'], d['sl']
    cmls = [0.05, 0.15, 0.25, 0.40]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.6), sharey=True)
    for ax, view, lab in ((axes[0], 'fitted', 'fitted carry'), (axes[1], 'current_quotes', "today's quotes")):
        grid = np.full((len(cmls), len(YEARS)), np.nan)
        for i, cm in enumerate(cmls):
            for j, k in enumerate(KEYS):
                cell = h5[view][k] if cm == 0.40 else sl[view].get(f'{k}_c{cm:.2f}')
                if cell:
                    grid[i, j] = _safe(cell)
        im = ax.imshow(grid, cmap='viridis_r', vmin=0, vmax=90, aspect='auto')
        ax.set_xticks(range(len(YEARS)), [f'{y}y' for y in YEARS])
        ax.set_yticks(range(len(cmls)), [f'{int(c*100)}%' for c in cmls])
        ax.set_xlabel('Horizon')
        ax.set_title(f'Bill share (%) vs any-point cap, terminal 15%\n{lab}', fontsize=10)
        for i in range(len(cmls)):
            for j in range(len(YEARS)):
                if not np.isnan(grid[i, j]):
                    ax.text(j, i, f'{grid[i, j]:.0f}', ha='center', va='center', fontsize=8,
                            color='white' if grid[i, j] > 45 else 'black')
    axes[0].set_ylabel('Any-point (in-period) cap')
    fig.colorbar(im, ax=axes, shrink=0.85, label='bill share (%)')
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_sens_caps.png', dpi=170)
    plt.close(fig)


def fig_sens_policy(d):
    sp = d['sp']
    pols = ['buy_hold_mark', 'cash_first', 'annual_rebal', 'threshold_10', 'glide_annual']
    labs = ['marked\n(judged)', 'cash-first\n(drift)', 'annual\nrebal', '10pp\nthreshold', 'glide\npath']
    cols = [GRAY, RED, NAVY, TEAL, '#b8860b']
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9), sharey=True)
    for ax, years in ((axes[0], 20), (axes[1], 30)):
        cell = sp['fitted'][f'{years}y']
        vals = [cell[p]['terminal_ru'] for p in pols]
        ax.bar(range(len(pols)), vals, color=cols, width=0.62)
        ax.axhline(0.25, color=RED, lw=1.2, ls='--')
        ax.text(-0.35, 0.27, '25% limit', color=RED, fontsize=8, ha='left')
        ax.axhline(0.15, color=GRAY, lw=1.0, ls=':')
        ax.text(-0.35, 0.17, '15% limit', color=GRAY, fontsize=8, ha='left')
        ax.set_xticks(range(len(pols)), labs, fontsize=8.5)
        ax.set_title(f'{years}y, fitted view: terminal-loss tail by policy\n(frozen 10y mix start)',
                     fontsize=10)
        ax.set_ylim(0, max(2.0, max(vals) * 1.15))
    axes[0].set_ylabel('Terminal-loss tail (upper bound)')
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_sens_policy.png', dpi=170)
    plt.close(fig)


def fig_sens_seeds(d):
    h5, t25, ss = d['h5'], d['t25'], d['ss']
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.9), sharey=True)
    fams = [('20261109 (15%)', lambda v, k: h5[v][k], TEAL, 'o'),
            ('20261109 (25%)', lambda v, k: t25[v][k], NAVY, 's'),
            ('20261110 (25%)', lambda v, k: d['t25f'][v][k], GRAY, '^'),
            ('20261111 (15%)', lambda v, k: ss[v][f'{k}_t0.15'], '#b8860b', 'D'),
            ('20261111 (25%)', lambda v, k: ss[v][f'{k}_t0.25'], RED, 'v')]
    for ax, view, lab in ((axes[0], 'fitted', 'fitted carry'), (axes[1], 'current_quotes', "today's quotes")):
        for name, get, col, mk in fams:
            ys = [_safe(get(view, k)) for k in KEYS]
            ax.plot(YEARS, ys, mk + '-', color=col, ms=4.5, lw=1.3, label=name, alpha=0.85)
        ax.set_xlabel('Horizon (years)')
        ax.set_title(f'Minimum validated bill share by seed family\n{lab}', fontsize=10)
        ax.set_ylim(0, 90)
        if view == 'fitted':
            ax.legend(fontsize=7.4, frameon=False, loc='upper left')
    axes[0].set_ylabel('Bill share (%)')
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_sens_seeds.png', dpi=170)
    plt.close(fig)


def main():
    d = assemble()
    d['t25f'] = json.loads((FIGS.parent / 'results' / 'final5_horizon_t25.json').read_text())
    fig_sens_terminal(d)
    fig_sens_caps(d)
    fig_sens_policy(d)
    fig_sens_seeds(d)
    print('figures written to', FIGS)


if __name__ == '__main__':
    main()
