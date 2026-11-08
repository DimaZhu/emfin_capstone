"""Assemble and render the 5th-edition unified scientific report."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'tbill'))

import build_report4
from report5_data import assemble
from content5 import build_content

OUT = Path('/downloads/ballast-unified-scientific-report-20261108-5th-edition.pdf')


def main():
    d = assemble()
    short, contents, blocks = build_content(d)
    build_report4.EDITION = '5th'
    build_report4.build(OUT, short, contents, blocks, HERE / 'figs5')
    print('written', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
