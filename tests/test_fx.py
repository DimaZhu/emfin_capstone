import numpy as np
import pandas as pd
import pytest
from emfin_v2.fx import load_reference,weekly_factor
from emfin_v2.real_estate import cash_and_mark


def test_official_fx_inverse_quote_integrity_and_past_only_anchors():
    s,m=load_reference()
    assert len(s)==11499 and str(s.index[-1].date())=='2026-10-30'
    assert s.iloc[-1]==pytest.approx(1/1.2776)
    index=pd.date_range('2020-01-03','2020-03-27',freq='W-FRI')
    fx,_=weekly_factor(index)
    assert fx.iloc[0]==pytest.approx(np.log(s.loc['2020-01-03']/s.loc['2019-12-27']))
    with pytest.raises(ValueError,match='stale'):weekly_factor(pd.date_range('2026-11-06',periods=2,freq='W-FRI'))


def test_fx_depreciation_changes_mark_but_unsold_property_cannot_fund_payments():
    price=np.ones((1,4));g=price.copy();fx=np.array([[1.,.9,.8,.7]])
    re=dict(holding_mode='fixed',fixed_weight=.1,net_rental_yield=0.,sale_week=0,sale_delay_weeks=1)
    mark,cash=cash_and_mark(price,g,re,fx_paths=fx)
    np.testing.assert_allclose(mark,fx);assert not cash.any()


def test_agreement_price_stays_local_until_settlement_then_usd_cash():
    price=np.array([[1.,1.2,1.3,1.4]]);g=np.array([[1.,1.,1.,1.1]]);fx=np.array([[1.,.9,.8,.7]])
    re=dict(sale_week=2,sale_delay_weeks=1,liquidation_haircut=.1,net_rental_yield=0.)
    mark,cash=cash_and_mark(price,g,re,fx_paths=fx)
    np.testing.assert_allclose(mark,[[1.,1.2*.9*.9,1.2*.9*.8,1.2*.9*.8*1.1]])
    np.testing.assert_allclose(cash,[[0.,0.,1.2*.9*.8,1.2*.9*.8*1.1]])


def test_rent_converts_at_receipt_not_horizon_fx():
    price=np.ones((1,3));fx=np.array([[1.,.8,.6]]);g=np.array([[1.,1.1,1.21]])
    mark,cash=cash_and_mark(price,g,dict(net_rental_yield=.052,sale_week=0),fx_paths=fx)
    np.testing.assert_allclose(cash,[[.001,.0011+.0008,(.0011+.0008)*1.1+.0006]])
    np.testing.assert_allclose(mark,price*fx+cash)


def test_fx_paths_must_be_positive_and_aligned():
    with pytest.raises(ValueError,match='FX'):cash_and_mark(np.ones((1,3)),np.ones((1,3)),{},fx_paths=np.zeros((1,3)))


def test_fx_joint_covariance_is_a_factor_not_an_extra_holding(tmp_path):
    import hashlib,json
    from emfin_v2.assets import load_registry
    from emfin_v2.default_run import load_config
    from emfin_v2.registry_runtime import configure,fit,draw
    from emfin_v2.fx import COLUMN
    c=load_config();c['real_estate'].update(source='synthetic',annual_drift=0.,annual_vol=0.,forward_mode='sample',equity_correlation=0.)
    c=configure(c,load_registry());c.update(fx=dict(enabled=True,mean_policy='zero'),horizon_weeks=1,student_nu=None)
    s,_=load_reference();s=s.loc['2018-01-01':'2020-01-31'];m={}
    for j,a in enumerate(c['asset_registry']['assets']):
        if a['return_model']!='etf_total_return':continue
        f=tmp_path/(a['id']+'.csv');v=np.exp(np.log(s.to_numpy()/s.iloc[0])+np.random.default_rng(j).normal(0,.0001,len(s)))
        pd.DataFrame(dict(date=s.index,total_return_index=v)).to_csv(f,index=False)
        p=tmp_path/(a['id']+'.json');p.write_text(json.dumps(dict(asset_id=a['id'],ticker=a['ticker'],currency='USD',return_type='total_return',adjustment_method='synthetic TEST FIXTURE only',source_url='https://example.invalid/test',use_terms='test fixture',file=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest())));m[a['id']]=str(p)
    c['history_manifests']=m;frame,mu,cov=fit(c)
    assert frame.columns[-1]==COLUMN and mu[-1]==0.
    assert cov.shape==(6,6) and len(c['asset_names'])==6
    assert not cov[c['cash_index']].any()
    assert c['fx_evidence']['correlations']['us_equity']>.99
    paths=draw(c,(frame,mu,cov),20000,33)
    # With zero local property shocks, the property's USD return is pure FX.
    empirical=np.corrcoef(np.log(paths[0][:,0,0]),np.log(paths[0][:,0,-1]))[0,1]
    model=cov[0,-1]/np.sqrt(cov[0,0]*cov[-1,-1])
    assert empirical==pytest.approx(model,abs=.035)
    assert paths[0].shape==(20000,1,6)
    assert not paths.funding_paths[:,:,5].any()
