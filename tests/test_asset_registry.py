import copy
import pytest
from emfin_v2.assets import load_registry,layout,validate_registry,wasserstein_minimum_buffer


def test_target_universe_roles_are_explicit_and_gold_is_not_equity():
    d=load_registry();s=layout(d)
    assert s['ids']==['us_equity','em_equity','gold','treasury','cash','sg_property']
    assert s['factor_indices']['equity']==[0,1]
    assert s['cash_index']==4 and s['property_indices']==[5]
    assert s['view_indices']==[0,1,2,3]
    assert wasserstein_minimum_buffer(d,1e8,2e-5,.95)==pytest.approx(6666.6666667)


def test_add_and_remove_dummy_asset_changes_all_layout_roles():
    d=load_registry();dummy=copy.deepcopy(d['assets'][0]);dummy.update(id='dummy',ticker='DUMMY',name='Dummy test equity');d['assets'].insert(0,dummy)
    s=layout(d);assert len(s['ids'])==7 and s['cash_index']==5 and s['property_indices']==[6]
    assert s['factor_indices']['equity']==[0,1,2]
    assert s['view_indices']==[0,1,2,3,4]
    d['assets'][0]['enabled']=False
    assert layout(d)==layout(load_registry())


@pytest.mark.parametrize('change',[lambda d:d['assets'][0].update(id='cash'),lambda d:d['assets'][0].update(return_model='invented'),lambda d:d['assets'][4].update(enabled=False),lambda d:d['assets'][0].update(haircut=float('nan'))])
def test_registry_fails_on_ambiguous_or_unsupported_models(change):
    d=load_registry();change(d)
    with pytest.raises(ValueError):validate_registry(d)


def test_runtime_add_remove_paths_holdings_and_views_follow_registry():
    import numpy as np,pandas as pd
    from emfin_v2.registry_runtime import configure,draw
    from emfin_v2.default_run import load_config,holding_bounds,probabilities
    from emfin_v2.market_views import evidence
    d=load_registry();dummy=copy.deepcopy(d['assets'][0]);dummy.update(id='dummy',ticker='DUMMY',name='Dummy test equity');d['assets'].insert(0,dummy)
    for doc in [d,load_registry()]:
        c=configure(load_config(),doc);n=len(c['asset_names'])-1
        dims=n+int(c['fx']['enabled']);mu=np.full(dims,.0003);cov=np.eye(dims)*.00005;
        if c['fx']['enabled']:mu[-1]=0.
        cov[c['cash_index'],:]=0;cov[:,c['cash_index']]=0
        f=pd.DataFrame(np.zeros((60,n)),index=pd.date_range('2020-01-03',periods=60,freq='W-FRI'))
        paths=draw(c,(f,mu,cov),100,42)
        assert paths[0].shape==(100,52,n+1)
        assert np.array_equal(paths.funding_paths[:,:,-1],np.zeros((100,52)))
        mins,fixed=holding_bounds(c,n+1);assert fixed=={n:.1}
        q,qs=probabilities(c,paths[0],paths.re_price_logs)
        v=evidence(c,paths,q,qs)
        assert len(v['rows'])==n-1
        assert v['rows'][0]['name']==c['asset_names'][0]
