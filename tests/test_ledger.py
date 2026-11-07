import numpy as np
import pytest
from emfin_v2.real_estate import ScenarioDraw
from emfin_v2.ledger import cash_first


def test_cash_first_hand_oracle_is98_not_provisioning100():
    paths=np.array([[[1.,1.25],[1.,1.5]]]);draw=ScenarioDraw((paths,np.array([[30.,10.]]),np.array([1,2]),np.array([30.,10.]),np.ones((1,2))),paths)
    c=dict(cash_index=0,real_estate=dict(enabled=False));r=cash_first(c,draw,[20.,80.])
    assert r['units_paths'][0,0,1]==pytest.approx(72.)
    assert r['units_paths'][0,1,1]==pytest.approx(65+1/3)
    assert r['terminal_net'][0]==pytest.approx(98.)
    assert r['funded'][0]


def test_cash_only_interest_and_same_week_order_conserve_wealth():
    paths=np.array([[[1.1],[1.21]]]);draw=ScenarioDraw((paths,np.array([[20.,30.,10.]]),np.array([1,1,2]),np.array([20.,30.,10.]),np.array([[1.1,1.21]])),paths)
    r=cash_first(dict(cash_index=0,real_estate=dict(enabled=False)),draw,[100.])
    assert r['terminal_net'][0]==pytest.approx((110-20-30)*1.1-10)
    np.testing.assert_allclose(r['payment_shortfalls'],0)


def test_property_rent_and_settlement_never_double_counted_or_spent_early():
    # Property paid rent2 in week1, settles90 in week2, no liquid assets.
    paths=np.array([[[1.,102.],[1.,92.]]]);spend=np.array([[[1.,2.],[1.,92.]]]);draw=ScenarioDraw((paths,np.array([[5.,10.]]),np.array([1,2]),np.array([5.,10.]),np.ones((1,2))),spend)
    c=dict(cash_index=0,real_estate=dict(enabled=True),asset_layout=dict(property_indices=[1]))
    r=cash_first(c,draw,[3.,1.]);assert r['funded'][0];assert r['terminal_net'][0]==pytest.approx(80.)
    assert r['cash_paths'][0,0]==0


def test_unsold_property_does_not_fund_early_call_and_arrears_persist():
    paths=np.array([[[1.,100.],[1.,100.]]]);spend=np.array([[[1.,0.],[1.,0.]]]);draw=ScenarioDraw((paths,np.array([[5.,10.]]),np.array([1,2]),np.array([5.,10.]),np.ones((1,2))),spend)
    c=dict(cash_index=0,real_estate=dict(enabled=True),asset_layout=dict(property_indices=[1]))
    r=cash_first(c,draw,[3.,1.]);assert not r['funded'][0]
    np.testing.assert_allclose(r['payment_shortfalls'],[[2.,12.]])
    assert r['terminal_net'][0]==pytest.approx(88.)


def test_budget_pass_must_not_be_reported_as_paid_in_full():
    from emfin_v2.evaluation import evaluate
    from emfin_v2.ledger import summarize_execution
    paths=np.ones((20,1,2));funding=paths.copy();funding[:,:,1]=0
    draw=ScenarioDraw((paths,np.full((20,1),95.),np.array([1]),np.array([95.]),np.ones((20,1))),funding)
    c=dict(wealth=100.,cash_index=0,confidence=.95,cml_budget=.1,loss_budget=.1,funding_budget_fraction=.2,real_estate=dict(enabled=True,holding_mode='fixed',fixed_weight=.1),asset_layout=dict(property_indices=[1]),minimum_weights=[0.,0.],wasserstein_radius=0.)
    p=np.full(20,.05);verdict=evaluate(c,[draw,draw],[90.,10.],[p,p],[p,p]);audit=summarize_execution(c,[draw,draw],[90.,10.])
    assert verdict['funding_pass'] and verdict['overall_pass']
    assert audit['funded_fraction']==0 and audit['observed_unpaid_calls']
    assert audit['paths']==40 and audit['paths_with_unpaid_calls']==40
    assert audit['largest_observed_unpaid']==pytest.approx(5.)
    assert audit['payment_outcomes'][0]['paid_in_full_fraction']==0
    assert not audit['full_funding_guarantee'] and not audit['wasserstein_certified']


def test_zero_unpaid_observations_are_not_a_guarantee():
    from emfin_v2.ledger import summarize_execution
    paths=np.ones((2,1,1));draw=ScenarioDraw((paths,np.ones((2,1)),np.array([1]),np.ones(1),np.ones((2,1))),paths)
    r=summarize_execution(dict(cash_index=0,real_estate=dict(enabled=False)),[draw],[100.])
    assert r['outcome']=='No unpaid calls observed' and r['funded_fraction']==1
    assert not r['full_funding_guarantee'] and 'unseen tails' in r['interpretation']


def test_execution_audit_only_clips_disclosed_solver_weight_roundoff():
    from emfin_v2.ledger import summarize_execution
    paths=np.ones((2,1,2));draw=ScenarioDraw((paths,np.ones((2,1)),np.array([1]),np.ones(1),np.ones((2,1))),paths)
    c=dict(wealth=100.,cash_index=0,real_estate=dict(enabled=False))
    r=summarize_execution(c,[draw],[100.,-1e-6]);assert r['numerical_negative_holdings_clipped']==1e-6
    with pytest.raises(ValueError,match='nonnegative'):summarize_execution(c,[draw],[101.,-1.])
