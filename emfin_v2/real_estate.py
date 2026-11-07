"""Explicit RE assumptions, not property forecasts or executable sale advice."""
from functools import lru_cache
import numpy as np

DEFAULTS = dict(smoothing_alpha=0., net_rental_yield=0., sale_week=0,
                sale_delay_weeks=12, history_case='central',forward_mode='view',forward_log_drift=.04)


def assumptions(re):
    return dict(DEFAULTS, **re)


def validate(re):
    r=assumptions(re)
    for k in ['smoothing_alpha','net_rental_yield','forward_log_drift']:
        if not isinstance(r[k],(int,float)) or not np.isfinite(r[k]):
            raise ValueError('RE '+k+' must be finite')
    if not 0<=r['smoothing_alpha']<=.8:raise ValueError('RE smoothing alpha must be 0-.8')
    if not 0<=r['net_rental_yield']<=.2:raise ValueError('RE net rental yield must be 0-20%')
    for k in ['sale_week','sale_delay_weeks']:
        if type(r[k]) is not int or not 0<=r[k]<=260:raise ValueError('RE '+k+' must be 0-260 whole weeks')
    if r['forward_mode'] not in ('view','sample'):raise ValueError('unknown RE forward mode')
    if not -.2<=r['forward_log_drift']<=.3:raise ValueError('RE forward log drift must be -20% to 30%')
    if r['history_case'] not in ('central','cautious','optimistic'):raise ValueError('unknown RE history case')


def unsmooth(returns,alpha):
    """Invert r_t = alpha*r_(t-1) + (1-alpha)*u_t on monthly log returns.

    Alpha is the weight on stale information. It is assumed, not inferred from
    short-window autocorrelation. Alpha zero is an exact identity.
    """
    x=np.asarray(returns,float)
    if x.ndim!=1 or len(x)<3 or not np.isfinite(x).all() or not 0<=alpha<=.8:
        raise ValueError('invalid monthly returns or smoothing alpha')
    return x.copy() if alpha==0 else (x[1:]-alpha*x[:-1])/(1-alpha)


@lru_cache(maxsize=32)
def history_statistics(returns,alpha,replicates=2000,block=3):
    x=unsmooth(returns,alpha);n=len(x)
    # Circular moving-block bootstrap preserves short local serial dependence.
    rng=np.random.default_rng(20261107)
    starts=rng.integers(0,n,(replicates,(n+block-1)//block))
    idx=(starts[:,:,None]+np.arange(block))%n
    samples=x[idx.reshape(replicates,-1)[:,:n]]
    drift=samples.mean(1)*12;vol=samples.std(1,ddof=1)*np.sqrt(12)
    return dict(annual_log_drift=float(x.mean()*12),annual_vol=float(x.std(ddof=1)*np.sqrt(12)),
        drift_range=np.quantile(drift,[.05,.5,.95]).tolist(),
        vol_range=np.quantile(vol,[.05,.5,.95]).tolist(),return_count=n,
        method=f'Circular moving-block bootstrap, {block}-month blocks, {replicates} resamples, fixed seed; marginal 5/50/95 percentiles, not a joint confidence region or forecast',
        smoothing_alpha=float(alpha))


def calibration(re):
    r=assumptions(re);validate(r)
    result=dict(annual_log_drift=r['annual_drift'],annual_vol=r['annual_vol'],
                source=r.get('source','synthetic'),assumptions=r,
                dependence_note='User-set Pearson correlation of weekly RE price shocks with equal-weight equity log shocks in the scenario model; not estimated from Abu Dhabi history. Other cross-asset correlations are induced by the shared factor model, not independently set.',
                rent_note='User-set net unlevered rental yield after operating costs, vacancy and taxes; paid weekly on initial property capital and reinvested in MMKT. No debt, FX or tenant/default model.')
    if r.get('source')=='abu_dhabi_private':
        from emfin_v2.abu_dhabi import default_path,local_calibration,monthly_returns
        observed=local_calibration()
        if observed is None:raise ValueError('Abu Dhabi private import unavailable; import locally or choose synthetic')
        returns=monthly_returns(str(default_path()))
        stats=history_statistics(tuple(returns),r['smoothing_alpha'])
        result.update(stats,observed=observed)
        if r['history_case']=='cautious':result.update(annual_log_drift=stats['drift_range'][0],annual_vol=stats['vol_range'][2])
        if r['history_case']=='optimistic':result.update(annual_log_drift=stats['drift_range'][2],annual_vol=stats['vol_range'][0])
        result['history_note']='Central uses sample moments. Cautious/optimistic combine opposite marginal bootstrap endpoints as sensitivity cases, not a joint probability statement. A short growth window is not a long-run expected return.'
    else:
        result['history_note']='Synthetic annual drift/vol are explicit inputs. No observed-history uncertainty or unsmoothing is inferred for synthetic data.'
    result['sample_implied_log_drift']=result['annual_log_drift']
    result['forward_log_drift']=r['forward_log_drift'] if r['forward_mode']=='view' else result['annual_log_drift']
    result['annual_log_drift']=result['forward_log_drift']
    result['forward_note']='4% default is an illustrative long-run price-log-return view, not a data estimate, calibrated prior, conservative bound or promised return. Net rent is separate. View mode pins the terminal log-price mean through entropy pooling; sample mode is an explicitly optional boom-window sensitivity.'
    return result


def cash_and_mark(price_paths,growth,re):
    """Per-dollar property mark and spendable cash for a fixed planned sale.

    sale_week=0 means no sale. Contract price is the scenario mark at sale_week,
    less the transaction haircut; proceeds settle after sale_delay_weeks. Rent
    stops at agreement. Pending proceeds have contractual value but are not cash.
    No reinvestment in property, repeated full sales, or dynamic selling policy.
    """
    r=assumptions(re);validate(r)
    price=np.asarray(price_paths,float);g=np.asarray(growth,float)
    if price.shape!=g.shape or price.ndim!=2 or not np.isfinite(price).all() or (price<0).any() or not np.isfinite(g).all() or (g<=0).any():raise ValueError('RE price and money-market paths must align')
    n,h=price.shape;week=r['sale_week'];settle=week+r['sale_delay_weeks']
    rent=np.zeros_like(price)
    for t in range(h):
        rent[:,t]=(rent[:,t-1]*g[:,t]/g[:,t-1] if t else 0.)
        if week==0 or t+1<=week:rent[:,t]+=r['net_rental_yield']/52
    mark=price+rent;cash=rent.copy()
    if 1<=week<=h:
        proceeds=price[:,week-1]*(1-r['liquidation_haircut'])
        for t in range(week-1,h):
            available=t+1>=settle
            value=proceeds*(g[:,t]/g[:,settle-1] if available else 1.)
            mark[:,t]=rent[:,t]+value
            if available:cash[:,t]+=value
    return mark,cash


class ScenarioDraw(tuple):
    """Five legacy-compatible fields plus a distinct funding-price path."""
    def __new__(cls,values,funding_paths,re_price_logs=None):
        obj=super().__new__(cls,values);obj.funding_paths=funding_paths;obj.re_price_logs=re_price_logs;return obj


def funding_paths(draw):
    return getattr(draw,'funding_paths',draw[0])
