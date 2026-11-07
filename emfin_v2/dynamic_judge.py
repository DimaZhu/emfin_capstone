"""Same executed-wealth judge for every dynamic and fixed-policy baseline.

The legacy affine W1 reserve is a reported stress screen only, NOT a valid
DRO certificate for nonlinear feedback. The joint funding screen is separate.
"""
import numpy as np
from scipy.stats import t
from emfin_v2.evaluation import common_tail
from emfin_v2.strict_funding import lower_bound


def judge(c,results,nominal,stressed,bases,steps):
    if len(results)<2:raise ValueError('two or more independent judge batches required')
    arrays=[];wealth=c['wealth'];names=['reference','nominal','stressed','common_hull']
    for r,q,qs in zip(results,nominal,stressed):
        n=len(r['funded']);measures=np.array([np.full(n,1/n),q,qs]);marked=r['shadow_wealth_paths']/wealth;losses=[r['shortfalls'][:,i]/wealth for i in range(len(steps))]+[np.maximum(0,1-marked).max(1),1-marked[:,-1]]
        arrays.append([[common_tail(z,[p],c['confidence'],k!=len(losses)-1) for p in measures]+[common_tail(z,measures,c['confidence'],k!=len(losses)-1)] for k,z in enumerate(losses)])
    x=np.array(arrays);family=x.shape[1]*x.shape[2];critical=t.ppf(1-.05/family,len(results)-1);upper=x.mean(0)+critical*x.std(0,ddof=1)/np.sqrt(len(results));reserve=c.get('wasserstein_radius',0)/(1-c['confidence']);checks=[]
    for k in range(x.shape[1]):
        limit=float(bases[k]*c['funding_budget_fraction']/wealth) if k<len(steps) else c['cml_budget'] if k==len(steps) else c['loss_budget'];high=float(upper[k].max());checks.append(dict(name=f'Executed funding week{steps[k]}' if k<len(steps) else 'Executed shadow path-loss tail' if k==len(steps) else 'Executed shadow terminal-loss tail',empirical_upper=high,stress_reserve=reserve,limit=limit,passed=bool(high+reserve<=limit)))
    flags=np.concatenate([r['funded'] for r in results]);cp=lower_bound(int(flags.sum()),len(flags));weighted={key:[float(r['funded']@(p/p.sum())) for r,p in zip(results,ps)] for key,ps in [('nominal',nominal),('stressed',stressed)]};strict=bool(cp>=.99 and min([v for a in weighted.values() for v in a])>=.99);net=np.concatenate([r['terminal_net'] for r in results]);from emfin_v2.dynamic_policy import ce
    return dict(overall_pass=bool(strict and all(z['passed'] for z in checks)),checks=checks,strict_pass=strict,fully_paid_paths=int(flags.sum()),paths=len(flags),funded_fraction=float(flags.mean()),reference_lower95=cp,weighted=weighted,common_cara_ledger_ce=ce(net,c['risk_tolerance']),net_mean=float(net.mean()),net_quantiles=np.quantile(net,[.05,.5,.95]).tolist(),cost_mean=float(np.mean([r['cost'].mean() for r in results])),turnover_mean=float(np.mean([r['turnover'].mean() for r in results])),trades_mean=float(np.mean([r['trades'].mean() for r in results])),largest_unpaid=max(float(r['shortfalls'].max()) for r in results),breaches=[z['name'] for z in checks if not z['passed']]+([] if strict else ['Joint paid-all99%screen']),wasserstein_certified=False,economic_probability_guarantee=False,scope='Shared executed-policy judge: actual unpaid calls and shadow marked wealth including actually-paid withdrawals accrued at cash. Batch/CP bounds conditional on frozen law/policy only. Legacy W1 additive reserve is an explicit stress screen, NOT a certificate for nonlinear feedback.')
