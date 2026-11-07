import numpy as np
import pytest
from emfin_v2.utilities import specification,native_ce,convex_objective


def test_local_absolute_aversion_match_and_hara_crra_surplus_identity():
    w=100.;T=10.;L=np.full(4,3.);x=np.array([70.,90.,100.,130.]);p=np.full(4,.25)
    s=specification('hara_payment_floor',w,T,L);assert s['gamma']==9.7
    assert s['gamma']/(w-3)==pytest.approx(1/T)
    h=native_ce('hara_payment_floor',x+3,x,p,w,T,L)
    power=native_ce('crra_gross',x,x-3,p,w,T,L,{'gamma':9.7})
    assert h['ce']==pytest.approx(power['ce'])
    assert x.min()<=h['ce']<=x.mean()
    scaled=native_ce('hara_payment_floor',1000*(x+3),1000*x,p,1000*w,1000*T,1000*L)
    assert scaled['ce']==pytest.approx(1000*h['ce'])


def test_power_domain_never_clips_and_initial_floor_cannot_be_invented():
    p=np.full(3,1/3);x=np.array([-1.,0.,100.]);r=native_ce('hara_payment_floor',x+3,x,p,100,10,np.full(3,3))
    assert not r['available'] and r['ce'] is None and r['domain_violations']==2
    with pytest.raises(ValueError):specification('hara_payment_floor',100,10,[101]*3)
    with pytest.raises(ValueError):specification('hara_payment_floor',100,10,[2,3,4])


def test_log_case_kink_slopes_and_ce_hand_oracle():
    p=np.array([.5,.5]);x=np.array([4.,16.]);r=native_ce('crra_gross',x,x,p,100,100,[3,3]);assert r['ce']==pytest.approx(8.)
    # Utility5x downside,1x upside; E[u(-10,20)]=-15, inverse=-3.
    r=native_ce('kinked_shortfall',[-7,23],[-10,20],p,100,10,[3,3]);assert r['ce']==pytest.approx(-3.)
    r=native_ce('cara',x,x,p,100,10,[3,3]);assert r['ce']<=x.mean()


@pytest.mark.parametrize('kind',['crra_gross','hara_payment_floor','kinked_shortfall'])
def test_convex_utility_solver_matches_independent_two_sleeve_grid(kind):
    import cvxpy as cp
    from emfin_v2.toolbox.solvers import solve_capped
    gross=np.array([[1.,.4],[1.,1.2],[1.,2.]]);p=np.array([.2,.5,.3]);weights=cp.Variable(2);g=gross@weights;net=g-.3
    objective,extra,spec=convex_objective(g,net,p,100,10,np.full(3,30.),kind)
    problem=cp.Problem(cp.Minimize(objective),[weights>=0,cp.sum(weights)==1,*extra]);solve_capped(problem)
    grid=np.linspace(0,1,10001);values=[]
    for risky in grid:
        outcome=100*(gross@np.array([1-risky,risky]));r=native_ce(kind,outcome,outcome-30,p,100,10,np.full(3,30.));values.append(r['ce'] if r['available'] else -np.inf)
    assert abs(float(weights.value[1])-grid[np.argmax(values)])<.003


def test_frozen_science_snapshot_labels_all_six_shared_cases():
    from emfin_v2.utility_science import load
    from emfin_v2.explorer import Controls
    s=load();assert s['available'] and len(s['studies'])==12
    assert Controls().objective_kind=='cara'
    for case in s['studies']:
        assert len(case['utilities'])==4
        h=next(x for x in case['utilities'] if x['kind']=='hara_payment_floor')
        if case['name']=='95M-final':
            assert all(x['selected'] is None for x in case['utilities'])
            assert h['raw']['native']['domain_violations']>0
