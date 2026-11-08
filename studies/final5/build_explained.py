"""Assemble and render the standalone explained document (Ballast theme).

Reuses the report builder from studies/tbill/build_report4 with a custom
cover (title/subtitle) and footer for the standalone guide."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'tbill'))

import build_report4 as R
from report6_data import assemble
from content_explained import build_content

OUT = Path('/downloads/ballast-explained-20261108.pdf')




def cover_flow(short_version, contents):
    flow = [R.Spacer(1, 34 * R.mm),
            R.Paragraph('PRIVATE RESEARCH - NOT INVESTMENT ADVICE', R.COVER_STYLES['kicker']),
            R.Paragraph('The Ballast funding-risk engine,<br/>explained from scratch', R.COVER_STYLES['title']),
            R.Paragraph('a standalone guide - 8 November 2026 - prepared for Tijs de Boer',
                        R.COVER_STYLES['subtitle']),
            R.Paragraph('The short version', R.COVER_STYLES['svh'])]
    for i, b in enumerate(short_version, 1):
        flow.append(R.Paragraph(b, R.COVER_STYLES['sv'], bulletText=f'{i}.'))
    flow.append(R.Paragraph(contents, R.COVER_STYLES['contents']))
    return flow


def build(out_path, short_version, contents, blocks, figdir):
    """Same as build_report4.build but with this document's own footer/title."""
    from reportlab.platypus import NextPageTemplate, PageBreak
    R.FOOTER1 = 'Ballast funding-risk engine - explained from scratch - 8 November 2026'
    doc = R.BaseDocTemplate(str(out_path), pagesize=R.A4,
                            leftMargin=R.M, rightMargin=R.M, topMargin=16 * R.mm, bottomMargin=20 * R.mm,
                            title='Ballast funding-risk engine - explained from scratch (standalone guide)',
                            author='Instinct research for Tijs de Boer')
    frame = R.Frame(R.M, 20 * R.mm, R.PAGE_W - 2 * R.M, R.PAGE_H - 36 * R.mm, id='main')
    cover_frame = R.Frame(18 * R.mm, 14 * R.mm, R.PAGE_W - 36 * R.mm, R.PAGE_H - 28 * R.mm, id='cover',
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([R.PageTemplate(id='cover', frames=[cover_frame], onPage=R.cover_footer),
                          R.PageTemplate(id='main', frames=[frame], onPage=R.footer)])
    flow = cover_flow(short_version, contents)
    flow += [NextPageTemplate('main'), PageBreak()]
    flow += R.blocks_to_flow(blocks, figdir)
    doc.build(flow)


def main():
    d = assemble()
    short, contents, blocks = build_content(d)
    build(OUT, short, contents, blocks, HERE / 'figs_explained')
    print('written', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
