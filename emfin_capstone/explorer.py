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
from emfin_capstone.toolbox import dataset,shrinkage,entropy_pooling as ep,seqep,liabilities,benchmark,risk_stats,reporting,scenario_market,mpep

@dataclass(frozen=True)
class Controls:
    liability: float=95.
    budget: float=.2
    view: float=50.
    student: bool=False
    sequential: bool=True
    stress: bool=False

    def validate(self):
        if not 0<=self.liability<=105 or not .01<=self.budget<=5 or not 0<=self.view<=100:
            raise ValueError('controls outside supported range')

@lru_cache(maxsize=1)
def base_inputs():
    frame=dataset.weekly_dataset();x=frame[dataset.COLUMNS].to_numpy()
    cov,_=shrinkage.ledoit_wolf_cov(x);raw=x.mean(0)
    target=np.r_[[raw[:3].mean()]*3,0.,0.,raw[5]]
    mean,_=shrinkage.shrink_mean(raw,target,len(x),156.)
    return frame,mean,cov

@lru_cache(maxsize=128)
def compute(c=Controls()):
    c.validate();start=time.perf_counter();frame,mean,cov=base_inputs()
    anchor=frame.iloc[-1];rng=np.random.default_rng(20261107)
    chol=np.linalg.cholesky(13*cov+1e-12*np.eye(6))
    def draw(n):
        z=rng.normal(size=(n,6))@chol.T
        if c.student:z/=np.sqrt(rng.chisquare(8,(n,1))/6)
        return dataset.gross_market(13*mean+z,anchor.YIELD_LEVEL,anchor.SPREAD_LEVEL)
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
    weekly=rng.normal(size=(2000,13,6))@np.linalg.cholesky(cov+1e-12*np.eye(6)).T+mean
    cumul=np.cumsum(weekly,1)
    path=np.stack([dataset.gross_market(cumul[:,h,:],anchor.YIELD_LEVEL,anchor.SPREAD_LEVEL,h+1)@selected for h in range(13)],1)
    fan=np.quantile(path/max(c.liability/100,.01),[.05,.25,.5,.75,.95],axis=0).tolist()
    return dict(controls=asdict(c),assets=['DFUS','DFAI','DFAE','UST10','USIG','MMKT'],weights=weights,rows=rows,
        points=points,frontier=reporting.efficient_frontier(market),fan=fan,errors=errors,
        seconds=time.perf_counter()-start,snapshot=str(frame.index[-1].date()),
        caveat='Illustrative single-date companion. Fixed synthetic haircuts; nominal fresh Monte Carlo, not historical OOS. Fan: gross wealth / total planned liability, before payouts; Gaussian paths even with Student-t selected. Stress is an equity mean-loss tilt, not CML. No client calibration.')


def template(result, static=False):
    text=(Path(__file__).parent/'web/explorer.html').read_text()
    return text.replace('__INITIAL_DATA__',json.dumps(result).replace('</','<\\/')).replace('__STATIC__','true' if static else 'false')


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);p.add_argument('--precompute',action='store_true');p.add_argument('--export',default=None)
    args=p.parse_args()
    if args.precompute:
        for due in (75.,90.,95.):
            for budget in (.1,.2,1.):compute(Controls(liability=due,budget=budget))
    first=compute()
    if args.export:
        Path(args.export).write_text(template(first,True));print(args.export);return
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ('/','/index.html'):
                self.send_error(404);return
            body=template(first).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body)
        def do_POST(self):
            if self.path!='/compute':self.send_error(404);return
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length>4096:raise ValueError('request too large')
                data=json.loads(self.rfile.read(length));result=compute(Controls(**data));body=json.dumps(result).encode()
                self.send_response(200)
            except Exception as e:
                body=json.dumps({'error':str(e)}).encode();self.send_response(400)
            self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
    print(f'Local explorer: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':main()
