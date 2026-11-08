"""Render the 4th edition of the unified scientific report (Ballast theme).

Content lives in content_*.py as block lists:
  ('h1', '21. Title')            numbered section heading
  ('h2', 'Sub heading')          minor heading
  ('p', 'text')                  justified paragraph
  ('bullets', ['...', ...])      bullet list
  ('numbers', ['...', ...])      numbered list
  ('table', [headers], [rows])   small grid table (all strings)
  ('fig', 'file.png', 'caption') embedded chart
  ('note', 'text')               small gray note
  ('pagebreak',)
"""
from pathlib import Path
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, Image, PageBreak, KeepTogether)

NAVY = HexColor('#0d1b2e')
TEAL = HexColor('#4fe3c1')
INK = HexColor('#1c2733')
GRAY = HexColor('#5b6b7a')
LINE = HexColor('#c9d4de')
PANEL = HexColor('#f2f6f9')

FOOTER1 = 'Ballast funding-risk engine - unified scientific report - 8 November 2026, 4th ed.'
FOOTER2 = 'Private research, not investment advice'

PAGE_W, PAGE_H = A4
M = 16 * mm

S = {
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=9.3, leading=13.2,
                           textColor=INK, alignment=TA_JUSTIFY, spaceAfter=5),
    'h1': ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=14, leading=17,
                         textColor=NAVY, spaceBefore=14, spaceAfter=6, keepWithNext=1),
    'h2': ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=10.5, leading=14,
                         textColor=NAVY, spaceBefore=9, spaceAfter=4, keepWithNext=1),
    'bullet': ParagraphStyle('bullet', fontName='Helvetica', fontSize=9.3, leading=13.2,
                             textColor=INK, alignment=TA_JUSTIFY, leftIndent=12,
                             bulletIndent=2, spaceAfter=3),
    'note': ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=8.2, leading=11,
                           textColor=GRAY, alignment=TA_LEFT, spaceAfter=5),
    'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=8.2, leading=10.5, textColor=INK),
    'cellb': ParagraphStyle('cellb', fontName='Helvetica-Bold', fontSize=8.2, leading=10.5, textColor=NAVY),
    'caption': ParagraphStyle('caption', fontName='Helvetica-Oblique', fontSize=8.2, leading=10.5,
                              textColor=GRAY, alignment=TA_CENTER, spaceBefore=2, spaceAfter=8),
}


def footer(canv, doc):
    canv.saveState()
    canv.setStrokeColor(LINE); canv.setLineWidth(0.5)
    canv.line(M, 14 * mm, PAGE_W - M, 14 * mm)
    canv.setFont('Helvetica', 7.2); canv.setFillColor(GRAY)
    canv.drawCentredString(PAGE_W / 2, 10.2 * mm, FOOTER1)
    canv.drawCentredString(PAGE_W / 2, 6.6 * mm, f'{FOOTER2} - page {doc.page}')
    canv.restoreState()


COVER_STYLES = {
    'kicker': ParagraphStyle('kicker', fontName='Helvetica', fontSize=10, leading=14,
                             textColor=TEAL, alignment=TA_LEFT, spaceAfter=10),
    'title': ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=26, leading=31,
                            textColor=HexColor('#ffffff'), spaceAfter=8),
    'subtitle': ParagraphStyle('subtitle', fontName='Helvetica', fontSize=12, leading=16,
                               textColor=HexColor('#c7d3de'), spaceAfter=22),
    'svh': ParagraphStyle('svh', fontName='Helvetica-Bold', fontSize=12, leading=15,
                          textColor=TEAL, spaceBefore=6, spaceAfter=7),
    'sv': ParagraphStyle('sv', fontName='Helvetica', fontSize=8.6, leading=11.8,
                         textColor=HexColor('#e8eef3'), leftIndent=14, bulletIndent=2, spaceAfter=4),
    'contents': ParagraphStyle('contents', fontName='Helvetica', fontSize=7.6, leading=10.5,
                               textColor=HexColor('#8fa6b8'), spaceBefore=10),
}


def cover_footer(canv, doc):
    canv.saveState()
    canv.setFillColor(NAVY)
    canv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    canv.setFillColor(TEAL)
    canv.rect(0, PAGE_H - 6 * mm, PAGE_W, 6 * mm, stroke=0, fill=1)
    canv.restoreState()


def cover_flow(short_version, contents):
    flow = [Spacer(1, 34 * mm),
            Paragraph('PRIVATE RESEARCH - NOT INVESTMENT ADVICE', COVER_STYLES['kicker']),
            Paragraph('The funding-risk engine,<br/>unified scientific report', COVER_STYLES['title']),
            Paragraph('4th edition - 8 November 2026 - prepared for Tijs de Boer', COVER_STYLES['subtitle']),
            Paragraph('The short version', COVER_STYLES['svh'])]
    for i, b in enumerate(short_version, 1):
        flow.append(Paragraph(b, COVER_STYLES['sv'], bulletText=f'{i}.'))
    flow.append(Paragraph(contents, COVER_STYLES['contents']))
    return flow


def blocks_to_flow(blocks, figdir):
    flow = []
    for b in blocks:
        kind = b[0]
        if kind == 'h1':
            flow.append(Paragraph(b[1], S['h1']))
            t = Table([['']], colWidths=[28 * mm], rowHeights=[1.6])
            t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), TEAL)]))
            t.keepWithNext = 1
            flow.append(t)
            sp = Spacer(1, 4); sp.keepWithNext = 1
            flow.append(sp)
        elif kind == 'h2':
            flow.append(Paragraph(b[1], S['h2']))
        elif kind == 'p':
            flow.append(Paragraph(b[1], S['body']))
        elif kind == 'bullets':
            for x in b[1]:
                flow.append(Paragraph(x, S['bullet'], bulletText='-'))
        elif kind == 'numbers':
            for i, x in enumerate(b[1], 1):
                flow.append(Paragraph(x, S['bullet'], bulletText=f'{i}.'))
        elif kind == 'note':
            flow.append(Paragraph(b[1], S['note']))
        elif kind == 'table':
            header, rows = b[1], b[2]
            ncol = len(header)
            data = [[Paragraph(h, S['cellb']) for h in header]]
            for r in rows:
                data.append([Paragraph(str(x), S['cell']) for x in r])
            avail = PAGE_W - 2 * M
            widths = b[3] if len(b) > 3 else None
            if widths is None:
                widths = [avail * 0.22] + [avail * 0.78 / (ncol - 1)] * (ncol - 1)
            else:
                tot = sum(widths)
                widths = [w / tot * avail for w in widths]
            t = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), PANEL),
                ('LINEBELOW', (0, 0), (-1, 0), 0.8, NAVY),
                ('LINEBELOW', (0, 1), (-1, -2), 0.4, LINE),
                ('LINEBELOW', (0, -1), (-1, -1), 0.8, NAVY),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            flow.append(t); flow.append(Spacer(1, 7))
        elif kind == 'fig':
            img = Image(str(figdir / b[1]))
            w = PAGE_W - 2 * M
            scale = w / img.imageWidth
            img.drawWidth = w; img.drawHeight = img.imageHeight * scale
            flow.append(KeepTogether([img, Paragraph(b[2], S['caption'])]))
        elif kind == 'pagebreak':
            flow.append(PageBreak())
    return flow


def build(out_path, short_version, contents, blocks, figdir):
    from reportlab.platypus import NextPageTemplate
    doc = BaseDocTemplate(str(out_path), pagesize=A4,
                          leftMargin=M, rightMargin=M, topMargin=16 * mm, bottomMargin=20 * mm,
                          title='Ballast funding-risk engine - unified scientific report, 4th edition',
                          author='Instinct research for Tijs de Boer')
    frame = Frame(M, 20 * mm, PAGE_W - 2 * M, PAGE_H - 36 * mm, id='main')
    cover_frame = Frame(18 * mm, 14 * mm, PAGE_W - 36 * mm, PAGE_H - 28 * mm, id='cover',
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='cover', frames=[cover_frame], onPage=cover_footer),
                          PageTemplate(id='main', frames=[frame], onPage=footer)])
    flow = cover_flow(short_version, contents)
    flow += [NextPageTemplate('main'), PageBreak()]
    flow += blocks_to_flow(blocks, figdir)
    doc.build(flow)
