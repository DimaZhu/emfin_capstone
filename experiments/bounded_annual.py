"""Prespecified capped-variance study, no production-default promotion."""
from pathlib import Path
import copy,json,time,hashlib,subprocess,traceback
import numpy as np
import pandas as pd
from emfin_v2.default_run import load_config,validate_config,setup,draw_paths,probabilities,solve
from emfin_v2.registry_runtime import fit_frame
from emfin_v2.bounded_volatility import initial_state,update,settings
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from experiments.robustness import config,simple_allocations,ledger_summary,actual_history_draw,digest,source_tree_hash,save
from experiments.model_adequacy import mixture_crps,mixture_quantile,empirical_crps,bootstrap_difference
from scipy.special import ndtr

ROOT=Path('artifacts/bounded-annual-20261107');PROTOCOL=Path('docs/BOUNDED_VOLATILITY_PROTOCOL.md')
MODELS=('gaussian_scale_mixture','bounded_ewma_mixture')


def data_evidence(c):
    return dict(manifests={k:json.loads(Path(v).read_text()) for k,v in c['history_manifests'].items()},fx=c.get('fx_evidence'),property_assumptions=c['real_estate'])


def metadata():
    return dict(code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),code_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),source_sha256=source_tree_hash(),protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest())


def selected_config(c,model,cap=9.):
    cc=copy.deepcopy(c);cc['scenario_model']=model
    if model=='bounded_ewma_mixture':cc['bounded_volatility']=dict(decay=.94,floor=.05,cap=cap)
    return validate_config(cc)


def weekly():
    started=time.perf_counter();c=load_config();frame=setup(c)[0];cash=c['asset_layout']['ids'][c['cash_index']];names=[x for x in frame if x!=cash];initial=frame.loc[frame.index<'2007-01-01',names].std(ddof=1);records=[];fits=[]
    for year in [2008,*range(2014,2026)]:
        past=frame.loc[frame.index<pd.Timestamp(f'{year}-01-01')];future=frame.loc[(frame.index>=pd.Timestamp(f'{year}-01-01'))&(frame.index<pd.Timestamp(f'{year+1}-01-01'))];cc=copy.deepcopy(c);_,mu,cov=fit_frame(cc,past);ids=[list(frame).index(n) for n in names];base=np.diag(cov)[ids];mean=mu[ids]
        states={cap:initial_state(past[names].to_numpy(),mean,base,decay=.94,floor=.05,cap=cap)[0] for cap in [4.,9.,16.]};hits={cap:dict(low=np.zeros(len(names),int),high=np.zeros(len(names),int)) for cap in states};fits.append(dict(year=year,fit_last=str(past.index[-1].date()),forecast_first=str(future.index[0].date()),fit_rows=len(past)))
        for date,raw in future[names].iterrows():
            observation=raw.to_numpy()
            for cap in [None,4.,9.,16.]:
                variance=base if cap is None else states[cap]
                for j,name in enumerate(names):
                    y=observation[j];sd=np.sqrt(variance[j]);m=mean[j];z=(y-m)/sd
                    records.append(dict(year=year,date=str(date.date()),asset=name,method='iid' if cap is None else f'bounded{int(cap)}',normalized_crps=mixture_crps(y,m,variance[j])/initial[name],qlike=float(np.log(variance[j]/initial[name]**2)+(y-m)**2/variance[j]),exception1=int(z<mixture_quantile(.01)),exception5=int(z<mixture_quantile(.05)),standardized=float(z),pit=float(np.array([.9,.1])@ndtr(z/np.sqrt([.75,3.25])))))
            for cap in states:
                states[cap],lo,hi=update(states[cap],observation-mean,base,decay=.94,floor=.05,cap=cap);hits[cap]['low']+=lo;hits[cap]['high']+=hi
        fits[-1]['hits']={str(k):{name:v.tolist() for name,v in z.items()} for k,z in hits.items()}
    df=pd.DataFrame(records);summary=[]
    for stage,years in [('development',[2008]),('validation',list(range(2014,2019))),('final',list(range(2019,2026)))]:
        d=df.loc[df.year.isin(years)]
        for (method,asset),a in d.groupby(['method','asset']):summary.append(dict(stage=stage,method=method,asset=asset,crps=float(a.normalized_crps.mean()),qlike=float(a.qlike.mean()),exceptions1=int(a.exception1.sum()),exceptions5=int(a.exception5.sum()),n=len(a),squared_lag=float(np.corrcoef(a.standardized.to_numpy()[:-1]**2,a.standardized.to_numpy()[1:]**2)[0,1])))
    final=df.loc[df.year>=2019].groupby(['date','method']).normalized_crps.mean().unstack();difference=final.bounded9-final.iid
    return dict(**metadata(),data_evidence=data_evidence(c),records=records,summary=summary,fits=fits,initial_scales=initial.to_dict(),paired={str(b):bootstrap_difference(difference,b) for b in [10,20,40]},seconds=time.perf_counter()-started,scope='Retrospective fixed-cap weekly marginals. No model selection or promotion.2008development;2014-2018validation;2019-2025final.')


def batches(c,fitted,n,seed,count,model,cap=9.):
    cc=selected_config(c,model,cap);draws=[draw_paths(cc,fitted,n,seed+j) for j in range(count)];ps=[probabilities(cc,d[0],d.re_price_logs) for d in draws]
    return draws,ps


def judged(c,draws,ps,allocation):
    return dict(final=evaluate(c,draws,allocation,[p[0] for p in ps],[p[1] for p in ps]),ledger=ledger_summary(c,draws,allocation),stressed_ledger=ledger_summary(c,draws,allocation,[p[1] for p in ps]))


def snapshot(c,fitted=None,sensitivity=True):
    started=time.perf_counter();c=validate_config(c);fitted=setup(c) if fitted is None else fitted
    validation={m:batches(c,fitted,c['validation_scenarios'],c['seed']+1000,c['validation_seeds'],m) for m in MODELS}
    judges={m:batches(c,fitted,c['evaluation_scenarios'],c['seed']+10000,c['evaluation_seeds'],m) for m in MODELS}
    if sensitivity:
        for label,model,cap in [('bounded4','bounded_ewma_mixture',4.),('bounded16','bounded_ewma_mixture',16.),('fhs','fhs_ewma',9.)]:judges[label]=batches(c,fitted,c['evaluation_scenarios'],c['seed']+10000,c['evaluation_seeds'],model,cap)
    raw={};statuses={};train_info={}
    for model in MODELS:
        cc=selected_config(c,model);dr=draw_paths(cc,fitted,c['train_scenarios'],c['seed']);p,ps=probabilities(cc,dr[0],dr.re_price_logs);baseline,anchor=simple_allocations(cc,dr);train_info[model]=dict(variance=dr.bounded_diagnostics,probability_sum=float(p.sum()),stress_probability_sum=float(ps.sum()))
        if model==MODELS[0]:raw.update(baseline)
        for name,objective in [('cara','cara'),('mv_matched','mean_variance')]:
            cc['objective_kind']=objective
            try:
                a,status=solve(cc,dr,p,ps,1.);statuses[model+':'+name]=status
                if a is not None:raw[model+':'+name]=a
            except Exception as e:statuses[model+':'+name]=dict(error=str(e),traceback=traceback.format_exc())
    rows=[];frozen={};specifications=[]
    for name,a in raw.items():
        trials=[];chosen=None
        for fraction in [1.,.75,.5,.25,0.]:
            b=fraction*a+(1-fraction)*anchor;passes={model:evaluate(c,*[validation[model][0],b],[p[0] for p in validation[model][1]],[p[1] for p in validation[model][1]])['overall_pass'] for model in MODELS};trials.append(dict(fraction=fraction,passed=passes))
            if all(passes.values()):chosen=b;break
        variants=[('raw',a)]+([('cross_validated',chosen)] if chosen is not None else [])
        for variant,allocation in variants:
            key=name+':'+variant;frozen[key]=allocation
            specifications.append(dict(method=key,weights=(allocation/c['wealth']).tolist(),validation_trials=copy.deepcopy(trials),calibrated_fraction=trials[-1]['fraction'] if variant=='cross_validated' else None))
    lock=dict(**metadata(),config_sha256=digest(c),fit_last=str(fitted[0].index[-1].date()),selection_time_utc=pd.Timestamp.now(tz='UTC').isoformat(),final_scored=False,portfolios=specifications)
    lock_path=ROOT/'locks'/(digest(dict(config=c,fit_last=lock['fit_last']))+'.json');save(lock,lock_path)
    for spec in specifications:
        allocation=frozen[spec['method']];rows.append(dict(**spec,judges={model:judged(c,draws,ps,allocation) for model,(draws,ps) in judges.items()}))
    fixture=[]
    if sensitivity:
        for label,payments in [('95M_final',[dict(name='Counterfactual95M',week=52,amount=95e6)]),('60M_early30M_final',[dict(name='Counterfactual60M',week=4,amount=60e6),dict(name='Counterfactual30M',week=52,amount=30e6)])]:
            cc=copy.deepcopy(c);cc['recurring_payout']=None;cc['liabilities']=payments
            for name in ['equal_weight','cash_reserve','cash_fixed_property']:
                for model in MODELS:
                    # Same market paths, replace only payment tuple. No solve or reselection.
                    from emfin_v2.real_estate import ScenarioDraw
                    ds=[]
                    for dr in judges[model][0]:
                        amounts=np.array([p['amount'] for p in payments]);steps=np.array([p['week'] for p in payments]);ds.append(ScenarioDraw((dr[0],np.broadcast_to(amounts,(len(dr[0]),len(amounts))).copy(),steps,amounts,dr[4]),dr.funding_paths,dr.re_price_logs))
                    fixture.append(dict(schedule=label,portfolio=name,model=model,**judged(cc,ds,judges[model][1],raw[name])))
    result=dict(**metadata(),data_evidence=data_evidence(c),selection_lock=lock,selection_lock_path=str(lock_path),config=c,config_sha256=digest(c),fit_first=str(fitted[0].index[0].date()),fit_last=str(fitted[0].index[-1].date()),fit_rows=len(fitted[0]),statuses=statuses,rows=rows,train_diagnostics=train_info,judge_diagnostics={k:[d.bounded_diagnostics for d in draws if getattr(d,'bounded_diagnostics',None) is not None] for k,(draws,_) in judges.items()},fixtures=fixture,seconds=time.perf_counter()-started,scope='Research cross-law final budgets and cash-first ledger. Both-law validation selects blends once. Final sets never repair. Counts are conditional model samples, not full-funding guarantees.')
    return result,frozen,judges


def historical(c,origins):
    start=time.perf_counter();full=setup(copy.deepcopy(c))[0];rows=[];scale=full.loc[full.index<'2007-01-01'].std(ddof=1)
    for origin in origins:
        t=time.perf_counter();cc=copy.deepcopy(c);cc['history_end']=origin;cc['real_estate']['history_end']=origin;cc=validate_config(cc)
        try:
            past=full.loc[full.index<=pd.Timestamp(origin)];fitted=fit_frame(cc,past);study,allocations,judges=snapshot(cc,fitted,False);realized,future=actual_history_draw(cc,full,pd.Timestamp(origin));r=[]
            for method,a in allocations.items():
                ledger=cash_first(cc,realized,a);r.append(dict(method=method,weights=(a/cc['wealth']).tolist(),terminal_net=float(ledger['terminal_net'][0]),funded=bool(ledger['funded'][0]),max_shortfall=float(ledger['payment_shortfalls'].max()),net_return=float(ledger['terminal_net'][0]/cc['wealth']-1)))
            scores=[];ids=[j for j,name in enumerate(full.columns) if name!=cc['asset_layout']['ids'][cc['cash_index']]];mu=fitted[1]
            for model,(draws,ps) in judges.items():
                # Reconstruct listed/FX log paths from same generator innovations;
                # FX is a factor, not an investable output sleeve.
                from emfin_v2.bounded_volatility import transform
                from emfin_v2.innovations import divisor
                _,mean,cov=fitted;eig,vec=np.linalg.eigh(cov);root=vec@np.diag(np.sqrt(np.maximum(eig,0)));rng=np.random.default_rng(cc['seed']+10000);n=cc['evaluation_scenarios'];z=rng.normal(size=(n,52,len(mean)))@root.T;cf=selected_config(cc,model);z/=divisor(cf,rng,n,52)
                if model=='bounded_ewma_mixture':z=transform(z,past.to_numpy(),mean,np.diag(cov),settings(cf))
                cumulative=np.cumsum(mean+z,axis=1);actual=np.cumsum(future.to_numpy(),axis=0)
                for h in [4,13,26,52]:
                    for j in ids:scores.append(dict(model=model,asset=full.columns[j],weeks=h,crps=empirical_crps(actual[h-1,j],cumulative[:,h-1,j])/float(scale.iloc[j]*np.sqrt(h))))
            rows.append(dict(origin=origin,fit_last=str(past.index[-1].date()),holdout_first=str(future.index[0].date()),holdout_last=str(future.index[-1].date()),results=r,multihorizon=scores,study=study,seconds=time.perf_counter()-t))
        except Exception as e:rows.append(dict(origin=origin,error=str(e),traceback=traceback.format_exc(),seconds=time.perf_counter()-t))
        print(origin,'seconds',rows[-1]['seconds'],'error',rows[-1].get('error'),flush=True)
    return dict(**metadata(),origins=rows,seconds=time.perf_counter()-start,scope='19 retrospective actual listed/FX annual paths. Property latest-vintage quarterly index, assumed45day lag, no revision-safe/tradable-price claim. Funding small-schedule dominance and nineteen outcomes do not prove tail frequency.')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['weekly','pilot','confirm','historical-pilot','historical']);args=p.parse_args();ROOT.mkdir(parents=True,exist_ok=True)
    if args.mode=='weekly':r=weekly()
    elif args.mode in ['pilot','confirm']:
        c=config(train=100,validation=200,evaluation=400,seeds=2) if args.mode=='pilot' else config(train=200,validation=400,evaluation=800,seeds=4);r=snapshot(c)[0]
    else:
        c=config(train=100,validation=200,evaluation=400,seeds=2);origins=[str(pd.Timestamp(f'{year}-12-31')-pd.Timedelta(days=(pd.Timestamp(f'{year}-12-31').weekday()-4)%7))[:10] for year in range(2006,2025)]
        if args.mode=='historical-pilot':origins=origins[:1]
        r=historical(c,origins)
    save(r,ROOT/(args.mode+'.json'));print(args.mode,r['seconds'],flush=True)
if __name__=='__main__':main()
