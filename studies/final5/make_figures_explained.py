"""Charts for the standalone explained document. Newcomer-first redesigns of
the sensitivity figures: one idea per chart, plain axis words, direct labels,
no overlapping colorbars. Pure rendering of frozen results into figs_explained/."""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report6_data import assemble

HERE = Path(__file__).resolve().parent
FIGS = HERE / 'figs_explained'
FIGS.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.edgecolor': '#e4eaf0', 'grid.color': '#e4eaf0', 'axes.grid': True,
                     'grid.linewidth': 0.7, 'font.family': 'DejaVu Sans'})
TEAL, NAVY, GRAY, RED, GOLD = '#0f7b6c', '#1f3864', '#8a8f98', '#b23a3a', '#b8860b'
YEARS = [5, 10, 15, 20, 30]
KEYS = [f'{y}y' for y in YEARS]


def _safe(cell):
    s = cell['search'].get('chosen_safe')
    return s * 100 if s is not None else np.nan


def fig_flow():
    """How the engine works, in four boxes."""
    fig, ax = plt.subplots(figsize=(10.2, 2.9))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3); ax.axis('off'); ax.grid(False)
    boxes = [
        ('The setup', '$100M to invest\n$250k paid out each month\n10% locked in property'),
        ('The engine\npicks a mix', 'how much in safe T-bills,\nhow much in stocks,\ngold and property'),
        ('Thousands of\nsimulated futures', 'market histories drawn\nunder two different\nmarket models'),
        ('The judge', 'a mix only counts if every\nrule holds: every payment\nmet, losses inside the caps'),
    ]
    w, h, y0 = 2.15, 1.75, 0.65
    xs = [0.15, 2.75, 5.35, 7.95]
    for (title, body), x in zip(boxes, xs):
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle='round,pad=0.08',
                                    facecolor='#f2f6f9', edgecolor='#c9d4de', lw=1.2))
        ax.text(x + w / 2, y0 + h - 0.32, title, ha='center', va='center',
                fontsize=10.5, fontweight='bold', color='#1f3864')
        ax.text(x + w / 2, y0 + 0.62, body, ha='center', va='center',
                fontsize=8.6, color='#1c2733')
    for x in (xs[0] + w + 0.09, xs[1] + w + 0.09, xs[2] + w + 0.09):
        ax.add_patch(FancyArrowPatch((x, y0 + h / 2), (x + 0.36, y0 + h / 2),
                                     arrowstyle='-|>', mutation_scale=16, color='#0f7b6c', lw=2))
    ax.text(5.0, 0.18, 'The answer: the safest mix that passes the judge, and what it is expected to leave behind.',
            ha='center', fontsize=9.5, style='italic', color='#5b6b7a')
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_x_flow.png', dpi=170)
    plt.close(fig)


def fig_horizon(d):
    """Takeaway 1: horizon dominates. Two clean lines, direct labels."""
    h5 = d['h5']
    fig, ax = plt.subplots(figsize=(10.2, 4.2))
    for view, lab, col in (('fitted', 'using shrunk history', TEAL),
                           ('current_quotes', "using today's T-bill yields", NAVY)):
        ys = [_safe(h5[view][k]) for k in KEYS]
        ax.plot(YEARS, ys, 'o-', color=col, lw=2.2, ms=6)
        for x, y in zip(YEARS, ys):
            ax.annotate(f'{y:.0f}%', (x, y), textcoords='offset points', xytext=(0, 8),
                        ha='center', fontsize=9, color=col)
        ax.annotate(lab, (YEARS[-1], ys[-1]), textcoords='offset points', xytext=(8, -4),
                    fontsize=10, color=col, fontweight='bold', va='center')
    ax.set_xticks(YEARS)
    ax.set_xlim(3.5, 33.5)
    ax.set_ylim(0, 80)
    ax.set_xlabel('How long the money must last (years)')
    ax.set_ylabel('Minimum share in T-bills\nthe judge requires (%)')
    ax.set_title('The longer the money must last, the more of it must sit in T-bills\n'
                 '(same $250k/month, same loss limits; two views of what T-bills pay)', fontsize=11.5)
    fig.tight_layout()
    fig.savefig(FIGS / 'fig_x_horizon.png', dpi=170)
    plt.close(fig)


def fig_terminal(d):
    """Takeaway 2: horizon x terminal limit heatmap, colorbar below, no overlap."""
    h5, sl, t25 = d['h5'], d['sl'], d['t25']
    losses = [0.05, 0.15, 0.25, 0.35, 0.50]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), sharey=True)
    im = None
    for ax, view, lab in ((axes[0], 'fitted', 'using shrunk history'),
                          (axes[1], 'current_quotes', "using today's yields")):
        grid = np.full((len(losses), len(YEARS)), np.nan)
        for i, L in enumerate(losses):
            for j, k in enumerate(KEYS):
                cell = h5[view][k] if L == 0.15 else (
                    t25[view][k] if L == 0.25 else sl[view].get(f'{k}_t{L:.2f}'))
                if cell:
                    grid[i, j] = _safe(cell)
        im = ax.imshow(grid, cmap='viridis_r', vmin=0, vmax=90, aspect='auto')
        ax.set_xticks(range(len(YEARS)), [f'{y}y' for y in YEARS])
        ax.set_yticks(range(len(losses)), [f'{int(L*100)}%' for L in losses])
        ax.set_xlabel('How long the money must last')
        ax.set_title(lab, fontsize=11)
        ax.grid(False)
        for i in range(len(losses)):
            for j in range(len(YEARS)):
                if not np.isnan(grid[i, j]):
                    ax.text(j, i, f'{grid[i, j]:.0f}', ha='center', va='center', fontsize=9.5,
                            color='white' if grid[i, j] > 45 else 'black')
    axes[0].set_ylabel('Allowed end-of-plan loss')
    axes[1].tick_params(axis='y', left=False, labelleft=False)
    fig.suptitle('Minimum T-bill share the judge requires (%), by horizon and end-of-plan loss limit\n'
                 'darker = more in T-bills = safer but lower expected leftover', fontsize=11.5, y=0.99)
    fig.tight_layout(rect=(0, 0.13, 1, 0.93))
    cb = fig.colorbar(im, ax=axes, orientation='horizontal', fraction=0.045, pad=0.16, shrink=0.55)
    cb.set_label('share in T-bills (%)', fontsize=9.5)
    fig.savefig(FIGS / 'fig_x_terminal.png', dpi=170)
    plt.close(fig)


def fig_policy(d):
    """Takeaway 3: execution policy bars, plain labels, values on bars."""
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
                 '(same starting mix, same simulated futures; bars above a line break that limit)', fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(FIGS / 'fig_x_policy.png', dpi=170)
    plt.close(fig)


def fig_seeds(d):
    """Takeaway 6: the noise band. Shaded min-max across three independent
    families of simulated futures at the 25% end-of-plan limit."""
    t25, ss = d['t25'], d['ss']
    t25f = json.loads((HERE / 'results' / 'final5_horizon_t25.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), sharey=True)
    for ax, view, lab in ((axes[0], 'fitted', 'using shrunk history'),
                          (axes[1], 'current_quotes', "using today's yields")):
        fams = np.array([
            [_safe(t25[view][k]) for k in KEYS],
            [_safe(t25f[view][k]) for k in KEYS],
            [_safe(ss[view][f'{k}_t0.25']) for k in KEYS],
        ])
        lo, hi = np.nanmin(fams, axis=0), np.nanmax(fams, axis=0)
        mid = np.nanmedian(fams, axis=0)
        ax.fill_between(YEARS, lo, hi, color=TEAL if view == 'fitted' else NAVY, alpha=0.22)
        ax.plot(YEARS, mid, 'o-', color=TEAL if view == 'fitted' else NAVY, lw=2, ms=5.5,
                label='middle answer')
        for j, (x, a, b) in enumerate(zip(YEARS, lo, hi)):
            ax.annotate(f'{a:.0f}-{b:.0f}', (x, b), textcoords='offset points',
                        xytext=(6 if j == 0 else 0, 7), ha='left' if j == 0 else 'center',
                        fontsize=8.6, color='#5b6b7a')
        ax.set_xticks(YEARS)
        ax.set_xlim(4, 31)
        ax.set_xlabel('How long the money must last (years)')
        ax.set_title(lab, fontsize=11)
        ax.set_ylim(0, 95)
    axes[0].set_ylabel('Minimum share in T-bills (%)')
    fig.suptitle('The same question on three independent sets of simulated futures:\n'
                 'the answer is a band, not a number (25% end-of-plan limit shown)', fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(FIGS / 'fig_x_seeds.png', dpi=170)
    plt.close(fig)


def main():
    d = assemble()
    fig_flow()
    fig_horizon(d)
    fig_terminal(d)
    fig_policy(d)
    fig_seeds(d)
    print('figures written to', FIGS)


if __name__ == '__main__':
    main()
