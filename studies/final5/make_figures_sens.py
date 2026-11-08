"""Charts for the sensitivity-and-trade-offs chapter. Pure rendering of
frozen results into figs6/ (run after the sens studies).

Newcomer revision (8 Nov 2026): plain words on every axis and title, one idea
per chart, heatmap colorbar below the panels (was overlapping the right
heatmap), 'darker = safer' stated on the chart, seed families drawn as a
shaded min-max band instead of five lines, policy limits in a legend instead
of text overlapping the bars."""
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
TEAL, NAVY, GRAY, RED, GOLD = '#0f7b6c', '#1f3864', '#8a8f98', '#b23a3a', '#b8860b'
YEARS = [5, 10, 15, 20, 30]
KEYS = [f'{y}y' for y in YEARS]
VIEWS = (('fitted', 'using shrunk history'), ('current_quotes', "using today's T-bill yields"))


def _safe(cell):
    s = cell['search'].get('chosen_safe')
    return s * 100 if s is not None else np.nan


def _heatmap(axes, grids, rows, suptitle, ylabel):
    im = None
    for ax, (view, lab), grid in zip(axes, VIEWS, grids):
        im = ax.imshow(grid, cmap='viridis_r', vmin=0, vmax=90, aspect='auto')
        ax.set_xticks(range(len(YEARS)), [f'{y}y' for y in YEARS])
        ax.set_yticks(range(grid.shape[0]),
                      [f'{int(v * 100)}%' for v in rows])
        ax.set_title(lab, fontsize=11)
        ax.grid(False)
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                if not np.isnan(grid[i, j]):
                    ax.text(j, i, f'{grid[i, j]:.0f}', ha='center', va='center', fontsize=9.5,
                            color='white' if grid[i, j] > 45 else 'black')
    axes[0].set_ylabel(ylabel)
    axes[1].tick_params(axis='y', left=False, labelleft=False)
    fig = axes[0].figure
    fig.suptitle(suptitle, fontsize=11.5, y=0.99)
    fig.tight_layout(rect=(0, 0.18, 1, 0.93))
    fig.supxlabel('How long the money must last (years)', fontsize=10.5, y=0.115)
    cax = fig.add_axes([0.29, 0.048, 0.42, 0.018])
    cb = fig.colorbar(im, cax=cax, orientation='horizontal')
    cb.ax.tick_params(labelsize=8.5)
    cb.ax.set_title('share in T-bills (%)', fontsize=9, pad=2.5)


def fig_sens_terminal(d):
    h5, sl, t25 = d['h5'], d['sl'], d['t25']
    losses = [0.05, 0.15, 0.25, 0.35, 0.50]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), sharey=True)
    grids = []
    for view, _ in VIEWS:
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
        grids.append(grid)
    _heatmap(axes, grids, losses,
             'Minimum share in T-bills the judge requires (%), by plan length and end-of-plan loss limit\n'
             'darker = more in T-bills = safer, but less expected leftover',
             'Allowed end-of-plan loss')
    fig.savefig(FIGS / 'fig_sens_terminal.png', dpi=170)
    plt.close(fig)


def fig_sens_caps(d):
    h5, sl = d['h5'], d['sl']
    cmls = [0.05, 0.15, 0.25, 0.40]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1), sharey=True)
    grids = []
    for view, _ in VIEWS:
        grid = np.full((len(cmls), len(YEARS)), np.nan)
        for i, cm in enumerate(cmls):
            for j, k in enumerate(KEYS):
                cell = h5[view][k] if cm == 0.40 else sl[view].get(f'{k}_c{cm:.2f}')
                if cell:
                    grid[i, j] = _safe(cell)
        grids.append(grid)
    _heatmap(axes, grids, cmls,
             'Minimum T-bill share (%), by plan length and the worst dip allowed at any moment\n'
             '(end-of-plan loss limit 15%)  -  darker = more in T-bills = safer',
             'Worst dip allowed\nat any moment')
    fig.savefig(FIGS / 'fig_sens_caps.png', dpi=170)
    plt.close(fig)


def fig_sens_policy(d):
    sp = d['sp']
    pols = ['buy_hold_mark', 'cash_first', 'annual_rebal', 'threshold_10', 'glide_annual']
    labs = ['do nothing\n(the judged mix)', 'never\nrebalance', 'rebalance\nyearly',
            'rebalance when\nmix drifts 10pts', 'glide path:\ntarget falls\nas end nears']
    cols = [GRAY, RED, NAVY, TEAL, GOLD]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.3), sharey=True)
    for ax, years in ((axes[0], 20), (axes[1], 30)):
        cell = sp['fitted'][f'{years}y']
        vals = [cell[p]['terminal_ru'] for p in pols]
        bars = ax.bar(range(len(pols)), vals, color=cols, width=0.62)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.04, f'{v:.2f}', ha='center',
                    fontsize=9, color='#1c2733')
        ax.axhline(0.25, color=RED, lw=1.2, ls='--', label='25% loss limit')
        ax.axhline(0.15, color=GRAY, lw=1.0, ls=':', label='15% loss limit')
        ax.legend(fontsize=9, frameon=False, loc='upper left')
        ax.set_xticks(range(len(pols)), labs, fontsize=8.6)
        ax.set_title(f'{years}-year plan', fontsize=11)
        ax.set_ylim(0, max(2.0, max(vals) * 1.18) + 0.35)
        ax.grid(axis='x', visible=False)
    axes[0].set_ylabel('Worst end-of-plan loss\n(upper bound, lower = safer)')
    fig.suptitle('How you run the mix matters - but it cannot fix the wrong starting mix\n'
                 '(same starting mix, same simulated futures; bars above a line break that limit)',
                 fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(FIGS / 'fig_sens_policy.png', dpi=170)
    plt.close(fig)


def fig_sens_seeds(d):
    """Seed noise as a shaded min-max band across independent families of
    simulated futures: 15% end-of-plan limit (2 families, top row) and 25%
    (3 families, bottom row)."""
    h5, t25, ss = d['h5'], d['t25'], d['ss']
    t25f = json.loads((FIGS.parent / 'results' / 'final5_horizon_t25.json').read_text())
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.4), sharex=True)
    rows = [
        ('15% end-of-plan limit',
         lambda v: np.array([[_safe(h5[v][k]) for k in KEYS],
                             [_safe(ss[v][f'{k}_t0.15']) for k in KEYS]])),
        ('25% end-of-plan limit',
         lambda v: np.array([[_safe(t25[v][k]) for k in KEYS],
                             [_safe(t25f[v][k]) for k in KEYS],
                             [_safe(ss[v][f'{k}_t0.25']) for k in KEYS]])),
    ]
    for i, (rlab, get) in enumerate(rows):
        for j, (view, lab) in enumerate(VIEWS):
            ax = axes[i][j]
            fams = get(view)
            lo, hi = np.nanmin(fams, axis=0), np.nanmax(fams, axis=0)
            mid = np.nanmedian(fams, axis=0)
            col = TEAL if view == 'fitted' else NAVY
            ax.fill_between(YEARS, lo, hi, color=col, alpha=0.22)
            ax.plot(YEARS, mid, 'o-', color=col, lw=2, ms=5.5)
            for jj, (x, a, b) in enumerate(zip(YEARS, lo, hi)):
                ax.annotate(f'{a:.0f}-{b:.0f}', (x, b), textcoords='offset points',
                            xytext=(6 if jj == 0 else 0, 7), ha='left' if jj == 0 else 'center',
                            fontsize=8.4, color='#5b6b7a')
            ax.set_xticks(YEARS)
            ax.set_xlim(4, 31)
            ax.set_ylim(0, 95)
            if i == 0:
                ax.set_title(lab, fontsize=11)
            if j == 0:
                ax.set_ylabel(f'{rlab}\nminimum share in T-bills (%)', fontsize=9.5)
            if i == 1:
                ax.set_xlabel('How long the money must last (years)')
    fig.suptitle('The same question on independent sets of simulated futures:\n'
                 'the answer is a band, not a number (ranges marked at each plan length)',
                 fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIGS / 'fig_sens_seeds.png', dpi=170)
    plt.close(fig)


def main():
    d = assemble()
    fig_sens_terminal(d)
    fig_sens_caps(d)
    fig_sens_policy(d)
    fig_sens_seeds(d)
    print('figures written to', FIGS)


if __name__ == '__main__':
    main()
