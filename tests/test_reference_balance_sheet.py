"""Independent tiny balance sheet checks, not calls back into model metrics.

No historical fit or stochastic calibration. Exact paths and cash flows expose
netting, weighted atom boundaries, path probability identity and optimizer domains.
"""
import numpy as np
import pytest
from emfin_v2.toolbox import liabilities,entropy_pooling as ep,mpep,tsdr,risk_stats


def test_hand_balance_sheet_one_and_multi_period_agree():
    # Wealth paths 100->110 and 100->90. First payout=40, final payout=50.
    # Cash growth=1: terminal net is 20 or 0. No per-date shortfall.
    values=np.array([[100.,110.],[100.,90.]])
    payouts=np.array([[40.,50.],[40.,50.]])
    got=liabilities.multiperiod_gap_metrics(values,payouts,np.array([1,2]),np.ones((2,2)),.5)
    np.testing.assert_array_equal(got.terminal_net,[20.,0.])
    np.testing.assert_array_equal(got.shortfall_cvar,[0.,0.])
    one=liabilities.funding_gap_metrics(values[:,-1],90.,.5)
    assert one.shortfall_cvar==0
    # Increase final payout to 60: second path is short 10, first is not.
    payouts[:,1]=60
    got=liabilities.multiperiod_gap_metrics(values,payouts,np.array([1,2]),np.ones((2,2)),.5)
    np.testing.assert_array_equal(got.terminal_net,[10.,-10.])
    np.testing.assert_array_equal(got.shortfall_cvar,[0.,10.])


def test_prior_payout_cost_accrues_not_nominal_only():
    values=np.array([[100.,106.]])
    payouts=np.array([[50.,55.]])
    got=liabilities.multiperiod_gap_metrics(values,payouts,np.array([1,2]),np.array([[1.,1.1]]),.5)
    assert got.terminal_net[0]==pytest.approx(-4.)
    assert got.shortfall_cvar[1]==pytest.approx(4.)


def test_weighted_tail_boundary_and_mpep_identity():
    # Worst tail mass .25: .10 at loss 40, .15 of the atom at loss 20.
    losses=np.array([0.,10.,20.,40.]);p=np.array([.4,.3,.2,.1])
    expected=(.1*40+.15*20)/.25
    assert mpep.cml_of_paths(losses,p,.75)==pytest.approx(expected)
    paths=np.stack([np.full(4,100.),100.-losses],1)[:,:,None]
    result=mpep.mpep(paths,[],np.array([100.]),prior_probs=p)
    np.testing.assert_allclose(result.posterior_probs,p)
    np.testing.assert_array_equal(mpep.max_path_loss(paths[:,:,0],100.),losses)
    projected=ep.joint_entropy_pooling(4,[],prior_probs=p)
    np.testing.assert_allclose(projected.posterior_probs,p)


def test_tsdr_successor_emission_is_one_transition_and_joint_row():
    states=np.array([0,1,2,0]);history=np.array([[1.,10.],[2.,20.],[3.,30.],[4.,40.]])
    prob=np.array([[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]])
    paths,labels=tsdr.resample_invariant_paths(history,states,prob,3,3,0,1)
    np.testing.assert_array_equal(paths,np.tile(history[1:][None,:,:],(3,1,1)))
    np.testing.assert_array_equal(labels,np.tile([1,2,0],(3,1)))


def test_mpep_cml_optimizer_does_not_spend_same_cash_twice():
    paths=np.ones((10,2,1));payouts=np.tile([60.,60.],(10,1))
    with pytest.raises(RuntimeError):
        liabilities.optimization_multiperiod(paths,np.ones(1),100.,payouts,np.array([1,2]),np.array([60.,60.]),
          np.ones((10,2)),10.,.95,1.,0.,cml_budget=.1,stress_probabilities=[np.full(10,.1)])


def test_private_archive_adapter_preserves_prices_and_netting(tmp_path):
    from emfin_v2.default_run import load_archive,load_config
    c=load_config();c['real_estate']['enabled']=False;c['horizon_weeks']=2;c['cash_index']=1
    p=tmp_path/'case.npz'
    np.savez(p,market_paths=np.array([[[20.,50.],[22.,50.]],[[20.,50.],[18.,50.]]]),
       prices_vector=np.array([20.,50.]),liability_scenarios=np.array([[40.,50.],[40.,50.]]),
       payout_steps=np.array([1,2]),liability_base=np.array([40.,50.]),mm_growth_paths=np.ones((2,2)))
    paths,amounts,steps,bases,growth=load_archive(p,c)
    np.testing.assert_allclose(paths[:,:,0],[[1.,1.1],[1.,.9]])
    got=liabilities.multiperiod_gap_metrics(paths@np.array([100.,0.]),amounts,steps,growth,.5)
    np.testing.assert_allclose(got.terminal_net,[20.,0.])


def test_entropy_projection_matches_hand_binary_group_solution():
    paths=np.array([[[.8]],[[.8]],[[1.2]],[[1.2]]])
    got=mpep.mpep(paths,[mpep.MPView('mean',0,value=1.1)],np.ones(1)).posterior_probs
    # Mean 1.1 requires mass .75 at 1.2 and .25 at .8; symmetry splits each group.
    np.testing.assert_allclose(got,[.125,.125,.375,.375],atol=1e-7)


def test_feasible_two_asset_optimizer_matches_explicit_balance_sheet():
    # At final date, bad risky path yields 100-20*w; cumulative payouts=90.
    # Zero funding gap requires w<=.5; holding floor w>=.5 fixes w=.5.
    paths=np.array([[[1.,1.],[1.5,1.]],[[1.,1.],[.8,1.]]])
    amounts=np.tile([40.,50.],(2,1));steps=np.array([1,2]);growth=np.ones((2,2))
    alloc,_=liabilities.optimization_multiperiod(paths,np.ones(2),100.,amounts,steps,
        np.array([40.,50.]),growth,10.,.5,1.,0.,minimum_weights=np.array([.5,0.]))
    np.testing.assert_allclose(alloc,[50.,50.],atol=.001)
    values=paths@alloc
    got=liabilities.multiperiod_gap_metrics(values,amounts,steps,growth,.5)
    np.testing.assert_allclose(got.terminal_net,[35.,0.],atol=.001)
    np.testing.assert_allclose(got.shortfall_cvar,[0.,0.],atol=.001)
