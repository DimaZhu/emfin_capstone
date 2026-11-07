"""Frozen preference comparison on shared paths and the existing judge."""
from pathlib import Path
import copy,time,json,subprocess,hashlib,traceback
import numpy as np
from emfin_v2.default_run import validate_config,setup,draw_paths,probabilities,solve
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from emfin_v2.utilities import native_ce,specification
from experiments.robustness import config,simple_allocations,source_tree_hash,save,digest
ROOT=Path('artifacts/utility-comparison-20261107');KINDS=['cara','crra_gross','hara_payment_floor','kinked_shortfall']


def provision(draw):return sum(draw[1][:,i]*draw[4][:,-1]/draw[4][:,step-1] for i,step in enumerate(draw[2]))


def main():
    started=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True);meta=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),source_sha256=source_tree_hash(),protocol_sha256=hashlib.sha256(Path('docs/UTILITY_COMPARISON_PROTOCOL.md').read_bytes()).hexdigest());studies=[]
    base=config(100,200,400,4);base['funding_mode']='pay_all_99';base=validate_config(base);fit=setup(base)
    for model in ['gaussian_scale_mixture','bounded_ewma_mixture']:
      for name,schedule in [('3M-monthly',None),('60M-early-30M-final',[dict(name='Counterfactual60M',week=13,amount=60e6),dict(name='Counterfactual30M',week=52,amount=30e6)]),('95M-final',[dict(name='Counterfactual95M',week=52,amount=95e6)])]:
        c=copy.deepcopy(base);c['scenario_model']=model
        if schedule is not None:c['recurring_payout']=None;c.pop('one_off_liabilities',None);c['liabilities']=schedule
        c=validate_config(c);dr=draw_paths(c,fit,100,c['seed']);p,ps=probabilities(c,dr[0],dr.re_price_logs);validation=[draw_paths(c,fit,200,c['seed']+1000+j) for j in range(4)];vp=[probabilities(c,v[0],v.re_price_logs) for v in validation];anchor=simple_allocations(c,dr)['cash_fixed_anchor'];specs=[];frozen=[]
        for kind in KINDS:
            if time.perf_counter()-started>300:save(dict(**meta,studies=studies,timeout=True),ROOT/'partial.json');raise TimeoutError('prespecified300s study budget')
            cc=copy.deepcopy(c);cc['objective_kind']=kind;status={};trials=[];raw=None;chosen=None
            try:
                raw,status=solve(cc,dr,p,ps,1.)
                if status['kind']!='optimized':raw=None
                if raw is not None:
                    frozen.append(dict(kind=kind,variant='raw',allocation=raw))
                    for fraction in [1.,.75,.5,.25,0.]:
                        a=fraction*raw+(1-fraction)*anchor;v=evaluate(cc,validation,a,[x[0] for x in vp],[x[1] for x in vp]);trials.append(dict(fraction=fraction,passed=v['overall_pass'],strict=v['strict_funding'],breaches=v['breaches']))
                        if v['overall_pass']:chosen=a;frozen.append(dict(kind=kind,variant='validated',allocation=a,fraction=fraction));break
            except Exception as error:status=dict(kind='unavailable',error=str(error),traceback=traceback.format_exc())
            specs.append(dict(kind=kind,status=status,validation_trials=trials,selected=chosen is not None))
        frozen.append(dict(kind='cara',variant='anchor_comparator',allocation=anchor))
        folder=ROOT/(model+'-'+name);folder.mkdir(exist_ok=True);lock=dict(**meta,config=c,specifications=specs,portfolios=frozen,final_scored=False,selection_time_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat());save(lock,folder/'selection_lock.json')
        # No final paths exist until all four preference selections are frozen.
        final=[draw_paths(c,fit,400,c['seed']+10000+j) for j in range(4)];fp=[probabilities(c,d[0],d.re_price_logs) for d in final];rows=[]
        for portfolio in frozen:
            kind=portfolio['kind'];a=portfolio['allocation'];verdict=evaluate(c,final,a,[x[0] for x in fp],[x[1] for x in fp]);audits=[cash_first(c,d,a) for d in final];x=np.concatenate([z['terminal_net'] for z in audits]);gross=np.concatenate([d[0][:,-1]@a for d in final]);L=np.concatenate([provision(d) for d in final]);q=np.concatenate([z[0]/4 for z in fp]);reference=np.full(len(x),1/len(x));native=native_ce(kind,gross,gross-L,q,c['wealth'],c['risk_tolerance'],L);common=native_ce('cara',x+L,x,reference,c['wealth'],c['risk_tolerance'],L)
            rows.append(dict(kind=kind,variant=portfolio['variant'],fraction=portfolio.get('fraction'),weights=(a/c['wealth']).tolist(),cash_weight=float(a[c['cash_index']]/c['wealth']),verdict=verdict,native_provisioning_ce=native,common_cara_ledger_ce=common['ce'],ledger_net_mean=float(x.mean()),ledger_quantiles=np.quantile(x,[.05,.5,.95]).tolist(),largest_unpaid=max(float(z['payment_shortfalls'].max()) for z in audits),model_support_domain_caveat='Finite-sample utility domain only; all-support admissibility unproven. Final native CE absent on nonpositive wealth/surplus. No clipping.'))
        study=dict(name=name,model=model,config=c,specifications=specs,rows=rows,lock_sha256=hashlib.sha256((folder/'selection_lock.json').read_bytes()).hexdigest());save(study,folder/'results.json');studies.append(study);print(model,name,[(z['kind'],z['selected'],z['status']['kind']) for z in specs],flush=True)
    result=dict(**meta,studies=studies,seconds=time.perf_counter()-started,scope='Prespecified same-path engineering preference comparison. No default/model selection, economic guarantee, final repair or client risk calibration. Native gross/net CEs are not cross-family rankings.');save(result,ROOT/'summary.json');print('seconds',result['seconds'],flush=True)

if __name__=='__main__':main()
