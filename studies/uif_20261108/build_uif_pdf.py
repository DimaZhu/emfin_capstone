"""UIF report PDF (owner ask 8 Nov 2026 17:09 SGT): one page per item -
1 estimation uncertainty, 3 inflation-linked payouts, 4 fees. Private
research, labeled sensitivities, no default changes. Numbers come only from
results/uif*.json.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

HERE = Path(__file__).resolve().parent
RES = HERE / 'results'
FIGS = HERE / 'figs'
FIGS.mkdir(exist_ok=True)
OUT = HERE / 'ballast-uncertainty-inflation-fees-20261108.pdf'
BLUE, ORANGE, GREY, GREEN = '#1f4e79', '#c55a11', '#7f7f7f', '#2e7d32'


def load(name):
    return json.loads((RES / name).read_text())


def fig_item1(d):
    views = [('fitted', 'Fitted means'), ('current_quotes', 'Current-quotes carry')]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    ax = axes[0]
    assets = ['us_equity', 'gold', 'treasury', 'tbill']
    labels = ['US equity', 'Gold', 'Treasury', 'T-bill']
    base = d['fitted']['seed20261109']['base_moments']['drift']
    cells = d['fitted']['seed20261109']['cells']
    data = [[100 * x['drift'][a] for x in cells] for a in assets]
    bp = ax.boxplot(data, vert=True, widths=0.55, patch_artist=True,
                    medianprops=dict(color=ORANGE, lw=2))
    for patch in bp['boxes']:
        patch.set_facecolor('#dbe7f3')
    for i, a in enumerate(assets):
        ax.plot(i + 1, 100 * base[a], 'D', color=BLUE, ms=7, zorder=3,
                label='Point estimate' if i == 0 else None)
    ax.set_xticks(range(1, 5), labels, fontsize=9)
    ax.set_ylabel('Fitted annual drift (%)')
    ax.set_title('What the drift could plausibly be\n(16 bootstrap refits, fitted view)', fontsize=10)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(axis='y', alpha=0.3)

    ax = axes[1]
    for i, (view, name) in enumerate(views):
        for seed, marker, lab in ((20261109, 'o', 'main seeds'), (20261111, '^', 'band seeds')):
            cells = d[view][f'seed{seed}']['cells']
            safes = [100 * x['chosen_safe'] for x in cells if x['chosen_safe'] is not None]
            jitter = np.linspace(-0.13, 0.13, len(safes))
            ax.scatter(np.full(len(safes), i) + jitter, safes, marker=marker,
                       color=BLUE if seed == 20261109 else GREY, s=42, alpha=0.85,
                       label=lab if i == 0 else None)
            if safes:
                ax.hlines(np.median(safes), i - 0.28, i + 0.28, color=ORANGE, lw=2)
    base_pts = {'fitted': 12.5, 'current_quotes': 10.0}
    for i, (view, name) in enumerate(views):
        ax.plot(i, base_pts[view], 'D', color=GREEN, ms=8, zorder=3,
                label='Reported point estimate' if i == 0 else None)
    ax.set_xticks(range(2), [n for _, n in views], fontsize=9)
    ax.set_ylabel('Validated safe (T-bill) share at 10y (%)')
    ax.set_title('Safe-share answer per refit\n(orange = median, green = reported)', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)

    ax = axes[2]
    cells = d['fitted']['seed20261109']['cells']
    fp = [x['frozen_final_pass'] for x in cells if x['frozen_final_pass'] is not None]
    cellsq = d['current_quotes']['seed20261109']['cells']
    fpq = [x['frozen_final_pass'] for x in cellsq if x['frozen_final_pass'] is not None]
    bars = [100 * np.mean(fp), 100 * np.mean(fpq)]
    ax.bar([0, 1], bars, color=[BLUE, GREY], width=0.5)
    for i, v in enumerate(bars):
        ax.text(i, v + 2, f'{v:.0f}%', ha='center', fontsize=11)
    ax.set_xticks([0, 1], ['Fitted', 'Current-quotes'], fontsize=9)
    ax.set_ylim(0, 115)
    ax.set_ylabel('% of refits where mix passes')
    ax.set_title('Frozen round-2 mix: share of plausible\nparameter worlds it survives', fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / 'item1.png', dpi=150)
    plt.close(fig)


def fig_item3(d):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    ax = axes[0]
    cases = []
    for view, vn in (('fitted', 'Fitted'), ('current_quotes', 'Quotes')):
        for years in (10, 20):
            nom = d[view][f'{years}y_nominal_s20261109']
            idx = d[view][f'{years}y_indexed_s20261109']
            cases.append((f'{vn} {years}y', 100 * nom['chosen_safe'], 100 * idx['chosen_safe']))
    x = np.arange(len(cases))
    ax.bar(x - 0.18, [c[1] for c in cases], 0.36, color=BLUE, label='Nominal $250k/mo (the rule)')
    ax.bar(x + 0.18, [c[2] for c in cases], 0.36, color=ORANGE, label='CPI-indexed payout')
    for i, c in enumerate(cases):
        ax.text(i - 0.18, c[1] + 1, f'{c[1]:.0f}', ha='center', fontsize=8)
        ax.text(i + 0.18, c[2] + 1, f'{c[2]:.0f}', ha='center', fontsize=8)
    ax.set_xticks(x, [c[0] for c in cases], fontsize=8)
    ax.set_ylabel('Validated safe share (%)')
    ax.set_title('Safe share: indexing payouts\nbarely moves the mix', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)

    ax = axes[1]
    for view, vn, color in (('fitted', 'Fitted', BLUE), ('current_quotes', 'Quotes', GREY)):
        for years in (10, 20):
            nom = d[view][f'{years}y_nominal_s20261109']['ce'] / 1e6
            idx = d[view][f'{years}y_indexed_s20261109']['ce'] / 1e6
            ax.plot([0, 1], [nom, idx], 'o-', color=color,
                    label=vn if years == 10 else None)
            ax.text(1.03, idx, f'{vn} {years}y: -${nom - idx:.0f}m', fontsize=8, color=color,
                    va='center')
    ax.set_xticks([0, 1], ['Nominal', 'CPI-indexed'], fontsize=9)
    ax.set_xlim(-0.4, 2.3)
    ax.set_ylabel('Certainty equivalent ($m)')
    ax.set_title('Cost of keeping pace with inflation\n(CARA CE of terminal wealth)', fontsize=10)
    ax.grid(alpha=0.3)

    ax = axes[2]
    months = np.arange(0, 241)
    idx_mean = np.exp(months * 0.00207)
    sd_band = 0.00357 * np.sqrt(np.maximum(months, 1))
    real = 250000 / idx_mean
    ax.plot(months / 12, real / 1000, color=BLUE, lw=2, label='Real value of fixed $250k')
    ax.fill_between(months[1:] / 12, 250000 / np.exp(months[1:] * 0.00207 + 1.645 * sd_band[1:]) / 1000,
                    250000 / np.exp(months[1:] * 0.00207 - 1.645 * sd_band[1:]) / 1000,
                    color=BLUE, alpha=0.15, label='90% CPI band')
    ax.axhline(250, color=ORANGE, lw=1.5, ls='--', label='CPI-indexed payout (real, constant)')
    ax.set_xlabel('Years')
    ax.set_ylabel('Monthly payout in today\'s dollars ($k)')
    ax.set_title('The real question behind item 3:\na nominal $250k erodes', fontsize=10)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / 'item3.png', dpi=150)
    plt.close(fig)


def fig_item4(d):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    tiers = ['trade0', 'trade10', 'trade25', 'trade10_aum25', 'trade10_aum50']
    tier_lab = ['none', '10bp', '25bp', '10bp+0.25%/yr', '10bp+0.50%/yr']
    pols = ['cash_first', 'annual_rebal', 'threshold_10', 'glide_annual']
    pol_lab = ['never', 'annual', 'threshold', 'glide']
    colors = plt.cm.Blues(np.linspace(0.35, 0.9, len(tiers)))

    ax = axes[0]
    cell = d['fitted']['10y_s20261109']['policies']
    x = np.arange(len(pols))
    for j, tier in enumerate(tiers):
        vals = [cell[f'{p}|{tier}']['total_fees_median'] / 1e6 for p in pols]
        ax.bar(x + (j - 2) * 0.16, vals, 0.15, color=colors[j], label=tier_lab[j])
    ax.set_xticks(x, pol_lab, fontsize=9)
    ax.set_ylabel('Fees paid over 10y ($m, median)')
    ax.set_title('What each policy costs in fees\n(10y, fitted, frozen mix)', fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(axis='y', alpha=0.3)

    ax = axes[1]
    for j, tier in enumerate(['trade0', 'trade10', 'trade25']):
        vals = [cell[f'{p}|{tier}']['terminal_ru'] for p in pols]
        ax.plot(x, vals, 'o-', color=colors[[0, 2, 4][j]], label=tier_lab[[0, 1, 2][j]])
    ax.axhline(0.15, color=ORANGE, ls='--', lw=1.2, label='15% terminal limit')
    ax.set_xticks(x, pol_lab, fontsize=9)
    ax.set_ylabel('Terminal-loss tail upper bound')
    ax.set_title('Trading fees and the loss tail:\nsmall moves, ranking holds', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[2]
    rows = []
    for view, vn in (('fitted', 'Fitted'), ('current_quotes', 'Quotes')):
        base = d[view]['10y_s20261109']  # noqa: F841
        for drag, key in ((0.0, None), (0.0025, '10y_search_drag0.0025'), (0.005, '10y_search_drag0.0050')):
            if key is None:
                safe = {'fitted': 0.125, 'current_quotes': 0.1}[view]
            else:
                safe = d[view][key]['chosen_safe']
            rows.append((vn, drag, 100 * safe))
    for i, (vn, drag, safe) in enumerate(rows):
        ax.bar(i, safe, 0.55, color=BLUE if vn == 'Fitted' else GREY)
        ax.text(i, safe + 1, f'{safe:.0f}%', ha='center', fontsize=9)
    ax.set_xticks(range(len(rows)),
                  [f'{vn}\n{drag * 100:.2f}%/yr' for vn, drag, _ in rows], fontsize=8)
    ax.set_ylabel('Validated safe share at 10y (%)')
    ax.set_title('Holding-fee drag on fitted means:\nthe fitted view is boundary-sensitive', fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / 'item4.png', dpi=150)
    plt.close(fig)


TEXT = {
    'item1': [
        "Item 1 - estimation uncertainty (bootstrap refits of drift and volatility, 26-week circular blocks,",
        "full 10-year dual-law safe-share search per refit, matched RNG streams).",
        "",
        "The reported 12.5% safe share (fitted view) is at the OPTIMISTIC EDGE of the plausible range:",
        "across 16 refits the validated safe share runs 10%-67.5% (median 46%); current-quotes 10%-52.5%",
        "(median 28%). Fitted US-equity drift ranges 3.4%-19.8%/yr around the 9.8% point estimate; vol is",
        "tighter (15.5%-20.8% around 18%). The frozen round-2 mix (32.5% safe) survives the final judge in",
        "12/16 refits under both views. Same order as the known seed noise (12.5% vs 52.5% across draw",
        "families): the point estimate should never be quoted without its band.",
    ],
    'item3': [
        "Item 3 - inflation-linked payouts (BLS CPI-U 1996-2025: mean 2.52%/yr; iid monthly model, declared).",
        "The nominal $250k/month stays the rule; this shows what an inflation-growing payout changes.",
        "",
        "Safe share barely moves (10y: 12.5% -> 12.5% fitted, 10% -> 10% quotes; 20y: 60% -> 60%, 45% -> 45%).",
        "Certainty equivalent carries the cost: -$4.4m at 10y, -$24m at 20y (quotes view) - inflation risk",
        "is paid in expected wealth, not a safer mix (-$22m at 20y fitted). Real value of the fixed $250k",
        "falls to ~$195k/mo by year 10 and ~$152k by year 20 (expected). Splitting the Treasury sleeve 50/50 into TIPS",
        "(exploratory) moved the 10y safe share from 12.5% to 15% - no free hedge under this model.",
    ],
    'item4': [
        "Item 4 - fees, no tax (trading fees 10/25bp per trade; holding fees 0.25/0.50%/yr on listed sleeves;",
        "on top of the existing 5-20bp sell haircuts; frozen mixes, policies never/annual/threshold/glide).",
        "",
        "Trading fees are second-order at these sizes: rebalancing the ~$60m liquid book annually costs a",
        "median ~$70k over 10y at 10bp, ~$180k at 25bp (medians; means are inflated by explosive paths).",
        "Holding fees matter more: 0.50%/yr on listed sleeves costs a median ~$5m over 10y and lifts the",
        "10y terminal tail by ~4pp for every policy. Policy rankings are unchanged in every tier - fees",
        "give no reason to trade less often. Holding-fee drag on fitted means moves the 10y safe share",
        "(12.5% -> 20% at 0.25%/yr, -> 30% at 0.50%/yr, fitted view only; quotes view unmoved at 10%)",
        "so treat as 'fees tighten an already touchy boundary', not a precise shift.",
    ],
}


def page(pdf, title, fig_path, lines):
    w, h = letter
    pdf.setFillColor(BLUE)
    pdf.setFont('Helvetica-Bold', 15)
    pdf.drawString(0.7 * inch, h - 0.75 * inch, title)
    pdf.setFillColor('black')
    pdf.setFont('Helvetica', 8.5)
    pdf.drawString(0.7 * inch, h - 0.95 * inch,
                   'Private research, not investment advice. Labeled sensitivity; no engine defaults change. 8 Nov 2026.')
    pdf.drawImage(str(fig_path), 0.45 * inch, h - 4.6 * inch, width=7.6 * inch, height=2.35 * inch,
                  preserveAspectRatio=False)
    y = h - 5.0 * inch
    pdf.setFont('Helvetica', 10)
    for line in lines:
        pdf.drawString(0.7 * inch, y, line)
        y -= 0.19 * inch
    pdf.showPage()


def main():
    d1, d3, d4 = load('uif1_estimation.json'), load('uif3_inflation.json'), load('uif4_fees.json')
    fig_item1(d1)
    fig_item3(d3)
    fig_item4(d4)
    pdf = canvas.Canvas(str(OUT), pagesize=letter)
    pdf.setTitle('Ballast - uncertainty, inflation, fees (8 Nov 2026)')
    page(pdf, 'Estimation uncertainty: the answer is a range', FIGS / 'item1.png', TEXT['item1'])
    page(pdf, 'Inflation-linked payouts: CE pays, mix holds', FIGS / 'item3.png', TEXT['item3'])
    page(pdf, 'Fees: cheap to rebalance, touchy boundary', FIGS / 'item4.png', TEXT['item4'])
    pdf.save()
    print(OUT)


if __name__ == '__main__':
    main()
