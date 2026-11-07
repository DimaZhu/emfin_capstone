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
