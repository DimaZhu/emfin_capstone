"""An imposed preference sensitivity, not identification of a client liability effect."""
import sys,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from emfin_capstone.toolbox import liabilities as l
rng=np.random.default_rng(81)
market=np.column_stack([np.exp(rng.normal(.012,.08,2000)),np.full(2000,1.005)])
rows=[]
for funding in [1.5,1.2,1.08,1.02]:
    liability=1e6/funding
    surplus=(1e6-liability)/1e6
    tolerance=l.surplus_scaled_cara_tolerance(100000.,surplus,.2)
    a,_=l.optimization_liability_aware(market,np.ones(2),1e6,liability,tolerance,.95,1.,1.)
    rows.append([funding,surplus,tolerance,a[0]/1e6])
p=Path('artifacts/surplus_sensitivity.csv');p.parent.mkdir(exist_ok=True)
with p.open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['funding_ratio','surplus_ratio','imposed_cara_tolerance','risky_weight']);w.writerows(rows)
print(p);print(rows)
