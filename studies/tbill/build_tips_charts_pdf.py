"""Chart pack PDF (Tijs, WhatsApp 8 Nov 2026 10:17): the new model - TIPS added,
10y horizon, 40% any-point cap, 15% terminal loss limit - in five charts plus
extras. One chart per page, plain-language description and takeaway per page.
Pure rendering of study_tips_charts.json; no simulations here.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Image, Table, TableStyle, PageBreak)

ROOT = Path('studies/tbill')
R = json.loads((ROOT / 'results/study_tips_charts.json').read_text())
FIGS = ROOT / 'figs_tips'
FIGS.mkdir(exist_ok=True)
OUT = ROOT / 'ballast-new-model-charts-20261108.pdf'

NAVY = '#0d1b2e'; TEAL = '#0e7c6b'; AMBER = '#b26a00'; GRAY = '#5b6b7a'
RED = '#b00020'; LINE = '#c9d4de'; PANEL = '#f2f6f9'
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white',
                     'axes.edgecolor': LINE, 'grid.color': '#e4eaf0', 'axes.grid': True,
                     'grid.linewidth': 0.7, 'font.family': 'DejaVu Sans'})

M = lambda x: x / 1e6


def savefig(fig, name):
    fig.savefig(FIGS / name, dpi=190, bbox_inches='tight')
    plt.close(fig)


NAMES = {'us_equity': 'US stocks (VTI)', 'em_equity': 'Emerging stocks (VWO)',
         'gold': 'Gold (GLD)', 'treasury': '7-10yr Treasuries (IEF)', 'tips': 'TIPS (TIP)',
         'tbill': 'T-bills', 'cash': 'Cash (0%)', 'sg_property': 'SG property'}
COLORS = {'us_equity': NAVY, 'em_equity': '#33506e', 'gold': AMBER, 'treasury': TEAL,
          'tips': '#5ab4a5', 'tbill': '#8fb8de', 'cash': '#d3dae2', 'sg_property': GRAY}

# ---- fig 1: the new portfolio ----
b = R['base']
w = b['weights']
order = [k for k in ['tbill', 'treasury', 'us_equity', 'gold', 'sg_property', 'tips', 'em_equity', 'cash']
         if w.get(k, 0) > 0.0005]
fig, ax = plt.subplots(figsize=(8.6, 3.4))
y = np.arange(len(order))[::-1]
ax.barh(y, [w[k] * 100 for k in order], color=[COLORS[k] for k in order], height=0.62)
for yi, k in zip(y, order):
    ax.text(w[k] * 100 + 0.5, yi, f"{w[k]*100:.1f}%", va='center', fontsize=11, color=NAVY)
ax.set_yticks(y, [NAMES[k] for k in order])
ax.set_xlim(0, 44)
ax.set_xlabel('Share of the $100M')
ax.set_title('The validated portfolio under the new model (TIPS added, 10 years, 40% any-point cap)',
             fontsize=12, color=NAVY, loc='left')
savefig(fig, 'f1_portfolio.png')

# ---- fig 2: utility models ----
u = R['utilities']
kinds = ['cara', 'crra_gross', 'hara_payment_floor', 'kinked_shortfall']
labels = ['CARA\n(constant abs.)', 'CRRA\n(constant rel.)', 'HARA\n(payment floor)', 'Kinked\nshortfall']
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
x = np.arange(4)
axes[0].bar(x, [u[k]['chosen_safe'] * 100 for k in kinds], color=TEAL, width=0.58)
for xi, k in zip(x, kinds):
    axes[0].text(xi, u[k]['chosen_safe'] * 100 + 0.8, f"{u[k]['chosen_safe']*100:.1f}%",
                 ha='center', fontsize=11, color=NAVY)
axes[0].set_xticks(x, labels, fontsize=9.5)
axes[0].set_ylabel('T-bill share chosen (%)')
axes[0].set_ylim(0, 50)
axes[0].set_title('What each utility picks', fontsize=11.5, color=NAVY, loc='left')
ces = [M(u[k]['common_cara_ledger_ce']) for k in kinds]
axes[1].bar(x, ces, color=NAVY, width=0.58)
for xi, v in zip(x, ces):
    axes[1].text(xi, v + 0.04, f"${v:.1f}M", ha='center', fontsize=11, color=NAVY)
axes[1].set_xticks(x, labels, fontsize=9.5)
axes[1].set_ylabel('Score (certainty equivalent, $M/yr)')
axes[1].set_ylim(109.5, 111.3)
axes[1].set_title('What each outcome scores (zoomed axis)', fontsize=11.5, color=NAVY, loc='left')
savefig(fig, 'f2_utilities.png')

# ---- fig 3: rebalancing frequency ----
rb = R['rebalancing']
freqs = ['never (buy & hold)', 'every 12 months', 'every 6 months', 'every 3 months', 'every month']
flab = ['Never', 'Yearly', '6 months', '3 months', 'Monthly']
fig, ax = plt.subplots(figsize=(8.6, 3.6))
x = np.arange(5)
ces = [M(rb[f]['common_cara_ledger_ce']) for f in freqs]
bars = ax.bar(x, ces, color=[GRAY] + [TEAL] * 4, width=0.58)
for xi, v, f in zip(x, ces, freqs):
    ax.text(xi, v + 0.03, f"${v:.2f}M", ha='center', fontsize=10.5, color=NAVY)
ax.set_xticks(x, flab)
ax.set_ylim(110.3, 111.7)
ax.set_ylabel('Score ($M/yr, zoomed axis)')
ax2 = ax.twinx()
ax2.spines['right'].set_visible(True)
q05 = [M(rb[f]['terminal_q05']) for f in freqs]
ax2.plot(x, q05, 'o--', color=AMBER, label='5% bad-case leftover')
for xi, v in zip(x, q05):
    ax2.annotate(f"${v:.1f}M", (xi, v), textcoords='offset points', xytext=(0, -16),
                 fontsize=9, color=AMBER, ha='center')
ax2.set_ylim(88, 112)
ax2.set_ylabel('5% bad-case leftover ($M)', color=AMBER)
ax2.tick_params(axis='y', colors=AMBER)
ax2.grid(False)
ax.set_title('Rebalancing frequency: all pass every safety check; the gain is small',
             fontsize=12, color=NAVY, loc='left')
savefig(fig, 'f3_rebalancing.png')

# ---- fig 4: horizons ----
hz = R['horizon']
years = [5, 10, 15, 20, 30]
safe = [hz[f'{y}y']['chosen_safe'] * 100 for y in years]
med = [M(hz[f'{y}y']['terminal_median']) for y in years]
q05h = [M(hz[f'{y}y']['terminal_q05']) for y in years]
fig, ax = plt.subplots(figsize=(8.6, 3.6))
x = np.arange(5)
ax.bar(x, safe, color=NAVY, width=0.54)
for xi, v in zip(x, safe):
    ax.text(xi, v + 1, f'{v:.0f}%', ha='center', fontsize=11, color=NAVY)
ax.set_xticks(x, [f'{y} years' for y in years])
ax.set_ylabel('T-bill share the checks require (%)')
ax.set_ylim(0, 60)
ax2 = ax.twinx()
ax2.spines['right'].set_visible(True)
ax2.plot(x, med, 'o-', color=TEAL, label='median leftover')
ax2.plot(x, q05h, 's--', color=AMBER, label='5% bad case')
for xi, v in zip(x, med):
    ax2.annotate(f"${v:.0f}M", (xi, v), textcoords='offset points', xytext=(0, 8),
                 fontsize=9, color=TEAL, ha='center')
ax2.set_ylabel('Leftover after all payments ($M)')
ax2.set_ylim(0, 460)
ax2.legend(loc='upper left', frameon=False, fontsize=9)
ax.set_title('Horizon: what changes from 5 to 30 years (15% loss limit at the end of each horizon)',
             fontsize=12, color=NAVY, loc='left')
savefig(fig, 'f4_horizon.png')

# ---- fig 5: in-period (any-point) cap sweep ----
sw = R['cml_sweep']
caps = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
safes = [sw[f'{c:.2f}']['chosen_safe'] * 100 for c in caps]
ces5 = [M(sw[f'{c:.2f}']['common_cara_ledger_ce']) for c in caps]
fig, ax = plt.subplots(figsize=(8.6, 3.6))
ax.plot([c * 100 for c in caps], safes, 'o-', color=NAVY, lw=2, label='T-bill share required')
for c, s in zip(caps, safes):
    ax.annotate(f'{s:.0f}%', (c * 100, s), textcoords='offset points', xytext=(0, 8),
                fontsize=9.5, color=NAVY, ha='center')
ax.axvspan(15, 50, color=PANEL, zorder=0)
ax.text(32, 78, 'from 15% up, the any-point cap no longer decides -\nthe 15% year-10 loss limit does (flat 37.5% bills)',
        fontsize=9.5, color=GRAY, ha='center')
ax.set_xlabel('Any-point (in-period) loss limit (%)')
ax.set_ylabel('T-bill share required (%)')
ax.set_ylim(0, 100)
ax2 = ax.twinx()
ax2.spines['right'].set_visible(True)
ax2.plot([c * 100 for c in caps], ces5, 's--', color=TEAL, label='Score')
ax2.set_ylabel('Score ($M/yr)', color=TEAL)
ax2.tick_params(axis='y', colors=TEAL)
ax2.set_ylim(90, 116)
ax2.grid(False)
ax.set_title('Loosening the any-point loss limit (year-10 limit held at 15%)', fontsize=12,
             color=NAVY, loc='left')
savefig(fig, 'f5_cml.png')

# ---- fig 6: benchmarks ----
bm = R['benchmarks']
blabels = {'clever (validated mix)': 'Clever\n(this engine)', 'all T-bills + property': 'All T-bills\n+ property',
           '60/40-style (60% stocks, 30% bills)': '60/40\nclassic', 'equal weight (1/N)': 'Equal\nweight',
           'reserve payouts, rest risky': 'Reserve payouts,\nrest risky'}
order6 = ['clever (validated mix)', 'all T-bills + property', 'reserve payouts, rest risky',
          'equal weight (1/N)', '60/40-style (60% stocks, 30% bills)']
fig, ax = plt.subplots(figsize=(8.6, 3.7))
x = np.arange(5)
ces6 = [M(bm[k]['common_cara_ledger_ce']) for k in order6]
cols = []
for k in order6:
    v = bm[k]
    cols.append(TEAL if (v['validation_pass'] and v['final_pass']) else (AMBER if v['final_pass'] else RED))
ax.bar(x, ces6, color=cols, width=0.58)
for xi, v, k in zip(x, ces6, order6):
    ax.text(xi, v + 0.5, f"${v:.1f}M", ha='center', fontsize=10.5, color=NAVY)
    verdict = bm[k]
    tag = 'passes both checks' if verdict['validation_pass'] and verdict['final_pass'] else (
        'fails selection check' if not verdict['validation_pass'] else 'fails final check')
    ax.text(xi, 4, tag, ha='center', fontsize=8.3, color='white', rotation=90, va='bottom')
ax.set_xticks(x, [blabels[k] for k in order6], fontsize=9.5)
ax.set_ylabel('Score ($M/yr)')
ax.set_ylim(0, 125)
ax.set_title('Clever vs simple: same futures, same safety checks', fontsize=12, color=NAVY, loc='left')
savefig(fig, 'f6_benchmarks.png')

# ---- fig 7: payout sensitivity ----
py = R['payout']
levels = ['50k', '100k', '250k']
fig, ax = plt.subplots(figsize=(8.6, 3.4))
x = np.arange(3)
ces7 = [M(py[k]['common_cara_ledger_ce']) for k in levels]
ax.bar(x, ces7, color=TEAL, width=0.5)
for xi, v, k in zip(x, ces7, levels):
    ax.text(xi, v + 1, f"${v:.1f}M", ha='center', fontsize=11, color=NAVY)
ax.set_xticks(x, ['$50k/month', '$100k/month', '$250k/month'])
ax.set_ylabel('Score ($M/yr)')
ax.set_ylim(0, 160)
ax.set_title('Payout size: identical portfolio (37.5% T-bills); only the score moves',
             fontsize=12, color=NAVY, loc='left')
savefig(fig, 'f7_payout.png')

# ---------------- PDF ----------------
NS = dict(fontName='Helvetica', fontSize=9.2, leading=12.4, textColor=HexColor('#1c2733'))
def st(name, **kw):
    base = dict(NS); base.update(kw)
    return ParagraphStyle(name, **base)
S = dict(
    title=st('t', fontName='Helvetica-Bold', fontSize=19, leading=23, textColor=HexColor(NAVY)),
    sub=st('s', fontSize=9.6, textColor=HexColor(GRAY), leading=12.8),
    h=st('h', fontName='Helvetica-Bold', fontSize=13.5, leading=16, textColor=HexColor(NAVY)),
    body=st('b'),
    small=st('sm', fontSize=7.8, leading=10, textColor=HexColor(GRAY)),
    take=st('k', fontSize=9.6, leading=12.8, textColor=HexColor(NAVY)),
)

def png_size(path):
    import struct
    with open(path, 'rb') as f:
        head = f.read(26)
    w, h = struct.unpack('>II', head[16:24])
    return w, h


def chart_page(title, desc, img, takeaway, note=None):
    pw, ph = png_size(FIGS / img)
    width = 182 * mm
    height = width * ph / pw
    el = [Paragraph(title, S['h']), Spacer(1, 3), Paragraph(desc, S['body']), Spacer(1, 6),
          Image(str(FIGS / img), width=width, height=height), Spacer(1, 6)]
    tt = Table([[Paragraph('<b>Takeaway:</b> ' + takeaway, S['take'])]], colWidths=[182 * mm])
    tt.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#eef6f4')),
                            ('BOX', (0, 0), (-1, -1), 0.8, HexColor(TEAL)),
                            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                            ('LEFTPADDING', (0, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-1, -1), 9)]))
    el.append(tt)
    if note:
        el += [Spacer(1, 5), Paragraph(note, S['small'])]
    el.append(PageBreak())
    return el

story = []
story += [Spacer(1, 30),
          Paragraph('The new model, in six charts', S['title']),
          Spacer(1, 6),
          Paragraph('Ballast engine - private research, 8 Nov 2026. New model: TIPS added (the only new asset), '
                    '10-year horizon, 40% any-point loss limit, 15% loss limit at the end of the horizon, '
                    '$250k/month for 120 months (a labeled assumption beyond the confirmed year), $100M, '
                    'Singapore property fixed at 10%. Every portfolio below passed the frozen selection check '
                    '(800 fresh paths) and the independent final check (1,600 separate fresh paths).',
                    S['sub']),
          Spacer(1, 16)]

bw = R['base']['weights']
tbl = [['T-bills', '7-10yr Treas.', 'US stocks', 'Gold', 'SG property', 'TIPS'],
       [f"{bw['tbill']*100:.1f}%", f"{bw['treasury']*100:.1f}%", f"{bw['us_equity']*100:.1f}%",
        f"{bw['gold']*100:.1f}%", f"{bw['sg_property']*100:.0f}%", f"{bw['tips']*100:.1f}%"]]
t = Table(tbl, colWidths=[30 * mm] * 6)
t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), HexColor(NAVY)),
                       ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
                       ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                       ('FONTSIZE', (0, 0), (-1, -1), 10), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                       ('TEXTCOLOR', (0, 1), (-1, 1), HexColor(TEAL)),
                       ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
stats = [['Score (CE)', 'Expected return', 'Median leftover', '5% bad case', 'Payments funded'],
         ['$110.8M/yr', '~5.5%/yr', '$133.9M', '$94.9M', '120/120 on all 1,600 paths']]
t2 = Table(stats, colWidths=[36 * mm] * 5)
t2.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), HexColor(PANEL)),
                        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor(GRAY)),
                        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('TEXTCOLOR', (0, 1), (-1, 1), HexColor(NAVY)),
                        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.4, HexColor(LINE))]))
story += [t, Spacer(1, 8), t2, Spacer(1, 14),
          Paragraph('What changed vs the version without TIPS: T-bills drop from 42.5% to 37.5% of wealth, '
                    'TIPS takes 3.2% (the optimizer asked for it on its own), and the score rises from '
                    '$109.1M to $110.8M a year. TIPS earns its place: inflation-linked government bonds were '
                    'the one exposure the universe lacked.', S['body']),
          Spacer(1, 8),
          Paragraph('Reading the pack: each page is one question, one chart, one takeaway. Axes that start '
                    'above zero are marked "zoomed". Nothing here is a client calibration; all of it is the '
                    'placeholder $100M case.', S['small']),
          PageBreak()]

story += chart_page(
    '1. Do the utility models disagree? (CARA, CRRA, HARA, shortfall)',
    'Four standard ways to score "a good outcome" were each given the steering wheel: each utility first '
    'sets its own risky-sleeve mix through the one-year optimizer, then the same safety checks pick the '
    'T-bill share. CARA (steady absolute caution), CRRA (steady relative caution), HARA (caution anchored '
    'on keeping the payments safe) and the kinked shortfall rule (hates missing payments, relaxed above '
    'them) all land within 2.5 points of each other: 37.5-40% T-bills, near-identical risky mixes, and '
    'scores within $0.6M a year.',
    'f2_utilities.png',
    'Under your loss limits, the choice of utility barely matters - the limits, not the utility, drive the '
    'portfolio. That is reassuring: the answer does not depend on an unmeasurable taste parameter.',
    'Honesty notes: scores are certainty equivalents on 1,600 shared final paths under the common CARA '
    'ledger convention, so they are comparable across rows. Each utility\'s native score (not shown) is not '
    'comparable across families. Kinked shortfall puts more into TIPS (7.9% of wealth) than the others - '
    'its only visible taste difference.')

story += chart_page(
    '2. Does rebalancing frequency matter?',
    'The validated mix was replayed over the same 1,600 ten-year futures, rebalanced back to target never, '
    'yearly, every 6 months, every 3 months, and monthly. Payments are always funded T-bills-first; '
    'rebalancing trades pay the same liquidation haircuts as everything else. Every frequency passes every '
    'safety check. The score rises with frequency but by at most $0.5M a year (monthly vs never), and the '
    'bad-case leftover improves by about $1M.',
    'f3_rebalancing.png',
    'Rebalance once a year and stop thinking about it. Monthly rebalancing adds nothing meaningful - it '
    'trades $119M over the decade for $0.05M a year over yearly.',
    'Honesty notes: custom rebalancing ledger, built for this study and labeled - the engine\'s older '
    'frequency machinery only supports four risky sleeves and this universe now has six. Buys are '
    'cost-free (sells pay haircuts); no taxes modeled. Earlier one-year research found the same ordering '
    '(annual first, small gap), so this is now confirmed at ten years with TIPS in the mix.')

story += chart_page(
    '3. What does the investment horizon change? (5 / 10 / 15 / 20 / 30 years)',
    'Same engine, same monthly $250k, same limits - only the clock changes. Per your instruction, the 15% '
    'loss limit sits at the END of each horizon (year 5, 10, 15, 20 or 30), not fixed at year 10. Two '
    'forces fight it out: early on, the any-point dip limit is loose enough that a bold mix passes '
    '(5 years: only 10% T-bills needed); through the middle horizons the end-of-horizon loss limit bites '
    'hardest (10-15 years: 37-43% T-bills); past about 20 years the limits are measured against today\'s '
    'wealth, and two decades of compounding means even a crash rarely ends 15% below the start - the limit '
    'mechanically loses its teeth (20 years: 10% T-bills passes). At 30 years the $90M of total payments '
    're-tightens the screws through the per-payment funding checks (45% T-bills).',
    'f4_horizon.png',
    'The 10-15 year zone is where your limits bind hardest. And a flag worth knowing: "loss vs where you '
    'started" stops meaning much past ~20 years - if you want a limit that keeps biting at long horizons, '
    'it should be measured from the peak (or from the expected path), not from the start.',
    'Honesty notes: exact T-bill shares at 15-30 years ride on a deliberately conservative tail bound '
    '(4 batches, Bonferroni); the direction of each effect is solid, the exact percentages carry Monte '
    'Carlo uncertainty. Nominal dollars throughout - 30 years of inflation is not in these numbers. '
    'Payouts of $250k/month are confirmed for one year only; longer schedules are a labeled assumption.')

story += chart_page(
    '4. What does the any-point (in-period) loss limit change?',
    'Holding the year-10 loss limit at 15%, the any-point dip limit was swept from 5% to 50%. At 5% the '
    'portfolio must hold 82.5% T-bills and the score drops to $94.4M. At 10%: 57.5% bills, $105.7M. From '
    '15% upward the curve goes flat at 37.5% bills and $110.8M - the any-point limit stops deciding and '
    'the year-10 limit takes over. Your current 40% setting is effectively "no extra dip constraint": '
    'loosening or tightening it anywhere between 15% and 50% changes nothing.',
    'f5_cml.png',
    'The dial that matters now is the 15% year-10 loss limit, not the 40% any-point cap. Relaxing the '
    'year-10 limit to 40% would drop T-bills to 10% and lift the score to $114.7M - at the price of a '
    'real chance of ending the decade well below where you started.',
    'Honesty notes: same 800 selection paths and 1,600 final paths for every point, so the differences '
    'are the limits, not luck. The flat segment is exact: one constraint strictly dominates there.')

story += chart_page(
    '5. Clever vs simple: is the optimizer worth it?',
    'Five strategies on identical futures through identical safety checks. The validated mix passes both '
    'the selection check and the independent final check, scoring $110.8M. Parking everything in T-bills '
    'also passes - but gives up $21.7M a year of score. The three simple aggressive rules all break: '
    '60/40 fails both checks (its dips are too deep for your limits); equal weight and '
    '"reserve the payouts, invest the rest" fail the selection check - and notice the trap: the reserve '
    'rule scores HIGHER ($112.2M) on the final paths. It scores higher precisely because it skipped the '
    'check that would have stopped it.',
    'f6_benchmarks.png',
    'The clever part is not the return - it is passing your own limits reliably. Simple rules either '
    'fail the checks or leave $20M+ a year on the table. A score without the safety check is not '
    'comparable: the reserve rule\'s higher number is what rule-breaking buys.',
    'Honesty notes: "60/40-style" = 60% US stocks, 30% T-bills, 10% property. Equal weight splits the '
    'free 90% across all six listed sleeves. Reserve = 10 years of payments ($30M) in T-bills, the rest '
    'at the optimizer\'s risky proportions. All judged by the same frozen discipline as the validated mix.')

story += chart_page(
    '6. Extra: does the payout size change the answer?',
    'From the science report\'s payout work, re-run under the new model at ten years. At $50k, $100k and '
    '$250k a month the validated portfolio is identical (37.5% T-bills): the safety checks scale with the '
    'payment, so the same mix passes at every level. Only the score moves - less paid out means more '
    'left compounding in bills and bonds.',
    'f7_payout.png',
    'The portfolio does not need to change with the payout in this range. What changes is only how much '
    'wealth compounds. (Below ~$200k/month the engine\'s fixed model-miss buffer and the per-payment '
    'allowance collide and it declines to run - the scaled-buffer sensitivity from the 4th edition is '
    'used here, labeled, nothing loosened.)',
    None)

story += [Paragraph('What the science report already answers (so nothing is double-counted)', S['h']),
          Spacer(1, 3),
          Paragraph('Reviewed the 3rd and 4th editions for anything important not yet charted under the '
                    'new model. Already covered there, still valid: market-model adequacy and tail '
                    'calibration vs real history (sections 3, 16), the forecast-model contest (4), the '
                    '19-year historical backtest (6), model-miss sensitivity (8), month-by-month trading '
                    'vs a fixed plan (9), why the safe pile was cash and what T-bills fixed (11, 21), '
                    'what wrong return views do (14), and "passed does not mean paid" (15). Re-run under '
                    'this exact new model in this pack: utilities (chart 1 = old section 7), rebalancing '
                    '(chart 2 = section 10), horizons (chart 3 = section 23, now with 5/15y and your '
                    'moving loss limit), loss limits (chart 4 = section 22), benchmarking (chart 5 = '
                    'section 5), payouts (chart 6 = section 13). The one report finding worth repeating: '
                    'the model\'s simulated tails match the worst real weeks well (section 3) - the '
                    'checks above are strict, not naive.', S['body']),
          Spacer(1, 8),
          Paragraph('Method: mix search over the T-bill share (2.5% steps, risky sleeve frozen at the '
                    'one-year optimizer\'s proportions), 4x200 selection paths, 4x400 independent final '
                    'paths with one-step-safer walk-back, cash-first payout ledger, certainty-equivalent '
                    'score under the common CARA convention, nominal dollars, fitted 1.8% average bill '
                    'yield (today\'s ~4% would lift every number). Code and results: private fork, branch '
                    'tips-model-10y, studies/tbill/study_tips_charts.py. Private research only; no client '
                    'calibration; nothing shared.', S['small'])]

doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                      topMargin=13 * mm, bottomMargin=12 * mm,
                      title='The new model, in six charts')
doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(doc.leftMargin, doc.bottomMargin,
                                                         doc.width, doc.height, id='f')])])
doc.build(story)
print('PDF built', OUT, OUT.stat().st_size)
