"""Joint all-date cash-ledger model check, not an economic or W1 guarantee."""
import numpy as np
from scipy.stats import beta
from emfin_v2.ledger import cash_first


def lower_bound(successes,n,alpha=.05):
    if type(n) is not int or type(successes) is not int or n<1 or not 0<=successes<=n or not 0<alpha<1:raise ValueError('valid whole successes/trials and alpha required')
    return 0. if successes==0 else float(beta.ppf(alpha,successes,n-successes+1))


def check(c,draws,allocation,nominal=None,stressed=None):
    if not draws:raise ValueError('nonempty generated scenario sets required')
    if any(not np.array_equal(d[2],draws[0][2]) or not np.array_equal(d[3],draws[0][3]) for d in draws):raise ValueError('same dated payment event required across batches')
    audits=[cash_first(c,d,allocation) for d in draws];flags=[a['funded'] for a in audits];flat=np.concatenate(flags);n=len(flat);s=int(flat.sum());target=.99
    ref=float(flat.mean());bound=lower_bound(s,n);rates={}
    for name,probabilities in [('nominal',nominal),('stressed',stressed)]:
        if probabilities is None:continue
        if len(probabilities)!=len(draws):raise ValueError('aligned probability batches required')
        fractions=[]
        for success,p in zip(flags,probabilities):
            p=np.asarray(p,float)
            if p.shape!=success.shape or not np.isfinite(p).all() or (p<0).any() or p.sum()<=0:raise ValueError('finite aligned nonnegative scenario probabilities required')
            fractions.append(float(success@(p/p.sum())))
        rates[name]=dict(mean=float(np.mean(fractions)),minimum_batch=float(min(fractions)),batches=fractions)
    iid_assumption=not bool(c.get('scenario_archives'))
    worst=min([bound,*[z['minimum_batch'] for z in rates.values()]])
    passed=bool(iid_assumption and worst>=target)
    return dict(mode='pay_all_99',target=target,paths=n,fully_funded_paths=s,reference_fraction=ref,reference_lower95=bound,weighted=rates,passed=passed,upper_failure=1-worst,generated_iid_assumption=iid_assumption,roundoff_dollars=1e-6,largest_unpaid=max(float(a['payment_shortfalls'].max()) for a in audits),wasserstein_certified=False,economic_probability_guarantee=False,scope='Joint event: every dated payment in full under the fixed cash-first rule. Exact one-sided95%binomial bound assumes independent generated paths conditional on the fitted model and frozen portfolio. Not coverage for EP-weighted estimates, validation-selected models, historical/economic uncertainty or W1 cash-ledger robustness.')
