"""Bounded strict-mode evidence and past-only empirical-radius snapshots."""
from pathlib import Path
import copy,json,time,subprocess,hashlib
import numpy as np
import pandas as pd
from emfin_v2.default_run import run,setup
from emfin_v2.radius_calibration import calibrate
from experiments.robustness import config,source_tree_hash,save

ROOT=Path('artifacts/strict-funding-20261107')


def main():
    started=time.perf_counter();ROOT.mkdir(parents=True,exist_ok=True)
    metadata=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True).strip()),source_sha256=source_tree_hash(),protocol_sha256=hashlib.sha256(Path('docs/STRICT_FUNDING_PROTOCOL.md').read_bytes()).hexdigest())
    c=config(100,200,300,2);c.update(funding_mode='pay_all_99',scenario_tier='interactive')
    pilot=run(c,ROOT/'pilot')
    c=config(100,200,400,4);c.update(funding_mode='pay_all_99',scenario_tier='bounded4batch strict diagnostic')
    confirm=run(c,ROOT/'confirm')
    fixtures=[]
    for name,schedule in [('95M-final',[dict(name='Counterfactual95M',week=52,amount=95e6)]),('60M-early-30M-final',[dict(name='Counterfactual early',week=13,amount=60e6),dict(name='Counterfactual final',week=52,amount=30e6)])]:
        cc=copy.deepcopy(c);cc['liabilities']=schedule
        z=run(cc,ROOT/name);fixtures.append(dict(name=name,status=z['status'],rows=z['rows'],weights=z['weights'],tradeoff=z['strict_tradeoff']))
    empirical=copy.deepcopy(c);empirical['radius_calibration_mode']='past_empirical'
    empirical_result=run(empirical,ROOT/'empirical-current')
    frame=setup(c)[0];history=[]
    for year in range(2006,2025):
        cc=copy.deepcopy(c);cc['history_end']=str(frame.loc[frame.index<pd.Timestamp(f'{year+1}-01-01')].index[-1].date());history.append(dict(year=year,**calibrate(cc,frame)))
    result=dict(**metadata,seconds=time.perf_counter()-started,pilot_seconds=pilot['seconds'],confirm_seconds=confirm['seconds'],current=dict(status=confirm['status'],rows=confirm['rows'],weights=confirm['weights'],tradeoff=confirm['strict_tradeoff']),fixtures=fixtures,radius_history=history,radius_current=empirical_result['config']['radius_calibration'],radius_status=empirical_result['status'],scope='Prespecified bounded research diagnostics.3Mdefault/95M/60M+30Mfixtures are illustrative, not user obligations. No default or budget replacement. No empirical99%orW1cash-ledger guarantee. Latest-vintage property, assumed45day release lag.')
    save(result,ROOT/'summary.json');print(json.dumps(dict(seconds=result['seconds'],status=confirm['status'],radius=result['radius_current']),indent=2))

if __name__=='__main__':main()
