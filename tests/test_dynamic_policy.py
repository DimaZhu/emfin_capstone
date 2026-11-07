import numpy as np
import pytest
from emfin_v2.real_estate import ScenarioDraw
from emfin_v2.dynamic_policy import execute,logits


def fixture(n=3,h=8,payment=3.):
    p=np.ones((n,h,6));steps=np.array([4,8]);a=np.tile([payment,payment],(n,1));draw=ScenarioDraw((p,a,steps,np.array([payment,payment]),np.ones((n,h))),p.copy());c=dict(wealth=100.,cash_index=4,real_estate=dict(enabled=True,sale_week=0,annual_rent_yield=0),asset_layout=dict(property_indices=[5]));return c,draw


def test_conservation_flat_prices_fees_with_settlement_receivables():
    c,d=fixture();initial=np.array([20.,20.,20.,20.,10.,10.]);th=logits(initial,c)
    for delay in [0,1,2]:
        r=execute(c,d,initial,th,fee=.01,delay=delay)
        np.testing.assert_allclose(r['terminal_net']+r['cost'],94.,atol=1e-8)
        assert np.all(r['cash_paths']>=-1e-6) and np.all(r['units_terminal']>=0)
        assert np.all(r['funded'])


def test_future_changes_do_not_change_past_controls_or_cash():
    c,d=fixture();initial=np.array([20.,20.,20.,20.,10.,10.]);th=np.r_[np.zeros(4),[1.,1.,1.,1.]]
    r=execute(c,d,initial,th);d[0][:,5:,0]*=2;s=execute(c,d,initial,th)
    np.testing.assert_allclose(r['net_wealth_paths'][:,:5],s['net_wealth_paths'][:,:5]);np.testing.assert_allclose(r['cash_paths'][:,:5],s['cash_paths'][:,:5])


def test_pending_sale_cannot_be_spent_before_settlement():
    c,d=fixture();initial=np.array([90.,0.,0.,0.,0.,10.]);d[2][:]=[1,2];d[1][:]=[10,10]
    r=execute(c,d,initial,np.r_[[-8]*4,[0]*4],delay=2)
    assert (r['shortfalls'][:,0]>0).all();assert not r['funded'].any()


def test_tiny_two_period_bellman_equals_full_nonanticipative_enumeration():
    from itertools import product
    # Grid actions and finite iid return law. This proves only this finite oracle.
    actions=[0.,.5,1.];returns=[.8,1.3];T=20.;payment=10.;fee=.01
    def step(wealth,share,ret):
        invested=(wealth-payment)*share/(1+fee)
        return (wealth-payment)*(1-share)+invested*ret*(1-fee)
    leaves={}
    for a in actions:
        states=[step(100,a,r) for r in returns]
        leaves[a]=[(b,c,np.mean([-np.exp(-step(states[i],action,r)/T) for i,action in enumerate([b,c]) for r in returns])) for b,c in product(actions,repeat=2)]
    exhaustive=max((value,a,b,c) for a,policies in leaves.items() for b,c,value in policies)
    bellman=[]
    for a in actions:
        continuation=[]
        for observed in returns:
            w=step(100,a,observed);continuation.append(max(np.mean([-np.exp(-step(w,b,r)/T) for r in returns]) for b in actions))
        bellman.append((np.mean(continuation),a))
    assert max(bellman)[0]==pytest.approx(exhaustive[0])
    # Cheating with the as-yet unseen second return gives a larger value.
    clairvoyant=max(np.mean([max(-np.exp(-step(step(100,a,observed),b,r)/T) for b in actions) for observed in returns for r in returns]) for a in actions)
    assert clairvoyant>exhaustive[0]


def test_pro_rata_means_cash_and_risky_both_used():
    c,d=fixture(h=8,payment=10.);initial=np.array([45.,0.,0.,0.,45.,10.])
    r=execute(c,d,initial,mode='pro_rata',fee=0,delay=0)
    # Each10withdrawal consumes halfcash/halfrisky on flat prices.
    assert r['units_terminal'][0,0]==pytest.approx(35.)
    assert r['cash_paths'][0,-1]==pytest.approx(35.)
