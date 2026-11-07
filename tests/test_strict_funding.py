import numpy as np
import pytest
from scipy.stats import binom
from emfin_v2.strict_funding import lower_bound,check
from emfin_v2.real_estate import ScenarioDraw


def fixture(n=400,property=False,amounts=(3.,)):
    h=len(amounts);paths=np.ones((n,h,2 if property else 1));funding=paths.copy()
    if property:funding[:,:,1]=0
    return dict(wealth=100.,cash_index=0,real_estate=dict(enabled=property),asset_layout=dict(property_indices=[1] if property else [])),ScenarioDraw((paths,np.tile(amounts,(n,1)),np.arange(1,h+1),np.array(amounts),np.ones((n,h))),funding)


def test_cp_all_success_boundary_and_binomial_inversion():
    assert lower_bound(400,400)==pytest.approx(.05**(1/400))
    assert lower_bound(298,298)<.99<=lower_bound(299,299)
    for s,n in [(1,10),(9,10),(396,400)]:assert binom.sf(s-1,n,lower_bound(s,n))==pytest.approx(.05)
    assert lower_bound(0,10)==0
    with pytest.raises(ValueError):lower_bound(11,10)


def test_small_n_and_archive_never_claim_full_model_screen():
    c,d=fixture(298);assert not check(c,[d],[100.])['passed']
    c,d=fixture();assert check(c,[d],[100.])['passed']
    c['scenario_archives']={'training':'x'};assert not check(c,[d],[100.])['passed']


def test_unsold_property95M_failure_and_weighted_no_binomial_claim():
    c,d=fixture(property=True,amounts=(95.,));r=check(c,[d],[90.,10.],[np.ones(400)],[np.ones(400)])
    assert r['reference_fraction']==0 and not r['passed'] and r['largest_unpaid']==5
    assert not r['wasserstein_certified'] and not r['economic_probability_guarantee']


def test_joint_date_event_not_per_date_and_weighted_stress_screen():
    c,d=fixture(amounts=(40.,40.));d[1][0,0]=110;d[1][1,1]=110
    r=check(c,[d],[100.]);assert r['fully_funded_paths']==398
    p=np.ones(400);p[:2]=100
    r=check(c,[d],[100.],stressed=[p]);assert r['weighted']['stressed']['minimum_batch']<.99 and not r['passed']
    with pytest.raises(ValueError):check(c,[d],[100.],stressed=[[-1]*400])
