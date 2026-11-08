"""Reproducible bounded robustness studies. No implicit grid, network or retries.

Research methods share frozen training/validation/judge sets for each model.
Historical results use past-only refits and the independent cash-first ledger.
"""
from pathlib import Path
import copy,json,time,hashlib,subprocess,traceback
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from emfin_v2.default_run import load_config,validate_config,setup,draw_paths,probabilities,solve,holding_bounds,metrics
from emfin_v2.evaluation import evaluate
from emfin_v2.ledger import cash_first
from emfin_v2.real_estate import ScenarioDraw,cash_and_mark
from emfin_v2.registry_runtime import fit_frame
from emfin_v2.historical_simulation import stationary_indices
from emfin_v2.toolbox.benchmark import mean_variance_allocation


def source_tree_hash():
    sha=hashlib.sha256()
    for folder in ('emfin_v2','experiments'):
        for file in sorted(Path(folder).rglob('*.py')):
            sha.update(str(file).encode());sha.update(file.read_bytes())
    return sha.hexdigest()


def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,default=str).encode()).hexdigest()


def config(train=200,validation=400,evaluation=800,seeds=4,seed=20261107):
    # Deliberate pin (8 Nov 2026): these robustness diagnostics were built and
    # tuned at the original 1-year default (52 weeks, 12 monthly payouts, 6%
    # cml cap). The owner moved the bundled default to 10 years / 40% cap;
    # the held-out actual-history and radius diagnostics below only have ~5
    # years of genuine future rows, so they keep the original scale.
    c=load_config();c.update(horizon_weeks=52,cml_budget=0.06);c['recurring_payout']['months']=12;c.update(train_scenarios=train,validation_scenarios=validation,evaluation_scenarios=evaluation,validation_seeds=seeds,evaluation_seeds=seeds,seed=seed,scenario_tier='bounded research pilot',multiplier_grid=[1.],cash_mix_grid=[1.,.75,.5,.25,0.])
    return validate_config(c)


def simple_allocations(c,draw):
    d=draw[0].shape[2];mins,fixed=holding_bounds(c,d);anchor=mins.copy()
    for i,v in fixed.items():anchor[i]=v
    anchor[c['cash_index']]+=1-anchor.sum();equal=anchor.copy();free=[i for i in range(d) if i not in fixed];remaining=1-sum(fixed.values());equal[:]=0
    for i,v in fixed.items():equal[i]=v
    while free:
        share=remaining/len(free);locked=[i for i in free if mins[i]>share]
        if not locked:
            for i in free:equal[i]=share
            break
        for i in locked:equal[i]=mins[i];remaining-=mins[i];free.remove(i)
    # A deliberately simple reserve policy: reserve all scheduled obligations
    # in cash, distribute the remaining free capital equally, keep fixed RE.
    reserve=equal.copy();cash=c['cash_index'];target=min(1-sum(v for i,v in fixed.items() if i!=cash),sum(p['amount'] for p in c['liabilities'])/c['wealth'])
    if reserve[cash]<target:
        others=[i for i in range(d) if i!=cash and i not in fixed];available=sum(max(0,reserve[i]-mins[i]) for i in others);needed=target-reserve[cash]
        if available>0:
            for i in others:reserve[i]-=min(needed,available)*(reserve[i]-mins[i])/available
            reserve[cash]+=min(needed,available)
    raw_mv=mean_variance_allocation(draw[0][:,-1].mean(0),np.cov(draw[0][:,-1].T),np.ones(d),c['wealth'],c['risk_tolerance'],minimum_weights=mins,fixed_weights=fixed)
    return {'equal_weight':equal*c['wealth'],'raw_mean_variance':raw_mv,'cash_reserve':reserve*c['wealth'],'cash_fixed_property':anchor*c['wealth']},anchor*c['wealth']


def ledger_summary(c,draws,a,probs=None):
    from scipy.special import logsumexp
    from emfin_v2.toolbox.mpep import cml_of_paths
    out=[]
    for j,d in enumerate(draws):
        r=cash_first(c,d,a);p=np.full(len(d[0]),1/len(d[0])) if probs is None else probs[j];gaps=[cml_of_paths(r['payment_shortfalls'][:,i],p,c['confidence']) for i in range(len(d[2]))]
        out.append(dict(net_ce=float(-c['risk_tolerance']*logsumexp(-r['terminal_net']/c['risk_tolerance'],b=p)),funded_probability=float(np.clip(r['funded']@p,0,1)),max_payment_tail_gap=float(max(gaps)),terminal_mean=float(r['terminal_net']@p)))
    return dict(batches=out,net_ce_mean=float(np.mean([x['net_ce'] for x in out])),funded_probability_mean=float(np.mean([x['funded_probability'] for x in out])),max_payment_tail_gap=max(x['max_payment_tail_gap'] for x in out),scope='Cash-first execution audit, not W1-certified or the optimizer accounting model.')


def fitted_study(c,fitted=None,include_resampling=False,resamples=8):
    started=time.perf_counter();c=validate_config(c);fitted=setup(c) if fitted is None else fitted
    train=draw_paths(c,fitted,c['train_scenarios'],c['seed']);q,qs=probabilities(c,train[0],train.re_price_logs)
    judge_config=copy.deepcopy(c);judge_config['scenario_model']='gaussian_scale_mixture'
    val=[draw_paths(judge_config,fitted,c['validation_scenarios'],c['seed']+1000+j) for j in range(c['validation_seeds'])]
    vp=[probabilities(c,x[0],x.re_price_logs) for x in val]
    judge=[draw_paths(judge_config,fitted,c['evaluation_scenarios'],c['seed']+10000+j) for j in range(c['evaluation_seeds'])]
    jp=[probabilities(c,x[0],x.re_price_logs) for x in judge]
    raw,anchor=simple_allocations(c,train);statuses={}
    for name,objective in [('cara_constraints','cara'),('mv_same_constraints','mean_variance')]:
        cc=copy.deepcopy(c);cc['objective_kind']=objective;a,status=solve(cc,train,q,qs,1.);statuses[name]=status
        if a is not None:raw[name]=a
    if include_resampling:
        indices=stationary_indices(len(fitted[0]),resamples,len(fitted[0]),8,c['seed']+200000);weights=[];replicates=[]
        for j,ix in enumerate(indices):
            cc=copy.deepcopy(c)
            if cc['real_estate']['enabled'] and cc['real_estate'].get('source')=='singapore_ura':
                from emfin_v2.singapore import history
                property_returns,_=history(cc['real_estate'].get('sg_property_type','All Residential'),cc.get('history_end'))
                pix=stationary_indices(len(property_returns),1,len(property_returns),4,c['seed']+400000+j)[0]
                cc['real_estate']['calibration_returns_override']=np.asarray(property_returns)[pix].tolist()
            ff=fit_frame(cc,fitted[0].iloc[ix].copy());dr=draw_paths(cc,ff,c['train_scenarios'],c['seed']+300000+j)
            try:
                pq,ps=probabilities(cc,dr[0],dr.re_price_logs);aa,st=solve(cc,dr,pq,ps,1.)
                replicates.append(dict(replica=j,status=st,weights=None if aa is None else (aa/c['wealth']).tolist()))
                if aa is not None and st['kind']=='optimized':weights.append(aa)
            except Exception as e:replicates.append(dict(replica=j,error=str(e)))
        # Never average silently across failed fits; require all declared replicas.
        statuses['whole_fit_bagging']=dict(replicates=replicates,successful=len(weights),required=resamples,scope='Stationary block refit of all listed/FX moments + scenario regeneration + EP + constrained solve. Property quarterly dispersion is refit under a separate past-only stationary quarterly bootstrap; cross-frequency joint dependence is still the declared equity-factor assumption, not estimated. Fixed forward views and liability schedules are not falsely resampled as data.')
        if len(weights)==resamples:raw['whole_fit_bagging']=np.mean(weights,axis=0)
    rows=[];frozen={}
    for name,a in raw.items():
        # Every method receives the same validation-selection budget and anchor.
        chosen=None;trials=[]
        for fraction in [1.,.75,.5,.25,0.]:
            candidate=fraction*a+(1-fraction)*anchor
            check=evaluate(c,val,candidate,[z[0] for z in vp],[z[1] for z in vp]);trials.append(dict(fraction=fraction,passed=check['overall_pass'],breaches=check['breaches']))
            if check['overall_pass']:chosen=candidate;break
        # Raw portfolios remain comparisons even if validation rejects them.
        for variant,allocation in [('raw',a)]+([('validation_calibrated',chosen)] if chosen is not None else []):
            key=name+':'+variant;verdict=evaluate(c,judge,allocation,[z[0] for z in jp],[z[1] for z in jp]);audit=ledger_summary(c,judge,allocation)
            provisioning_ce=np.array([metrics(c,dr,allocation)[1] for dr in judge])
            rows.append(dict(method=key,weights=(allocation/c['wealth']).tolist(),final=verdict,ledger=audit,provisioning_ce=provisioning_ce.tolist(),validation_trials=trials,calibrated_fraction=trials[-1]['fraction'] if variant=='validation_calibrated' else None))
            frozen[key]=allocation
    base=next(z for z in rows if z['method']=='equal_weight:raw')
    for row in rows:
        diffs=np.array([x['net_ce'] for x in row['ledger']['batches']])-np.array([x['net_ce'] for x in base['ledger']['batches']]);row['paired_ledger_ce_vs_equal']=dict(mean=float(diffs.mean()),standard_error=float(diffs.std(ddof=1)/np.sqrt(len(diffs))),scope='Paired conditional Monte Carlo difference, no outer-parameter or economic coverage')
    return dict(code_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),source_tree_sha256=source_tree_hash(),data_manifests={k:json.loads(Path(v).read_text()) for k,v in c.get('history_manifests',{}).items()},config=c,judge_model='gaussian_scale_mixture',rows=rows,statuses=statuses,seconds=time.perf_counter()-started,fit_first=str(fitted[0].index.min()),fit_last=str(fitted[0].index.max()),fit_rows=len(fitted[0]),config_sha256=digest(c),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),label='Bounded matched-judge study. Validation selects once; final portfolios are frozen. Raw and calibrated methods are distinct. No performance superiority assumed.'),frozen


def actual_history_draw(c,frame,origin):
    import pandas as pd,csv,calendar
    from datetime import date,timedelta
    from emfin_v2.singapore import ROOT
    future=frame.loc[frame.index>origin].iloc[:c['horizon_weeks']]
    if len(future)!=c['horizon_weeks']:raise ValueError('not enough genuine held-out weekly rows')
    liquid=len(c['liquidity_haircuts']);logs=future.iloc[:,:liquid].to_numpy();paths=np.exp(np.cumsum(logs,axis=0))[None,:,:];growth=paths[:,:,c['cash_index']].copy();paths*=1-np.array(c['liquidity_haircuts']);funding=paths.copy();re_logs=None
    if c['real_estate']['enabled']:
        with (ROOT/'ura_private_residential_quarterly.csv').open() as f:quarter=[x for x in csv.DictReader(f) if x['property_type']==c['real_estate']['sg_property_type']]
        records=[]
        for x in quarter:
            y=int(x['quarter'][:4]);m=int(x['quarter'][-1])*3;records.append((date(y,m,calendar.monthrange(y,m)[1])+timedelta(days=45),float(x['index'])))
        def index_at(ts):return [v for day,v in records if day<=pd.Timestamp(ts).date()][-1]
        initial=index_at(origin);prices=np.array([[index_at(day)/initial for day in future.index]]);re_logs=np.log(prices)
        fx=np.exp(np.cumsum(future.iloc[:,-1].to_numpy()))[None,:] if c['fx']['enabled'] else None
        mark,cash=cash_and_mark(prices,growth,c['real_estate'],fx_paths=fx);paths=np.concatenate([paths,mark[:,:,None]],axis=2);funding=np.concatenate([funding,cash[:,:,None]],axis=2)
    steps=np.array([p['week'] for p in c['liabilities']]);base=np.array([p['amount'] for p in c['liabilities']]);return ScenarioDraw((paths,base[None,:],steps,base,growth),funding,re_logs),future


def walk_forward(origins,c,model='gaussian_scale_mixture',resamples=0):
    import pandas as pd
    fullc=copy.deepcopy(c);fullfit=setup(fullc);frame=fullfit[0];results=[]
    for origin in origins:
        start=time.perf_counter();cc=copy.deepcopy(c);cc['history_end']=origin;cc['real_estate']['history_end']=origin;cc['scenario_model']=model;cc=validate_config(cc)
        try:
            past=frame.loc[frame.index<=pd.Timestamp(origin)].copy();fitted=fit_frame(cc,past);study,allocations=fitted_study(cc,fitted,include_resampling=resamples>0,resamples=resamples)
            realised,forward=actual_history_draw(cc,frame,pd.Timestamp(origin));rows=[]
            for name,a in allocations.items():
                audit=cash_first(cc,realised,a);returns=audit['net_wealth_paths'][0]/cc['wealth']-1;rows.append(dict(method=name,weights=(a/cc['wealth']).tolist(),terminal_net=float(audit['terminal_net'][0]),funded=bool(audit['funded'][0]),max_shortfall=float(audit['payment_shortfalls'].max()),minimum_net_return=float(returns.min()),ledger_net_return=float(returns[-1]),model_final_pass=next(x['final']['overall_pass'] for x in study['rows'] if x['method']==name)))
            results.append(dict(origin=origin,fit_last=str(past.index[-1].date()),fit_rows=len(past),holdout_first=str(forward.index[0].date()),holdout_last=str(forward.index[-1].date()),rows=rows,study=study,seconds=time.perf_counter()-start))
        except Exception as e:results.append(dict(origin=origin,error=str(e),traceback=traceback.format_exc(),seconds=time.perf_counter()-start))
    return dict(model=model,origins=results,scope='Past-only listed/FX refits and property quarters available under an assumed45-day publication lag. Latest data vintages, NOT revision-safe or true point-in-time archives. Annual holdings are fixed with cash-first proportional sales; no future rebalance. Specific crisis years are descriptive holdouts, not independent tail-frequency proof.')


def empirical_radius_diagnostics(c,fitted):
    """Past-only adjacent empirical path-distribution discrepancy, not coverage."""
    x=fitted[0].to_numpy();h=c['horizon_weeks'];blocks=[]
    for start in range(0,len(x)-h+1,h):blocks.append(np.exp(np.cumsum(x[start:start+h],axis=0)))
    if len(blocks)<4:return dict(available=False,reason='fewer than four nonoverlapping horizon blocks')
    b=np.array(blocks);half=len(b)//2;n=min(half,len(b)-half);left=b[:n];right=b[-n:];cost=cdist(left.reshape(n,-1),right.reshape(n,-1),metric='chebyshev');i,j=linear_sum_assignment(cost);distance=float(cost[i,j].mean())
    return dict(available=True,distance=distance,blocks=len(b),nonoverlap_horizon=h,earlier_blocks=n,later_blocks=n,metric='max_path empirical equal-mass assignment on listed/FX paths only',configured_radius=c.get('wasserstein_radius',0),scope='Historical distribution-shift diagnostic, not a statistically justified W1 radius or property/liability calibration. Early versus recent regimes need not be stationary; no confidence coverage inferred.')


def save(result,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else float(x),allow_nan=False)+'\n')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['pilot','sensitivity','walkforward','resample','fhs'],default='pilot');p.add_argument('--output',required=True);args=p.parse_args();c=config();started=time.perf_counter()
    if args.mode=='pilot':
        result,_=fitted_study(c);result['radius_diagnostic']=empirical_radius_diagnostics(c,setup(c))
    elif args.mode=='resample':result,_=fitted_study(c,include_resampling=True,resamples=8)
    elif args.mode=='fhs':c['scenario_model']='fhs_ewma';result,_=fitted_study(c)
    elif args.mode=='walkforward':result=walk_forward(['2007-12-28','2019-12-27','2021-12-31'],c)
    else:
        cases=[]
        # Prespecified reduced sensitivity matrix, not Cartesian optimization.
        for n,seed,radius in [(100,20261107,0.00002),(200,20261108,0.00002),(400,20261107,0.00002),(200,20261107,0.),(200,20261107,0.00001),(200,20261107,0.00004)]:
            cc=config(train=n,seed=seed);cc['wasserstein_radius']=radius
            try:rr,_=fitted_study(cc);cases.append(rr)
            except Exception as e:cases.append(dict(config=cc,error=str(e)))
        result=dict(cases=cases,scope='Prespecified bounded seed/sample/radius sensitivity, no best-case selection or automatic default change.')
    result['wall_seconds']=time.perf_counter()-started;save(result,args.output);print(args.output,result['wall_seconds'],flush=True)
if __name__=='__main__':main()
