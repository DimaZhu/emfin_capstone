"""Independent oracles prompted by Meucci Risk and Asset Allocation (2005).

No book source code or copied examples. Values below are our own fixtures.
Printed pp.262,275,277-279,293-294,336-340 motivate these properties.
"""
import numpy as np
import pytest
from emfin_v2.toolbox import risk_stats,shrinkage,scenario_market,mpep


def test_var_is_inverse_empirical_cdf_not_interpolated_atom():
    assert risk_stats.empirical_var([0.,10.],.95)==10.
    assert risk_stats.empirical_var([0.,10.],.5)==0.
    assert risk_stats.empirical_var([0.,10.],0.)==0.
    assert risk_stats.empirical_var([0.,0.,10.],2/3)==0.


@pytest.mark.parametrize('sample,level',[([], .95),([np.nan],.95),([np.inf],.95),([1,2],-1),([1,2],1),([1,2],np.nan)])
@pytest.mark.parametrize('function',[risk_stats.empirical_cvar,risk_stats.empirical_var])
def test_invalid_risk_statistic_inputs_are_not_numbers(sample,level,function):
    with pytest.raises(ValueError):function(sample,level)


def test_single_stochastic_sleeve_covariance_has_matrix_shape():
    x=np.array([[1.],[3.],[2.],[5.]])
    covariance,delta=shrinkage.ledoit_wolf_cov(x)
    assert covariance.shape==(1,1)
    assert covariance[0,0]==pytest.approx(np.var(x,ddof=1))
    assert delta==1.


def test_loss_expected_shortfall_coherence_with_atoms_and_signed_losses():
    a=np.array([-4.,0.,2.,7.]);b=np.array([3.,5.,-1.,1.]);c=.7
    es=lambda x:risk_stats.empirical_cvar(x,c)
    assert es(a+11)==pytest.approx(es(a)+11)
    assert es(3*a)==pytest.approx(3*es(a))
    assert es(a+b)<=es(a)+es(b)+1e-12
    assert es(a+np.array([0.,1.,0.,1.]))>=es(a)
    assert es(a)==pytest.approx(mpep.cml_of_paths(a,np.full(4,.25),c))


def test_cara_certainty_equivalent_money_units_and_jensen():
    outcomes=np.array([60.,90.,130.,170.]);tolerance=25.
    ce=scenario_market.empirical_certainty_equivalent(outcomes,tolerance)
    assert ce<=outcomes.mean() and ce>=outcomes.min()
    assert scenario_market.empirical_certainty_equivalent(outcomes+17,tolerance)==pytest.approx(ce+17)
    assert scenario_market.empirical_certainty_equivalent(1000*outcomes,1000*tolerance)==pytest.approx(1000*ce)
    expected=-tolerance*np.log(np.exp(-outcomes/tolerance).sum()/4)
    assert ce==pytest.approx(expected)


def test_mean_variance_approximation_is_not_exact_cara_for_skewed_market():
    # A market that never underperforms cash can still be underweighted by
    # fixed-coefficient MV. This is a benchmark limitation, not CARA identity.
    outcomes=np.array([100.,100.,100.,300.]);tolerance=20.
    exact=scenario_market.empirical_certainty_equivalent(outcomes,tolerance)
    approximation=outcomes.mean()-np.var(outcomes)/(2*tolerance)
    assert exact>100. and approximation<100.


def test_cara_matches_gaussian_price_closed_form_not_a_lognormal_identity():
    # Independent Gauss-Hermite integration of a normal *wealth* distribution.
    from numpy.polynomial.hermite import hermgauss
    from scipy.special import logsumexp
    nodes,weights=hermgauss(40);mean=100.;sd=17.;tolerance=23.
    outcomes=mean+np.sqrt(2)*sd*nodes
    ce=-tolerance*logsumexp(-outcomes/tolerance,b=weights/np.sqrt(np.pi))
    assert ce==pytest.approx(mean-sd**2/(2*tolerance),abs=1e-10)
