"""Post-result nonanticipativity-relaxation upper bound, not a policy."""
import json
from pathlib import Path
import numpy as np
from emfin_v2.default_run import setup
from emfin_v2.dynamic_policy import perfect_foresight_relaxation,ce
from experiments.dynamic_robust import models
from experiments.dynamic_execution import drawsets,evaluate_policy
from experiments.robustness import save
ROOT=Path('artifacts/dynamic-policy-20261107')
old=json.loads((ROOT/'selection_lock.json').read_text());rob=json.loads((ROOT/'robust/selection_lock.json').read_text());c=old['config'];fit=setup(c);initial=np.array(old['initial_allocation']);laws=models(c,fit);upper=[];validation=[]
for name,(cc,f) in laws.items():
    ds,ps=drawsets(cc,f,400,220000);x=np.concatenate([perfect_foresight_relaxation(cc,d,initial) for d in ds]);upper.append(dict(model=name,perfect_foresight_sample_ce=ce(x,c['risk_tolerance']),scope='Pathwise clairvoyant frictionless weekly relaxation; sample bound only, not executable, not a true-law CI or achieved return.'))
    val,vp=drawsets(cc,f,200,210000)
    for p in rob['policies'][:3]:validation.append(dict(model=name,policy=p['name'],judge=evaluate_policy(cc,val,vp,initial,p)[0]))
save(dict(sample_relaxation_upper=upper,baseline_validation=validation,scope='Post-result diagnostic; no training/selection or final repair. Sample upper gap is not closed.'),ROOT/'bounds.json');print([(x['model'],x['perfect_foresight_sample_ce']/1e6) for x in upper]);print('baselinevalidation',[(x['model'],x['policy'],x['judge']['overall_pass']) for x in validation])
