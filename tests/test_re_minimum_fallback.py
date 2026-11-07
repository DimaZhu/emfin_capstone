import numpy as np
from unittest.mock import patch
from emfin_v2.default_run import load_config,setup,draw_paths,probabilities,solve


def test_minimum_holding_fallback_respects_re_and_pointwise_guards():
    c=load_config();c['real_estate'].update(enabled=True,minimum_weight=.1)
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
