"""Post-result attribution only, frozen feedback policy, no reselection."""
import json,copy,time
from pathlib import Path
import numpy as np
from scipy.stats import t
from emfin_v2.default_run import setup
from emfin_v2.dynamic_policy import ce
from experiments.dynamic_execution import ROOT,drawsets,evaluate_policy
from experiments.robustness import save


def paired(a,b,tolerance):
    differences=np.array([ce(x['terminal_net'],tolerance)-ce(y['terminal_net'],tolerance) for x,y in zip(a,b)]);half=float(t.ppf(1-.05/4,len(a)-1)*differences.std(ddof=1)/np.sqrt(len(a)));return dict(batch_ce_differences=differences.tolist(),mean=float(differences.mean()),lower=float(differences.mean()-half),upper=float(differences.mean()+half),scope='Paired4batch conditional Monte Carlo CE-difference diagnostic, Bonferroni for2fixedlaws; not model/historical/economic confidence or a post-selection policy-optimality certificate.')


def main():
    started=time.perf_counter();lock=json.loads((ROOT/'selection_lock.json').read_text());c=lock['config'];initial=np.array(lock['initial_allocation']);selected=next(x for x in lock['policies'] if x['mode']=='feedback');fit=setup(c);policies=[dict(name='same_first_trade_then_cash_first',mode='feedback_initial_only',theta=selected['theta']),dict(name='same_first_trade_static_target',mode='feedback_static_target',theta=selected['theta']),selected,dict(name='original_cash_first',mode='cash_first')];rows=[];shifts=[]
    for model in ['gaussian_scale_mixture','bounded_ewma_mixture']:
        cc=copy.deepcopy(c);cc['scenario_model']=model;ds,ps=drawsets(cc,fit,400,10000);results={}
        for policy in policies:
            v,rs=evaluate_policy(cc,ds,ps,initial,policy);rows.append(dict(model=model,policy=policy['name'],judge=v));results[policy['name']]=rs
        for reference in ['same_first_trade_then_cash_first','same_first_trade_static_target','original_cash_first']:
            rows.append(dict(model=model,comparison='feedback minus '+reference,paired=paired(results[selected['name']],results[reference],c['risk_tolerance'])))
    frame,mu,cov=fit;mu=mu.copy();risky=[i for i in range(len(c['liquidity_haircuts'])) if i!=c['cash_index']];mu[risky]-=.02/52;ds,ps=drawsets(c,(frame,mu,cov),400,10000)
    for policy in policies:shifts.append(dict(name='drift_minus2pp',policy=policy['name'],judge=evaluate_policy(c,ds,ps,initial,policy)[0]))
    save(dict(rows=rows,shift_diagnostics=shifts,seconds=time.perf_counter()-started,scope='POST-RESULT attribution after seeing primary final CEs. Same frozen policy first-action target and original draws. No training or selection. These are not independent confirmatory outcomes.'),ROOT/'attribution.json');print(json.dumps(dict(rows=[dict(model=z['model'],policy=z.get('policy',z.get('comparison')),ce=z.get('judge',{}).get('common_cara_ledger_ce'),pass_all=z.get('judge',{}).get('overall_pass'),paired=z.get('paired')) for z in rows]),indent=2))

if __name__=='__main__':main()
