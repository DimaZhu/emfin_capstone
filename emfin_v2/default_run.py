"""One default argument: funding-aware allocation under Student-t path uncertainty.

No model promises a never-failing solve. The runner instead always writes a
status report: validated allocation, verified cash fallback, or no feasible
allocation. Failed optimizations are never relabeled as optimal.
"""
from pathlib import Path
import json,time
import numpy as np
from scipy.stats import t as student
from emfin_v2.toolbox import dataset,shrinkage,liabilities,entropy_pooling as ep,benchmark,risk_stats,mpep,seqep

from emfin_v2.real_estate import ScenarioDraw, funding_paths
from emfin_v2.config import CONFIG_DIR
DEFAULT_CONFIG=CONFIG_DIR/'default.json'


def load_config(path=DEFAULT_CONFIG):
    try:
        c=json.loads(Path(path).read_text())
    except (OSError,json.JSONDecodeError) as error:raise ValueError('Cannot read model config: '+str(error)) from error
    required=['wealth','horizon_weeks','student_nu','confidence','risk_tolerance','liabilities','liquidity_haircuts','evaluation_seeds','validation_seeds','real_estate','funding_budget_fraction','loss_budget','cml_budget','liability_vol','train_scenarios','validation_scenarios','evaluation_scenarios','seed','multiplier_grid','view_spread','stress_mean_path_loss_increment','label']
    if not isinstance(c,dict) or any(key not in c for key in required):raise ValueError('Incomplete model config; copy the bundled default.json and replace its documented inputs')
    if c.get('recurring_payout') is not None:
        from emfin_v2.payouts import expand_recurring
        c['one_off_liabilities']=c.get('one_off_liabilities',c['liabilities'])
        c['liabilities']=expand_recurring(c['recurring_payout'],c['horizon_weeks'],c['one_off_liabilities'])
    numbers=['wealth','confidence','risk_tolerance','funding_budget_fraction','loss_budget','cml_budget','liability_vol','view_spread','stress_mean_path_loss_increment']
    if any(not isinstance(c[k],(int,float)) or not np.isfinite(c[k]) for k in numbers):raise ValueError('Model numeric inputs must be finite numbers')
    for key in ['horizon_weeks','train_scenarios','validation_scenarios','evaluation_scenarios','validation_seeds','evaluation_seeds','seed']:
        if type(c[key]) is not int or c[key]<0:raise ValueError(key+' must be a nonnegative integer')
    if any(c[k]<20 for k in ['train_scenarios','validation_scenarios','evaluation_scenarios']):raise ValueError('at least 20 scenarios per split required')
    if c['liability_vol']<0 or c['funding_budget_fraction']<0 or c['loss_budget']<0 or c['cml_budget']<0:raise ValueError('risk budgets and liability volatility must be nonnegative')
    if not c['multiplier_grid'] or any(not isinstance(x,(int,float)) or not np.isfinite(x) or not 0<x<=1 for x in c['multiplier_grid']):raise ValueError('budget multipliers must be in (0,1]')
    if 'cash_mix_grid' in c and (not c['cash_mix_grid'] or any(not isinstance(x,(int,float)) or not np.isfinite(x) or not 0<=x<=1 for x in c['cash_mix_grid'])):raise ValueError('cash mix fractions must be in [0,1]')
    if c['student_nu'] is not None and (not isinstance(c['student_nu'],(int,float)) or not np.isfinite(c['student_nu'])):raise ValueError('Student-t nu must be finite or null')
    if not isinstance(c['liabilities'],list) or any(not isinstance(i,dict) or not all(k in i for k in ('name','week','amount')) or type(i['week']) is not int or not isinstance(i['amount'],(int,float)) or not np.isfinite(i['amount']) for i in c['liabilities']):raise ValueError('payout rows require name, integer week and finite amount')
    if not isinstance(c['real_estate'],dict) or any(k not in c['real_estate'] for k in ('enabled','minimum_weight','equity_correlation','annual_vol','annual_drift','liquidation_haircut')):raise ValueError('incomplete RE assumptions')
    if c['wealth']<=0 or c['horizon_weeks']<1 or (c['student_nu'] is not None and c['student_nu']<=4) or not 0<c['confidence']<1 or c['risk_tolerance']<=0:
        raise ValueError('invalid wealth, horizon, nu, confidence or utility tolerance')
    if not c['liabilities']:raise ValueError('provide at least one payout row; use amount zero for no obligation')
    if any(i['amount']<0 or not 1<=i['week']<=c['horizon_weeks'] for i in c['liabilities']):
        raise ValueError('liabilities must have nonnegative amounts and valid due weeks')
    if len(c['liquidity_haircuts'])!=6 or any(not 0<=h<1 for h in c['liquidity_haircuts']):
        raise ValueError('six liquidity haircuts in [0,1) required')
    if c['evaluation_seeds']<2 or c['validation_seeds']<2:
        raise ValueError('at least two independent seeds per interval')
    c.setdefault('wasserstein_radius',0.)
    c.setdefault('wasserstein_liability_scale',.01)
    from emfin_v2.toolbox.wasserstein import validate
    validate(c['wasserstein_radius'],c['wasserstein_liability_scale'])
    c.setdefault('sequential_ep',True)
    c.setdefault('cash_index',5)
    c.setdefault('view_instruments',[1,0])
    c.setdefault('minimum_weights',None)
    c.setdefault('scenario_archives',None)
    if c['scenario_archives']:
        paths=[c['scenario_archives']['training']]+c['scenario_archives']['validation']+c['scenario_archives']['evaluation']
        if len(c['scenario_archives']['validation'])<2 or len(c['scenario_archives']['evaluation'])<2:
            raise ValueError('private archive mode requires at least two distinct validation/evaluation files')
        import hashlib
        seen=set()
        for file in paths:
            digest=hashlib.sha256(Path(file).read_bytes()).hexdigest()
            if digest in seen:raise ValueError('training/validation/evaluation archives must not be duplicate files')
            seen.add(digest)
    re=c['real_estate']
    if any(not isinstance(re[k],(int,float)) or not np.isfinite(re[k]) for k in ('minimum_weight','equity_correlation','annual_vol','annual_drift','liquidation_haircut')):raise ValueError('RE assumptions must be finite')
    if not 0<=re['minimum_weight']<=1 or not -1<=re['equity_correlation']<=1 or re['annual_vol']<0 or not 0<=re['liquidation_haircut']<1:
        raise ValueError('invalid RE assumptions')
    from emfin_v2.real_estate import validate
    from emfin_v2.market_views import validate_views
    validate_views(c.get('market_return_views',{}))
    if not 0<=c['stress_mean_path_loss_increment']<=.1:raise ValueError('stress view increment must be 0-10 percentage points')
    validate(re)
    return c


def load_archive(path,c):
    with np.load(path,allow_pickle=False) as f:
        required=['market_paths','prices_vector','liability_scenarios','payout_steps','liability_base','mm_growth_paths']
        arrays={key:np.array(f[key]) for key in required}
        funding=np.array(f['funding_paths']) if 'funding_paths' in f else None
        re_logs=np.array(f['re_price_log_paths']) if 're_price_log_paths' in f else None
    paths=arrays['market_paths'];prices=arrays['prices_vector'].ravel()
    if paths.ndim!=3 or any(size<1 for size in paths.shape):raise ValueError('archive needs nonempty (scenario,week,asset) paths')
    if not np.equal(arrays['payout_steps'],np.round(arrays['payout_steps'])).all():raise ValueError('archive payout steps must be whole weeks')
    n,h,d=paths.shape
    liabilities_=arrays['liability_scenarios'];steps=arrays['payout_steps'].astype(int).ravel()
    base=arrays['liability_base'].ravel();growth=arrays['mm_growth_paths']
    if prices.shape!=(d,) or (prices<=0).any() or liabilities_.shape!=(n,len(steps)) or base.shape!=steps.shape or growth.shape!=(n,h):
        raise ValueError('archive dimensions do not align')
    if any(not np.isfinite(a).all() for a in arrays.values()) or (growth<=0).any() or (liabilities_<0).any() or (base<0).any() or (steps<1).any() or (steps>h).any():
        raise ValueError('archive has nonfinite/negative values or invalid payout steps')
    if h!=c['horizon_weeks'] or not 0<=c['cash_index']<d:
        raise ValueError('archive horizon/cash index disagrees with config')
    if c['real_estate']['enabled'] and funding is None:
        raise ValueError('RE archive mode requires separate funding_paths; marked property is not cash')
    if funding is not None and (funding.shape!=paths.shape or not np.isfinite(funding).all() or (funding<0).any()):
        raise ValueError('archive funding_paths must align and be finite/nonnegative')
    if c['real_estate']['enabled'] and (re_logs is None or re_logs.shape!=(n,h) or not np.isfinite(re_logs).all()):raise ValueError('RE archives need finite re_price_log_paths with shape (scenario,week)')
    return ScenarioDraw((paths/prices,liabilities_,steps,base,growth),paths/prices if funding is None else funding/prices,re_logs)


def interval(values):
    x=np.asarray(values,float);mean=x.mean(0)
    half=student.ppf(.975,len(x)-1)*x.std(0,ddof=1)/np.sqrt(len(x))
    return dict(mean=np.atleast_1d(mean).tolist(),low=np.atleast_1d(mean-half).tolist(),high=np.atleast_1d(mean+half).tolist())


def setup(c):
    frame=dataset.weekly_dataset();x=frame[dataset.COLUMNS].to_numpy()
    cov,_=shrinkage.ledoit_wolf_cov(x);mu=x.mean(0)
    mu,_=shrinkage.shrink_mean(mu,np.r_[[mu[:3].mean()]*3,0.,0.,mu[5]],len(x),156.)
    return frame,mu,cov


def draw_paths(c,fit,n,seed,stressed=False):
    frame,mu,cov=fit;h=c['horizon_weeks'];rng=np.random.default_rng(seed)
    z=rng.normal(size=(n,h,6))@np.linalg.cholesky(cov+1e-12*np.eye(6)).T
    equity_gaussian=z[:,:,:3].mean(2)/max(np.sqrt(cov[:3,:3].sum()/9),1e-12)
    scale=np.ones((n,h,1))
    if c['student_nu'] is not None:
        scale=np.sqrt(rng.chisquare(c['student_nu'],(n,h,1))/(c['student_nu']-2))
        z/=scale
    cumul=np.cumsum(mu+z,axis=1);last=frame.iloc[-1]
    paths=np.stack([dataset.gross_market(cumul[:,j],last.YIELD_LEVEL,last.SPREAD_LEVEL,j+1) for j in range(h)],1)
    growth=paths[:,:,5].copy() # no haircut on MMKT
    paths*=1-np.asarray(c['liquidity_haircuts'])
    re=c['real_estate'];funding=paths;re_log=None
    if re['enabled']:
        from emfin_v2.real_estate import calibration,cash_and_mark
        cal=calibration(re);rho=re['equity_correlation']
        shock=(rho*equity_gaussian+np.sqrt(1-rho*rho)*rng.normal(size=(n,h)))/scale[:,:,0]
        re_log=np.cumsum(cal['annual_log_drift']/52+cal['annual_vol']/np.sqrt(52)*shock,axis=1)
        mark,spendable=cash_and_mark(np.exp(re_log),growth,re)
        funding=np.concatenate([paths,spendable[:,:,None]],axis=2)
        paths=np.concatenate([paths,mark[:,:,None]],axis=2)
    steps=np.array([i['week'] for i in c['liabilities']],int)
    bases=np.array([i['amount'] for i in c['liabilities']],float)
    # Explicit optional liability model: same amount shock per payout, correlated
    # with terminal equity stress; default is a deterministic schedule.
    vol=c['liability_vol'];stress=-cumul[:,-1,:3].mean(1)
    stress=(stress-stress.mean())/max(stress.std(),1e-9)
    amounts=bases[None,:]*np.exp(vol*(.3*stress[:,None]+np.sqrt(.91)*rng.normal(size=(n,len(bases))))-.5*vol*vol)
    return ScenarioDraw((paths,amounts,steps,bases,growth),funding,re_log)


def probabilities(c,paths,re_price_logs=None):
    n=len(paths);uniform=np.full(n,1/n)
    # Views and stress belong to these exact path rows.
    i,j=c['view_instruments']
    if not 0<=i<paths.shape[2] or not 0<=j<paths.shape[2]:raise ValueError('view instrument index outside scenario archive')
    terminal=paths[:,-1]-1.
    uniform=np.full(n,1/n)
    views=[];fixed_views=[]
    requested=c.get('market_return_views',{})
    from emfin_v2.market_views import validate_views
    validate_views(requested)
    if c['view_spread']!=0 and not requested:
        views.append(seqep.SeqView(0,lambda p: ep.relative_mean_view(terminal,i,j,c['view_spread'])))
    if terminal.shape[1]>2 and c.get('view_vol_cap') is not None:
        views.append(seqep.SeqView(1,lambda p: ep.volatility_cap(terminal,2,c['view_vol_cap'],pin_mean=p['mean',2])))
    if requested:
        indices=[int(k) for k in requested]
        absolute=ep.View(terminal[:,indices],[requested[str(k)] for k in indices],name='Explicit expected horizon-return targets')
        fixed_views.append(absolute)
        views.append(seqep.SeqView(2,lambda p:absolute,name='My asset return targets'))
    re_view=None
    if c['real_estate']['enabled']:
        from emfin_v2.real_estate import calibration
        if re_price_logs is None:raise ValueError('RE entropy-pooling view needs underlying re_price_log_paths, not rental/sale marks')
        target=calibration(c['real_estate'])['forward_log_drift']*c['horizon_weeks']/52
        re_view=ep.View(np.asarray(re_price_logs)[:,-1],[target],name='Explicit forward RE log-price mean')
        fixed_views.append(re_view)
        views.append(seqep.SeqView(3,lambda p:re_view,name='Forward RE price view'))
    if c.get('sequential_ep',True):
        q=seqep.sequential_entropy_pooling(terminal,views,sweeps=2).posterior_probs
    else:
        pins=seqep._extract_params(terminal,uniform)
        q=ep.joint_entropy_pooling(n,[v.build(pins) for v in views]).posterior_probs
    if fixed_views:
        q=ep.joint_entropy_pooling(n,fixed_views,prior_probs=q).posterior_probs
    loss=np.maximum(0,1-paths[:,:,[i,j]].mean(2)).max(1)
    target=float(loss@q+c['stress_mean_path_loss_increment'])
    try:
        qs=ep.joint_entropy_pooling(n,[ep.View(loss,[target],sense='ge')]+fixed_views,prior_probs=q).posterior_probs
    except (ValueError,RuntimeError):
        raise ValueError('stress target unsupported by simulated paths; reduce stress or increase scenario support')
    return q,qs


def metrics(c,draw,a,probs=None):
    paths,amounts,steps,bases,growth=draw
    m=liabilities.multiperiod_gap_metrics(paths@a,amounts,steps,growth,c['confidence'])
    from scipy.special import logsumexp
    p=np.full(len(paths),1/len(paths)) if probs is None else np.asarray(probs,float)
    ce=-c['risk_tolerance']*logsumexp(-m.terminal_net/c['risk_tolerance'],b=p)
    gaps=[]
    for i,step in enumerate(steps):
        required=amounts[:,i].copy()
        for j,prior in enumerate(steps):
            if prior<step or (prior==step and j<i):required+=amounts[:,j]*growth[:,step-1]/growth[:,prior-1]
        gaps.append(mpep.cml_of_paths(np.maximum(required-funding_paths(draw)[:,step-1]@a,0),p,c['confidence']))
    return np.array(gaps),float(ce)


def dro_buffer(c,a,liability=True):
    from emfin_v2.toolbox.wasserstein import penalty
    return c['wealth']*penalty(a/c['wealth'],c.get('wasserstein_radius',0.),c['confidence'],c.get('wasserstein_liability_scale',.01) if liability else 0.)


def solve(c,draw,q,qs,mult):
    paths,amounts,steps,bases,growth=draw;n,d=paths.shape[0],paths.shape[2]
    lower_buffer=c['wealth']*c.get('wasserstein_radius',0.)/(1-c['confidence'])/d
    smallest_budget=float(np.min(bases*c['funding_budget_fraction']*mult))
    if lower_buffer>smallest_budget+1e-8:
        return None,dict(kind='incompatible risk settings',reason=f'W1 buffer is at least ${lower_buffer:,.0f}, above the smallest payment budget ${smallest_budget:,.0f}; adjust radius or budget explicitly, not solver tolerances',cash_fallback_rejected=True)
    try:
        a,diag=liabilities.optimization_multiperiod(paths,np.ones(d),c['wealth'],amounts,steps,bases,growth,
            c['risk_tolerance'],c['confidence'],c['loss_budget'],c['funding_budget_fraction']*mult,
            scenario_probs=q,n_optimization_scenarios=n,cml_budget=c['cml_budget'],
            stress_probabilities=[qs],funding_stress_probabilities=[qs],
            wasserstein_radius=c.get('wasserstein_radius',0.),wasserstein_liability_scale=c.get('wasserstein_liability_scale',.01),
            funding_market_paths=funding_paths(draw),
            minimum_weights=c.get('minimum_weights') if c.get('minimum_weights') is not None else np.r_[np.zeros(6),c['real_estate']['minimum_weight']] if d==7 else None)
        return a,dict(kind='optimized',**diag)
    except RuntimeError as err:
        # Cash is not assumed feasible: require pointwise budgets, a stronger
        # check than any scenario weighting or convex mixture of posteriors.
        a=np.zeros(d);a[c['cash_index']]=c['wealth']
        gap,_=metrics(c,draw,a)
        portfolio=paths@a/c['wealth']
        max_loss=float(np.maximum(0,1-portfolio).max())
        required=np.zeros(len(paths));pointwise=[]
        for i in np.argsort(steps,kind='stable'):
            need=amounts[:,i].copy()
            for j in range(len(steps)):
                if steps[j]<steps[i] or (steps[j]==steps[i] and j<i):
                    need+=amounts[:,j]*growth[:,steps[i]-1]/growth[:,steps[j]-1]
            pointwise.append(float(np.maximum(need-funding_paths(draw)[:,steps[i]-1]@a,0).max()) <= c['funding_budget_fraction']*mult*bases[i]+1e-6)
        if (not c.get('minimum_weights') or all(v==0 for j,v in enumerate(c['minimum_weights']) if j!=c['cash_index'])) and (d!=7 or c['real_estate']['minimum_weight']==0) and all(pointwise) and max_loss+dro_buffer(c,a,False)/c['wealth']<=min(c['loss_budget'],c['cml_budget']):
            return a,dict(kind='verified pointwise cash fallback',reason=str(err))
        return None,dict(kind='unavailable',reason=str(err),cash_fallback_rejected=True)


def run(c,output='artifacts/default'):
    started=time.perf_counter()
    archive=c.get('scenario_archives')
    fit=None if archive else setup(c)
    draw=load_archive(archive['training'],c) if archive else draw_paths(c,fit,c['train_scenarios'],c['seed'])
    if archive:
        import copy
        c=copy.deepcopy(c)
        prior=c['liabilities']
        c['liabilities']=[dict(name=prior[i]['name'] if len(prior)==len(draw[2]) else f'Imported payout {i+1}',week=int(step),amount=float(draw[3][i])) for i,step in enumerate(draw[2])]
    q,qs=probabilities(c,draw[0],getattr(draw,'re_price_logs',None));d=draw[0].shape[2]
    mins=np.asarray(c['minimum_weights'],float) if c.get('minimum_weights') is not None else np.r_[np.zeros(6),c['real_estate']['minimum_weight']] if d==7 else np.zeros(d)
    if mins.shape!=(d,) or not np.isfinite(mins).all() or (mins<0).any() or mins.sum()>1:raise ValueError('invalid minimum holdings')
    equal=np.full(d,1/d)
    for _ in range(d+1):
        locked=equal<mins
        equal=np.maximum(equal,mins)
        free=equal>mins+1e-12
        if equal.sum()<=1+1e-12:break
        if not free.any():equal=mins.copy();break
        equal[free]-=(equal.sum()-1)/free.sum()
    baseline={'1/N':equal*c['wealth']}
    baseline['shrunk MV']=benchmark.mean_variance_allocation(draw[0][:,-1].mean(0),np.cov(draw[0][:,-1].T),np.ones(d),c['wealth'],c['risk_tolerance'],minimum_weights=mins)
    validation=[load_archive(p,c) for p in archive['validation']] if archive else [draw_paths(c,fit,c['validation_scenarios'],c['seed']+1000+j) for j in range(c['validation_seeds'])]
    validation_stress=[probabilities(c,v[0],getattr(v,'re_price_logs',None))[1] for v in validation]
    calibration=[];chosen=None;status={}
    for mult in sorted(c['multiplier_grid'],reverse=True):
        a,diag=solve(c,draw,q,qs,mult)
        if a is None:
            calibration.append(dict(multiplier=mult,status=diag));continue
        # A finite calibration grid may damp the risky allocation with cash.
        # This is disclosed as portfolio calibration, not an optimality claim.
        # Cash must satisfy stronger pointwise training budgets before mixing.
        cash=np.zeros(d);cash[c['cash_index']]=c['wealth']
        cash_safe=True
        for k,step in enumerate(draw[2]):
            need=draw[1][:,k].copy()
            for j,prior in enumerate(draw[2]):
                if prior<step or (prior==step and j<k):need+=draw[1][:,j]*draw[4][:,step-1]/draw[4][:,prior-1]
            cash_safe &= bool(np.maximum(need-funding_paths(draw)[:,step-1]@cash,0).max()+dro_buffer(c,cash) <= c['funding_budget_fraction']*mult*draw[3][k])
        cash_safe &= bool(np.maximum(0,1-draw[0]@cash/c['wealth']).max()+dro_buffer(c,cash,False)/c['wealth']<=min(c['cml_budget'],c['loss_budget']))
        if np.any(mins[np.arange(d)!=c['cash_index']]>0):cash_safe=False
        grid=c.get('cash_mix_grid',[1.,.75,.5,.25,0.]) if cash_safe else [1.]
        for risky_fraction in grid:
            candidate=risky_fraction*a+(1-risky_fraction)*cash
            ci=interval([metrics(c,v,candidate)[0] for v in validation])
            stress_ci=interval([metrics(c,v,candidate,ps)[0] for v,ps in zip(validation,validation_stress)])
            budgets=draw[3]*c['funding_budget_fraction']
            passed=bool(np.all(np.maximum(ci['high'],stress_ci['high'])+dro_buffer(c,candidate)<=budgets))
            calibration.append(dict(multiplier=mult,risky_fraction=risky_fraction,status=diag['kind'],wasserstein_buffer=dro_buffer(c,candidate),gap_cvar=ci,stressed_gap_cvar=stress_ci,passed=passed))
            if passed:
                chosen=candidate;status=dict(diag)
                if risky_fraction<1:
                    status['kind']='calibrated optimizer/cash mixture'
                    status['risky_fraction']=risky_fraction
                    status['optimality_claim']=False
                break
        if chosen is not None:break
    allocations=dict(baseline)
    if chosen is not None:allocations['proposed']=chosen
    else:status={'kind':'no calibration candidate passed','note':'No proposed allocation is returned; baselines remain comparators, not safe fallbacks.'}
    # Counterfactual stress panel: nominal-funded optimizer versus robust one,
    # same training scenarios and all other parameters fixed.
    nominal,nomdiag=solve(c,draw,q,q,calibration[-1]['multiplier'])
    if nominal is not None and chosen is not None:
        alpha=calibration[-1].get('risky_fraction',1.)
        cash=np.zeros(d);cash[c['cash_index']]=c['wealth']
        nominal=alpha*nominal+(1-alpha)*cash
    if nominal is not None:allocations['without posterior stress']=nominal
    evaluation=[load_archive(p,c) for p in archive['evaluation']] if archive else [draw_paths(c,fit,c['evaluation_scenarios'],c['seed']+10000+j) for j in range(c['evaluation_seeds'])]
    for v in validation+evaluation:
        if v[0].shape[1:]!=draw[0].shape[1:] or not np.array_equal(v[2],draw[2]) or not np.array_equal(v[3],draw[3]):raise ValueError('all split archives must share asset/horizon dimensions, payout weeks and liability bases')
    evaluation_stress=[probabilities(c,v[0],getattr(v,'re_price_logs',None))[1] for v in evaluation]
    rows=[];fan={}
    for name,a in allocations.items():
        scores=[metrics(c,v,a) for v in evaluation]
        gap_ci=interval([s[0] for s in scores]);ce_ci=interval([s[1] for s in scores])
        stress_gap_ci=interval([metrics(c,v,a,ps)[0] for v,ps in zip(evaluation,evaluation_stress)])
        rows.append(dict(method=name,net_ce=ce_ci,gap_cvar=gap_ci,stressed_gap_cvar=stress_gap_ci,training_gap=metrics(c,draw,a)[0].tolist(),wasserstein_buffer=dro_buffer(c,a),wasserstein_gap_upper=(np.maximum(gap_ci['high'],stress_gap_ci['high'])+dro_buffer(c,a)).tolist(),budgets=(draw[3]*c['funding_budget_fraction']).tolist(),
                         evaluation_pass=bool(np.all(np.maximum(gap_ci['high'],stress_gap_ci['high'])+dro_buffer(c,a)<=draw[3]*c['funding_budget_fraction']))))
        # Before/after payout fan, cash provision convention, fixed planned liabilities.
        v=evaluation[0];values=v[0]@a
        paid=np.zeros_like(values)
        for j,step in enumerate(v[2]):
            paid[:,step-1:]+=v[1][:,j,None]*v[4][:,step-1:]/v[4][:,[step-1]]
        fan[name]=np.quantile((values-paid)/c['wealth'],[.05,.25,.5,.75,.95],axis=0).tolist()
    gross_common=draw[0][:,-1]
    from emfin_v2.toolbox.reporting import efficient_frontier
    common_mu=(gross_common-1).mean(0);common_cov=np.cov(gross_common,rowvar=False)
    frontier=efficient_frontier(gross_common)
    points={name:dict(risk=float(np.sqrt((a/c['wealth'])@common_cov@(a/c['wealth']))),mean=float(common_mu@(a/c['wealth']))) for name,a in allocations.items()}
    result=dict(frontier=frontier,points=points,label=c['label'],config=c,snapshot=c.get('valuation_date','user-supplied archive') if archive else str(fit[0].index[-1].date()),seconds=time.perf_counter()-started,
        status=status,calibration=calibration,rows=rows,weights={k:(a/c['wealth']).tolist() for k,a in allocations.items()},
        assets=c.get('asset_names',['DFUS','DFAI','DFAE','UST10','USIG','MMKT']+(['AD apartments (private observed calibration)'] if d==7 and c['real_estate'].get('source')=='abu_dhabi_private' else ['Singapore URA private residential price index'] if d==7 and c['real_estate'].get('source')=='singapore_ura' else ['RE synthetic'] if d==7 else [])),
        net_wealth_fan=fan, supersedes='All earlier multi-period figures before cumulative payout correction.',
        caveats=['Wasserstein risk bounds use an explicit L1 transport metric on normalized path prices and cumulative payout requirements, unrestricted support and a development-selected radius, not a confidence-calibrated ambiguity set. Utility remains nominal.',
                 'Monte Carlo t intervals describe batch estimates conditional on the fitted model, not economic forecast uncertainty. Zero observed losses yield zero-width intervals, not a bound on unseen tails.',
                 'Archive split independence is the input provider responsibility; generated mode uses disjoint calibration/evaluation seeds. Final failures are never recalibrated away.',
                 'Stressed posterior and nominal share funding/CML thresholds, covering their finite convex hull only.',
                 'Liabilities and views are illustrative; Student-t nu=8 is development-selected, not client evidence.',
                 'Default weekly t shocks aggregate by summation; quarterly shocks are not assumed to preserve t degrees of freedom.',
                 'Cumulative payouts use money-market opportunity costs, not dynamic rebalancing. RE uses an explicit fixed planned sale/settlement schedule; marked value is not available cash.',
                 'Cash mixing is an explicit validation-selected portfolio calibration grid, not a claim of globally optimal robust weights.',
                 'With minimum holdings, 1/N is equal-weighted over the remaining free budget; all methods honor the same minima.'])
    from emfin_v2.dashboard import summarize
    result['dashboard']=summarize(c,draw,q,qs,evaluation,allocations,rows,status,result['assets'])
    def convert(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x).__name__)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(result,indent=2,default=convert,allow_nan=False)+'\n')
    lines=['# Default funding-risk comparison',c['label'],f"Snapshot {result['snapshot']}; status: {status['kind']}",
           '|Method|Net CE mean ($)|Per-date nominal/stressed gap CVaR upper CI ($)|W1 buffer ($)|Upper bounds incl. W1 ($)|Pass risk budgets?|' ,'|---|---:|---|---:|---|---|']
    for row in rows:lines.append(f"|{row['method']}|{row['net_ce']['mean'][0]:,.0f}|{', '.join(f'{g:,.0f}/{s:,.0f}' for g,s in zip(row['gap_cvar']['high'],row['stressed_gap_cvar']['high']))}|{row['wasserstein_buffer']:,.0f}|{', '.join(f'{v:,.0f}' for v in row['wasserstein_gap_upper'])}|{row['evaluation_pass']}|")
    lines+=['## Qualifications']+['- '+c for c in result['caveats']]
    (out/'report.md').write_text('\n\n'.join(lines)+'\n')
    import csv
    with (out/'benchmarks.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['method','net_ce_mean','net_ce_low','net_ce_high','date_gap_means','date_gap_CI_upper','stressed_gap_CI_upper','budgets','wasserstein_buffer','wasserstein_gap_upper','pass'])
        for r in rows:w.writerow([r['method'],r['net_ce']['mean'][0],r['net_ce']['low'][0],r['net_ce']['high'][0],json.dumps(r['gap_cvar']['mean']),json.dumps(r['gap_cvar']['high']),json.dumps(r['stressed_gap_cvar']['high']),json.dumps(r['budgets']),r['wasserstein_buffer'],json.dumps(r['wasserstein_gap_upper']),r['evaluation_pass']])
    # Shared chart renderer; exported HTML never pretends static controls run Python.
    from emfin_v2.explorer import from_default,template
    (out/'report.html').write_text(template(from_default(result),True))
    print(out/'report.md',status['kind'],f"{result['seconds']:.2f}s",flush=True)
    return result


def main(argv=None):
    import argparse,sys
    argv=list(sys.argv[1:] if argv is None else argv)
    if '--research' in argv and ('--help' in argv or '-h' in argv):
        from emfin_v2.engine import main as research
        research([a for a in argv if a!='--research'])
        return
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(DEFAULT_CONFIG));p.add_argument('--output',default='artifacts/default');p.add_argument('--research',action='store_true')
    args,extra=p.parse_known_args(argv)
    if args.research:
        from emfin_v2.engine import main as research
        try:
            research(extra)
        except (ValueError,RuntimeError) as error:
            dest=Path('artifacts/research');dest.mkdir(parents=True,exist_ok=True)
            (dest/'status.json').write_text(json.dumps(dict(status='unavailable',reason=str(error),superseded='Older multi-period figures are invalid after cumulative payout correction.'),indent=2)+'\n')
            print('Research run unavailable:',error)
        return
    if extra:p.error('research flags require --research; default uses one JSON config')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    try:run(load_config(args.config),out)
    except (ValueError,RuntimeError,np.linalg.LinAlgError) as e:
        report={'status':'unavailable','reason':str(e),'no_allocation':True}
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        (out/'report.md').write_text('# Run unavailable\n\n'+str(e)+'\n\nNo allocation was returned.\n')
        print(out/'report.md','unavailable:',e)

if __name__=='__main__':main()
