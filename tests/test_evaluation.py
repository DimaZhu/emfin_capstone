import numpy as np
import pytest
from scipy.optimize import linprog
from emfin_v2.evaluation import common_tail,evaluate
from emfin_v2.real_estate import ScenarioDraw


def lp_reference(losses,probs,alpha,nonnegative):
    x=np.asarray(losses);p=np.asarray(probs);p=p/p.sum(1)[:,None];n=len(x)
    # Independent RU LP in eta, n excesses, and upper-envelope value.
    rows=[];bounds=[]
    for i in range(n):
        row=np.zeros(n+2);row[0]=-1;row[i+1]=-1;rows.append(row);bounds.append(-x[i])
    for measure in p:
        rows.append(np.r_[1,measure/(1-alpha),-1]);bounds.append(0.)
    objective=np.r_[np.zeros(n+1),1.]
    result=linprog(objective,A_ub=rows,b_ub=bounds,bounds=[(0,None) if nonnegative else (None,None)]+[(0,None)]*n+[(None,None)],method='highs')
    assert result.success
    return result.fun


def test_exact_hull_envelope_matches_independent_linear_program():
    rng=np.random.default_rng(732)
    for _ in range(20):
        losses=rng.choice(np.arange(-3,5),size=9).astype(float)
        probs=rng.random((3,9));probs[0,0]=0
        for nonnegative in [False,True]:
            assert common_tail(losses,probs,.73,nonnegative)==pytest.approx(lp_reference(losses,probs,.73,nonnegative),abs=1e-10)


def test_convex_hull_cannot_be_replaced_with_endpoint_cvar():
    # At alpha=.5, one measure has half-mass loss 2 and another is constant1.
    # Their endpoint CVaRs are2 and1; hull supremum2, common threshold2 here.
    # Random LP oracle above also covers crossings between atoms.
    x=np.array([0.,1.,2.]);p=np.array([[.8,0,.2],[0,1,0]])
    endpoints=max(common_tail(x,[q],.5) for q in p)
    assert endpoints==pytest.approx(1.)
    assert common_tail(x,p,.5)==pytest.approx(1.25)


def fixture():
    c=dict(wealth=100.,confidence=.5,cml_budget=.1,loss_budget=.15,funding_budget_fraction=.2,real_estate=dict(enabled=False),minimum_weights=[0.,0.],fixed_weights={},wasserstein_radius=0.)
    paths=np.tile(np.array([[[.8,1.],[1.,1.]]]),(4,1,1));steps=np.array([1,2]);base=np.array([10.,10.]);growth=np.ones((4,2));amounts=np.tile(base,(4,1));draw=ScenarioDraw((paths,amounts,steps,base,growth),paths)
    return c,[draw,draw],np.full(4,.25)


def test_cash_funded_portfolio_still_fails_path_risk_without_repair():
    c,draws,p=fixture();a=np.array([100.,0.]);before=a.copy()
    r=evaluate(c,draws,a,[p,p],[p,p])
    assert r['funding_pass'] and not r['overall_pass']
    assert r['breaches']==['Held-out path-loss tail']
    assert next(z for z in r['checks'] if z['kind']=='path_loss')['upper']==pytest.approx(.2)
    np.testing.assert_array_equal(a,before)


def test_safe_cash_passes_and_early_date_failure_is_not_hidden():
    c,draws,p=fixture();assert evaluate(c,draws,[0.,100.],[p,p],[p,p])['overall_pass']
    bad=[ScenarioDraw(tuple(x.copy() for x in draw),draw.funding_paths.copy()) for draw in draws]
    for draw in bad:draw.funding_paths[:,0,1]=0
    r=evaluate(c,bad,[0.,100.],[p,p],[p,p])
    assert not r['funding_pass'] and r['worst_funding_week']==1
    assert r['checks'][1]['passed']


def test_holdings_and_stress_are_independent_final_gates():
    c,draws,p=fixture();c['fixed_weights']={'0':.1}
    r=evaluate(c,draws,[0.,100.],[p,p],[p,p]);assert not r['overall_pass']
    assert 'Fixed holding 0' in r['breaches']
    c['fixed_weights']={};c['cml_budget']=.3
    for draw in draws:draw[0][0,1,0]=.01
    stress=np.array([1.,0,0,0])
    r=evaluate(c,draws,[100.,0.],[p,p],[stress,stress]);assert not r['overall_pass']
    assert next(z for z in r['checks'] if z['kind']=='terminal_loss')['measure_upper']['stressed']>.9


def test_fractional_tail_and_zero_loss_diagnostics_are_explicit():
    assert common_tail([0.,1.,3.],[[1,1,1]],.5)==pytest.approx(7/3)
    c,draws,p=fixture();r=evaluate(c,draws,[0.,100.],[p,p],[p,p])
    assert r['interval']['comparisons']==16
    assert 'zero-width' in r['interval']['scope']


def test_server_budget_and_single_flight_primitives():
    from emfin_v2.explorer import validate_server_work,COMPUTE_SLOT
    config=dict(train_scenarios=100,validation_scenarios=200,evaluation_scenarios=300,validation_seeds=2,evaluation_seeds=2,horizon_weeks=52)
    assert validate_server_work(config)==57200
    config['evaluation_scenarios']=10**9
    with pytest.raises(ValueError,match='work cap'):validate_server_work(config)
    assert COMPUTE_SLOT.acquire(blocking=False)
    try:assert not COMPUTE_SLOT.acquire(blocking=False)
    finally:COMPUTE_SLOT.release()
