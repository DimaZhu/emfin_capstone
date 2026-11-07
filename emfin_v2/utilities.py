"""Explicit utility arguments. HARA payment floor is power utility on surplus."""
import numpy as np
from scipy.special import logsumexp
KINDS=('cara','mean_variance','crra_gross','hara_payment_floor','kinked_shortfall')


def specification(kind,wealth,tolerance,provision,settings=None):
    if kind not in KINDS:raise ValueError('unknown allocation objective')
    settings=settings or {};p=np.asarray(provision,float)
    if not np.isfinite(p).all() or wealth<=0 or tolerance<=0:raise ValueError('finite utility inputs required')
    floor=float(p.mean());surplus=wealth-floor
    gamma=float(settings.get('gamma',wealth/tolerance if kind=='crra_gross' else surplus/tolerance))
    if kind=='hara_payment_floor' and (surplus<=0 or not np.allclose(p,floor,rtol=0,atol=1e-6)):raise ValueError('HARA matching requires positive initial surplus and deterministic terminal payment floor')
    if kind in ('crra_gross','hara_payment_floor') and (not np.isfinite(gamma) or gamma<=0):raise ValueError('positive finite power gamma required')
    penalty=float(settings.get('shortfall_penalty',4.));margin=float(settings.get('domain_margin',1e-8))
    if not np.isfinite(penalty) or penalty<0 or not np.isfinite(margin) or margin<=0:raise ValueError('valid shortfall penalty and positive domain margin required')
    return dict(kind=kind,gamma=gamma if kind in ('crra_gross','hara_payment_floor') else None,shortfall_penalty=penalty,domain_margin=margin,terminal_payment_floor=floor,initial_surplus=surplus,argument='gross terminal marked wealth' if kind=='crra_gross' else 'terminal surplus after payments',scale=wealth if kind!='hara_payment_floor' else surplus,local_absolute_aversion=1/tolerance if kind in ('cara','crra_gross','hara_payment_floor') and not settings.get('gamma') else None,scope='Engineering preference comparison, not client-calibrated. HARA(gross minus floor) is CRRA on surplus at the same gamma. Native CEs with gross/net arguments are not cross-family rankings.')


def convex_objective(gross,net,p,wealth,tolerance,provision,kind,settings=None):
    import cvxpy as cp
    spec=specification(kind,wealth,tolerance,provision,settings);extra=[]
    if kind in ('crra_gross','hara_payment_floor'):
        x=gross if kind=='crra_gross' else net;extra=[x>=spec['domain_margin']];z=x*wealth/spec['scale'];g=spec['gamma']
        u=cp.log(z) if abs(g-1)<1e-10 else cp.power(z,1-g)/(1-g)
        objective=-p@u
    elif kind=='kinked_shortfall':objective=-p@net+spec['shortfall_penalty']*(p@cp.pos(-net))
    else:raise ValueError('use existing exact CARA/mean-variance route')
    return objective,extra,spec


def native_ce(kind,gross,net,p,wealth,tolerance,provision,settings=None):
    spec=specification(kind,wealth,tolerance,provision,settings);x=np.asarray(gross if kind=='crra_gross' else net,float);q=np.asarray(p,float)
    if x.ndim!=1 or q.shape!=x.shape or not np.isfinite(x).all() or not np.isfinite(q).all() or (q<0).any() or q.sum()<=0:raise ValueError('finite aligned utility outcomes/probabilities required')
    q=q/q.sum();support=q>0;bad=int(np.count_nonzero(x<=0)) if kind in ('crra_gross','hara_payment_floor') else 0
    if bad:return dict(available=False,domain_violations=bad,ce=None,**spec)
    if kind=='cara':ce=-tolerance*logsumexp(np.log(q[support])-x[support]/tolerance)
    elif kind in ('crra_gross','hara_payment_floor'):
        g=spec['gamma'];logs=np.log(x[support]);ce=float(np.exp(q[support]@logs if abs(g-1)<1e-10 else logsumexp(np.log(q[support])+(1-g)*logs)/(1-g)))
    elif kind=='kinked_shortfall':
        expected=float(q@(x-spec['shortfall_penalty']*np.maximum(-x,0)));ce=expected if expected>=0 else expected/(1+spec['shortfall_penalty'])
    else:raise ValueError('native mean-variance CE is not expected utility')
    return dict(available=bool(np.isfinite(ce)),ce=float(ce) if np.isfinite(ce) else None,domain_violations=bad,**spec)
