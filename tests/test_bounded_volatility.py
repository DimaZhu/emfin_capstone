import copy
import numpy as np
import pytest
from scipy.integrate import quad
from emfin_v2.bounded_volatility import settings,update,initial_state,transform,log_moment_bound
from emfin_v2.innovations import log_gross_moment,describe
from emfin_v2.default_run import load_config,validate_config,setup,draw_paths


def test_variance_update_hand_oracle_and_caps():
    h,lo,hi=update([2,2,0],[2,30,10],[2,2,0],decay=.7,floor=.5,cap=3)
    np.testing.assert_allclose(h,[2.6,6,0]);np.testing.assert_array_equal(hi,[False,True,False])
    h,lo,hi=update([0,2],[0,1],[2,2],decay=.7,floor=.5,cap=3)
    assert h[0]==1 and lo[0]


def test_large_shocks_state_bound_zero_cash_and_prefix_invariance():
    rng=np.random.default_rng(8);past=rng.normal(size=(100,2));past[:,1]=0.;base=np.array([1.,0.]);x=rng.normal(size=(5,52,2));x[:,0,0]=1e100;x[:,:,1]=0
    out,meta=transform(x,past,[0,0],base,return_diagnostics=True)
    short=transform(x[:,:13],past,[0,0],base)
    np.testing.assert_array_equal(out[:,:13],short);np.testing.assert_array_equal(out[:,:,1],0)
    assert meta['simulated_upper_hits'][0]>0
    assert np.array(meta['maximum'])[0]<=9 and np.array(meta['minimum'])[0]>=.05
    assert np.isfinite(out).all()


def test_future_history_cannot_change_past_state():
    rng=np.random.default_rng(5);x=rng.normal(size=(100,2));a=initial_state(x[:80],[0,0],[1,1]);x[80:]=1e10
    b=initial_state(x[:80],[0,0],[1,1]);np.testing.assert_array_equal(a[0],b[0]);assert a[1]==b[1]


def test_constant_unit_variance_cap_floor_one_matches_input():
    x=np.random.default_rng(3).normal(size=(7,12,2));past=np.random.default_rng(4).normal(size=(70,2))
    a=transform(x,past,[0,0],[1,2],dict(floor=1.,cap=1.));np.testing.assert_array_equal(a,x)


def test_bound_vs_exact_one_step_quadrature_and_joint_cauchy():
    p=np.array([.9,.1]);v=np.array([.75,3.25]);h=.7;exposure=-.4;mu=.01
    exact=quad(lambda z:sum(p*np.exp(exposure*(mu+np.sqrt(h*v)*z)))*np.exp(-z*z/2)/np.sqrt(2*np.pi),-12,12)[0]
    bound=log_moment_bound([mu],[.1],[exposure],1,cap=9)
    assert np.log(exact)<=bound
    R=np.array([[1,-.7],[-.7,1]]);D=np.diag(np.sqrt([9,2]));b=np.array([-1,2])
    assert b@D@R@D@b <= (abs(b)@np.sqrt([9,2]))**2
    assert log_moment_bound([0,0],[1,2],b,52)==pytest.approx(52*log_moment_bound([0,0],[1,2],b,1))


def test_invalid_bounds_and_iid_analytic_formula_reject():
    for params in [dict(cap=float('inf')),dict(floor=0),dict(cap=.5),dict(decay=1),dict(unknown=1)]:
        with pytest.raises(ValueError):settings(dict(bounded_volatility=params))
    with pytest.raises(ValueError,match='recursive conditional'):log_gross_moment(dict(scenario_model='bounded_ewma_mixture'),[0],[[1]],[1])
    assert 'finite' in describe(dict(scenario_model='bounded_ewma_mixture'))['price_exponential_moments']


def test_integrated_model_default_unchanged_and_shared_property_latent():
    c=load_config();assert c['scenario_model']=='gaussian_scale_mixture';f=setup(c);a=draw_paths(c,f,30,123)
    cc=copy.deepcopy(c);cc['scenario_model']='bounded_ewma_mixture';cc=validate_config(cc);b=draw_paths(cc,f,30,123)
    assert b.bounded_diagnostics is not None and np.isfinite(b[0]).all()
    np.testing.assert_array_equal(a.re_price_logs,b.re_price_logs)
    np.testing.assert_array_equal(a[4],b[4]);np.testing.assert_array_equal(b[4],1.)
    np.testing.assert_array_equal(b[0],draw_paths(cc,f,30,123)[0])
    np.testing.assert_array_equal(a[0],draw_paths(c,f,30,123)[0]);assert not np.array_equal(a[0],b[0])
    assert load_config()['scenario_model']=='gaussian_scale_mixture'


def test_conditional_covariance_scaling_independent_sample():
    rng=np.random.default_rng(16);base=np.array([.04,.09]);R=np.array([[1,.4],[.4,1]]);cov=np.diag(np.sqrt(base))@R@np.diag(np.sqrt(base));past=rng.multivariate_normal([0,0],cov,100)
    h,_=initial_state(past,[0,0],base);z=rng.multivariate_normal([0,0],cov,size=(80000,1));v=rng.choice([.75,3.25],(80000,1,1),p=[.9,.1]);out=transform(z*np.sqrt(v),past,[0,0],base)
    expected=np.diag(np.sqrt(h))@R@np.diag(np.sqrt(h));np.testing.assert_allclose(np.cov(out[:,0].T),expected,rtol=.04,atol=.0005)
