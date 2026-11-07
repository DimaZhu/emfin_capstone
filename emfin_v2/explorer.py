"""Small local-only explorer over shared engine primitives, no web dependencies.

This fast companion is a single-date, deterministic-liability experiment, not
an interactive replacement for every multi-period/real-estate experiment.
"""
import argparse
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
import json,time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import numpy as np
from emfin_v2.toolbox import dataset,shrinkage,entropy_pooling as ep,seqep,liabilities,benchmark,risk_stats,reporting,scenario_market,mpep

@dataclass(frozen=True)
class Controls:
    liability: float=3.
    budget: float=20.
    view: float=50.
    student: bool=True
    sequential: bool=True
    stress: bool=True
    multiperiod: bool=True
    real_estate: bool=False
    re_min: float=0.
    wealth: float=100.
    scenario_tier: str='interactive'
    recurring_monthly_k: float=250.
    recurring_months: int=12
    recurring_first_week: int=4
    recurring_spacing_weeks: float=52/12
    horizon: int=52
    profile: str='Balanced'
    payouts: tuple | None=None
    cml: float=6.
    re_source: str='singapore_ura'
    re_sg_type: str='All Residential'
    dro: bool=True
    dro_radius: float=.00002
    re_alpha: float=0.
    re_rent: float=0.
    re_correlation: float=.3
    re_sale_week: int=0
    re_sale_delay: int=12
    re_history: str='central'
    re_haircut: float=10.
    re_forward_drift: float=4.
    re_forward_mode: str='view'
    asset_views: tuple | None=None
    stress_increment: float=1.



    def validate(self):
        if not 0<=self.liability<=105 or not .01<=self.budget<=50 or not 0<=self.view<=100:
            raise ValueError('controls outside supported range')
        if not 0<=self.re_min<=30:raise ValueError('RE minimum must be 0-30%')
        if not np.isfinite(self.wealth) or not 1<=self.wealth<=1000 or type(self.horizon) is not int or not 1<=self.horizon<=52:raise ValueError('capital $1-1000M; horizon 1-52 whole weeks')
        if self.scenario_tier not in ('interactive','full'):raise ValueError('unknown scenario tier')
        if self.profile not in ('Preserve','Balanced','Growth','Aggressive'):raise ValueError('unknown risk profile')
        if self.re_source not in ('singapore_ura','abu_dhabi_private','synthetic'):raise ValueError('unknown RE data source')
        if not np.isfinite(self.dro_radius) or not 0<=self.dro_radius<=.001:raise ValueError('Wasserstein radius must be 0-.001')
        from emfin_v2.real_estate import validate
        validate(dict(sg_property_type=self.re_sg_type,smoothing_alpha=self.re_alpha,net_rental_yield=self.re_rent/100,sale_week=self.re_sale_week,sale_delay_weeks=self.re_sale_delay,history_case=self.re_history,forward_mode=self.re_forward_mode,forward_log_drift=self.re_forward_drift/100))
        if not np.isfinite(self.re_correlation) or not -1<=self.re_correlation<=1:raise ValueError('RE dependence must be -1 to 1')
        if not np.isfinite(self.re_haircut) or not 0<=self.re_haircut<100:raise ValueError('RE sale haircut must be 0 to below 100%')
        if not np.isfinite(self.stress_increment) or not 0<=self.stress_increment<=10:raise ValueError('stress increment must be 0-10 percentage points')
        if self.asset_views is not None and (len(self.asset_views)!=5 or any(not np.isfinite(v) or not -50<=v<=50 for v in self.asset_views)):raise ValueError('five expected horizon returns must be -50% to 50%')
        if type(self.recurring_months) is not int or not 0<=self.recurring_months<=60:raise ValueError('recurring months must be0-60')
        from emfin_v2.payouts import expand_recurring
        if self.recurring_months:expand_recurring(dict(amount=self.recurring_monthly_k*1000,months=self.recurring_months,first_week=self.recurring_first_week,spacing_weeks=self.recurring_spacing_weeks),self.horizon)
        if not 1<=self.cml<=40:raise ValueError('path-loss tail budget must be 1-40%')
        if self.payouts is not None:
            if len(self.payouts)>6:raise ValueError('up to six additional one-off payouts')
            for name,week,amount in self.payouts:
                if not isinstance(name,str) or len(name)>80 or type(week) is not int or not 1<=week<=self.horizon or not np.isfinite(amount) or not 0<=amount<=2000:raise ValueError('invalid payout name, week or amount')

@lru_cache(maxsize=1)
def base_inputs():
    frame=dataset.weekly_dataset();x=frame[dataset.COLUMNS].to_numpy()
    cov,_=shrinkage.ledoit_wolf_cov(x);raw=x.mean(0)
    target=np.r_[[raw[:3].mean()]*3,0.,0.,raw[5]]
    mean,_=shrinkage.shrink_mean(raw,target,len(x),156.)
    return frame,mean,cov

@lru_cache(maxsize=128)
def compute(c=Controls()):
    c.validate()
    if c.multiperiod:
        from emfin_v2.default_run import load_config,run
        from tempfile import TemporaryDirectory
        config=load_config()
        config['scenario_tier']=c.scenario_tier
        if c.scenario_tier=='interactive':
            config.update(train_scenarios=100,validation_scenarios=200,evaluation_scenarios=300,validation_seeds=2,evaluation_seeds=2,multiplier_grid=[1.,.25],cash_mix_grid=[1.,.5,0.])
            config['label']='Interactive COARSE one-year model, 100/200/300 scenarios and two validation/evaluation seeds; not research-grade evidence'

        config['wealth']=c.wealth*1e6
        config['horizon_weeks']=c.horizon
        config['risk_profile']=c.profile
        config['risk_tolerance']=config['wealth']*dict(Preserve=.05,Balanced=.1,Growth=.2,Aggressive=.4)[c.profile]
        config['cml_budget']=c.cml/100
        config['wasserstein_radius']=c.dro_radius if c.dro else 0.
        from emfin_v2.payouts import expand_recurring
        one_off=[] if c.payouts is None else [dict(name=name,week=week,amount=amount*1e6) for name,week,amount in c.payouts]
        config['recurring_payout']=dict(amount=c.recurring_monthly_k*1000,months=c.recurring_months,first_week=c.recurring_first_week,spacing_weeks=c.recurring_spacing_weeks) if c.recurring_months else None
        config['one_off_liabilities']=one_off
        config['liabilities']=expand_recurring(config['recurring_payout'],c.horizon,one_off)
        if not config['liabilities']:config['liabilities']=[dict(name='No payment',week=c.horizon,amount=0)]
        config['funding_budget_fraction']=c.budget/100
        config['view_spread']=.005*c.view/50
        config['sequential_ep']=c.sequential
        config['stress_mean_path_loss_increment']=c.stress_increment/100 if c.stress else 0.
        config['market_return_views']={str(i):v/100 for i,v in enumerate(c.asset_views)} if c.asset_views is not None else {}
        config['student_nu']=8. if c.student else None
        config['real_estate']['enabled']=c.real_estate
        config['real_estate']['source']=c.re_source
        config['real_estate']['sg_property_type']=c.re_sg_type
        config['real_estate']['minimum_weight']=c.re_min/100 if c.real_estate else 0.
        config['real_estate'].update(smoothing_alpha=c.re_alpha,net_rental_yield=c.re_rent/100,equity_correlation=c.re_correlation,sale_week=c.re_sale_week,sale_delay_weeks=c.re_sale_delay,history_case=c.re_history,liquidation_haircut=c.re_haircut/100,forward_mode=c.re_forward_mode,forward_log_drift=c.re_forward_drift/100)
        with TemporaryDirectory() as folder:
            result=run(config,folder)
        data=from_default(result);data['controls']=asdict(c)
        return data
    start=time.perf_counter();frame,mean,cov=base_inputs()
    anchor=frame.iloc[-1];rng=np.random.default_rng(20261107)
    chol=np.linalg.cholesky(c.horizon*cov+1e-12*np.eye(6))
    def draw(n):
        z=rng.normal(size=(n,6))@chol.T
        if c.student:z/=np.sqrt(rng.chisquare(8,(n,1))/6)
        return dataset.gross_market(c.horizon*mean+z,anchor.YIELD_LEVEL,anchor.SPREAD_LEVEL,c.horizon)
    market=draw(1000);judge=draw(8000)
    # A fixed synthetic proportional liquidity haircut, not calibrated costs.
    haircut=np.array([.001,.0015,.002,.0005,.001,0.])
    market*=1-haircut;judge*=1-haircut
    x=market-1
    views=[]
    if c.view>0:
        views=[seqep.SeqView(0,lambda p: ep.relative_mean_view(x,1,0,.005*c.view/50),name='equity rank'),
               seqep.SeqView(1,lambda p: ep.volatility_cap(x,2,.065,pin_mean=p['mean',2]),name='EM volatility cap')]
    uniform=np.full(len(x),1/len(x))
    if c.sequential:q=seqep.sequential_entropy_pooling(x,views,sweeps=2).posterior_probs
    else:q=ep.joint_entropy_pooling(len(x),[v.build(seqep._extract_params(x,uniform)) for v in views]).posterior_probs
    # Explicit mean-loss stress on the equity basket, not a CML view.
    loss=-x[:,:3].mean(1)
    stress_q=ep.joint_entropy_pooling(len(x),[ep.View(loss,[float(loss@q+.01)],sense='ge')],prior_probs=q).posterior_probs
    alloc={'1/N':np.full(6,1e8/6),'shrunk MV':benchmark.mean_variance_allocation(market.mean(0),np.cov(market.T),np.ones(6),1e8,1e7)}
    errors={}
    for name,probs,due in [('EP',q,0.),('EP+stress',stress_q,0.),('liability-aware',stress_q if c.stress else q,c.liability*1e6)]:
        try:
            alloc[name],_=liabilities.optimization_liability_aware(market,np.ones(6),1e8,due,1e7,.95,.15,c.budget/100,scenario_probs=probs)
        except RuntimeError as e:errors[name]=str(e)
    rows=[];weights={};points={}
    mu=x.mean(0);sigma=np.cov(x.T)
    for name,a in alloc.items():
        w=a/1e8;weights[name]=w.tolist();points[name]=dict(risk=float(np.sqrt(w@sigma@w)),mean=float(w@mu))
        gap=np.maximum(c.liability*1e6-judge@a,0)
        in_gap=np.maximum(c.liability*1e6-market@a,0)
        rows.append(dict(method=name,ce=float(scenario_market.empirical_certainty_equivalent(judge@a,1e7)),
            gap_cvar=risk_stats.empirical_cvar(gap,.95),nominal_gap=mpep.cml_of_paths(in_gap,stress_q if name=='EP+stress' or (name=='liability-aware' and c.stress) else q if name in ('EP','liability-aware') else uniform,.95),budget=c.liability*1e6*c.budget/100))
    selected=alloc.get('liability-aware',alloc['shrunk MV'])/1e8
    # Fresh Gaussian weekly paths for fan, explicitly nominal even when t is on.
    weekly=rng.normal(size=(2000,c.horizon,6))@np.linalg.cholesky(cov+1e-12*np.eye(6)).T+mean
    cumul=np.cumsum(weekly,1)
    path=np.stack([dataset.gross_market(cumul[:,h,:],anchor.YIELD_LEVEL,anchor.SPREAD_LEVEL,h+1)@selected for h in range(c.horizon)],1)
    fan=np.quantile(path/max(c.liability/100,.01),[.05,.25,.5,.75,.95],axis=0).tolist()
    return dict(controls=asdict(c),assets=['DFUS','DFAI','DFAE','UST10','USIG','MMKT'],weights=weights,rows=rows,
        points=points,frontier=reporting.efficient_frontier(market),fan=fan,errors=errors,
        seconds=time.perf_counter()-start,snapshot=str(frame.index[-1].date()),
        caveat='Illustrative single-date companion. Fixed synthetic haircuts; nominal fresh Monte Carlo, not historical OOS. Fan: gross wealth / total planned liability, before payouts; Gaussian paths even with Student-t selected. Stress is an equity mean-loss tilt, not CML. No client calibration.')


def from_default(result):
    """Same data for CLI static export and the live multi-period panel."""
    cfg=result['config'];rows=[]
    for r in result['rows']:
        rows.append(dict(method=r['method'],ce=r['net_ce']['mean'][0],gap_cvar=r['gap_cvar']['mean'][-1],
            gap_upper=r['wasserstein_gap_upper'][-1],stress_gap=r['stressed_gap_cvar']['mean'][-1],nominal_gap=r['training_gap'][-1],budget=r['budgets'][-1]))
    selected='proposed' if 'proposed' in result['net_wealth_fan'] else 'shrunk MV'
    return dict(controls=dict(scenario_tier=cfg.get('scenario_tier','full'),liability=sum(i['amount'] for i in cfg['liabilities'])/1e6,
        recurring_monthly_k=cfg.get('recurring_payout',{}).get('amount',0)/1000 if cfg.get('recurring_payout') else 0,recurring_months=cfg.get('recurring_payout',{}).get('months',0) if cfg.get('recurring_payout') else 0,recurring_first_week=cfg.get('recurring_payout',{}).get('first_week',4) if cfg.get('recurring_payout') else 4,recurring_spacing_weeks=cfg.get('recurring_payout',{}).get('spacing_weeks',52/12) if cfg.get('recurring_payout') else 52/12,
        budget=cfg['funding_budget_fraction']*100,view=cfg['view_spread']/.005*50,
        student=cfg['student_nu'] is not None,sequential=cfg.get('sequential_ep',True),stress=cfg['stress_mean_path_loss_increment']>0,
        multiperiod=True,real_estate=cfg['real_estate']['enabled'],re_min=cfg['real_estate']['minimum_weight']*100,
        re_sg_type=cfg['real_estate'].get('sg_property_type','All Residential'),re_alpha=cfg['real_estate'].get('smoothing_alpha',0.),re_rent=cfg['real_estate'].get('net_rental_yield',0.)*100,
        re_correlation=cfg['real_estate']['equity_correlation'],re_sale_week=cfg['real_estate'].get('sale_week',0),
        re_sale_delay=cfg['real_estate'].get('sale_delay_weeks',12),re_history=cfg['real_estate'].get('history_case','central'),re_haircut=cfg['real_estate']['liquidation_haircut']*100,re_forward_mode=cfg['real_estate'].get('forward_mode','view'),re_forward_drift=cfg['real_estate'].get('forward_log_drift',.04)*100,stress_increment=cfg['stress_mean_path_loss_increment']*100,asset_views=tuple(cfg.get('market_return_views',{}).get(str(i),0.)*100 for i in range(5)) if cfg.get('market_return_views') else None),
        dashboard=result.get('dashboard'),all_fans=result['net_wealth_fan'],assets=result['assets'],weights=result['weights'],rows=rows,points=result['points'],frontier=result['frontier'],
        training_label='Training gap CVaR (uniform)',fan=result['net_wealth_fan'][selected],fan_title='Net wealth after cumulative payouts',
        fan_note='5/25/50/75/95 percentiles. Net wealth / initial wealth. Payouts provisioned at money-market growth; due weeks are shown on the chart and do not move with the horizon.',
        seconds=result['seconds'],snapshot=result['snapshot'],errors={} if result['status']['kind'] in ('optimized','calibrated optimizer/cash mixture','verified pointwise cash fallback','verified pointwise minimum-holdings fallback') else {'proposed':result['status']['kind']},
        caveat='Status: '+result['status']['kind']+'. Optimizer share '+str(result['status'].get('risky_fraction','not applicable'))+'. Multi-period default: cumulative payouts, calibrated funding budget, shared nominal/stressed-posterior funding and CML bounds. Table shows final nominal mean / worst nominal-stressed upper CI; JSON reports every date and both measures. RE source and sale/rent assumptions are explicit; no measured cross-asset dependence. '+result['caveats'][0])


def template(result, static=False):
    text=(Path(__file__).parent/'web/explorer.html').read_text()
    return text.replace('__INITIAL_DATA__',json.dumps(result).replace('</','<\\/')).replace('__STATIC__','true' if static else 'false')


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);p.add_argument('--precompute',action='store_true');p.add_argument('--export',default=None)
    args=p.parse_args()
    if args.precompute:
        for monthly in (125.,250.,500.):
            for budget in (.1,.2,1.):compute(Controls(recurring_monthly_k=monthly,budget=budget))
    first=compute()
    if args.export:
        Path(args.export).write_text(template(first,True));print(args.export);return
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/','/index.html'):
                self.send_error(404);return
            body=template(first).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.path not in ('/compute','/run-config'):self.send_error(404);return
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length>262144:raise ValueError('request too large')
                data=json.loads(self.rfile.read(length))
                if self.path=='/run-config':
                    from tempfile import TemporaryDirectory
                    from emfin_v2.default_run import load_config,run
                    with TemporaryDirectory() as folder:
                        config_file=Path(folder)/'config.json';config_file.write_text(json.dumps(data))
                        result=from_default(run(load_config(config_file),folder))
                else:
                    if data.get('payouts') is not None:data['payouts']=tuple(tuple(row) for row in data['payouts'])
                    if data.get('asset_views') is not None:data['asset_views']=tuple(data['asset_views'])
                    result=compute(Controls(**data))
                body=json.dumps(result).encode()
                self.send_response(200)
            except Exception as e:
                body=json.dumps({'error':str(e)}).encode();self.send_response(400)
            self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
    print(f'Local explorer: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':main()
