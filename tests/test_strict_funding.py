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


def test_strict_final_verdict_distinct_from_tail_budget():
    from emfin_v2.evaluation import evaluate
    c,d=fixture(property=True,amounts=(95.,));c.update(confidence=.95,funding_budget_fraction=.2,cml_budget=.06,loss_budget=.2,wasserstein_radius=0.,wasserstein_metric='max_path',minimum_weights=[0.,0.],fixed_weights={'1':.1});c['real_estate'].update(holding_mode='fixed',fixed_weight=.1)
    p=np.ones(400)/400
    original=evaluate(c,[d,d],[90.,10.],[p,p],[p,p]);assert original['funding_pass'] and original['overall_pass']
    c['funding_mode']='pay_all_99';strict=evaluate(c,[d,d],[90.,10.],[p,p],[p,p])
    assert strict['funding_pass'] and not strict['funding_rule_pass'] and not strict['overall_pass']
    assert strict['strict_funding']['reference_fraction']==0


def test_default_modes_unchanged_and_control_mapping():
    from emfin_v2.default_run import load_config,validate_config
    from emfin_v2.explorer import Controls
    c=load_config();assert c['funding_mode']=='tail_allowance' and c['radius_calibration_mode']=='manual'
    assert Controls().funding_mode=='tail_allowance'
    for key in ['funding_mode','radius_calibration_mode']:
        bad=dict(c);bad[key]='unknown'
        with pytest.raises(ValueError):validate_config(bad)
