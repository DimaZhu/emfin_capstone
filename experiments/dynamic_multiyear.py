"""Exploratory 3/5year fixed-target frequency tests, immutable final holdouts."""
from pathlib import Path
import json,time,copy,hashlib
import numpy as np
from scipy.stats import t
from emfin_v2.default_run import setup
from emfin_v2.payouts import expand_recurring
from experiments.dynamic_execution import drawsets
from experiments.dynamic_frequency import evaluate
from experiments.dynamic_robust import models
from experiments.dynamic_attribution import paired
from experiments.robustness import save
ROOT=Path('artifacts/dynamic-policy-20261107/multiyear')

def extended(c,years):
    c=copy.deepcopy(c);c['horizon_weeks']=52*years;c['recurring_payout']['months']=12*years;c['liabilities']=expand_recurring(c['recurring_payout'],c['horizon_weeks']);c['one_off_liabilities']=[];return c

def main():
    start=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True);old=json.loads(Path('artifacts/dynamic-policy-20261107/selection_lock.json').read_text());original=old['config'];initial=np.array(old['initial_allocation']);fit=setup(original);freqs=[1,3,6,12];studies=[]
    for years in [3,5]:
        c=extended(original,years);laws=models(c,fit);validation=[]
        for name,(cc,ff) in laws.items():
            ds,ps=drawsets(cc,ff,200,410000+years*10000)
            for f in freqs:validation.append(dict(model=name,months=f,judge=evaluate(cc,ds,ps,initial,f)[0]))
        passed=[f for f in freqs if all(r['judge']['overall_pass'] for r in validation if r['months']==f)];scores={f:min(r['judge']['common_cara_ledger_ce'] for r in validation if r['months']==f) for f in passed};selected=max(scores,key=scores.get) if scores else None
        save(dict(config=c,initial=initial.tolist(),validation=validation,selected=selected,scores=scores,offsets=dict(validation=410000+years*10000,final=510000+years*10000),final_scored=False,protocol_sha256=hashlib.sha256(Path('docs/DYNAMIC_POLICY_PROTOCOL.md').read_bytes()).hexdigest()),ROOT/f'{years}year_selection_lock.json');rows=[];pairs=[]
        for name,(cc,ff) in laws.items():
            ds,ps=drawsets(cc,ff,400,510000+years*10000);results={}
            for f in freqs:
                v,rs=evaluate(cc,ds,ps,initial,f);rows.append(dict(model=name,months=f,judge=v));results[f]=rs
            for f in [1,3,6]:
                z=paired(results[f],results[12],c['risk_tolerance']);delta=np.array(z['batch_ce_differences']);half=float(t.ppf(1-.05/48,3)*delta.std(ddof=1)/2);z.update(lower=z['mean']-half,upper=z['mean']+half,scope='Simultaneous24comparison Bonferroni4batch conditional MC diagnostic; no economic/model/optimality coverage.');pairs.append(dict(model=name,comparison=f'{f}month minus12month',paired=z))
        studies.append(dict(years=years,total_payments=years*3e6,selected=selected,validation=validation,rows=rows,paired=pairs))
        if time.perf_counter()-start>120:raise TimeoutError('prespecified120second cap')
    out=dict(seconds=time.perf_counter()-start,studies=studies,scope='Exploratory3and5year extrapolation, same target/fourlaws/budgets/fees/settlement, fresh4x400final/law.250kamount confirmed;duration sensitivity only. No global/economic optimum.');save(out,ROOT/'summary.json');print(json.dumps(dict(seconds=out['seconds'],studies=[dict(years=s['years'],selected=s['selected'],rows=[dict(model=x['model'],months=x['months'],ce=x['judge']['common_cara_ledger_ce'],passed=x['judge']['overall_pass'],breaches=x['judge']['breaches'],cost=x['judge']['cost_mean'])for x in s['rows']])for s in studies]),indent=2))

if __name__=='__main__':main()
