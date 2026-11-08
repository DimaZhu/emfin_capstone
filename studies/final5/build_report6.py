"""Assemble and render the final five-question report."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'tbill'))

import build_report4
from report6_data import assemble
from content6 import build_content

OUT = Path('/downloads/ballast-final-five-questions-20261108.pdf')


def main():
    d = assemble()
    short, contents, blocks = build_content(d)
    build_report4.EDITION = 'final'
    build_report4.build(OUT, short, contents, blocks, HERE / 'figs6')
    print('written', OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
