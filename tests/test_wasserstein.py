"""Independent transport LP and optimizer reference checks for W1 risk bounds."""
import cvxpy as cp
import numpy as np
import pytest
from scipy.optimize import linprog
from emfin_v2.toolbox import wasserstein,liabilities


def test_dual_l1_metric_uses_linf_slope_and_liability_coordinate():
    assert wasserstein.penalty([.5,.5],.01,.95)==pytest.approx(.1)
    assert wasserstein.penalty([.1,.9],.01,.95,.95)==pytest.approx(.19)
    assert wasserstein.penalty([.1,.9],0.,.95)==0.
    x=cp.Variable(2);p=cp.Problem(cp.Minimize(wasserstein.cvx_penalty(x,.01,.95)),[x==[.1,.9]])
    p.solve(solver='CLARABEL');assert p.value==pytest.approx(.18,abs=1e-7)


def test_fixed_threshold_bound_matches_adversarial_transport_limit():
    # One empirical atom at zero. Move epsilon/M mass to -M.
    # Hinge max(0,-w*z-eta) has Lipschitz w; mass-at-infinity approaches eps*w.
    eps=.01;w=.5;eta=.1
    for far in (100.,1000.,10000.):
        support=np.array([0.,-far]);loss=np.maximum(0,-w*support-eta)
        lp=linprog(-loss,A_ub=[np.abs(support)],b_ub=[eps],A_eq=[[1.,1.]],b_eq=[1.],bounds=(0,None),method='highs')
        assert lp.success
        exact_upper=eps*w
        assert -lp.fun<=exact_upper+1e-10
        assert exact_upper+lp.fun==pytest.approx(eps*eta/far)


def test_dro_zero_radius_reduces_to_same_problem_and_positive_radius_tightens():
    paths=np.array([[[1.,1.],[1.5,1.]],[[1.,1.],[.8,1.]]])
    args=(paths,np.ones(2),100.,np.tile([40.,50.],(2,1)),np.array([1,2]),np.array([40.,50.]),np.ones((2,2)),100.,.5,1.,.001)
    a,_=liabilities.optimization_multiperiod(*args)
    zero,_=liabilities.optimization_multiperiod(*args,wasserstein_radius=0.)
    dro,_=liabilities.optimization_multiperiod(*args,wasserstein_radius=.0001)
    np.testing.assert_allclose(a,zero,atol=1e-6)
    assert dro[0]<a[0]
    m=liabilities.multiperiod_gap_metrics(paths@dro,args[3],args[4],args[6],.5)
    buffer=100*wasserstein.penalty(dro/100,.0001,.5,.01)
    assert np.all(m.shortfall_cvar+buffer<=args[5]*.001+1e-4)


@pytest.mark.parametrize('radius,scale',[(-1,.01),(float('nan'),.01),(.01,-1)])
def test_invalid_dro_inputs(radius,scale):
    with pytest.raises(ValueError):wasserstein.penalty([.5,.5],radius,.95,scale)
