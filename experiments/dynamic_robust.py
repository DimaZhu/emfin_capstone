"""Exploratory finite-model-set robust policy search, fresh frozen final paths."""
from pathlib import Path
import json,copy,time,hashlib,subprocess
import numpy as np
from scipy.optimize import differential_evolution
from emfin_v2.default_run import setup,draw_paths
from emfin_v2.dynamic_policy import execute,logits
from experiments.dynamic_execution import training_score,drawsets,evaluate_policy
from experiments.dynamic_attribution import paired
from experiments.robustness import save,source_tree_hash
ROOT=Path('artifacts/dynamic-policy-20261107/robust')


def models(c,fit):
    result={};frame,mu,cov=fit;risky=[i for i in range(len(c['liquidity_haircuts'])) if i!=c['cash_index']]
    for name,law,drift,scale in [('iid_nominal','gaussian_scale_mixture',0,1.),('bounded_nominal','bounded_ewma_mixture',0,1.),('iid_drift_minus2pp','gaussian_scale_mixture',-.02,1.),('iid_drift_minus2pp_cov1.2','gaussian_scale_mixture',-.02,1.2)]:
        cc=copy.deepcopy(c);cc['scenario_model']=law;m=mu.copy();m[risky]+=drift/52;result[name]=(cc,(frame,m,cov*scale))
    return result


def main():
    started=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True);old=json.loads(Path('artifacts/dynamic-policy-20261107/selection_lock.json').read_text());c=old['config'];initial=np.array(old['initial_allocation']);original=next(x for x in old['policies'] if x['mode']=='feedback');fit=setup(c);laws=models(c,fit);train={name:draw_paths(cc,f,100,c['seed']+200000) for name,(cc,f) in laws.items()};rng=np.random.default_rng(20261108);population=rng.uniform([-8]*4+[-4]*4,[8]*4+[4]*4,(40,8));population[0]=original['theta'];first=np.array(original['theta'],float);first[:4]+=first[5]*sum(x['amount'] for x in c['liabilities'])/(c['wealth']*.9);first[4:]=0;population[1]=first;population[2]=logits(initial,c);trials=[]
    def objective(theta):
        if time.perf_counter()-started>180:raise TimeoutError('prespecified180ssearch budget')
        scores={name:training_score(cc,execute(cc,train[name],initial,theta,record=False)) for name,(cc,f) in laws.items()};worst=min(x['ce'] for x in scores.values());violation=max(x['violation'] for x in scores.values());score=-worst/c['wealth']+100*violation;trials.append(dict(theta=np.array(theta).tolist(),score=score,worst_ce=worst,feasible=all(x['feasible'] for x in scores.values()),laws=scores));return score
    differential_evolution(objective,[(-8,8)]*4+[(-4,4)]*4,maxiter=8,popsize=5,init=population,seed=20261108,polish=False,tol=0,atol=0,workers=1,updating='immediate');training_seconds=time.perf_counter()-started;feasible=sorted([z for z in trials if z['feasible']],key=lambda z:z['worst_ce'],reverse=True);unique=[]
    for z in feasible:
        if not any(np.allclose(z['theta'],x['theta'],rtol=0,atol=1e-10) for x in unique):unique.append(z)
        if len(unique)==12:break
    validation={name:drawsets(cc,f,200,210000) for name,(cc,f) in laws.items()};attempts=[];selected=None
    for i,z in enumerate(unique):
        policy=dict(name='robust_feedback',mode='feedback',theta=z['theta'],training_rank=i+1);verdicts={name:evaluate_policy(cc,*validation[name],initial,policy)[0] for name,(cc,f) in laws.items()};attempts.append(dict(policy=policy,training=z,judges=verdicts))
        if all(v['overall_pass'] for v in verdicts.values()):selected=policy;break
    policies=[dict(name='original_cash_first',mode='cash_first'),dict(name='pro_rata_withdrawal',mode='pro_rata'),dict(name='static_target_monthly',mode='static_target'),dict(name='original_feedback',mode='feedback',theta=original['theta']),dict(name='original_first_trade_only',mode='feedback_initial_only',theta=original['theta'])]
    if selected:policies += [selected,dict(name='robust_first_trade_only',mode='feedback_initial_only',theta=selected['theta'])]
    meta=dict(code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_tree_hash(),protocol_sha256=hashlib.sha256(Path('docs/DYNAMIC_POLICY_PROTOCOL.md').read_bytes()).hexdigest());lock=dict(**meta,config=c,initial=initial.tolist(),models=list(laws),fresh_seed_offsets=dict(training=200000,validation=210000,final=220000),policies=policies,training_trials=trials,validation_trials=attempts,selected=selected,final_scored=False);save(lock,ROOT/'selection_lock.json');rows=[];comparisons=[]
    for name,(cc,f) in laws.items():
        ds,ps=drawsets(cc,f,400,220000);results={}
        for policy in policies:
            v,rs=evaluate_policy(cc,ds,ps,initial,policy);rows.append(dict(model=name,policy=policy['name'],judge=v));results[policy['name']]=rs
        if selected:
            for reference in ['original_cash_first','robust_first_trade_only','original_first_trade_only']:
                z=paired(results['robust_feedback'],results[reference],c['risk_tolerance']);z['scope']='Exploratory paired4batch conditional MC diagnostic; original2law multiplicity constant, not simultaneous across all4laws/comparisons. No economic/model/global-optimality coverage.';comparisons.append(dict(model=name,comparison='robust_feedback minus '+reference,paired=z))
    output=dict(**meta,seconds=time.perf_counter()-started,training_seconds=training_seconds,evaluations=len(trials),feasible_training=len(feasible),validation_trials=attempts,selected=selected,rows=rows,comparisons=comparisons,lock_sha256=hashlib.sha256((ROOT/'selection_lock.json').read_bytes()).hexdigest(),scope='EXPLORATORY redesign after primary final drift failure. Finite4model-set robust SEARCH only, fresh disjoint paths, no final repair or universal/W1policy certificate. Confirmed250k/month.');save(output,ROOT/'summary.json');print(json.dumps(dict(seconds=output['seconds'],training_seconds=training_seconds,feasible=len(feasible),selected=selected,rows=[dict(model=x['model'],policy=x['policy'],ce=x['judge']['common_cara_ledger_ce'],passed=x['judge']['overall_pass'],breaches=x['judge']['breaches']) for x in rows]),indent=2))

if __name__=='__main__':main()
