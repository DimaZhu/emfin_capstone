import numpy as np
import pytest
from scipy.special import logsumexp
from scipy.optimize import minimize_scalar
from emfin_v2.toolbox.liabilities import optimization_multiperiod


def test_log_cara_objective_matches_direct_cara_and_reports_ce_with_zero_probability_support():
    # Independent one-dimensional true CARA optimum, including a zero-mass path.
    terminal=np.array([[1.,1.18],[1.,.9],[1.,1.04],[1.,.1]])
    paths=terminal[:,None,:];p=np.array([.4,.3,.3,0.]);wealth=100.;tau=10.
    def ce(w):return -tau*logsumexp(-wealth*(terminal@np.array([1-w,w]))/tau,b=p)
    reference=minimize_scalar(lambda w:-ce(w),bounds=(0.,1.),method='bounded')
    a,d=optimization_multiperiod(paths,np.ones(2),wealth,np.zeros((4,1)),np.array([1]),np.array([0.]),np.ones((4,1)),tau,.95,1.,.2,cml_budget=1.,scenario_probs=p)
    assert a[1]/wealth==pytest.approx(reference.x,abs=2e-4)
    assert d['ce_in_solver']==pytest.approx(ce(a[1]/wealth),abs=.0002)


def test_presolve_certificate_uses_whole_holdings_domain_not_current_solution():
    paths=np.tile(np.array([[[1.,1.1,1.],[1.,1.2,1.]]]),(20,1,1));funding=paths.copy();funding[:,:,2]=0
    a,d=optimization_multiperiod(paths,np.ones(3),100.,np.ones((20,1)),np.array([2]),np.array([1.]),np.ones((20,2)),10.,.95,1.,.2,cml_budget=1.,fixed_weights={2:.1},funding_market_paths=funding,wasserstein_radius=.00002)
    cert=d['funding_presolve_certificates'];assert len(cert)==1
    assert cert[0]['worst_holdings_w1']==pytest.approx(.00036)
    assert cert[0]['upper_bound']<=cert[0]['budget']
    assert a[2]==pytest.approx(10.,abs=.0001)
    # Tighten only the W1 gap budget. Cannot certify a constraint away then.
    _,d=optimization_multiperiod(paths,np.ones(3),100.,np.ones((20,1))*95,np.array([2]),np.array([95.]),np.ones((20,2)),10.,.95,1.,.0005,cml_budget=1.,fixed_weights={2:.1},funding_market_paths=funding,wasserstein_radius=.00002)
    assert not d['funding_presolve_certificates']


def test_new_universe_clarabel_regression_and_original_guardrails():
    from emfin_v2.default_run import load_config,setup,draw_paths,probabilities,solve,metrics,dro_buffer
    from emfin_v2.toolbox.mpep import cml_of_paths
    c=load_config();c.update(scenario_model='legacy_student_t',student_nu=8.,wasserstein_metric='legacy_l1');d=draw_paths(c,setup(c),100,c['seed']);q,qs=probabilities(c,d[0],d.re_price_logs)
    a,status=solve(c,d,q,qs,1.)
    assert status['kind']=='optimized' and status['solver']=='CLARABEL'
    assert status['status']=='optimal'
    assert a[-1]==pytest.approx(c['wealth']*.1,abs=1.)
    assert len(status['funding_presolve_certificates'])==12
    for prob in [q,qs]:
        gaps,_=metrics(c,d,a,prob)
        assert np.all(gaps+dro_buffer(c,a)<=d[3]*c['funding_budget_fraction']+1.)
        losses=np.maximum(0,1-d[0]@a/c['wealth']).max(1)
        assert cml_of_paths(losses,prob,c['confidence'])+dro_buffer(c,a,False)/c['wealth']<=c['cml_budget']+1e-6


def test_finite_moment_maxpath_default_solver_passes_original_guards():
    from emfin_v2.default_run import load_config,setup,draw_paths,probabilities,solve,metrics,dro_buffer
    from emfin_v2.toolbox.mpep import cml_of_paths
    c=load_config();d=draw_paths(c,setup(c),100,c['seed']);q,qs=probabilities(c,d[0],d.re_price_logs)
    a,status=solve(c,d,q,qs,1.)
    assert status['kind']=='optimized' and status['status']=='optimal'
    assert a[-1]==pytest.approx(c['wealth']*.1,abs=1.)
    for p in [q,qs]:
        assert np.all(metrics(c,d,a,p)[0]+dro_buffer(c,a)<=d[3]*c['funding_budget_fraction']+1.)
        loss=np.maximum(0,1-d[0]@a/c['wealth']).max(1)
        assert cml_of_paths(loss,p,c['confidence'])+dro_buffer(c,a,False)/c['wealth']<=c['cml_budget']+1e-6
