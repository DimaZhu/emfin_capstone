"""Seven-sleeve optimizer example. RE calibration is SYNTHETIC, not BIS/ADREC."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from emfin_capstone.toolbox import dataset,shrinkage,liabilities,risk_stats

def run():
    data=dataset.weekly_dataset();x=data[dataset.COLUMNS].to_numpy()
    cov,_=shrinkage.ledoit_wolf_cov(x);mu=x.mean(0)
    rng=np.random.default_rng(20261107)
    inv=13*mu+rng.standard_normal((2000,6))@np.linalg.cholesky(13*cov+1e-12*np.eye(6)).T
    last=data.iloc[-1];market=dataset.gross_market(inv,last.YIELD_LEVEL,last.SPREAD_LEVEL)
    # A stated synthetic quarterly property model. No national stale index is
    # passed off as current Abu Dhabi evidence. 30% equity-factor correlation,
    # 12% annual volatility, 4% annual drift and 10% liquidation haircut.
    eq=inv[:,:3].mean(1);z_eq=(eq-eq.mean())/eq.std()
    re=0.9*np.exp(.04/4+.12/2*(.3*z_eq+np.sqrt(1-.3**2)*rng.standard_normal(len(eq))))
    seven=np.column_stack([market,re]);rows=[]
    for due in (600000.,950000.):
        for held in (0.,.2):
            mins=np.r_[np.zeros(6),held]
            try:
                a,d=liabilities.optimization_liability_aware(seven,np.ones(7),1e6,due,100000.,.95,.15,.002,minimum_weights=mins)
                rows.append(dict(liability=due,minimum_re=held,status=d['status'],weights=(a/1e6).tolist(),
                    in_sample_gap_cvar=risk_stats.empirical_cvar(np.maximum(due-seven@a,0),.95)))
            except RuntimeError as e:
                rows.append(dict(liability=due,minimum_re=held,status='unavailable',reason=str(e)))
    return dict(label='Synthetic RE scenario sleeve in the actual shared optimizer, not client-calibrated',
        assets=['DFUS','DFAI','DFAE','UST10','USIG','MMKT','RE synthetic'],
        assumptions=dict(re_annual_drift=.04,re_annual_vol=.12,equity_correlation=.3,liquidation_haircut=.10),
        excluded=['family company: no inputs supplied','BIS UAE RPPI: stale national series, not used to calibrate this sleeve'],results=rows)

if __name__=='__main__':
    r=run();p=Path('artifacts/real_estate_allocation.json');p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps(r,indent=2))
