from emfin_v2.default_run import LEGACY_CONFIG
import numpy as np
import pytest
from emfin_v2.real_estate import unsmooth,history_statistics,cash_and_mark,ScenarioDraw,funding_paths,validate
from emfin_v2.default_run import load_config,setup,draw_paths,metrics


def test_unsmoothing_recovers_constructed_process():
    alpha=.5;true=np.array([.02,-.01,.03,-.02]);reported=[.01]
    for x in true:reported.append(alpha*reported[-1]+(1-alpha)*x)
    assert np.allclose(unsmooth(reported,alpha),true)
    assert np.array_equal(unsmooth(reported,0),reported)
    with pytest.raises(ValueError):unsmooth(reported,1)


def test_bootstrap_is_reproducible_and_short_history_labelled():
    x=tuple(np.linspace(-.02,.03,45))
    a=history_statistics(x,.4);b=history_statistics(x,.4)
    assert a==b and a['return_count']==44
    assert a['drift_range'][0]<a['drift_range'][2]
    assert 'not a joint' in a['method']


def test_unsold_property_is_not_spendable():
    p=np.full((2,4),1.2);g=np.ones((2,4))
    mark,cash=cash_and_mark(p,g,dict(net_rental_yield=.052,sale_week=0,liquidation_haircut=.1))
    assert np.allclose(cash[0],[.001,.002,.003,.004])
    assert np.allclose(mark,p+cash)


def test_sale_contract_then_settlement_no_double_sale_or_rent():
    p=np.array([[1.,1.1,1.3,1.4,1.5]]);g=np.ones_like(p)
    mark,cash=cash_and_mark(p,g,dict(net_rental_yield=.052,sale_week=2,sale_delay_weeks=2,liquidation_haircut=.1))
    assert np.allclose(cash,[.001,.002,.002,.992,.992])
    assert np.allclose(mark,[1.001,.992,.992,.992,.992])


def test_settlement_after_horizon_keeps_receivable_not_cash():
    p=np.ones((1,3));g=np.ones_like(p)
    mark,cash=cash_and_mark(p,g,dict(sale_week=1,sale_delay_weeks=5,liquidation_haircut=.1))
    assert np.allclose(mark,.9) and np.allclose(cash,0)


def test_generated_mark_vs_funding_and_dependence():
    c=load_config(LEGACY_CONFIG);c['student_nu']=None;c['horizon_weeks']=13
    c['real_estate'].update(enabled=True,source='synthetic',equity_correlation=.6,net_rental_yield=0.,sale_week=0)
    d=draw_paths(c,setup(c),5000,45)
    assert len(d)==5 and d[0].shape==funding_paths(d).shape
    assert np.allclose(funding_paths(d)[:,:,6],0)
    # Equity price log shocks retain common equity Gaussian factor.
    eq=np.diff(np.log(np.concatenate([np.ones((5000,1,3)),d[0][:,:,:3]/(1-np.array(c['liquidity_haircuts'][:3]))],axis=1)),axis=1).mean(2)
    re=np.diff(np.log(np.concatenate([np.ones((5000,1)),d[0][:,:,6]],axis=1)),axis=1)
    assert abs(np.corrcoef(eq.ravel(),re.ravel())[0,1]-.6)<.02


def test_funding_metrics_do_not_count_unsold_property():
    c=load_config(LEGACY_CONFIG);c['confidence']=.95
    paths=np.array([[[1.,1.]],[[1.,1.]]]);funding=paths.copy();funding[:,:,1]=0
    draw=ScenarioDraw((paths,np.array([[50.],[50.]]),np.array([1]),np.array([50.]),np.ones((2,1))),funding)
    gap,ce=metrics(c,draw,np.array([0.,100.]))
    assert gap[0]==50 and ce==pytest.approx(50)


@pytest.mark.parametrize('kw',[dict(sale_week=-1),dict(smoothing_alpha=.9),dict(net_rental_yield=-.1),dict(sale_delay_weeks=1.5)])
def test_invalid_re_assumptions(kw):
    with pytest.raises(ValueError):validate(kw)


def test_optimizer_does_not_spend_marked_property():
    from emfin_v2.toolbox.liabilities import optimization_multiperiod
    mark=np.tile(np.array([[[1.,1.],[1.,2.]]]),(4,1,1))
    cash=mark.copy();cash[:,:,1]=0.
    a,_=optimization_multiperiod(mark,np.ones(2),100.,np.full((4,1),90.),np.array([2]),np.array([90.]),np.ones((4,2)),100.,.5,1.,0.,funding_market_paths=cash)
    assert a[0]>=90.-1e-4 and a[1]<=10.+1e-4


def test_forward_re_view_pins_mean_in_nominal_and_stress():
    from emfin_v2.default_run import probabilities
    c=load_config(LEGACY_CONFIG);c['real_estate'].update(enabled=True,source='synthetic',annual_drift=.15,forward_log_drift=.02,forward_mode='view')
    draw=draw_paths(c,setup(c),400,52)
    q,qs=probabilities(c,draw[0],draw.re_price_logs)
    target=.02*c['horizon_weeks']/52
    assert q@draw.re_price_logs[:,-1]==pytest.approx(target,abs=1e-7)
    assert qs@draw.re_price_logs[:,-1]==pytest.approx(target,abs=1e-7)
    with pytest.raises(ValueError):probabilities(c,draw[0])


def test_sample_drift_requires_explicit_sample_mode():
    from emfin_v2.real_estate import calibration
    r=dict(source='synthetic',annual_drift=.15,annual_vol=.12)
    assert calibration(r)['annual_log_drift']==.04
    assert calibration(dict(r,forward_mode='sample'))['annual_log_drift']==.15
