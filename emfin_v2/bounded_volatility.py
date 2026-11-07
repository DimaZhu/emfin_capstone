"""Declared capped-EWMA variance, not an ordinary GARCH or a hidden return cap.

Bounds are fixed multiples of the past covariance diagonal at each origin.
All finite-horizon price power moments exist under the Gaussian mixture.
"""
import numpy as np

DEFAULT=dict(decay=.94,floor=.05,cap=9.)


def settings(c):
    x=dict(DEFAULT,**c.get('bounded_volatility',{}))
    if set(x)!=set(DEFAULT) or any(not isinstance(v,(int,float)) or not np.isfinite(v) for v in x.values()) or not 0<x['decay']<1 or not 0<x['floor']<=1<=x['cap']:
        raise ValueError('bounded variance requires decay in(0,1),0<floor<=1<=finite cap')
    return x


def update(variance,shock,base,decay=.94,floor=.05,cap=9.):
    # Zero baseline factors stay identically zero, including cash.
    variance=np.asarray(variance,float);shock=np.asarray(shock,float);base=np.asarray(base,float)
    if not np.isfinite(variance).all() or not np.isfinite(shock).all() or not np.isfinite(base).all() or (base<0).any():raise ValueError('finite variance,shock,nonnegative baseline required')
    with np.errstate(over='ignore'):
        raw=decay*variance+(1-decay)*shock**2
    nxt=np.clip(raw,floor*base,cap*base)
    return nxt,(raw<floor*base)&(base>0),(raw>cap*base)&(base>0)


def initial_state(history,mean,base,**params):
    x=np.asarray(history,float);mu=np.asarray(mean,float);b=np.asarray(base,float)
    if x.ndim!=2 or len(x)<52 or mu.shape!=(x.shape[1],) or b.shape!=mu.shape or not np.isfinite(x).all() or not np.isfinite(mu).all():raise ValueError('finite aligned past history of52rows required')
    h=b.copy();low=np.zeros(len(b),int);high=low.copy()
    for row in x:
        h,l,u=update(h,row-mu,b,**params);low+=l;high+=u
    return h,dict(lower=low.tolist(),upper=high.tolist(),past_rows=len(x))


def transform(innovations,history,mean,base,params=None,return_diagnostics=False):
    """Scale joint baseline shocks without changing their Gaussian latent rows.

    At step t state depends only on history and steps before t. Each n,h,d
    input shock has baseline diagonal variance base; random mixture scales
    are already applied. Property keeps its separately constructed latent link.
    """
    params=dict(DEFAULT,**(params or {}));settings(dict(bounded_volatility=params))
    x=np.asarray(innovations,float);b=np.asarray(base,float)
    if x.ndim!=3 or x.shape[-1]!=len(b) or not np.isfinite(x).all():raise ValueError('finite aligned n,h,d innovations required')
    start,past_hits=initial_state(history,mean,b,**params);h=np.broadcast_to(start,(len(x),len(b))).copy();out=np.zeros_like(x);low=np.zeros(len(b),int);high=low.copy();minimum=np.full(len(b),np.inf);maximum=np.zeros(len(b))
    for t in range(x.shape[1]):
        ratio=np.sqrt(np.divide(h,b,out=np.zeros_like(h),where=b>0));out[:,t]=x[:,t]*ratio
        minimum=np.minimum(minimum,h.min(0));maximum=np.maximum(maximum,h.max(0))
        h,l,u=update(h,out[:,t],b,**params);low+=l.sum(0);high+=u.sum(0)
    if not np.isfinite(out).all():raise ValueError('bounded innovation arithmetic overflow')
    diagnostics=dict(settings=params,baseline_variance=b.tolist(),initial_variance=start.tolist(),minimum=minimum.tolist(),maximum=maximum.tolist(),next_minimum=h.min(0).tolist(),next_maximum=h.max(0).tolist(),past_hits=past_hits,simulated_lower_hits=low.tolist(),simulated_upper_hits=high.tolist(),simulated_updates=len(x)*x.shape[1],scope='Variance state cap, not a return cap or tail-calibration guarantee. Hits are update counts per factor.')
    return (out,diagnostics) if return_diagnostics else out


def log_moment_bound(mean,base,exposure,weeks,cap=9.,max_mixture_variance=3.25):
    """Conservative marginal/joint log-MGF upper bound, NOT an exact moment.

    Cauchy-Schwarz bounds b'DRD b by (sum|b_j|sqrt(cap*base_j))^2
    for any correlation matrix. Iterated conditional expectation gives H times
    this one-step bound. For property include its Gaussian-linear loading bound.
    """
    mu=np.asarray(mean,float);v=np.asarray(base,float);b=np.asarray(exposure,float)
    if mu.ndim!=1 or b.shape!=mu.shape or v.shape!=mu.shape or not np.isfinite(np.r_[mu,v,b,cap,max_mixture_variance]).all() or (v<0).any() or cap<1 or max_mixture_variance<=0 or type(weeks) is not int or weeks<1:raise ValueError('finite aligned bound inputs and whole positive horizon required')
    return float(weeks*(b@mu+.5*max_mixture_variance*(np.abs(b)@np.sqrt(cap*v))**2))
