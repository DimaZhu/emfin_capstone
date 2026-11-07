import copy
import numpy as np
import pandas as pd
import pytest
from emfin_v2.radius_calibration import balanced_distances,calibrate


def config():return dict(horizon_weeks=52,asset_registry={'x':1},wasserstein_metric='max_path',liquidity_haircuts=[0.],cash_index=0,real_estate=dict(enabled=False),fx=dict(enabled=False),wealth=100.,confidence=.95,funding_budget_fraction=.2,liabilities=[dict(amount=3.)])


def test_assignment_oracle_invariance_and_determinism():
    x=np.arange(8.)[:,None,None]
    # Reconstruct seeded assignment1independently: ordered1D transport is sorting.
    order=np.random.default_rng(20261107).permutation(8)
    oracle=np.mean(np.abs(np.sort(order[:4])-np.sort(order[-4:])))
    d=balanced_distances(x);assert d[0]==pytest.approx(oracle)
    assert d==balanced_distances(x)
    assert d==balanced_distances(np.repeat(np.repeat(x,3,axis=1),2,axis=2))
    with pytest.raises(ValueError):balanced_distances(x[:7])


def test_past_only_cutoff_incomplete_and_no_feasibility_truncation():
    frame=pd.DataFrame(np.random.default_rng(1).normal(0,.03,(600,1)),index=pd.date_range('2000-01-07',periods=600,freq='W-FRI'))
    c=config();c['history_end']=str(frame.index[519].date());r=calibrate(c,frame)
    changed=frame.copy();changed.iloc[520:]=100
    assert r==calibrate(c,changed)
    assert r['blocks']==10 and r['last_observation']==c['history_end']
    assert r['budget_conflict'] and r['radius']>.01
    c['history_end']=str(frame.index[363].date());r=calibrate(c,frame);assert not r['available'] and 'radius' not in r
    c['horizon_weeks']=26
    with pytest.raises(ValueError):calibrate(c,frame)
