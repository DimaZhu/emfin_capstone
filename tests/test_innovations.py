import copy
import numpy as np
import pytest
from emfin_v2.innovations import DEFAULT_MIXTURE,divisor,log_gross_moment,validate


def test_mixture_covariance_and_exponential_moments_match_analytic_values():
    c=dict(scenario_model='gaussian_scale_mixture',innovation_mixture=copy.deepcopy(DEFAULT_MIXTURE),student_nu=None)
    rng=np.random.default_rng(312);n=160000;mu=np.array([.002,-.001]);cov=np.array([[.025,.008],[.008,.015]])
    z=(rng.normal(size=(n,3,2))@np.linalg.cholesky(cov).T)/divisor(c,rng,n,3)
    np.testing.assert_allclose(np.cov(z.reshape(-1,2),rowvar=False),cov,atol=.0002)
    x=np.cumsum(mu+z,axis=1)[:,-1]
    for b in [[1,0],[2,0],[0,1],[1,1],[-1,1]]:
        observed=np.exp(x@b);expected=np.exp(log_gross_moment(c,mu,cov,b,3));se=observed.std(ddof=1)/np.sqrt(n)
        assert abs(observed.mean()-expected)<5*se
    # Development default has positive excess kurtosis but all exponential moments.
    p=np.array(DEFAULT_MIXTURE['probabilities']);v=np.array(DEFAULT_MIXTURE['variance_scales']);assert 3*(p@(v*v)-1)>0


def test_legacy_log_t_nonzero_price_moments_are_infinite():
    c=dict(scenario_model='legacy_student_t',student_nu=8)
    assert np.isinf(log_gross_moment(c,[0.],[[.01]],[1.]))
    assert log_gross_moment(c,[.01],[[0.]],[1.])==pytest.approx(.01)


def test_invalid_mixture_cannot_silently_rescale_covariance():
    c=dict(scenario_model='gaussian_scale_mixture',innovation_mixture=dict(probabilities=[.5,.5],variance_scales=[1.,3.]))
    with pytest.raises(ValueError,match='weighted mean1'):validate(c)


def test_same_seed_and_joint_variance_state_are_reproducible():
    c=dict(scenario_model='gaussian_scale_mixture')
    a=divisor(c,np.random.default_rng(1),10,3);b=divisor(c,np.random.default_rng(1),10,3)
    np.testing.assert_array_equal(a,b);assert a.shape==(10,3,1)
