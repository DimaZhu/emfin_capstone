"""Frozen finite frequency comparison, distinct payment funding and rebalancing."""
from pathlib import Path
import json,time,hashlib
import numpy as np
from emfin_v2.default_run import setup
from emfin_v2.dynamic_policy import execute
from emfin_v2.dynamic_judge import judge
from experiments.dynamic_execution import drawsets
from experiments.dynamic_robust import models
from experiments.dynamic_attribution import paired
from scipy.stats import t
from experiments.robustness import save
ROOT=Path('artifacts/dynamic-policy-20261107/frequency')

def evaluate(c,ds,ps,a,f):
    rs=[execute(c,d,a,mode='static_frequency',record=False,rebalance_months=f) for d in ds]
    return judge(c,rs,[p[0] for p in ps],[p[1] for p in ps],ds[0][3],ds[0][2]),rs

def main():
    start=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True);old=json.loads(Path('artifacts/dynamic-policy-20261107/selection_lock.json').read_text());c=old['config'];a=np.array(old['initial_allocation']);laws=models(c,setup(c));freqs=[1,3,6,12];validation=[]
    for name,(cc,fit) in laws.items():
        ds,ps=drawsets(cc,fit,200,310000)
        for f in freqs:validation.append(dict(model=name,months=f,judge=evaluate(cc,ds,ps,a,f)[0]))
    passed=[f for f in freqs if all(r['judge']['overall_pass'] for r in validation if r['months']==f)];scores={f:min(r['judge']['common_cara_ledger_ce'] for r in validation if r['months']==f) for f in passed};selected=max(scores,key=scores.get) if passed else None
    save(dict(config=c,initial=a.tolist(),validation=validation,scores=scores,selected=selected,offsets=dict(validation=310000,final=320000),final_scored=False,protocol_sha256=hashlib.sha256(Path('docs/DYNAMIC_POLICY_PROTOCOL.md').read_bytes()).hexdigest()),ROOT/'selection_lock.json');rows=[];pairs=[]
    for name,(cc,fit) in laws.items():
        ds,ps=drawsets(cc,fit,400,320000);results={}
        for f in freqs:
            v,rs=evaluate(cc,ds,ps,a,f);rows.append(dict(model=name,months=f,judge=v));results[f]=rs
        for f in [1,3,6]:
            z=paired(results[f],results[12],c['risk_tolerance']);delta=np.array(z['batch_ce_differences']);half=float(t.ppf(1-.05/(2*12),3)*delta.std(ddof=1)/2);z.update(lower=z['mean']-half,upper=z['mean']+half,scope='Simultaneous12comparison Bonferroni4batch conditional MC diagnostic only; no economic/model/post-selection optimality coverage.');pairs.append(dict(model=name,comparison=f'{f}month minus12month',paired=z))
    result=dict(seconds=time.perf_counter()-start,selected=selected,validation=validation,rows=rows,paired=pairs,scope='Fixed original target;one-year only. Fresh4x400final paths/law. No global optimal horizon or economic probability guarantee. Same5bps/1weeksettlement/250kmonthlypayments.');save(result,ROOT/'summary.json');print(json.dumps(dict(seconds=result['seconds'],selected=selected,rows=[dict(model=x['model'],months=x['months'],ce=x['judge']['common_cara_ledger_ce'],passed=x['judge']['overall_pass'],cost=x['judge']['cost_mean']) for x in rows]),indent=2))

if __name__=='__main__':main()
