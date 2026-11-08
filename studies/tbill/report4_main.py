"""Assemble and render the 4th-edition PDF."""
from pathlib import Path
from build_report4 import build
from content_a import SHORT_VERSION, CONTENTS, SECTIONS_1_10
from content_b import SECTIONS_11_20, APPENDICES
from content_c import SECTIONS_21_23

HERE = Path(__file__).resolve().parent
OUT = Path('/downloads/ballast-unified-scientific-report-20261108-4th-edition.pdf')

blocks = SECTIONS_1_10 + SECTIONS_11_20 + SECTIONS_21_23 + APPENDICES
build(OUT, SHORT_VERSION, CONTENTS, blocks, HERE / 'figs')
print('written', OUT, OUT.stat().st_size, 'bytes')
