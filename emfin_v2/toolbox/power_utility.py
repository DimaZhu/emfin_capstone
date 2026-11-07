"""Exact finite-scenario CRRA utility of strictly positive surplus.

This is not a floor/clipped utility: surplus >= an explicit epsilon is a
constraint on every supplied scenario. It can be infeasible. It does not prove
positive surplus on an unbounded population distribution. A no-shortfall domain
is a different economic model from CARA with an allowed funding-gap budget.
"""
import numpy as np
import cvxpy as cp
from emfin_v2.toolbox import solvers


def allocate_positive_surplus(market_samples,prices,wealth,liability_due,
                              relative_risk_aversion=2.,scenario_probs=None,
                              surplus_floor_ratio=1e-5,confidence=.95,loss_budget=.15):
    m=np.asarray(market_samples,float);prices=np.asarray(prices,float).ravel()
    gamma=float(relative_risk_aversion)
    if m.ndim!=2 or m.shape[1]!=len(prices) or not np.isfinite(m).all() or not np.isfinite(prices).all() or (prices<=0).any():
        raise ValueError('finite scenario matrix and positive aligned prices required')
    if not np.isfinite(gamma) or gamma<=0 or wealth<=0 or liability_due<0 or not 0<surplus_floor_ratio<1 or not 0<=confidence<1:
        raise ValueError('positive gamma/wealth/domain floor and valid liability/confidence required')
    p=np.full(len(m),1/len(m)) if scenario_probs is None else np.asarray(scenario_probs,float)
    if p.shape!=(len(m),) or not np.isfinite(p).all() or (p<0).any() or p.sum()<=0:
        raise ValueError('finite aligned nonnegative probabilities required')
    p=p/p.sum();gross=m/prices
    w=cp.Variable(len(prices));relative_wealth=gross@w
    surplus=relative_wealth-liability_due/wealth
    reference=max(1-liability_due/wealth,surplus_floor_ratio)
    normalized=surplus/reference
    if abs(gamma-1)<1e-10:utility=p@cp.log(normalized)
    else:utility=(p@cp.power(normalized,1-gamma))/(1-gamma)
    eta=cp.Variable()
    cvar=eta+p@cp.pos(1-relative_wealth-eta)/(1-confidence)
    constraints=[cp.sum(w)==1,w>=0,surplus>=surplus_floor_ratio,cvar<=loss_budget]
    problem=cp.Problem(cp.Maximize(utility),constraints)
    solver=solvers.solve_capped(problem,'positive-surplus CRRA')
    achieved=gross@w.value-liability_due/wealth
    if np.min(achieved)<surplus_floor_ratio-1e-7:
        raise RuntimeError('strict surplus domain not met')
    if abs(gamma-1)<1e-10:ce=np.exp(p@np.log(achieved))
    else:ce=(p@(achieved**(1-gamma)))**(1/(1-gamma))
    return w.value*wealth/prices,dict(status=problem.status,solver=solver,surplus_ce=float(ce*wealth),
        minimum_scenario_surplus=float(achieved.min()*wealth),relative_risk_aversion=gamma,
        domain='strictly positive in every supplied scenario; no population guarantee')
