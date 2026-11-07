"""Past-only empirical shift-stress radius, not a confidence calibration."""
import csv,calendar
from datetime import date,timedelta
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


def balanced_distances(blocks,repetitions=64,seed=20261107):
    x=np.asarray(blocks,float)
    if x.ndim<2 or len(x)<8 or not np.isfinite(x).all():raise ValueError('at least8finite full path blocks required')
    # max absolute primitive-coordinate path difference; deterministic liabilities
    # have zero displacement. This is the price term of declared max_path cost.
    cost=cdist(x.reshape(len(x),-1),x.reshape(len(x),-1),metric='chebyshev');rng=np.random.default_rng(seed);half=len(x)//2;values=[]
    for _ in range(repetitions):
        order=rng.permutation(len(x));left=order[:half];right=order[-half:];d=cost[np.ix_(left,right)];i,j=linear_sum_assignment(d);values.append(float(d[i,j].mean()))
    return values


def calibrate(c,frame):
    from emfin_v2.real_estate import cash_and_mark
    from emfin_v2.singapore import ROOT
    if c['horizon_weeks']!=52:raise ValueError('empirical annual path radius requires52week horizon')
    if not c.get('asset_registry') or c.get('wasserstein_metric')!='max_path':raise ValueError('empirical radius requires actual-instrument registry and max_path metric')
    if c.get('history_end'):frame=frame.loc[frame.index<=pd.Timestamp(c['history_end'])]
    if not frame.index.is_monotonic_increasing or not frame.index.is_unique:raise ValueError('physical chronological unique history required')
    liquid=len(c['liquidity_haircuts']);h=52;blocks=[];dates=[];quarter=[]
    if c['real_estate']['enabled']:
        if c['real_estate'].get('source')!='singapore_ura':raise ValueError('empirical property calibration requires the explicit Singapore source')
        with (ROOT/'ura_private_residential_quarterly.csv').open()as f:
            for row in csv.DictReader(f):
                if row['property_type']==c['real_estate']['sg_property_type']:
                    year=int(row['quarter'][:4]);month=int(row['quarter'][-1])*3;quarter.append((date(year,month,calendar.monthrange(year,month)[1])+timedelta(days=45),float(row['index'])))
        def index_at(day):return [v for release,v in quarter if release<=pd.Timestamp(day).date()][-1]
    for start in range(0,len(frame)-h+1,h):
        data=frame.iloc[start:start+h];paths=np.exp(np.cumsum(data.iloc[:,:liquid].to_numpy(),axis=0))[None,:,:];growth=paths[:,:,c['cash_index']].copy();paths*=1-np.asarray(c['liquidity_haircuts']);funding=paths.copy()
        if c['real_estate']['enabled']:
            initial=index_at(data.index[0]-pd.Timedelta(days=7));local=np.array([[index_at(day)/initial for day in data.index]]);fx=np.exp(np.cumsum(data.iloc[:,-1].to_numpy()))[None,:] if c['fx']['enabled'] else None;mark,spendable=cash_and_mark(local,growth,c['real_estate'],fx_paths=fx);paths=np.concatenate([paths,mark[:,:,None]],axis=2);funding=np.concatenate([funding,spendable[:,:,None]],axis=2)
        blocks.append(np.r_[paths.ravel(),funding.ravel()]);dates.append(dict(first=str(data.index[0].date()),last=str(data.index[-1].date())))
    common=dict(blocks=len(blocks),block_weeks=52,dates=dates,last_observation=str(frame.index[-1].date()),scope='Empirical past-path half-split distribution-shift stress calibration, NOT90%coverage or a confidence-calibrated ball. Latest property vintage with assumed45day lag; no observed cash/liability variation is not evidence of no uncertainty. Not calibrated to future funding pass or utility.')
    if len(blocks)<8:return dict(available=False,reason='At least8complete52week blocks required; no manual/zero fallback',**common)
    distances=balanced_distances(blocks);radius=float(np.quantile(distances,.9,method='inverted_cdf'));buffer=c['wealth']*radius/(1-c['confidence']);smallest=min(p['amount']*c['funding_budget_fraction'] for p in c['liabilities'])
    return dict(available=True,radius=radius,quantile=.9,repetitions=64,seed=20261107,distances=distances,unavoidable_funding_buffer_dollars=buffer,smallest_funding_budget=smallest,budget_conflict=buffer>smallest,**common)
