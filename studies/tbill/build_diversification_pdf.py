"""One-page diversification addendum PDF (Ballast theme), 8 Nov 2026."""
from pathlib import Path
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle)

ROOT = Path('studies/tbill')
R = json.loads((ROOT / 'results/study_diversification.json').read_text())

NAVY = HexColor('#0d1b2e'); TEAL = HexColor('#0e7c6b'); INK = HexColor('#1c2733')
GRAY = HexColor('#5b6b7a'); LINE = HexColor('#c9d4de'); PANEL = HexColor('#f2f6f9')
WARN = HexColor('#8a5a00')
PAGE_W, PAGE_H = A4

def st(name, **kw):
    base = dict(fontName='Helvetica', fontSize=8.2, leading=10.6, textColor=INK)
    base.update(kw)
    return ParagraphStyle(name, **base)

S = dict(
    title=st('t', fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=NAVY),
    sub=st('s', fontSize=8.6, textColor=GRAY, leading=11),
    h=st('h', fontName='Helvetica-Bold', fontSize=9.6, leading=12, textColor=NAVY, spaceBefore=5),
    body=st('b'),
    small=st('sm', fontSize=7.4, leading=9.4, textColor=GRAY),
    warn=st('w', fontSize=7.8, leading=10, textColor=WARN),
)

def c(x): return f"${x/1e6:.1f}M"

rows = [
    ('control', 'control', None),
    ('managed_futures', 'Managed futures (DBMF)', 'control_w2019'),
    ('tips', 'TIPS (TIP)', 'control'),
    ('commodities', 'Broad commodities (DBC)', 'control_w2006'),
    ('agg_bond', 'US aggregate bonds (AGG)', 'control'),
    ('long_treasury', '20+yr Treasuries (TLT)', 'control'),
    ('reits', 'US REITs (VNQ)', 'control'),
]
tbl = [['Asset added', 'Fit window', '1y opt. sleeve share', '6% cap: bills, CE (delta)', '40% cap: bills, CE (delta)']]
for key, label, ctrl in rows:
    d = R[key]
    if key == 'control':
        tbl.append(['Nothing (current universe)', '2005-2026', '-',
                    f"{d['cells']['cml6']['chosen_safe']*100:.0f}%, {c(d['cells']['cml6']['common_cara_ledger_ce'])}",
                    f"{d['cells']['cml40']['chosen_safe']*100:.0f}%, {c(d['cells']['cml40']['common_cara_ledger_ce'])}"])
        continue
    cd = R[ctrl]
    sleeve = d['sleeve_proportions_1y_optimizer'].get(key, 0)
    sleeve_txt = f"{sleeve*100:.0f}%" + (' (tilt)' if d['exploratory_tilt'] else '')
    win = {'managed_futures': '2019-2026 *', 'commodities': '2006-2026'}.get(key, '2005-2026')
    cells = []
    for cap in ('cml6', 'cml40'):
        a, b = d['cells'][cap], cd['cells'][cap]
        delta = (a['common_cara_ledger_ce'] - b['common_cara_ledger_ce']) / 1e6
        cells.append(f"{a['chosen_safe']*100:.0f}%, {c(a['common_cara_ledger_ce'])} ({delta:+.1f})")
    tbl.append([label, win, sleeve_txt] + cells)

t = Table(tbl, colWidths=[44*mm, 20*mm, 24*mm, 47*mm, 47*mm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), NAVY), ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 7.8),
    ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), PANEL]),
    ('GRID', (0, 0), (-1, -1), 0.4, LINE), ('TOPPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('LEFTPADDING', (0, 0), (-1, -1), 4),
]))

story = [
    Paragraph('Which asset adds the most diversification?', S['title']),
    Paragraph('Ballast engine addendum - 8 Nov 2026 - private research, T-bill registry, $100M, '
              '$250k/month x120 (labeled beyond the confirmed year), 10-year horizon, property fixed 10%. '
              'Each row: the candidate added to the current universe, sleeve share from the frozen 1-year optimizer '
              '("tilt" = exploratory 10% sleeve allocation where the optimizer declined it), then the validated 10-year '
              'mix at the 6% cap (current) and the 40% cap (owner default, 8 Nov). CE = certainty equivalent per year. '
              'Deltas are vs the control on the SAME fit window.', S['sub']),
    Spacer(1, 4), t,
    Paragraph('* Managed futures only has history from May 2019, so its whole universe is fitted on 2019-2026 - no 2008, '
              'no 2011, no 2013. That window is calm for stocks and strong for trend-following (2022), which flatters every '
              'number on its row; its deltas are honest (vs the same-window control) but the window is not.', S['warn']),
    Spacer(1, 2),
    Paragraph('Reading the answer', S['h']),
    Paragraph('<b>1. Managed futures (DBMF/KMLM type) is the strongest addition the data supports.</b> Near-zero or negative '
              'correlation to the current mix, including in the worst equity weeks (-0.33 for KMLM overall), the largest '
              'diversification-metric gains (effective bets 4.2 -> 5.1), and the biggest CE gains at both caps. Caveat above '
              'is the reason to size it carefully, not to skip it: 7.5 years of ETF history is thin. A longer index series '
              '(e.g. SG Trend) is the follow-up.', S['body']),
    Paragraph('<b>2. TIPS (TIP) is the robust runner-up.</b> Full 2005-2026 history, picked by the optimizer on its own '
              '(6% of the sleeve), helps at both caps, and adds the one exposure the universe lacks: inflation-linked '
              'government bonds. Screening: correlation 0.52 to the mix, effective bets 4.2 -> 4.6.', S['body']),
    Paragraph('<b>3. Commodities and aggregate bonds are marginal.</b> Both need a forced tilt; commodities help only at the '
              'strict cap (2022-driven), aggregate bonds overlap with the IEF sleeve (corr 0.74). Long Treasuries only pay at '
              'the loose cap; REITs subtract at the loose cap. Rejected at screening: developed ex-US equity (VEA) and '
              'low-vol (USMV) - too correlated to add anything; SCHP/PDBC/KMLM duplicates with shorter history.', S['body']),
    Paragraph('The portfolio under the new defaults (10y, 40% cap)', S['h']),
    Paragraph('Validated mix: <b>42.5% T-bills, 22.5% US equity, 14.4% 7-10yr Treasuries, 10.7% gold, 10% property</b> - '
              'CE $109.1M/yr, median leftover $140M, 5% bad case $93M, expected return 5.9%/yr, every payment funded on every '
              'final path, independent check passes. Finding: at the 40% cap the 15% year-10 loss limit now BINDS - relaxed to '
              '40% it would allow 12.5% bills (CE higher, 5% bad case lower). The binding constraint has flipped from the '
              'any-point dip to the end-of-decade outcome.', S['body']),
    Paragraph('Method and honesty notes: mix search over T-bill share (2.5% steps, risky sleeve frozen at 1y-optimizer '
              'proportions), 4x200 fresh validation paths, 4x400 independent final paths, one-step-safer walk-back; nominal '
              'dollars; fitted 1.8% average bill yield (today\'s ~4% would lift every row); not a full 10-year cvxpy '
              'optimization; screening measures: correlation in worst-5% equity weeks, Meucci effective number of bets, '
              'Choueifaty-Coignard diversification ratio. Code/results: branch owner-defaults-10y-cml40, '
              'studies/tbill/study_diversification.py.', S['small']),
]

doc = BaseDocTemplate(str(ROOT / 'ballast-diversification-20261108.pdf'), pagesize=A4,
                      leftMargin=14*mm, rightMargin=14*mm, topMargin=12*mm, bottomMargin=10*mm,
                      title='Which asset adds the most diversification?')
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')
doc.addPageTemplates([PageTemplate(id='p', frames=[frame])])
doc.build(story)
print('PDF built')
