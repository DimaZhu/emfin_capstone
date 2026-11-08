"""Generate the charts for the 4th-edition report (Ballast theme)."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

NAVY = '#0d1b2e'; TEAL = '#4fe3c1'; GRAY = '#5b6b7a'; RED = '#c0392b'
HERE = Path(__file__).resolve().parent
FIG = HERE / 'figs'
FIG.mkdir(exist_ok=True)
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': '#c9d4de',
    'axes.linewidth': 0.8, 'axes.titlesize': 10, 'axes.titleweight': 'bold',
    'axes.titlecolor': NAVY, 'axes.labelcolor': '#1c2733', 'xtick.color': GRAY,
    'ytick.color': GRAY, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'axes.grid': True, 'grid.color': '#e6edf2', 'grid.linewidth': 0.7,
    'axes.axisbelow': True, 'legend.frameon': False,
})

res = json.load(open(HERE / 'results' / 'study_tbill.json'))['results']
cr = json.load(open(HERE / 'results' / 'current_rate_sensitivity.json'))


def m(x):
    return x / 1e6


# --- fig 1: allocation before/after -----------------------------------------
labels = ['US\nequity', 'EM\nequity', 'Gold', 'US\nTreasuries', 'Cash /\nmoney mkt', 'T-bills\n(3M roll)', 'SG\nresidential']
base = res['control_baseline']['selected']['weights']  # 6 assets
base7 = list(base[:4]) + [base[4], 0.0, base[5]]
tb = res['tbill_anchor']['selected']['weights']        # 7 assets
tb7 = [tb[0], tb[1], tb[2], tb[3], tb[5], tb[4], tb[6]]
x = np.arange(7); w = 0.38
fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=170)
ax.bar(x - w/2, [v*100 for v in base7], w, color='#8fa6b8', label='Baseline (3rd ed.): cash earns 0%')
ax.bar(x + w/2, [v*100 for v in tb7], w, color=NAVY, label='With T-bills (4th ed.): bills earn a real yield')
for xi, v in zip(x - w/2, base7):
    if v > 0.005: ax.text(xi, v*100 + 1, f'{v*100:.0f}', ha='center', fontsize=7.5, color=GRAY)
for xi, v in zip(x + w/2, tb7):
    if v > 0.005: ax.text(xi, v*100 + 1, f'{v*100:.0f}', ha='center', fontsize=7.5, color=NAVY)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
ax.set_ylabel('Portfolio weight (%)'); ax.set_ylim(0, 95)
ax.set_title('Validated portfolio, before and after the T-bill asset ($250k/month)')
ax.legend(fontsize=8, loc='upper left')
fig.tight_layout(); fig.savefig(FIG / 'fig_alloc.png'); plt.close(fig)

# --- fig 2: score vs payout --------------------------------------------------
pays = [50, 100, 125, 250]
b = [m(res[f'payout{p}000_baseline']['selected']['common_cara_ledger_ce']) for p in pays]
t = [m(res[f'payout{p}000_tbill']['selected']['common_cara_ledger_ce']) for p in pays]
fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=170)
ax.plot(pays, b, 'o-', color='#8fa6b8', lw=1.8, label='Baseline (3rd ed.)')
ax.plot(pays, t, 'o-', color=NAVY, lw=1.8, label='With T-bills (4th ed.)')
for px, yb, yt in zip(pays, b, t):
    ax.annotate(f'+{yt-yb:.1f}', (px, (yb+yt)/2), textcoords='offset points',
                xytext=(8, 0), fontsize=8, color=TEAL if False else '#1d8a70', fontweight='bold')
ax.set_xlabel('Monthly payment (thousand $)'); ax.set_ylabel('Score (certainty equivalent, $M)')
ax.set_title('Portfolio score by monthly payment level')
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / 'fig_payout.png'); plt.close(fig)

# --- fig 3: long-horizon terminal wealth ------------------------------------
mixes = ['anchor(90% safe)', 'step70', 'step50', 'step30']
mix_names = ['90% safe', '70% safe', '50% safe', '30% safe']
h10 = [m(r['terminal_median']) for r in res['horizon10y_tbill']['rows']]
h20 = [m(r['terminal_median']) for r in res['horizon20y_tbill']['rows']]
h30 = [m(r['terminal_median']) for r in res['horizon30y_tbill']['rows']]
pass10 = [r['final_pass'] for r in res['horizon10y_tbill']['rows']]
pass20 = [r['final_pass'] for r in res['horizon20y_tbill']['rows']]
pass30 = [r['final_pass'] for r in res['horizon30y_tbill']['rows']]
x = np.arange(4); w = 0.26
fig, ax = plt.subplots(figsize=(7.2, 3.1), dpi=170)
for off, vals, passes, lab, col in [(-w, h10, pass10, '10 years', '#8fa6b8'),
                                    (0, h20, pass20, '20 years', '#456a86'),
                                    (w, h30, pass30, '30 years', NAVY)]:
    ax.bar(x + off, vals, w, color=col, label=lab)
    for xi, v, p in zip(x + off, vals, passes):
        mark = '' if p else '  x'
        ax.text(xi, v + 6, f'{v:.0f}{mark}', ha='center', fontsize=7, color=(GRAY if p else RED))
ax.set_xticks(x); ax.set_xticklabels(mix_names)
ax.set_ylabel('Median wealth at horizon end ($M)')
ax.set_title('Median wealth at horizon end, by mix (x = fails the one-year loss limits)')
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / 'fig_horizon.png'); plt.close(fig)

# --- fig 4: T-bill history ----------------------------------------------------
import csv
rows = []
DATA = HERE.parents[1] / 'emfin_v2' / 'resources' / 'data' / 'actual_etfs'
with open(DATA / [p.name for p in DATA.glob('tbill-*.csv')][0]) as f:
    for r in csv.DictReader(f):
        rows.append((r['date'], float(r['total_return_index'])))
rows = [r for r in rows if r[0] >= '2005-01-01']
wealth = np.array([x for _, x in rows]) / rows[0][1]
dates = np.arange(len(rows)) / 52.0
fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=170)
ax.plot(dates, wealth, color=NAVY, lw=1.6)
ax.set_xlabel('Years since start of 2005'); ax.set_ylabel('Growth of $1')
ax.set_title('Three-month Treasury bills, weekly roll, 2005-2026 (constructed from FRED DGS3MO)')
ax.annotate('2009-2021: rates near zero,\nbills earn almost nothing', xy=(7, wealth[7*52]), xytext=(2.2, 1.45),
            fontsize=8, color=GRAY, arrowprops=dict(arrowstyle='-', color=GRAY, lw=0.8))
ax.annotate('2022-2026: rates back to 4-5%,\nthe flat line bends up again', xy=(20.5, 1.43), xytext=(12.5, 1.30),
            fontsize=8, color=GRAY, arrowprops=dict(arrowstyle='-', color=GRAY, lw=0.8))
fig.tight_layout(); fig.savefig(FIG / 'fig_tbill_history.png'); plt.close(fig)

# --- fig 5: cumulative-loss cap sweep ----------------------------------------
caps = ['3%', '6% (current)', '10%']
base_ce = [np.nan, m(res['cmlcap6_baseline']['selected']['common_cara_ledger_ce']),
           m(res['cmlcap10_baseline']['selected']['common_cara_ledger_ce'])]
tb_ce = [np.nan, m(res['cmlcap6_tbill']['selected']['common_cara_ledger_ce']),
         m(res['cmlcap10_tbill']['selected']['common_cara_ledger_ce'])]
fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=170)
x = np.arange(3); w = 0.36
ax.bar(x - w/2, base_ce, w, color='#8fa6b8', label='Baseline (cash)')
ax.bar(x + w/2, tb_ce, w, color=NAVY, label='With T-bills')
ax.text(0, 96.8, 'engine refuses:\nnothing passes', ha='center', fontsize=8, color=RED)
for xi, v in zip(x - w/2, base_ce):
    if not np.isnan(v): ax.text(xi, v + 0.15, f'{v:.2f}', ha='center', fontsize=8, color=GRAY)
for xi, v in zip(x + w/2, tb_ce):
    if not np.isnan(v): ax.text(xi, v + 0.15, f'{v:.2f}', ha='center', fontsize=8, color=NAVY)
ax.text(2 + w/2, tb_ce[2] + 0.62, 'not certified: mix fails\nthe final held-out judge', ha='center', fontsize=7.5, color=RED)
ax.set_xticks(x); ax.set_xticklabels(caps)
ax.set_ylabel('Score ($M)'); ax.set_ylim(95.5, 103)
ax.set_title('What happens if the any-point loss limit moves (labeled sensitivity)')
ax.legend(fontsize=8, loc='upper left')
fig.tight_layout(); fig.savefig(FIG / 'fig_caps.png'); plt.close(fig)

print('figures written:', sorted(p.name for p in FIG.glob('*.png')))
