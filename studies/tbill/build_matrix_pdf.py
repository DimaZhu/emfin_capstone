"""Build the loss-limit matrix addendum PDF (10-year horizon), Ballast theme."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, Image)

ROOT = Path('studies/tbill')
D = json.loads((ROOT / 'results/study_matrix.json').read_text())
CELLS = D['cells']
CML = [6, 8, 10, 15, 20, 30]
LOSS = [15, 20, 25, 30, 40]

NAVY = HexColor('#0d1b2e')
TEAL = HexColor('#4fe3c1')
INK = HexColor('#1c2733')
GRAY = HexColor('#5b6b7a')
LINE = HexColor('#c9d4de')
PANEL = HexColor('#f2f6f9')

PAGE_W, PAGE_H = A4
M = 16 * mm

S = {
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=9.3, leading=13.2,
                           textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5),
    'h1': ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=13, leading=16,
                         textColor=NAVY, spaceBefore=10, spaceAfter=5, keepWithNext=1),
    'bullet': ParagraphStyle('bullet', fontName='Helvetica', fontSize=9.3, leading=13.2,
                             textColor=INK, alignment=TA_JUSTIFY, leftIndent=10,
                             bulletIndent=2, spaceAfter=3),
    'note': ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=8.2, leading=11,
                           textColor=GRAY, spaceBefore=4, spaceAfter=4),
    'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=8.2, leading=10.5, textColor=INK),
    'cellb': ParagraphStyle('cellb', fontName='Helvetica-Bold', fontSize=8.2, leading=10.5, textColor=NAVY),
    'kicker': ParagraphStyle('kicker', fontName='Helvetica', fontSize=9.5, leading=13,
                             textColor=GRAY, spaceAfter=6),
    'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=21, leading=25,
                            textColor=NAVY, spaceAfter=6),
    'subtitle': ParagraphStyle('subtitle', fontName='Helvetica', fontSize=11, leading=15,
                               textColor=INK, spaceAfter=10),
}


def cell(cml, loss):
    return CELLS[f'cml{cml}_loss{loss}']


def make_figure(path):
    ce = np.array([[cell(r, c)['common_cara_ledger_ce'] / 1e6 for c in LOSS] for r in CML])
    safe = np.array([[cell(r, c)['chosen_safe'] for c in LOSS] for r in CML])
    fig, ax = plt.subplots(figsize=(7.3, 4.1), dpi=200)
    cmap = LinearSegmentedColormap.from_list('ballast', ['#eaf4fb', '#9cc3e5', '#2f6da3', '#0d1b2e'])
    ax.imshow(ce, cmap=cmap, aspect='auto', vmin=ce.min() - 2, vmax=ce.max() + 2)
    for i in range(len(CML)):
        for j in range(len(LOSS)):
            light = ce[i, j] < (ce.min() + ce.max()) / 2
            color = '#0d1b2e' if light else 'white'
            ax.text(j, i - 0.13, f'${ce[i, j]:.1f}M', ha='center', va='center',
                    fontsize=10.5, fontweight='bold', color=color)
            ax.text(j, i + 0.20, f'{safe[i, j] * 100:.0f}% T-bills', ha='center', va='center',
                    fontsize=8, color=color)
    ax.set_xticks(range(len(LOSS)), [f'{c}%' for c in LOSS], fontsize=9)
    ax.set_yticks(range(len(CML)), [f'{r}%' for r in CML], fontsize=9)
    ax.set_xlabel('Worst allowed loss at the 10-year mark (loosening ->)', fontsize=9)
    ax.set_ylabel('Any-point loss cap along the way', fontsize=9)
    ax.set_title('Best 10-year certainty equivalent that does not break the limits\n'
                 '(score in \\$M over 10 years, after \\$30M of payouts; safe share below)',
                 fontsize=10.5, color='#0d1b2e', pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-.5, len(LOSS)), minor=True)
    ax.set_yticks(np.arange(-.5, len(CML)), minor=True)
    ax.grid(which='minor', color='white', linewidth=2.5)
    ax.tick_params(which='both', length=0)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def footer(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, 0, PAGE_W, 12 * mm, stroke=0, fill=1)
    canv.setFillColor(TEAL)
    canv.setFont('Helvetica', 7.5)
    canv.drawString(M, 4.6 * mm, 'Ballast funding-risk engine - loss-limit matrix addendum - 8 November 2026')
    canv.drawRightString(PAGE_W - M, 4.6 * mm, 'Private research, not investment advice')
    canv.restoreState()


def build(out_path, fig_path):
    doc = BaseDocTemplate(str(out_path), pagesize=A4,
                          leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=16 * mm)
    frame = Frame(M, 16 * mm, PAGE_W - 2 * M, PAGE_H - 16 * mm - M, id='main')
    doc.addPageTemplates([PageTemplate(id='p', frames=[frame], onPage=footer)])

    story = []
    story.append(Paragraph('BALLAST ENGINE - ADDENDUM', S['kicker']))
    story.append(Paragraph('How much do the two loss limits cost over 10 years?', S['title']))
    story.append(Paragraph(
        'You asked for a matrix of the two loss budgets at a 10-year horizon, loosening both from '
        'their current strictest values, with the best portfolio that stays inside each pair of limits. '
        'Labeled sensitivity: only the 1-year, $250k/month case is confirmed; 10 years x $250k/month '
        '($30M total) is exploratory.', S['subtitle']))

    story.append(Paragraph('The headline in one line', S['h1']))
    story.append(Paragraph(
        'At 10 years, only the any-point drawdown cap matters. The year-10 loss cap '
        'never binds anywhere in the 15-40% band: after a decade of growth, even a '
        '90%-risky mix ends below the starting $100M in at most an 8% tail bound, far inside every '
        'column. So every row of the matrix is one number, and the column choice is free within this '
        'range. Loosening the drawdown cap from 6% to 30% lifts the 10-year certainty equivalent '
        'from $97.0M to $112.7M (+$15.7M) and cuts T-bills from 78% to 20% of the portfolio.', S['body']))
    story.append(Spacer(1, 4))
    story.append(Image(str(fig_path), width=PAGE_W - 2 * M, height=(PAGE_W - 2 * M) * 4.1 / 7.3))
    story.append(Paragraph(
        'Each cell is the best-scoring mix on fresh validation paths, then re-checked on independent '
        'final paths. Score = CARA certainty equivalent of 10-year leftover wealth plus payout cover, '
        'same ledger convention as the unified report; it is a 10-year score, not comparable to the '
        'one-year CE figures. Every cell passes the strict all-payments check (funded on every final '
        'path, zero missed payments).', S['note']))

    story.append(Paragraph('What each loosening buys you', S['h1']))
    headers = ['Any-point cap', 'T-bills', 'VTI', 'Gold', 'IEF', 'Property',
               'Expected return', 'Score (CE)', 'Median left', '5% bad case']
    rows = []
    for r in CML:
        c = cell(r, 15)
        w = c['weights']
        rows.append([
            f'{r}% (current)' if r == 6 else f'{r}%',
            f"{w['US Treasury bills (3-month roll)'] * 100:.0f}%",
            f"{w['US equity'] * 100:.1f}%",
            f"{w['Gold'] * 100:.1f}%",
            f"{w['US Treasuries'] * 100:.1f}%",
            f"{w['Singapore URA All Residential'] * 100:.0f}%",
            f"{c['expected_annual_return'] * 100:.1f}%/yr",
            f"${c['common_cara_ledger_ce'] / 1e6:.1f}M",
            f"${c['terminal_median'] / 1e6:.0f}M",
            f"${c['terminal_q05'] / 1e6:.0f}M",
        ])
    tbl = Table([headers] + rows, colWidths=[21 * mm, 15 * mm, 13 * mm, 13 * mm, 13 * mm, 16 * mm,
                                             22 * mm, 19 * mm, 19 * mm, 19 * mm])
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.8),
        ('TEXTCOLOR', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 1), (0, -1), NAVY),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, NAVY),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [PANEL, HexColor('#ffffff')]),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    story.append(tbl)
    story.append(Paragraph(
        'Rows are identical across the 15-40% year-10 loss columns, so one row per any-point cap. '
        'Median left / 5% bad case: leftover after all $30M of payouts, on the independent final paths. '
        'Expected return: model-fitted annual portfolio return. All rows: every payment funded on every '
        'final path; independent final check passed with zero walk-back.', S['note']))

    story.append(Paragraph('How to read this', S['h1']))
    for b in [
        'The drawdown cap is your real risk dial. It alone sets the safe share: 6% forces 78% T-bills; '
        '30% allows 20%. The year-10 loss cap only starts to bind below roughly 8% (the tail bound of the most aggressive mix), outside the range tested.',
        'Payments are safe everywhere in this matrix: $250k/month is about 3% of wealth per year, and '
        'every mix funds every payment on every simulated path. This matrix is purely about how much '
        'short-term pain you accept along the way.',
        'The trade is concrete: accepting a possible 30% dip instead of 6% adds about $15.7M of '
        '10-year score, raises the median leftover from $101M to $147M, and even the 5% bad case '
        'improves from $86M to $97M. The cost is living through the deeper dips.',
    ]:
        story.append(Paragraph(b, S['bullet'], bulletText='-'))

    story.append(Paragraph('Method and limits', S['h1']))
    for b in [
        'Mix search, not full optimization: the engine optimizer is priced for one year, so each cell '
        'searches safe shares from 10% to 90% in 2.5% steps. The risky sleeve keeps the one-year '
        'optimizer proportions (VTI : gold : Treasuries = 26 : 24 : 50, no EM) and property stays '
        'fixed at 10%. A true 10-year optimizer might find slightly better mixes inside each cell.',
        'Frozen validation discipline: selection on 4 x 200 fresh validation paths, then an independent '
        'final check on 4 x 400 disjoint paths. All 30 cells passed the final check with no step-back. '
        'The binding check at every frontier is the any-point path-loss tail, exactly as in the 1-year case.',
        'Same model caveats as the 4th edition, amplified by horizon: weekly iid mixture law fitted to '
        'history (volatility clustering grows more relevant over 10 years), nominal dollars (no inflation '
        'indexation), T-bill yield fitted at its 2005-2026 average of 1.8% (today\'s ~4% would lift every '
        'cell), and a fixed 10% illiquid property sleeve. Monte Carlo diagnostics, not economic guarantees.',
    ]:
        story.append(Paragraph(b, S['bullet'], bulletText='-'))
    story.append(Paragraph(
        'Source: studies/tbill/study_matrix.py, results/study_matrix.json on branch tbill-asset '
        '(private fork). Draws shared across all cells (same seeds), so differences between cells are '
        'purely the limits, not simulation noise.', S['note']))

    doc.build(story)


if __name__ == '__main__':
    fig = ROOT / 'figs' / 'fig_matrix.png'
    make_figure(fig)
    out = ROOT / 'ballast-loss-limit-matrix-10y-20261108.pdf'
    build(out, fig)
    print('wrote', out)
