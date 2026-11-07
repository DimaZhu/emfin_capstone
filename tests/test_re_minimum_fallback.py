import numpy as np
from unittest.mock import patch
from emfin_v2.default_run import load_config,setup,draw_paths,probabilities,solve


def test_minimum_holding_fallback_respects_re_and_pointwise_guards():
    c=load_config();c['real_estate'].update(enabled=True,minimum_weight=.1,holding_mode='minimum')
    d=draw_paths(c,setup(c),100,c['seed']);q,qs=probabilities(c,d[0],d.re_price_logs)
    with patch('emfin_v2.toolbox.liabilities.optimization_multiperiod',side_effect=RuntimeError('test solver failure')):
        a,status=solve(c,d,q,qs,1.)
    assert status['kind']=='verified pointwise minimum-holdings fallback'
    assert status['optimality_claim'] is False
    assert a[6]==1e7 and a[5]==9e7 and a.sum()==1e8
    with patch('emfin_v2.toolbox.liabilities.optimization_multiperiod',side_effect=RuntimeError('test solver failure')):
        c['funding_budget_fraction']=.01
        rejected,_=solve(c,d,q,qs,1.)
    assert rejected is None


def test_fixed_holdings_fallback_is_an_equality_not_a_floor():
    c=load_config();d=draw_paths(c,setup(c),100,c['seed']);q,qs=probabilities(c,d[0],d.re_price_logs)
    with patch('emfin_v2.toolbox.liabilities.optimization_multiperiod',side_effect=RuntimeError('test solver failure')):
        a,status=solve(c,d,q,qs,1.)
    assert status['kind']=='verified pointwise fixed-holdings fallback'
    assert a[6]==1e7 and a[5]==9e7


def test_fixed_holding_constraint_in_optimizer_and_benchmark():
    from emfin_v2.toolbox.liabilities import optimization_multiperiod
    from emfin_v2.toolbox.benchmark import mean_variance_allocation
    # Asset1 has strictly better return; floor-only would buy it all.
    paths=np.tile(np.array([[[1.,1.1],[1.,1.2]]]),(20,1,1))
    a,_=optimization_multiperiod(paths,np.ones(2),100.,np.zeros((20,1)),np.array([2]),np.array([0.]),np.ones((20,2)),10.,.95,1.,.2,cml_budget=1.,fixed_weights={'1':.1})
    assert np.allclose(a,[90.,10.],atol=1e-5)
    b=mean_variance_allocation(paths[:,-1].mean(0),np.eye(2)*.001,np.ones(2),100.,10.,fixed_weights={'1':.1})
    assert np.allclose(b,[90.,10.],atol=1e-4)
