"""Frozen-protocol past-only marginal forecasts, not portfolio optimization.

All scores are losses (smaller is better). Gaussian-mixture CRPS and empirical
CRPS are exact marginal formulas, not Monte Carlo density approximations.
"""
from pathlib import Path
import json,time,hashlib,subprocess
import numpy as np
import pandas as pd
from scipy.special import ndtr,logsumexp
from scipy.optimize import minimize,brentq
from scipy.signal import lfilter
from emfin_v2.default_run import load_config,setup
from emfin_v2.registry_runtime import fit_frame
from emfin_v2.historical_simulation import filter_ewma

P=np.array([.9,.1]);V=np.array([.75,3.25]);MODELS=('iid_mix','ewma_mix','garch_mix','ewma_fhs')
PROTOCOL=Path('docs/MODEL_ADEQUACY_PROTOCOL.md')


def absolute_normal(mean,sd):
    mean,sd=np.broadcast_arrays(np.asarray(mean,float),np.asarray(sd,float))
    if (sd<0).any() or not np.isfinite(mean).all() or not np.isfinite(sd).all():raise ValueError('finite means and nonnegative sd required')
    z=np.divide(mean,sd,out=np.zeros_like(mean),where=sd>0)
    result=2*sd*np.exp(-.5*z*z)/np.sqrt(2*np.pi)+mean*(2*ndtr(z)-1)
    return np.where(sd>0,result,np.abs(mean))


def mixture_crps(y,mu,variance,p=P,v=V):
    sd=np.sqrt(variance*np.asarray(v));p=np.asarray(p)
    return float(p@absolute_normal(y-mu,sd)-.5*np.sum(p[:,None]*p[None,:]*absolute_normal(0.,np.sqrt(sd[:,None]**2+sd[None,:]**2))))


def empirical_crps(y,support):
    x=np.sort(np.asarray(support,float));n=len(x)
    if not n or not np.isfinite(x).all() or not np.isfinite(y):raise ValueError('finite nonempty empirical support required')
    return float(np.abs(x-y).mean()-np.dot(2*np.arange(1,n+1)-n-1,x)/n**2)


def garch_variances(shocks,omega,alpha,beta,initial):
    """v[t] conditions on shocks[:t]; extra final entry predicts next row."""
    x=np.asarray(shocks,float)
    if x.ndim!=1 or not np.isfinite(x).all() or min(omega,initial)<=0 or min(alpha,beta)<0 or alpha+beta>.99900001:raise ValueError('valid finite stationary variance inputs required')
    forcing=np.r_[0.,omega+alpha*x*x]
    variance=lfilter([1.],[1.,-beta],forcing,zi=[initial])[0]
    if (variance<=0).any() or not np.isfinite(variance).all():raise ValueError('invalid variance recursion')
    return variance


def fit_garch(shocks):
    x=np.asarray(shocks,float)
    if x.ndim!=1 or len(x)<104 or not np.isfinite(x).all() or np.std(x)<=0:raise ValueError('nondegenerate104-row shock history required')
    unit=float(np.sqrt(np.mean(x*x)));e=x/unit;initial=max(float(np.mean(e[:52]**2)),1e-8)
    def objective(theta):
        omega,alpha,beta=theta
        if alpha+beta>.99900001:return 1e10+(alpha+beta)*1e5
        h=garch_variances(e,omega,alpha,beta,initial)[:-1]
        return float(np.mean(np.log(h[52:])+e[52:]**2/h[52:]))
    attempts=[];success=[]
    for alpha,beta in [(.05,.90),(.10,.80),(.15,.60)]:
        r=minimize(objective,[1-alpha-beta,alpha,beta],method='SLSQP',bounds=[(1e-8,5.),(0.,.998),(0.,.998)],constraints=[dict(type='ineq',fun=lambda t:.999-t[1]-t[2])],options=dict(maxiter=200,ftol=1e-9))
        valid=bool(r.success and np.isfinite(r.fun) and r.x[1]+r.x[2]<=.99900001 and r.fun<1e9)
        attempts.append(dict(success=valid,status=int(r.status),message=str(r.message),objective=float(r.fun),parameters=r.x.tolist(),iterations=int(r.nit)))
        if valid:success.append(r)
    if not success:return dict(available=False,attempts=attempts,scope='All fixed starts failed, no fallback or omitted fit')
    r=min(success,key=lambda r:r.fun);omega,alpha,beta=r.x;h=garch_variances(e,omega,alpha,beta,initial)*unit**2
    return dict(available=True,omega=float(omega*unit**2),alpha=float(alpha),beta=float(beta),next_variance=float(h[-1]),variance=h[:-1].tolist(),attempts=attempts,fit_objective='Gaussian QML, burn first52 residuals; fixed-shape mixture used only for forecast distribution')


def mixture_quantile(prob):
    return float(brentq(lambda z:float(P@ndtr(z/np.sqrt(V)))-prob,-30.,30.))
Q={a:mixture_quantile(a) for a in (.01,.05)}


def annual_forecasts(frame,c,year):
    """Frames include future rows only as a scoring source, never fitting inputs."""
    past=frame.loc[frame.index<pd.Timestamp(f'{year}-01-01')].copy();future=frame.loc[(frame.index>=pd.Timestamp(f'{year}-01-01'))&(frame.index<pd.Timestamp(f'{year+1}-01-01'))].copy()
    if len(past)<104 or len(future)<1:raise ValueError('insufficient annual training or forecast rows')
    import copy
    cc=copy.deepcopy(c);_,full_mu,full_cov=fit_frame(cc,past)
    ids=[i for i,name in enumerate(past.columns) if name!=cc['asset_layout']['ids'][cc['cash_index']]]
    names=list(past.columns[ids]);x=past.iloc[:,ids].to_numpy();mu=full_mu[ids];static=np.diag(full_cov)[ids]
    # Existing FHS filter uses its warm-up mean in EWMA variance recursion;
    # both EWMA competitors use exactly that state/centering. Predictive mean
    # remains the common shrinkage-based annual mean across all models.
    residuals,ewma=filter_ewma(x,.94);center=x[:52].mean(0)
    fits={name:fit_garch(x[:,j]-mu[j]) for j,name in enumerate(names)}
    good=all(r['available'] for r in fits.values());gh=np.array([fits[name].get('next_variance',np.nan) for name in names]);records=[]
    for date,raw in future.iloc[:,ids].iterrows():
        observation=raw.to_numpy();forecast_vars={'iid_mix':static,'ewma_mix':ewma.copy(),'garch_mix':gh.copy(),'ewma_fhs':ewma.copy()}
        for method in MODELS:
            if method=='garch_mix' and not good:continue
            for j,name in enumerate(names):
                y=float(observation[j]);m=float(mu[j]);variance=float(forecast_vars[method][j]);sd=np.sqrt(variance)
                if method=='ewma_fhs':
                    support=m+sd*residuals[:,j];crps=empirical_crps(y,support);pit=float(np.mean(support<=y));quantiles={a:float(np.quantile(support,a,method='inverted_cdf')) for a in Q}
                else:
                    crps=mixture_crps(y,m,variance);pit=float(P@ndtr((y-m)/(sd*np.sqrt(V))));quantiles={a:m+sd*z for a,z in Q.items()}
                record=dict(date=str(date.date()),year=year,method=method,asset=name,observed=y,mean=m,variance=variance,crps=crps,pit=pit,standardized=float((y-m)/sd))
                for a,q in quantiles.items():
                    tag=str(int(a*100));record['q'+tag]=q;record['exception'+tag]=int(y<q);record['pinball'+tag]=float((a-int(y<q))*(y-q))
                records.append(record)
        # The realization enters state only after every forecast was recorded.
        ewma=.94*ewma+.06*(observation-center)**2
        if good:
            gh=np.array([fits[name]['omega']+fits[name]['alpha']*(observation[j]-mu[j])**2+fits[name]['beta']*gh[j] for j,name in enumerate(names)])
    fit_record=dict(year=year,fit_last=str(past.index[-1].date()),fit_rows=len(past),forecast_first=str(future.index[0].date()),forecast_last=str(future.index[-1].date()),names=names,garch_available=good,garch=fits)
    return records,fit_record


def source_hash():
    h=hashlib.sha256()
    for p in sorted([*Path('emfin_v2').rglob('*.py'),Path(__file__)]):h.update(str(p).encode());h.update(p.read_bytes())
    return h.hexdigest()


def save(path,data):
    Path(path).write_text(json.dumps(data,indent=2,allow_nan=False,default=lambda x:float(x) if isinstance(x,np.generic) else x)+'\n')


def run_stage(years,out,stage):
    start=time.perf_counter();c=load_config();frame=setup(c)[0];frame=frame.loc[frame.index<pd.Timestamp('2026-01-01')]
    initial=frame.loc[frame.index<=pd.Timestamp('2006-12-31')];cash=c['asset_layout']['ids'][c['cash_index']];scale={name:float(initial[name].std(ddof=1)) for name in frame if name!=cash}
    records=[];fits=[]
    for year in years:
        t=time.perf_counter()
        try:
            r,f=annual_forecasts(frame,c,year);records.extend(r)
        except (ValueError,RuntimeError) as error:
            # Preserve an unavailable year, never shorten history or silently
            # remove it from aggregate selection/comparison requirements.
            f=dict(year=year,error=str(error),garch_available=False)
        f['seconds']=time.perf_counter()-t;fits.append(f)
    for r in records:
        s=scale[r['asset']];r['normalized_crps']=r['crps']/s;r['qlike']=float(np.log(r['variance']/s**2)+(r['observed']-r['mean'])**2/r['variance'])
    result=dict(stage=stage,years=years,protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),code_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),source_sha256=source_hash(),initial_scales=scale,initial_first=str(initial.index[0].date()),initial_last=str(initial.index[-1].date()),data_manifests={k:json.loads(Path(v).read_text()) for k,v in c['history_manifests'].items()},fx_manifest=c.get('fx_evidence'),fits=fits,records=records,seconds=time.perf_counter()-start,scope='One-week marginal forecasts only. Annual refits use past observations; no portfolio optimization, EP stress or annual funding guarantee. Dates were already inspected before this retrospective protocol.')
    path=Path(out);path.parent.mkdir(parents=True,exist_ok=True);save(path,result);return result


def select(validation,path):
    frame=pd.DataFrame(validation['records']);years=set(validation['years']);scores={}
    for method in MODELS[1:]:
        data=frame.loc[frame.method==method]
        if set(data.year)==years and len(data)==len(frame.loc[frame.method=='iid_mix']):scores[method]=float(data.normalized_crps.mean())
    if not scores:raise ValueError('no complete conditional candidate')
    chosen=min(scores,key=lambda key:(scores[key],key));result=dict(selected=chosen,criterion='Mean equal-asset normalized CRPS, validation2014-2018 only',validation_scores=scores,validation_sha256=hashlib.sha256(json.dumps(validation,sort_keys=True).encode()).hexdigest(),protocol_sha256=validation['protocol_sha256'],source_sha256=validation['source_sha256'],selection_time_utc=pd.Timestamp.now(tz='UTC').isoformat(),final_scores_computed=False)
    save(path,result);return result


def bootstrap_difference(values,block,replicates=2000,seed=20261107):
    x=np.asarray(values,float);rng=np.random.default_rng(seed);n=len(x);starts=rng.integers(n,size=(replicates,(n+block-1)//block));index=(starts[:,:,None]+np.arange(block))%n;means=x[index.reshape(replicates,-1)[:,:n]].mean(1)
    return dict(block_weeks=block,replicates=replicates,mean=float(x.mean()),percentile95=np.quantile(means,[.025,.975]).tolist(),scope='Exploratory circular-block percentile interval, not selection-adjusted formal coverage')


def summarize(result,locked):
    frame=pd.DataFrame(result['records']);rows=[]
    if any('error' in f for f in result['fits']):raise ValueError('incomplete years: comparative summary withheld')
    counts=frame.groupby('method').size()
    if any(method not in counts or counts[method]!=counts['iid_mix'] for method in MODELS):raise ValueError('incomplete model forecasts: comparative summary withheld')
    for method in MODELS:
        for name in ['ALL',*result['initial_scales']]:
            data=frame.loc[frame.method==method]
            if name!='ALL':data=data.loc[data.asset==name]
            if data.empty:continue
            std=data.standardized.to_numpy();lag=None
            if name!='ALL':lag=float(np.corrcoef(std[:-1]**2,std[1:]**2)[0,1])
            rows.append(dict(method=method,asset=name,observations=len(data),weeks=data.date.nunique(),normalized_crps=float(data.normalized_crps.mean()),qlike=float(data.qlike.mean()),exception1=int(data.exception1.sum()),exception5=int(data.exception5.sum()),exception1_rate=float(data.exception1.mean()),exception5_rate=float(data.exception5.mean()),normalized_pinball1=float((data.pinball1/data.asset.map(result['initial_scales'])).mean()),normalized_pinball5=float((data.pinball5/data.asset.map(result['initial_scales'])).mean()),squared_standardized_lag1=lag,pit_histogram=np.histogram(data.pit,bins=np.linspace(0,1,11))[0].tolist()))
    weekly=frame.groupby(['date','method'])[['normalized_crps','qlike']].mean().unstack('method');chosen=locked['selected'];diff=weekly['normalized_crps'][chosen]-weekly['normalized_crps']['iid_mix']
    annual=frame.groupby(['year','method'])[['normalized_crps','qlike','exception1','exception5']].mean().reset_index().to_dict('records')
    return dict(selected=chosen,rows=rows,annual=annual,paired_primary={str(block):bootstrap_difference(diff.to_numpy(),block) for block in [10,20,40]},protocol_sha256=result['protocol_sha256'],selection=locked,final_weeks=len(diff),scope='Negative score difference favors conditional candidate. Five assets are not independent replications. One-week marginal quality does not validate joint paths, annual utility/funding, property or a model promotion.')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['pilot','validation','final','development']);p.add_argument('--folder',default='artifacts/model-adequacy-20261107');args=p.parse_args();folder=Path(args.folder);folder.mkdir(parents=True,exist_ok=True)
    years={'pilot':[2014],'validation':list(range(2014,2019)),'final':list(range(2019,2026)),'development':list(range(2007,2014))}[args.stage]
    if args.stage=='final':
        locked=json.loads((folder/'selection.json').read_text())
        if locked['protocol_sha256']!=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest():raise ValueError('protocol changed after validation lock')
        if locked['source_sha256']!=source_hash():raise ValueError('implementation changed after validation lock')
    result=run_stage(years,folder/(args.stage+'.json'),args.stage)
    if args.stage=='validation':print(json.dumps(select(result,folder/'selection.json'),indent=2))
    if args.stage=='final':save(folder/'summary.json',summarize(result,locked))
    print(args.stage,'seconds',result['seconds'],'records',len(result['records']),'annual_failed',sum(not f['garch_available'] for f in result['fits']))

if __name__=='__main__':main()
