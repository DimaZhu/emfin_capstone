"""Read-only judge of frozen holdings. Never selects or repairs portfolios.

The simultaneous conditional batch bounds are Monte Carlo diagnostics, not
historical/economic coverage. Measures include reference, nominal and stress.
A common RU threshold covers their finite convex hull, not an arbitrary law.
"""
import numpy as np
from scipy.stats import t
from emfin_v2.real_estate import funding_paths
from emfin_v2.toolbox.wasserstein import penalty


def common_tail(losses, measures, confidence, nonnegative_threshold=True):
    """Exact finite-support min_eta max_measure RU envelope, no optimizer.

Between adjacent loss atoms each RU objective is affine. A minimum of their
upper envelope is at an atom or a pairwise line crossing. Include zero when
eta must be nonnegative. This also handles fractional tail atoms.
"""
    x=np.asarray(losses,float).ravel();p=np.asarray(measures,float)
    if p.ndim!=2 or p.shape[1]!=len(x) or not len(x) or not np.isfinite(x).all() or not np.isfinite(p).all() or (p<0).any() or (p.sum(1)<=0).any() or not 0<confidence<1:
        raise ValueError('finite aligned losses and probabilities required')
    p=p/p.sum(1)[:,None];order=np.argsort(x);x=x[order];p=p[:,order]
    knots=np.unique(np.r_[0.,x[x>=0]]) if nonnegative_threshold else np.unique(x)
    # Tail integrals strictly above eta. Repeated atoms cause no discontinuity.
    tail_p=np.cumsum(p[:,::-1],axis=1)[:,::-1]
    tail_x=np.cumsum((p*x)[:,::-1],axis=1)[:,::-1]
    tail_p=np.c_[tail_p,np.zeros(len(p))];tail_x=np.c_[tail_x,np.zeros(len(p))]
    ix=np.searchsorted(x,knots,side='right');slope=1-tail_p[:,ix]/(1-confidence);intercept=tail_x[:,ix]/(1-confidence)
    values=slope*knots+intercept;best=float(values.max(0).min())
    if len(knots)>1:
        for i in range(len(p)):
            for j in range(i):
                denom=slope[i,:-1]-slope[j,:-1]
                cross=np.divide(intercept[j,:-1]-intercept[i,:-1],denom,out=np.full(len(denom),np.nan),where=np.abs(denom)>1e-14)
                ok=(cross>=knots[:-1])&(cross<=knots[1:])
                if ok.any():best=min(best,float((slope[:,:-1][:,ok]*cross[ok]+intercept[:,:-1][:,ok]).max(0).min()))
    return best


def evaluate(c, draws, allocation, nominal, stressed):
    """All budgets/holdings under frozen independent draw sets.

No numerical acceptance tolerance: risk comparisons use the exact declared
budget. Holdings residuals have explicit absolute weight tolerances only.
"""
    from emfin_v2.default_run import holding_bounds
    a=np.asarray(allocation,float);wealth=c['wealth'];w=a/wealth
    if len(draws)<2 or len(nominal)!=len(draws) or len(stressed)!=len(draws):raise ValueError('at least two aligned evaluation batches required')
    if a.ndim!=1 or not np.isfinite(a).all():raise ValueError('finite allocation required')
    mins,fixed=holding_bounds(c,len(a));tol=1e-7
    holding_checks=[dict(name='Fully invested',current=float(abs(w.sum()-1)),limit=tol),dict(name='No shorting',current=float(max(0,-w.min())),limit=tol),dict(name='Minimum holdings residual',current=float(max(0,np.max(mins-w))),limit=tol)]
    holding_checks += [dict(name=f'Fixed holding {i}',current=float(abs(w[i]-v)),limit=tol) for i,v in fixed.items()]
    for item in holding_checks:item['passed']=item['current']<=item['limit']
    keys=['reference','nominal','stressed','common_hull'];n_dates=len(draws[0][2]);batches=[]
    for draw,q,qs in zip(draws,nominal,stressed):
        paths,amounts,steps,bases,growth=draw
        if paths.shape[2]!=len(a) or len(steps)!=n_dates or not np.array_equal(steps,draws[0][2]) or not np.array_equal(bases,draws[0][3]):raise ValueError('unaligned evaluation draw')
        measures=np.array([np.full(len(paths),1/len(paths)),q,qs]);values=paths@a/wealth;spendable=funding_paths(draw)@a
        losses=[]
        for i,step in enumerate(steps):
            required=amounts[:,i].copy()
            for j,prior in enumerate(steps):
                if prior<step or (prior==step and j<i):required+=amounts[:,j]*growth[:,step-1]/growth[:,prior-1]
            losses.append(np.maximum(required-spendable[:,step-1],0)/wealth)
        losses.extend([np.maximum(0,1-values).max(1),1-values[:,-1]])
        batch=[]
        for k,loss in enumerate(losses):
            nonnegative=k!=len(losses)-1
            batch.append([common_tail(loss,[p],c['confidence'],nonnegative) for p in measures]+[common_tail(loss,measures,c['confidence'],nonnegative)])
        batches.append(batch)
    x=np.asarray(batches);familysize=x.shape[1]*x.shape[2]
    critical=t.ppf(1-.05/familysize,len(draws)-1)
    mean=x.mean(0);high=mean+critical*x.std(0,ddof=1)/np.sqrt(len(draws))
    checks=[];market_buffer=penalty(w,c.get('wasserstein_radius',0),c['confidence'],metric=c.get('wasserstein_metric','legacy_l1'));funding_buffer=penalty(w,c.get('wasserstein_radius',0),c['confidence'],c.get('wasserstein_liability_scale',.01),metric=c.get('wasserstein_metric','legacy_l1'))
    for k in range(n_dates+2):
        funding=k<n_dates;scale=wealth if funding else 1.
        limit=draws[0][3][k]*c['funding_budget_fraction'] if funding else c['cml_budget'] if k==n_dates else c['loss_budget']
        buffer=(funding_buffer if funding else market_buffer)*scale
        bounds={name:float(high[k,i]*scale+buffer) for i,name in enumerate(keys)}
        upper=max(bounds.values());checks.append(dict(kind='funding' if funding else 'path_loss' if k==n_dates else 'terminal_loss',name=f'Held-out funding: week {int(draws[0][2][k])}' if funding else 'Held-out path-loss tail' if k==n_dates else 'Held-out terminal-loss tail',payout_index=k if funding else None,week=int(draws[0][2][k]) if funding else None,upper=upper,limit=float(limit),passed=bool(upper<=limit),unit='usd' if funding else 'fraction',measure_upper=bounds,mean={name:float(mean[k,i]*scale) for i,name in enumerate(keys)},buffer=float(buffer)))
    funding_pass=all(z['passed'] for z in checks if z['kind']=='funding');overall=funding_pass and all(z['passed'] for z in checks) and all(z['passed'] for z in holding_checks)
    funding=[z for z in checks if z['kind']=='funding'];worst=max(funding,key=lambda z:z['upper']/z['limit'] if z['limit']>0 else (float('inf') if z['upper']>0 else 0))
    return dict(funding_pass=funding_pass,overall_pass=bool(overall),checks=checks,holdings=holding_checks,breaches=[z['name'] for z in checks+holding_checks if not z['passed']],worst_funding_week=worst['week'],worst_funding_index=worst['payout_index'],batch_estimates=x.tolist(),measure_names=keys,interval=dict(confidence=.95,adjustment='Bonferroni one-sided conditional batch Student-t bounds',comparisons=familysize,batches=len(draws),scope='Conditional Monte Carlo diagnostic across listed checks and measures. No economic/model coverage; zero-width intervals do not bound unseen tails.'),scope='Frozen holdings; independent final draws; no repair or selection on final results. Common-threshold bound covers reference/nominal/stressed finite convex hull. Current provisioning convention, not a trading ledger.')
