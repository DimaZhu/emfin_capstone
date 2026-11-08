"""One-PDF report for the open-points fixes (owner ask 8 Nov 2026 11:05):
what changed per fix, whether each fix moved the chosen portfolio, and the
constraint sensitivity (point 6). Pure rendering of studies/fixes/results/*.json;
no simulations here.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Image, Table, TableStyle, PageBreak)

RES = Path('studies/fixes/results')
FIGS = Path('studies/fixes/figs_report')
FIGS.mkdir(exist_ok=True)
OUT = Path('studies/fixes/open-points-fixes-report-20261108.pdf')

F1 = json.loads((RES / 'fix1_market_model.json').read_text())
F2 = json.loads((RES / 'fix2_radius.json').read_text())
F3 = json.loads((RES / 'fix3_real_terms.json').read_text())
F4 = json.loads((RES / 'fix4_longhorizon.json').read_text())
F5 = json.loads((RES / 'fix5_current_rates.json').read_text())
F6 = json.loads((RES / 'fix6_grid.json').read_text())
BASE = json.loads(Path('studies/tbill/results/study_tips_charts.json').read_text())['base']

NAVY = '#0d1b2e'; TEAL = '#0e7c6b'; AMBER = '#b26a00'; GRAY = '#5b6b7a'
RED = '#b00020'; LINE = '#c9d4de'; PANEL = '#f2f6f9'
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.edgecolor': LINE, 'grid.color': '#e4eaf0', 'axes.grid': True,
                     'grid.linewidth': 0.7, 'font.family': 'DejaVu Sans'})

H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=19, leading=23, textColor=HexColor(NAVY))
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=13.5, leading=17, textColor=HexColor(NAVY),
                    spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle('body', fontName='Helvetica', fontSize=10.3, leading=14.2,
                      textColor=HexColor('#1c2b3a'), spaceAfter=6)
SMALL = ParagraphStyle('small', parent=BODY, fontSize=8.6, leading=11.6, textColor=HexColor(GRAY))

NAMES = {'us_equity': 'US stocks', 'em_equity': 'EM stocks', 'gold': 'Gold',
         'treasury': '7-10yr Treasuries', 'tips': 'TIPS', 'tbill': 'T-bills',
         'cash': 'Cash', 'sg_property': 'SG property'}


def money(x):
    return f"${x/1e6:,.1f}M"


def mix_table(weights_list, row_labels):
    cols = ['Portfolio', 'T-bills', 'IEF 7-10y', 'US stocks', 'Gold', 'TIPS', 'SG prop.']
    keys = ('tbill', 'treasury', 'us_equity', 'gold', 'tips', 'sg_property')
    data = [cols]
    for lab, w in zip(row_labels, weights_list):
        data.append([lab] + [f"{100*w.get(k, 0):.1f}%" for k in keys])
    t = Table(data, colWidths=[56 * mm] + [20 * mm] * 6)
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8.6),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 8.6),
        ('BACKGROUND', (0, 0), (-1, 0), HexColor(PANEL)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), ['white', HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.4, HexColor(LINE)),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def savefig(fig, name):
    fig.savefig(FIGS / name, dpi=190, bbox_inches='tight')
    plt.close(fig)
    return str(FIGS / name)


# ---- chart 1: fix 6, upside given up vs terminal limit ----
cells = F6['cells']
cmls, losses = F6['meta']['cmls'], F6['meta']['losses']
loosest_ce = max(c['common_cara_ledger_ce'] for c in cells.values())
fig, ax = plt.subplots(figsize=(8.2, 3.3))
for cml, marker in [(0.15, 'o'), (0.4, 's'), (1.0, '^')]:
    ys = []
    for loss in losses:
        cell = cells.get(f'cml{cml:.2f}_loss{loss:.2f}')
        ys.append((loosest_ce - cell['common_cara_ledger_ce']) / 1e6 if cell else np.nan)
    ax.plot([100 * l for l in losses], ys, marker=marker,
            label=f"any-point cap {int(100*cml)}%" if cml != 1.0 else 'no any-point cap')
ax.axvline(15, color=GRAY, lw=1, ls='--')
ax.text(15.5, ax.get_ylim()[1] * 0.02 + 11.4, 'his 15% default', fontsize=9, color=GRAY)
ax.set_xlabel('Terminal loss limit (%)')
ax.set_ylabel('Certainty equivalent given up ($M/yr equiv.)')
ax.set_title('Point 6 sensitivity: what tighter limits cost (10y, $250k/month)')
ax.legend(frameon=False, fontsize=9.5)
fig6_chart = savefig(fig, 'fix6_grid.png')

# ---- chart 2: safe share + CE across fixes ----
rows = [
    ('Base (frozen)', BASE['weights']['tbill'], BASE['common_cara_ledger_ce']),
    ('1: FHS-EWMA, base sleeve', F1['fhs_ewma_frozen_sleeve']['weights']['tbill'],
     F1['fhs_ewma_frozen_sleeve']['common_cara_ledger_ce']),
    ('1: bounded EWMA, own sleeve', F1['bounded_ewma_mixture_own_sleeve']['weights']['tbill'],
     F1['bounded_ewma_mixture_own_sleeve']['common_cara_ledger_ce']),
    ('4: true 10y sleeve', F4['mix_10y_sleeve']['weights']['tbill'],
     F4['mix_10y_sleeve']['common_cara_ledger_ce']),
    ('5: current rates', F5['current_rates']['weights']['tbill'],
     F5['current_rates']['common_cara_ledger_ce']),
]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.1))
y = np.arange(len(rows))[::-1]
a1.barh(y, [100 * r[1] for r in rows], color=TEAL, height=0.6)
a1.set_yticks(y, [r[0] for r in rows], fontsize=9)
a1.set_xlabel('T-bill share (%)')
a1.set_title('Did the answer move? Safe share')
for yi, r in zip(y, rows):
    a1.text(100 * r[1] + 1, yi, f"{100*r[1]:.1f}%", va='center', fontsize=9, color=NAVY)
a1.set_xlim(0, 75)
a2.barh(y, [r[2] / 1e6 for r in rows], color=NAVY, height=0.6)
a2.set_yticks(y, [''] * len(rows))
a2.set_xlabel('Certainty equivalent ($M)')
a2.set_title('Certainty equivalent')
for yi, r in zip(y, rows):
    a2.text(r[2] / 1e6 + 1, yi, f"{r[2]/1e6:.0f}", va='center', fontsize=9, color=NAVY)
a2.set_xlim(0, 150)
fig.tight_layout()
moves_chart = savefig(fig, 'moves.png')

# ---------------- document ----------------
doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=17 * mm, rightMargin=17 * mm,
                      topMargin=15 * mm, bottomMargin=14 * mm, title='Open points 1-6: fixes')
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')


def footer(canv, doc_):
    canv.saveState()
    canv.setFont('Helvetica', 7.5)
    canv.setFillColor(HexColor(GRAY))
    canv.drawString(17 * mm, 8 * mm, 'Open points 1-6 fixes - private research, not investment advice - 8 Nov 2026')
    canv.drawRightString(A4[0] - 17 * mm, 8 * mm, f'page {doc_.page}')
    canv.restoreState()


doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=footer)])

story = []
story.append(Paragraph('Open points 1-6: what the fixes changed', H1))
story.append(Spacer(1, 4))
story.append(Paragraph(
    'Six open points from the model review, worked through on the frozen 10-year setup '
    '(T-bills + TIPS model, $250k/month for 120 months, 40% any-point loss cap, 15% terminal loss '
    'limit). Every variant below is a labeled sensitivity run under the same validation discipline: '
    'the portfolio is picked on validation draws and re-judged on independent final draws, with a '
    'one-step-safer walk-back. Nothing here changes an engine default.', BODY))
story.append(Paragraph(
    f"The base answer before the fixes: <b>{100*BASE['weights']['tbill']:.1f}% T-bills</b>, "
    f"certainty equivalent <b>{money(BASE['common_cara_ledger_ce'])}</b>, all 120 payments funded.", BODY))
story.append(Spacer(1, 2))
story.append(Paragraph('The one-line answer per fix', H2))
CELL = ParagraphStyle('cell', parent=BODY, fontSize=8.2, leading=10.6, spaceAfter=0)
CELLH = ParagraphStyle('cellh', parent=CELL, fontName='Helvetica-Bold')
def P(x, h=False):
    return Paragraph(x, CELLH if h else CELL)
summary = Table([
    [P('Fix', 1), P('What was done', 1), P('Did the chosen portfolio move?', 1)],
    [P('1 market model too well-behaved'), P('Bootstrap/regime variants (FHS-EWMA, bounded EWMA mixture) fitted and judged'),
     P('Yes, both directions: 10% and 60% bills (from 37.5%)')],
    [P('2 model-miss radius uncalibrated'), P('Calibrated from refit instability + radius grid'),
     P('No portfolio change possible: any real radius breaks the budgets')],
    [P('3 everything nominal'), P('Full real-terms variant: CPI-deflated draws, indexed payouts, TIPS as the real safe asset'),
     P('No mix passes the 15% real limit at all - the nominal safety is partly an illusion')],
    [P('4 1y-proportion screens'), P('True 10-year optimization for the risky sleeve'),
     P('Yes: 17.5% bills, more IEF; CE +$1.9M')],
    [P('5 rerun at current rates'), P('Safe-asset carry at 5 Nov 2026 quotes (bill 4.17%, 10y 4.84%, TIPS real 2.60%)'),
     P('Yes: 30% bills, CE $123.1M (+$12.2M)')],
    [P('6 constraint tightness'), P('Sensitivity grid only, nothing changed'),
     P('n/a - grid below')],
], colWidths=[38 * mm, 76 * mm, 62 * mm])
summary.setStyle(TableStyle([
    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8.4),
    ('FONT', (0, 1), (-1, -1), 'Helvetica', 8.2),
    ('BACKGROUND', (0, 0), (-1, 0), HexColor(PANEL)),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), ['white', HexColor('#f8fafc')]),
    ('GRID', (0, 0), (-1, -1), 0.4, HexColor(LINE)),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
]))
story.append(summary)
story.append(Spacer(1, 8))
story.append(Image(moves_chart, width=176 * mm, height=63 * mm))
story.append(Paragraph(
    'Certainty equivalent (CE) is the sure yearly-dollar answer that scores the same as the risky '
    'plan after funding every payment - higher is better, and differences of $1-2M are small '
    'against the $110.8M base.', SMALL))
story.append(PageBreak())

# ---- fix 6 ----
story.append(Paragraph('Point 6 - the constraint sensitivity (nothing changed)', H2))
story.append(Paragraph(
    'How much upside tighter or looser limits give up, around the 40% any-point cap and 15% '
    'terminal loss limit defaults. Two clean results. First, at his 40% default the <b>any-point '
    'cap never binds</b>: cap 40% or no cap at all give the identical portfolio and certainty '
    'equivalent at every terminal limit in the grid. Second, the <b>terminal loss limit is the '
    'one with teeth</b>:', BODY))
story.append(Image(fig6_chart, width=172 * mm, height=69 * mm))
ref = F6['reference_cell'] if 'reference_cell' in F6 else None
story.append(Paragraph(
    'At his 15% default the plan gives up <b>$3.88M</b> against the loosest setting; at 10% it '
    'gives up $7.49M; at 5%, $11.69M. Loosening from 15% to 25% recovers the whole $3.88M; past '
    '25% there is nothing more to recover - the curve is flat. One nuance on the cap: at his 40% '
    'default it never binds, but a tight 15% cap starts to bind once the terminal limit is '
    'loosened to 25% or more (it holds the safe share at 37.5% where the plan would otherwise '
    'drop to 10% bills).', BODY))
story.append(PageBreak())

# ---- fix 1 ----
story.append(Paragraph('Fix 1 - a less well-behaved market model', H2))
story.append(Paragraph(
    'The fitted iid mixture is calm: squared-return autocorrelation about 0.00 against 0.32 in '
    'history, so it misses vol clustering. Two bootstrap/regime variants were fitted and run '
    'through the same pipeline: <b>FHS-EWMA</b> (filtered historical simulation, today\'s vol '
    'regime) and a <b>bounded EWMA mixture</b>.', BODY))
story.append(Paragraph(
    f"FHS-EWMA sees a calm current regime (equity vol 9.6% vs 18% fitted) and, on the frozen "
    f"base sleeve, the safe share <b>falls to {100*F1['fhs_ewma_frozen_sleeve']['weights']['tbill']:.0f}% bills</b> "
    f"(CE {money(F1['fhs_ewma_frozen_sleeve']['common_cara_ledger_ce'])}). "
    f"The bounded EWMA mixture pushes the other way once its own sleeve is re-solved: "
    f"<b>{100*F1['bounded_ewma_mixture_own_sleeve']['weights']['tbill']:.0f}% bills</b> "
    f"(CE {money(F1['bounded_ewma_mixture_own_sleeve']['common_cara_ledger_ce'])}). "
    'Every cross-judgment passes (each model\'s answer stays valid under the other\'s draws).', BODY))
story.append(Paragraph(
    'Honest caveat: the FHS-EWMA run as wired is a current-vol-regime law - its lower safe share '
    'is a regime statement ("vol is calm right now"), not just "the same world with fatter tails". '
    'The answer is genuinely model-dependent, which is the point of the open point: the mix moves '
    'by 27 points of bills either way depending on which law of motion is true.', BODY))
story.append(Paragraph('Fix 4 - true long-horizon optimization', H2))
story.append(Paragraph(
    'Instead of screening 1-year sleeve proportions onto 10 years, the risky sleeve was solved '
    'directly on the 10-year problem (n=100 in 8.6s, n=200 in 76s; n=400 is out of sandbox reach '
    'and labeled as such). The 10-year solve wants much more 7-10yr Treasuries in the sleeve '
    '(56% of risky vs 40% at 1y).', BODY))
story.append(mix_table(
    [BASE['weights'], F4['mix_10y_sleeve']['weights'], F5['current_rates']['weights']],
    ['Base: 1y sleeve, fitted means', 'Fix 4: true 10y sleeve', 'Fix 5: current rates']))
story.append(Spacer(1, 4))
story.append(Paragraph(
    f"Fix 4 moves the answer to <b>17.5% bills</b> and lifts the certainty equivalent to "
    f"<b>{money(F4['mix_10y_sleeve']['common_cara_ledger_ce'])}</b> (+$1.9M vs base) - the "
    '1-year screen was leaving a little on the table by under-using the bond fund.', BODY))
story.append(Paragraph('Fix 5 - current rates as a second default view', H2))
story.append(Paragraph(
    'The fitted window carries bills at 1.81%; the market quote on 5 Nov 2026 is 4.17% '
    '(10y 4.84%, 10y TIPS real 2.60%, FRED H.15). With safe-asset carry set to current quotes '
    '(vols, correlations and risky means unchanged - a labeled simplification), the answer moves '
    f"to <b>30% bills</b> and the certainty equivalent rises to <b>{money(F5['current_rates']['common_cara_ledger_ce'])}</b> "
    '(+$12.2M). TIPS drop to zero at a 2.6% real quote against 4.8% nominal on the 10y. '
    'This is a second default view worth adopting next to the fitted-means view.', BODY))
story.append(PageBreak())

# ---- fix 3 ----
story.append(Paragraph('Fix 3 - real terms: the uncomfortable one', H2))
story.append(Paragraph(
    'Everything was re-run in today\'s dollars: every scenario path deflated by a bootstrapped '
    'inflation path (US CPI 1947-2026, mean 3.5%/yr, 10-year regime spread 1.8%-6.5%), payouts '
    'inflation-indexed, TIPS modeled as the real safe asset at the live 2.60% real yield. Two '
    'modeling traps were caught on the way: treating TIPS as a nominal-quote override, and '
    'deflating TIPS by the simulated inflation path - both quietly turn TIPS back into nominal '
    'bonds exactly in the high-inflation states where they should protect.', BODY))
story.append(Paragraph(
    '<b>No static mix passes the 15% real terminal loss limit at 10 years.</b> Not the base '
    'sleeve, not a re-solved sleeve, not 90% TIPS (the most the fixed 10% property allows), at '
    'fitted means or at current rates. The reason is structural: 10-year inflation-regime '
    'uncertainty puts about ±20% of real dispersion into every nominal asset, and the only real '
    'asset (TIPS) still carries ~6% real-yield vol. Judged in real terms, today\'s base portfolio '
    f"is worth a certainty equivalent of <b>{money(F3['cross_base_on_real']['common_cara_ledger_ce'])}</b> "
    f"- against {money(BASE['common_cara_ledger_ce'])} nominal - and it breaches both real loss "
    'tails. In plain words: the 15% limit reads as protection in dollars-of-the-day, and a large '
    'part of that protection is an inflation illusion.', BODY))
fl = F3['real_feasible_limits']
story.append(Paragraph(
    f"What a real limit can be: scanning budgets with the judge unchanged, the tightest pair any "
    f"candidate passes is about <b>{100*fl['tightest']['anypoint_cap']:.0f}% any-point / "
    f"{100*fl['tightest']['terminal_limit']:.0f}% terminal</b> - for 90% TIPS + 10% property at "
    f"current rates, real CE {money(fl['common_cara_ledger_ce'])}. If a real limit is wanted, "
    'it has to be looser than the nominal one, or the horizon has to shorten.', BODY))
story.append(Paragraph('Fix 2 - the model-miss radius', H2))
ri = F2['refit_instability']
story.append(Paragraph(
    f"The buffer radius was calibrated from <b>refit instability</b> as asked: bootstrap refits of "
    f"the fitting window, distances between refit and base scenario sets in the declared path "
    f"geometry. Calibrated radius: <b>{ri['radius_q90']:.2f}</b> (q90; the existing past-empirical "
    f"52-week method gives {F2['past_empirical_52w'].get('radius', 0):.2f} on its own horizon). "
    f"The current manual radius is <b>2e-5</b> - four to five orders of magnitude smaller.", BODY))
story.append(Paragraph(
    'The radius grid shows why: the current 2e-5 already spends $40k of the $50k smallest '
    'per-payment budget on buffer alone. At 2.5e-5 the answer is unchanged (37.5% bills); at '
    '3e-5 every mix fails. A radius calibrated to how much the fitted model actually moves on '
    'refitting is unaffordable under the declared budgets by orders of magnitude. So the '
    'model-miss buffer is cosmetic by construction - making it real is a budget decision '
    '(looser limits or a different distance geometry), not a calibration decision.', BODY))
story.append(Paragraph('Caveats that apply to everything above', H2))
story.append(Paragraph(
    'Private research on owner-accepted Yahoo data; parametric scenarios, not a backtest. '
    'Inflation is bootstrapped independently of asset returns (labeled simplification). '
    'The judge\'s tail bounds are Monte Carlo diagnostics over 4 batches, not economic coverage. '
    'Current-quotes carry is a snapshot of 5 Nov 2026. No engine default was changed; every '
    'variant is a labeled study under studies/fixes/.', SMALL))

doc.build(story)
print('built', OUT)
