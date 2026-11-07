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
    c,d=fixture();initial=np.array([90.,0.,0.,0.,0.,10.]);d[2][:]=[1,2];d[1][:]=[10,10];d[3][:]=[10,10]
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


def test_perfect_foresight_relaxation_dominates_every_executed_path():
    from emfin_v2.dynamic_policy import perfect_foresight_relaxation
    c,d=fixture(n=50);rng=np.random.default_rng(7);d[0][:,:,:4]=np.exp(np.cumsum(rng.normal(0,.03,(50,8,4)),axis=1));initial=np.array([20.,20.,20.,20.,10.,10.]);upper=perfect_foresight_relaxation(c,d,initial)
    for mode in ['cash_first','pro_rata','static_target','feedback','feedback_initial_only','feedback_static_target']:
        r=execute(c,d,initial,logits(initial,c),mode,fee=.001,delay=1)
        assert np.all(r['terminal_net']<=upper+1e-8)
    flatc,flatd=fixture();np.testing.assert_allclose(perfect_foresight_relaxation(flatc,flatd,initial),94.)


def test_initial_action_comparators_equal_feedback_at_timezero():
    c,d=fixture();initial=np.array([20.,20.,20.,20.,10.,10.]);th=np.array([-2.,-3.,-4.,-1.,1.,-.5,.5,.5])
    feedback=execute(c,d,initial,th,fee=.001,delay=1)
    for mode in ['feedback_initial_only','feedback_static_target']:
        r=execute(c,d,initial,th,mode,fee=.001,delay=1)
        np.testing.assert_allclose(feedback['net_wealth_paths'][:,:2],r['net_wealth_paths'][:,:2]);np.testing.assert_allclose(feedback['cash_paths'][:,:2],r['cash_paths'][:,:2])


def test_same_dynamic_judge_refuses_unpaid_despite_small_tail_budget():
    from emfin_v2.dynamic_judge import judge
    c,d=fixture(payment=48.);initial=np.array([0.,0.,0.,0.,90.,10.]);r=execute(c,d,initial,mode='cash_first',delay=0)
    c.update(confidence=.95,risk_tolerance=10.,funding_budget_fraction=.2,cml_budget=.06,loss_budget=.2,wasserstein_radius=0.)
    p=np.full(3,1/3);v=judge(c,[r]*4,[p]*4,[p]*4,d[3],d[2]);assert not v['strict_pass'] and not v['overall_pass'];assert v['largest_unpaid']==6


def test_annual_frequency_is_cashfirst_over_one_year_and_preserves_payments():
    c,d=fixture();a=np.array([20.,20.,20.,20.,10.,10.]);annual=execute(c,d,a,mode='static_frequency',rebalance_months=12);cashfirst=execute(c,d,a,mode='cash_first');np.testing.assert_allclose(annual['terminal_net'],cashfirst['terminal_net']);assert annual['funded'].all()


def test_future_random_liabilities_and_property_rent_are_not_silently_accepted():
    c,d=fixture();a=np.array([20.,20.,20.,20.,10.,10.]);d[1][1,1]+=1
    with pytest.raises(ValueError,match='fixed known'):execute(c,d,a,mode='cash_first')
    c,d=fixture();c['real_estate']['net_rental_yield']=.04
    with pytest.raises(ValueError,match='zero rent'):execute(c,d,a,mode='cash_first')


def test_frozen_frequency_snapshot_matches_declared_scope():
    from emfin_v2.dynamic_science import load
    s=load();assert s['available'] and s['selected_months']==12 and len(s['rows'])==16
    assert all(x['judge']['overall_pass'] and x['judge']['fully_paid_paths']==1600 for x in s['rows'])
    assert all(not x['judge']['wasserstein_certified'] for x in s['rows'])
    assert 'NONE' in s['dynamic_takeaway']
