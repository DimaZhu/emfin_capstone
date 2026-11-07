"""Compact frozen dynamic/frequency evidence for the companion, not a live solve."""
import json
from pathlib import Path
ROOT=Path('artifacts/dynamic-policy-20261107')
DEST=Path('emfin_v2/resources/data/science/dynamic-policy-20261107.json')
SOURCES=['https://stanford.edu/~boyd/papers/pdf/dyn_port_opt.pdf','https://stanford.edu/~boyd/papers/pdf/portfolio.pdf','https://web.stanford.edu/~boyd/papers/port_opt_bound.html','https://www.karlin.mff.cuni.cz/~kopa/papers/Portfolio.pdf','https://www.karlin.mff.cuni.cz/~kopa/papers/vanc-ed.pdf','https://www.gams.com/~svigerske/publications/outofsample.pdf']

def main():
 f=json.loads((ROOT/'frequency/summary.json').read_text());r=json.loads((ROOT/'robust/summary.json').read_text());multi=json.loads((ROOT/'multiyear/summary.json').read_text());out=dict(multiyear=multi['studies'],available=True,scope='FROZEN RESEARCH, 7 November 2026. $250k/month x 12; $100M research balance sheet, original target 76.39% cash and 10% unsold property. Synthetic paths fitted to actual-history inputs; not historical OOS. 5bps per buy/sell and 1 week settlement are assumptions. Not recomputed by edited controls. No default change.',takeaway='Annual/no within-year rebalancing ranks first of four frequencies in validation and all four final laws. One-year horizon and cash-heavy target only; not a proven long-run optimum. All 16 frequency/law final rows pass this conditional screen. Lower-drift paired intervals can overlap zero.',dynamic_takeaway='No proven best dynamic rule. Eight-parameter feedback search: 360 evaluations; primary feedback passes two nominal laws but fails lower drift. Same first trade then no feedback beats repeated feedback in post-hoc attribution. Exploratory robust search: 40 training-feasible candidates, NONE of the top 12 passes all four validation laws. Fresh final feedback and first-trade-only policies fail both lower-drift laws; three simple baselines pass all four.',selected_months=f['selected'],rows=f['rows'],robust_rows=r['rows'],sources=SOURCES)
 DEST.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
