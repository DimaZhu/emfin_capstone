"""Past-only EWMA filtered historical innovations with joint row resampling.

This is a declared EWMA FHS variant, not an exact replication of GARCH FHS.
The forecast volatility recurses on simulated shocks. Residual row dependence
across assets/FX is preserved. No future row enters a volatility estimate.
"""
import numpy as np


def stationary_indices(length,n_samples,size,mean_block,seed):
    if min(length,n_samples,size)<1 or mean_block<1:raise ValueError('positive dimensions and mean block>=1 required')
    rng=np.random.default_rng(seed);out=np.zeros((n_samples,size),int);out[:,0]=rng.integers(length,size=n_samples)
    for t in range(1,size):
        restart=rng.random(n_samples)<1/mean_block
        out[:,t]=np.where(restart,rng.integers(length,size=n_samples),(out[:,t-1]+1)%length)
    return out


def filter_ewma(history,decay=.94):
    x=np.asarray(history,float)
    if x.ndim!=2 or len(x)<52 or not np.isfinite(x).all() or not 0<decay<1:raise ValueError('finite52-row history and EWMA decay in (0,1) required')
    # Initial52 weeks are warm-up, never residual observations. Then forecast
    # variance at t uses shocks through t-1, not the observation being scaled.
    center=x[:52].mean(0);initial=np.mean((x[:52]-center)**2,axis=0)
    variance=np.maximum(initial,1e-12);residual=[]
    for row in x[52:]:
        shock=row-center;residual.append(shock/np.sqrt(variance));variance=decay*variance+(1-decay)*shock**2
    if len(residual)<20:raise ValueError('FHS requires at least72 past weeks including warm-up')
    z=np.asarray(residual);z-=z.mean(0);scale=np.sqrt(np.mean(z*z,axis=0));z/=np.where(scale>1e-12,scale,1.)
    return z,variance


def fhs_innovations(history,n,h,seed,decay=.94):
    z,variance=filter_ewma(history,decay);rng=np.random.default_rng(seed);v=np.broadcast_to(variance,(n,len(variance))).copy();out=np.zeros((n,h,len(variance)))
    rows=rng.integers(len(z),size=(n,h))
    for t in range(h):
        shock=np.sqrt(v)*z[rows[:,t]];out[:,t]=shock;v=decay*v+(1-decay)*shock**2
    if not np.isfinite(out).all():raise ValueError('FHS volatility recursion overflowed')
    return out
