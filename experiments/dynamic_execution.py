"""Bounded causal policy search and honest independent execution evaluation."""
from pathlib import Path
import copy,json,time,hashlib,subprocess
import numpy as np
from scipy.optimize import differential_evolution
from emfin_v2.default_run import load_config,setup,draw_paths,probabilities
from emfin_v2.dynamic_policy import execute,logits,ce
from emfin_v2.dynamic_judge import judge
from emfin_v2.toolbox.risk_stats import empirical_cvar
from experiments.robustness import config,source_tree_hash,save
ROOT=Path('artifacts/dynamic-policy-20261107')


def initial_weights(c):
    source=Path('artifacts/utility-comparison-20261107/summary.json')
    if not source.exists():source=Path('docs/evidence/dynamic-policy-20261107/prerequisites/utility-summary.json')
    study=json.loads(source.read_text());s=next(x for x in study['studies'] if x['model']=='gaussian_scale_mixture' and x['name']=='3M-monthly');raw=next(x for x in s['rows'] if x['kind']=='cara' and x['variant']=='raw');selected=next(x for x in s['rows'] if x['kind']=='cara' and x['variant']=='validated');return np.array(selected['weights'])*c['wealth'],np.array(raw['weights'])*c['wealth']


def training_score(c,r):
    wealth=c['wealth'];reserve=c.get('wasserstein_radius',0)/(1-c['confidence']);shadow=r['shadow_wealth_paths']/wealth;risks=[empirical_cvar(np.maximum(0,1-shadow).max(1),c['confidence'])+reserve-c['cml_budget'],empirical_cvar(1-shadow[:,-1],c['confidence'])+reserve-c['loss_budget']]
    risks += [empirical_cvar(r['shortfalls'][:,i]/wealth,c['confidence'])+reserve-p['amount']*c['funding_budget_fraction']/wealth for i,p in enumerate(c['liabilities'])]
    fraction=float(r['funded'].mean());mean_unpaid=float(r['shortfalls'].mean()/wealth);violation=float(sum(max(0,x) for x in risks)+max(0,.99-fraction)+mean_unpaid);value=ce(r['terminal_net'],c['risk_tolerance']);return dict(score=-value/wealth+100*violation,ce=value,feasible=bool(violation<=1e-12),violation=violation,funded=fraction,cost=float(r['cost'].mean()),turnover=float(r['turnover'].mean()),risks=risks)


def drawsets(c,fit,n,offset):
    draws=[draw_paths(c,fit,n,c['seed']+offset+j) for j in range(4)];ps=[probabilities(c,d[0],d.re_price_logs) for d in draws];return draws,ps


def evaluate_policy(c,draws,ps,initial,policy,fee=.0005,delay=1):
    results=[execute(c,d,initial,policy.get('theta'),policy['mode'],fee,delay,False) for d in draws];v=judge(c,results,[p[0] for p in ps],[p[1] for p in ps],draws[0][3],draws[0][2]);return v,results


def pilot():
    c=config(100,200,400,4);fit=setup(c);dr=draw_paths(c,fit,100,c['seed']);initial,raw=initial_weights(c);rng=np.random.default_rng(20261107);candidates=np.vstack([logits(initial,c),logits(raw,c),rng.uniform([-8]*4+[-4]*4,[8]*4+[4]*4,(38,8))]);start=time.perf_counter();rows=[]
    for theta in candidates:rows.append(training_score(c,execute(c,dr,initial,theta,record=False)))
    result=dict(evaluations=len(rows),seconds=time.perf_counter()-start,feasible=sum(x['feasible'] for x in rows),best_ce=max(x['ce'] for x in rows if x['feasible']),scope='Timing pilot only. Full fixed search not started.');ROOT.mkdir(parents=True,exist_ok=True);save(result,ROOT/'pilot.json');print(json.dumps(result))


def main():
    started=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True);c=config(100,200,400,4);fit=setup(c);initial,raw=initial_weights(c);dr=draw_paths(c,fit,100,c['seed']);bounds=[(-8,8)]*4+[(-4,4)]*4;rng=np.random.default_rng(20261107);population=rng.uniform([-8]*4+[-4]*4,[8]*4+[4]*4,(40,8));population[0]=logits(initial,c);population[1]=logits(raw,c);trials=[];searchstart=time.perf_counter()
    def objective(theta):
        if time.perf_counter()-searchstart>180:raise TimeoutError('prespecified180ssearch budget')
        stats=training_score(c,execute(c,dr,initial,theta,record=False));trials.append(dict(theta=np.array(theta).tolist(),**stats));return stats['score']
    result=differential_evolution(objective,bounds,maxiter=8,popsize=5,init=population,seed=20261107,polish=False,tol=0,atol=0,updating='immediate',workers=1)
    candidates=sorted([x for x in trials if x['feasible']],key=lambda x:x['ce'],reverse=True);unique=[]
    for z in candidates:
        if not any(np.allclose(z['theta'],v['theta'],rtol=0,atol=1e-10) for v in unique):unique.append(z)
        if len(unique)==12:break
    laws={};validation={}
    for model in ['gaussian_scale_mixture','bounded_ewma_mixture']:
        cc=copy.deepcopy(c);cc['scenario_model']=model;laws[model]=cc;validation[model]=drawsets(cc,fit,200,1000)
    validation_trials=[];selected=None
    for i,z in enumerate(unique):
        policy=dict(name=f'feedback_training_rank{i+1}',mode='feedback',theta=z['theta']);judges={model:evaluate_policy(cc,*validation[model],initial,policy)[0] for model,cc in laws.items()};validation_trials.append(dict(policy=policy,training=z,judges=judges))
        if all(v['overall_pass'] for v in judges.values()):selected=policy;break
    policies=[dict(name='cash_first_static_holdings',mode='cash_first'),dict(name='pro_rata_withdrawal',mode='pro_rata'),dict(name='static_target_monthly',mode='static_target')]
    if selected:policies.append(selected)
    meta=dict(code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_tree_hash(),protocol_sha256=hashlib.sha256(Path('docs/DYNAMIC_POLICY_PROTOCOL.md').read_bytes()).hexdigest());lock=dict(**meta,config=c,initial_allocation=initial.tolist(),initial_scope='same starting holdings for every policy;feedback can trade at time0and pays fees',policies=policies,validation_trials=validation_trials,search_trials=trials,final_scored=False);save(lock,ROOT/'selection_lock.json');rows=[];base_finals={}
    for model,cc in laws.items():
        final,ps=drawsets(cc,fit,400,10000);base_finals[model]=(final,ps)
        for policy in policies:
            v,_=evaluate_policy(cc,final,ps,initial,policy);rows.append(dict(model=model,policy=policy['name'],mode=policy['mode'],judge=v))
    # Prespecified fixed sensitivities; no reselection. Results for all baselines
    # and selected policy use the SAME altered path arrays/measures.
    sensitivity=[]
    shifts=[('drift_minus2pp',-.02,1.),('drift_plus2pp',.02,1.),('covariance_x.8',0.,.8),('covariance_x1.2',0.,1.2)]
    for name,drift,scale in shifts:
        cc=copy.deepcopy(c);frame,mu,cov=fit;mu=mu.copy();cov=cov.copy();risky=[i for i in range(len(c['liquidity_haircuts'])) if i!=c['cash_index']];mu[risky]+=drift/52;cov*=scale;ds,ps=drawsets(cc,(frame,mu,cov),400,10000)
        for policy in policies:sensitivity.append(dict(name=name,policy=policy['name'],judge=evaluate_policy(cc,ds,ps,initial,policy)[0]))
    ds,ps=base_finals['gaussian_scale_mixture']
    for name,fee,delay in [('zero_fee',0.,1),('fee10bps',.001,1),('fee25bps',.0025,1),('instant_settlement',.0005,0),('two_week_settlement',.0005,2)]:
        for policy in policies:sensitivity.append(dict(name=name,policy=policy['name'],judge=evaluate_policy(c,ds,ps,initial,policy,fee,delay)[0]))
    # W1-informed adverse path perturbation: deterministic tiny common price
    # decline of epsilon (cash/property unchanged), not a worst-law optimizer.
    adverse=[];epsilon=c['wasserstein_radius']
    altered=[]
    for d in ds:
        from emfin_v2.real_estate import ScenarioDraw
        dd=ScenarioDraw(tuple(np.array(v,copy=True) for v in d),np.array(d.funding_paths,copy=True),np.array(d.re_price_logs,copy=True));risky=[i for i in range(d[0].shape[2]) if i!=c['cash_index'] and i not in c['asset_layout']['property_indices']];dd[0][:,:,risky]=np.maximum(0,dd[0][:,:,risky]-epsilon);altered.append(dd)
    for policy in policies:adverse.append(dict(name='fixed_max_path_epsilon_downshift',radius=epsilon,policy=policy['name'],judge=evaluate_policy(c,altered,ps,initial,policy)[0],scope='One chosen adverse perturbation within declared price sup-norm radius; NOT full Wasserstein robust optimization/certification. EPweights kept frozen.'))
    output=dict(**meta,seconds=time.perf_counter()-started,search_seconds=time.perf_counter()-searchstart,evaluations=len(trials),feasible_training=len(candidates),unique_validation_candidates=len(unique),selected=selected,initial_allocation=initial.tolist(),rows=rows,sensitivity=sensitivity,w1_diagnostic=adverse,validation_trials=validation_trials,search_trials=trials,lock_sha256=hashlib.sha256((ROOT/'selection_lock.json').read_bytes()).hexdigest(),scope='Causal bounded-class training search, conditional simulation evidence only; no global policy optimum or nonlinear W1certificate. Same initial holdings/paths/costs/judge for every policy;confirmed250k/month only.');save(output,ROOT/'summary.json');print(json.dumps(dict(seconds=output['seconds'],evaluations=len(trials),selected=selected,rows=[dict(model=z['model'],policy=z['policy'],pass_all=z['judge']['overall_pass'],ce=z['judge']['common_cara_ledger_ce']) for z in rows]),indent=2))

if __name__=='__main__':
    import sys
    pilot() if '--pilot' in sys.argv else main()
