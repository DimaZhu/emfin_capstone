"""Assemble every frozen input for the final five-question report."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def J(p):
    return json.loads((ROOT / p).read_text())


def assemble():
    d = {}
    d['h5'] = J('studies/final5/results/final5_horizon.json')          # fresh Q3 sweep
    d['q4'] = J('studies/final5/results/final5_inperiod.json')         # fresh Q4 slice
    d['charts'] = J('studies/tbill/results/study_tips_charts.json')    # new-model pack (seed 20261107)
    d['r2'] = J('studies/round2/results/round2_dual_law.json')         # round-2 dual-law (seed 20261108)
    d['fix6'] = J('studies/fixes/results/fix6_grid.json')              # full cml x loss grid
    d['mix10'] = J('studies/round2/results/round2_longhorizon_mix.json')
    d['real'] = J('studies/round2/results/round2_real_repricing.json')
    return d
