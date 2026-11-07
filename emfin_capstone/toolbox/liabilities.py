"""Liabilities in the objective — the module that makes the engine liability-aware.

The engine so far maximizes certainty equivalent of terminal wealth under a
CVaR budget.  The thesis of the capstone is that the family's *liabilities*
belong inside that problem: scheduled payouts (school fees, a property
purchase, follow-on capital calls) are what the wealth is for.

Model (documented for the paper):
  * A liability schedule: named amounts due at given week offsets.
    v1 treats amounts and dates as deterministic — the schedule is the
    client's plan.  Stochastic amounts (e.g. FX-linked payouts) slot into
    the same interface later as an (n_scenarios,) amount vector.
  * Horizon aggregation: payouts due within (0, tau] must be funded by tau.
    v1 aggregates them to a single outflow L at tau, conservative when the
    alternative is investing that cash at the horizon's risky mix.  A
    multi-period version is the natural extension, flagged in limitations.
  * Funding gap per scenario: g_s = max(0, L - W_s), with W the horizon
    liquidation value (net of liquidity costs — plug the convolved
    scenarios in upstream, see toolbox.liquidity).
  * Objective: maximize CARA certainty equivalent of *net* wealth W - L.
  * Constraint: CVaR of the funding gap <= gamma_shortfall * L, via the
    Rockafellar-Uryasev variational form — the same trick the existing
    scenario engine uses for portfolio loss, applied to the shortfall.

Rockafellar & Uryasev (2000/2002) for the CVaR form.
"""

from __future__ import annotations

from dataclasses import dataclass

import cvxpy as cp
import numpy as np

from emfin_capstone.toolbox import risk_stats


@dataclass(frozen=True)
class Liability:
    name: str
    amount: float  # dollars, due at `week`
    week: int


@dataclass(frozen=True)
class LiabilitySchedule:
    items: tuple[Liability, ...]

    def amount_due_by(self, horizon_weeks: int) -> float:
        """Total payouts falling due within (0, horizon]."""
        return sum(item.amount for item in self.items if 0 < item.week <= horizon_weeks)


@dataclass(frozen=True)
class LiabilityMetrics:
    liability_due: float
    shortfall_probability: float
    expected_shortfall: float  # E[max(0, L - W)]
    shortfall_cvar: float  # CVaR of the funding gap at the given level
    confidence_level: float


def funding_gap_metrics(
    wealth_samples: np.ndarray,
    liability_due: float,
    confidence_level: float = 0.95,
) -> LiabilityMetrics:
    """Shortfall statistics of horizon wealth against the amount due."""
    gaps = np.maximum(0.0, liability_due - np.asarray(wealth_samples, dtype=float).ravel())
    return LiabilityMetrics(
        liability_due=liability_due,
        shortfall_probability=float((gaps > 0).mean()),
        expected_shortfall=float(gaps.mean()),
        shortfall_cvar=risk_stats.empirical_cvar(gaps, confidence_level),
        confidence_level=confidence_level,
    )


def optimization_liability_aware(
    market_samples: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    liability_due: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma_loss: float,
    gamma_shortfall: float,
    long_only: bool = True,
    n_optimization_scenarios: int = 10_000,
) -> tuple[np.ndarray, dict]:
    """Maximize CARA CE of net wealth (W - L) under loss + shortfall budgets.

    Same SAA structure as ``scenario_market.optimization_with_cvar_constrain``:
    weights formulation, nondimensionalized, CLARABEL, first N rows in the
    solver.  ``gamma_loss`` budgets CVaR of the relative portfolio loss
    (as before); ``gamma_shortfall`` budgets CVaR of the funding gap as a
    fraction of the liability (1.0 = the gap itself may be fully in the
    tail; 0.05 = at most 5% of L expected in the worst 5% of outcomes).

    Returns (share allocations, diagnostics dict).  With
    ``liability_due = 0`` this reduces to the asset-only problem.
    """
    solver_samples = market_samples[:n_optimization_scenarios]
    n_scenarios, n_assets = solver_samples.shape
    gross_return = solver_samples / prices_vector.ravel()

    weights = cp.Variable(n_assets)
    rel_wealth = gross_return @ weights  # W_s / wealth
    rel_liability = liability_due / wealth
    rel_net = rel_wealth - rel_liability
    rel_risk_tolerance = risk_tolerance / wealth

    ce_rel = -rel_risk_tolerance * (
        cp.log_sum_exp(-rel_net / rel_risk_tolerance) - np.log(n_scenarios)
    )

    # portfolio loss budget (as in the asset-only engine)
    rel_loss = 1 - rel_wealth
    t_loss = cp.Variable()
    cvar_loss = t_loss + cp.sum(cp.pos(rel_loss - t_loss)) / ((1 - confidence_level) * n_scenarios)

    constraints = [cp.sum(weights) == 1, cvar_loss <= gamma_loss]
    if long_only:
        constraints.append(weights >= 0)

    # funding-gap budget (only binds when there is a liability)
    t_gap = cp.Variable()
    if liability_due > 0:
        gap = rel_liability - rel_wealth  # negative gap = surplus
        cvar_gap = t_gap + cp.sum(cp.pos(gap - t_gap)) / ((1 - confidence_level) * n_scenarios)
        constraints.append(cvar_gap <= gamma_shortfall * rel_liability)

    problem = cp.Problem(cp.Maximize(ce_rel), constraints)
    problem.solve(solver="CLARABEL")
    if weights.value is None:
        raise RuntimeError(f"liability-aware optimization failed: {problem.status}")

    allocations = weights.value * wealth / prices_vector.ravel()
    diagnostics = {
        "status": problem.status,
        "ce_in_solver": float(problem.value) * wealth,
        "weights": weights.value.copy(),
    }
    return allocations, diagnostics
