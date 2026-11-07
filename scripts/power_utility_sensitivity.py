"""Finite positive-domain CRRA demonstration, synthetic market only."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from emfin_v2.toolbox.power_utility import allocate_positive_surplus
rng=np.random.default_rng(123)
market=np.column_stack([np.exp(rng.normal(.02,.06,1000)),np.full(1000,1.005)])
rows=[]
for liability in (500000.,900000.,980000.):
    for gamma in (.5,1.,3.):
        try:
            a,d=allocate_positive_surplus(market,np.ones(2),1e6,liability,gamma)
            rows.append(dict(liability=liability,gamma=gamma,risky_weight=float(a[0]/1e6),**d))
        except RuntimeError as e:rows.append(dict(liability=liability,gamma=gamma,status='unavailable',reason=str(e)))
r=dict(label='Synthetic exact positive-surplus CRRA sensitivity, not client calibration',
       caveat='Positive surplus enforced on supplied scenarios only. This changes the economic model by prohibiting all scenario shortfalls.',results=rows)
p=Path('artifacts/power_utility_sensitivity.json');p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(p)
