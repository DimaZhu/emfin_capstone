"""Registry adapter, with explicit data and economics rather than sleeve aliases."""
import copy,json
from pathlib import Path
import numpy as np
from emfin_v2.assets import load_registry,active_assets,layout
from emfin_v2.asset_history import weekly_returns
from emfin_v2.toolbox import shrinkage


def configure(c,document=None):
    c=copy.deepcopy(c);doc=load_registry() if document is None else document
    doc=copy.deepcopy(doc)
    for a in doc['assets']:
        if a['return_model']=='quarterly_property':a['enabled']=c['real_estate']['enabled']
    s=layout(doc);assets=active_assets(doc)
    # Return generators append property; don't silently reorder an arbitrary registry.
    if s['property_indices'] and s['property_indices']!=[len(assets)-1]:raise ValueError('property must be last in current path adapter')
    c.update(asset_registry=doc,asset_layout=s,asset_names=s['names'],cash_index=s['cash_index'],liquidity_haircuts=[a['haircut'] for a in assets if a['return_model']!='quarterly_property'],view_spread=0.,view_instruments=s['factor_indices'].get('equity',[]),view_vol_cap=None)
    if not c['view_instruments']:raise ValueError('a registry equity factor is required for current stress and liability model')
    if doc.get('reporting_currency')!='USD' or any(a['currency']!='USD' for a in assets if a['return_model']!='quarterly_property'):raise ValueError('current adapter requires USD listed assets/cash and reporting currency')
    c['fx']=dict(dict(enabled=bool(s['property_indices']) and c['real_estate'].get('source')=='singapore_ura',mean_policy='zero'),**c.get('fx',{}))
    if s['property_indices'] and c['real_estate'].get('source')=='abu_dhabi_private':raise ValueError('SGD property registry cannot silently use an Abu Dhabi source; choose the explicit legacy universe')
    c['minimum_weights']=s['minimum_weights']
    if s['property_indices']:c['minimum_weights'][s['property_indices'][0]]=c['real_estate']['minimum_weight']
    return c


def fit(c):
    if not c.get('history_manifests'):raise ValueError('Actual VTI/VWO/GLD/Treasury total-return histories required. Configure private history_manifests; no proxy or old-sleeve substitution is permitted.')
    frame=weekly_returns(c['asset_registry'],c['history_manifests'],c.get('history_end'))
    manifests=[json.loads(Path(p).read_text()) for p in c['history_manifests'].values()]
    test=any('test' in (m['adjustment_method']+' '+m['use_terms']).lower() for m in manifests)
    c['history_evidence']=dict(label='SYNTHETIC TEST FIXTURE ONLY. Not market data or an investment result.' if test else 'Actual instrument calibration histories; parametric scenario paths, not an actual-history backtest.',first_week=str(frame.index[0].date()),last_week=str(frame.index[-1].date()),weekly_returns=len(frame),sources=[dict(asset_id=m['asset_id'],source_url=m['source_url'],use_terms=m['use_terms'],sha256=m['sha256']) for m in manifests])
    if len(frame)<52:raise ValueError('at least52 common weekly actual-instrument observations required')
    from emfin_v2.fx import weekly_factor,COLUMN
    if c['fx']['enabled']:
        fx,m=weekly_factor(frame.index,c['fx'].get('manifest'))
        frame[COLUMN]=fx
        c['fx_evidence']=dict(m,annual_log_vol=float(fx.std(ddof=1)*np.sqrt(52)),annual_sample_log_drift=float(fx.mean()*52),mean_policy=c['fx']['mean_policy'],correlations={k:float(frame[k].corr(fx)) for k in frame if k not in (COLUMN,c['asset_layout']['ids'][c['cash_index']])},first_week=str(frame.index[0].date()),last_week=str(frame.index[-1].date()),dependence_note='Joint listed-ETF/FX covariance fitted on common weekly dates. Weekly property dependence is assumed through its user-set equity shock correlation; property/FX correlation is induced, not separately estimated from quarterly property data. Daily FX is NY noon while ETF NAV is close, so observations are not synchronous.')
    x=frame.to_numpy();mu=x.mean(0);cov=np.zeros((x.shape[1],x.shape[1]))
    ids=list(frame.columns);stochastic=[i for i,a in enumerate(active_assets(c['asset_registry'])) if a['return_model']=='etf_total_return']
    if c['fx']['enabled']:stochastic.append(len(mu)-1)
    shrunk,_=shrinkage.ledoit_wolf_cov(x[:,stochastic]);cov[np.ix_(stochastic,stochastic)]=shrunk
    if c['fx']['enabled']:
        c['fx_evidence']['model_annual_log_vol']=float(np.sqrt(cov[-1,-1]*52))
        c['fx_evidence']['model_correlations']={frame.columns[i]:float(cov[i,-1]/np.sqrt(cov[i,i]*cov[-1,-1])) for i in stochastic if i!=len(mu)-1 and cov[i,i]>0}
    # Shrink listed risky means toward a cross-asset mean, leaving stated cash carry unchanged.
    target=mu.copy();cash=c['cash_index'];risky=[i for i in range(len(mu)-(1 if c['fx']['enabled'] else 0)) if i!=cash]
    if risky:target[risky]=mu[risky].mean()
    mu,_=shrinkage.shrink_mean(mu,target,len(x),156.)
    if c['fx']['enabled']:
        if c['fx']['mean_policy']!='zero':raise ValueError('only explicitly zero FX log-drift policy supported')
        mu[-1]=0.
    return frame,mu,cov


def draw(c,fitted,n,seed):
    from emfin_v2.real_estate import calibration,cash_and_mark,ScenarioDraw
    frame,mu,cov=fitted;h=c['horizon_weeks'];d=len(mu)
    if d!=len(c['liquidity_haircuts'])+int(c['fx']['enabled']):raise ValueError('listed asset plus FX factor dimensions differ')
    rng=np.random.default_rng(seed)
    eig,vec=np.linalg.eigh(cov);root=vec@np.diag(np.sqrt(np.maximum(eig,0)))
    gaussian=rng.normal(size=(n,h,d))@root.T
    members=c['asset_layout']['factor_indices']['equity'];variance=cov[np.ix_(members,members)].sum()/len(members)**2
    factor=gaussian[:,:,members].mean(2)/max(np.sqrt(variance),1e-12)
    scale=np.ones((n,h,1))
    if c['student_nu'] is not None:scale=np.sqrt(rng.chisquare(c['student_nu'],(n,h,1))/(c['student_nu']-2))
    cumul=np.cumsum(mu+gaussian/scale,axis=1)
    fx=np.exp(cumul[:,:,-1]) if c['fx']['enabled'] else None
    liquid_count=len(c['liquidity_haircuts']);paths=np.exp(cumul[:,:,:liquid_count]);growth=paths[:,:,c['cash_index']].copy();paths*=1-np.asarray(c['liquidity_haircuts'])
    funding=paths;re_log=None
    if c['real_estate']['enabled']:
        re=c['real_estate'];cal=calibration(re);rho=re['equity_correlation']
        shock=(rho*factor+np.sqrt(1-rho*rho)*rng.normal(size=(n,h)))/scale[:,:,0]
        re_log=np.cumsum(cal['annual_log_drift']/52+cal['annual_vol']/np.sqrt(52)*shock,axis=1)
        mark,spendable=cash_and_mark(np.exp(re_log),growth,re,fx_paths=fx)
        paths=np.concatenate([paths,mark[:,:,None]],axis=2);funding=np.concatenate([funding,spendable[:,:,None]],axis=2)
    steps=np.array([i['week'] for i in c['liabilities']],int);bases=np.array([i['amount'] for i in c['liabilities']],float)
    stress=-cumul[:,-1,members].mean(1);stress=(stress-stress.mean())/max(stress.std(),1e-9)
    v=c['liability_vol'];amounts=bases[None,:]*np.exp(v*(.3*stress[:,None]+np.sqrt(.91)*rng.normal(size=(n,len(bases))))-.5*v*v)
    return ScenarioDraw((paths,amounts,steps,bases,growth),funding,re_log)
