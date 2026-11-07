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

from emfin_capstone.toolbox import risk_stats, solvers


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
    scenario_probs: np.ndarray | None = None,
    minimum_weights: np.ndarray | None = None,
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
    if scenario_probs is None:
        log_probs = np.full(n_scenarios, -np.log(n_scenarios))
        probs = np.full(n_scenarios, 1.0 / n_scenarios)
    else:
        probs = np.asarray(scenario_probs, dtype=float).ravel()[:n_optimization_scenarios]
        probs = probs / probs.sum()
        log_probs = np.log(probs)
    gross_return = solver_samples / prices_vector.ravel()

    weights = cp.Variable(n_assets)
    rel_wealth = gross_return @ weights  # W_s / wealth
    rel_liability = liability_due / wealth
    rel_net = rel_wealth - rel_liability
    rel_risk_tolerance = risk_tolerance / wealth

    # weighted CE: -zeta * log sum_s q_s exp(-net_s / zeta); for uniform q
    # this is exactly the unweighted form above
    # Center on the no-market-move surplus to avoid exp(-40) scaling.
    reference_net = 1.0 - liability_due / wealth
    expected_disutility = cp.sum(cp.multiply(probs, cp.exp(-(rel_net - reference_net) / rel_risk_tolerance)))

    # portfolio loss budget (as in the asset-only engine)
    rel_loss = 1 - rel_wealth
    t_loss = cp.Variable()
    cvar_loss = t_loss + cp.sum(cp.multiply(probs, cp.pos(rel_loss - t_loss))) / (1 - confidence_level)

    constraints = [cp.sum(weights) == 1, cvar_loss <= gamma_loss]
    if long_only:
        constraints.append(weights >= 0)

    if minimum_weights is not None:
        mins = np.asarray(minimum_weights,float).ravel()
        if mins.shape != (n_assets,) or not np.isfinite(mins).all() or (mins<0).any() or mins.sum()>1:
            raise ValueError("minimum weights must align, be nonnegative and sum to at most 1")
        constraints.append(weights >= mins)

    # funding-gap budget (only binds when there is a liability).  The gap is
    # one-sided — a surplus does not offset a shortfall in the tail — so the
    # loss variable is max(0, L - W), matching funding_gap_metrics.
    if liability_due > 0:
        gap = cp.pos(rel_liability - rel_wealth)
        t_gap = cp.Variable()
        cvar_gap = t_gap + cp.sum(cp.multiply(probs, cp.pos(gap - t_gap))) / (1 - confidence_level)
        constraints.append(cvar_gap <= gamma_shortfall * rel_liability)

    problem = cp.Problem(cp.Minimize(expected_disutility), constraints)
    used_solver = solvers.solve_capped(problem, name="liability-aware optimization")

    allocations = weights.value * wealth / prices_vector.ravel()
    diagnostics = {
        "status": problem.status,
        "solver": used_solver,
        "ce_in_solver": float(reference_net - rel_risk_tolerance * np.log(problem.value)) * wealth,
        "weights": weights.value.copy(),
    }
    return allocations, diagnostics


@dataclass(frozen=True)
class TailBudgetCalibration:
    """Result of calibrating the in-solver shortfall budget against OOS reality."""

    best_multiplier: float  # in-solver gamma_shortfall = multiplier * nominal budget
    best_allocation: np.ndarray
    history: tuple[tuple[float, float], ...]  # (multiplier, realized OOS gap CVaR $) probes
    target: float  # the OOS budget the calibration was aiming at ($)


def calibrate_shortfall_budget(
    solve_fn,
    evaluate_fn,
    target: float,
    lo: float = 0.1,
    hi: float = 1.0,
    tol: float = 0.05,
    max_iter: int = 6,
) -> TailBudgetCalibration:
    """Tighten the in-solver shortfall budget until it holds out-of-sample.

    SAA tail noise: a CVaR constraint that binds in-solver on N scenarios
    realizes looser on fresh draws (~2x at 10k scenarios in this engine).
    So the nominal budget cannot be trusted directly.  This binary-searches
    the multiplier applied to the nominal in-solver budget for the LARGEST
    multiplier whose realized out-of-sample funding-gap CVaR still respects
    the target - the loosest in-solver budget that is honest out-of-sample,
    i.e. maximum CE subject to the OOS constraint.

    ``solve_fn(mult)`` returns the allocation solved with
    ``gamma_shortfall = mult * nominal``; ``evaluate_fn(alloc)`` returns the
    realized OOS gap CVaR in dollars (paired seeds kill most of the noise).
    Monotonicity assumed: tighter in-solver budget -> lower realized CVaR.

    Edge cases are honest: if the nominal budget (mult = hi) already passes
    OOS, keep it; if even the tightest probe (mult = lo) fails, return lo
    and the history shows the failure.
    """
    cache: dict[float, tuple[np.ndarray, float]] = {}

    def probe(m: float) -> float:
        if m not in cache:
            alloc = np.asarray(solve_fn(m), dtype=float)
            cache[m] = (alloc, float(evaluate_fn(alloc)))
        return cache[m][1]

    history: list[tuple[float, float]] = []
    if probe(hi) <= target:
        history = [(m, cache[m][1]) for m in sorted(cache)]
        return TailBudgetCalibration(hi, cache[hi][0], tuple(history), target)
    probe(lo)
    best = lo
    l, h = lo, hi
    for _ in range(max_iter):
        mid = 0.5 * (l + h)
        if probe(mid) <= target:
            best, l = mid, mid
        else:
            h = mid
        if (h - l) <= tol:
            break
    history = [(m, cache[m][1]) for m in sorted(cache)]
    return TailBudgetCalibration(best, cache[best][0], tuple(history), target)


@dataclass(frozen=True)
class MultiPeriodMetrics:
    """Funding diagnostics per payout date plus terminal net wealth."""

    shortfall_probability: np.ndarray  # (n_payouts,) P(W < L_i) at each due date
    shortfall_cvar: np.ndarray  # (n_payouts,) CVaR of max(0, L_i - W) at each due date
    terminal_net: np.ndarray  # (n_scenarios,) terminal wealth net of provisioned payouts


def multiperiod_gap_metrics(
    value_paths: np.ndarray,
    liability_scenarios: np.ndarray,
    payout_steps: np.ndarray,
    mm_growth_paths: np.ndarray,
    confidence_level: float,
) -> MultiPeriodMetrics:
    """Evaluate funding along a scenario path, not just at the horizon.

    ``value_paths``: (n_scenarios, n_steps) portfolio value path;
    ``liability_scenarios``: (n_scenarios, n_payouts) amounts due;
    ``payout_steps``: step index (1-based into n_steps) of each payout;
    ``mm_growth_paths``: (n_scenarios, n_steps) gross growth of $1 in the
    money-market sleeve - payouts are provisioned at the money-market rate
    from their due date (LDI-style), so the terminal cost of payout i is
    L_i * G(T)/G(t_i).  Conservative and convex; documented in ENGINE_V2.
    """
    values = np.asarray(value_paths, dtype=float)
    liabilities = np.atleast_2d(np.asarray(liability_scenarios, dtype=float))
    growth = np.asarray(mm_growth_paths, dtype=float)
    steps = np.asarray(payout_steps, dtype=int).ravel()
    n_scenarios, n_steps = values.shape
    if liabilities.shape[0] != n_scenarios or growth.shape != values.shape:
        raise ValueError("value paths, liabilities and MM growth must align scenario-for-scenario")
    if np.any(steps < 1) or np.any(steps > n_steps):
        raise ValueError("payout steps must index into the path")

    probs, cvars = [], []
    terminal_net = values[:, -1].copy()
    for i, step in enumerate(steps):
        gap = np.maximum(0.0, liabilities[:, i] - values[:, step - 1])
        probs.append(float((gap > 0).mean()))
        cvars.append(risk_stats.empirical_cvar(gap, confidence_level))
        terminal_net -= liabilities[:, i] * growth[:, -1] / growth[:, step - 1]
    return MultiPeriodMetrics(
        shortfall_probability=np.array(probs),
        shortfall_cvar=np.array(cvars),
        terminal_net=terminal_net,
    )


def optimization_multiperiod(
    market_paths: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    liability_scenarios: np.ndarray,
    payout_steps: np.ndarray,
    liability_base: np.ndarray,
    mm_growth_paths: np.ndarray,
    risk_tolerance: float,
    confidence_level: float,
    gamma_loss: float,
    gamma_shortfall: float,
    long_only: bool = True,
    n_optimization_scenarios: int = 10_000,
    scenario_probs: np.ndarray | None = None,
    cml_budget: float | None = None,
    stress_probabilities: list[np.ndarray] | None = None,
) -> tuple[np.ndarray, dict]:
    """Multi-period, stochastic-liability allocation.

    Extends ``optimization_liability_aware`` two ways, as the module
    docstring promised:

    * Stochastic amounts: liability i due at step t_i is an
      (n_scenarios,) vector (e.g. capital calls that grow in equity
      drawdowns), not a fixed number.  CE is taken over net terminal wealth
      scenario-by-scenario.
    * Multi-period funding: each payout carries its own funding-gap
      constraint evaluated on the portfolio's value AT ITS DUE DATE
      (wealth path, not just horizon wealth) - a payout due in week 10
      cannot be funded by week-13 gains.

    Provisioning convention (keeps the problem convex): payout i is funded
    at its due date and the opportunity cost accrues at the money-market
    rate, so terminal net wealth is
    W_T - sum_i L_i,s * G_T,s / G_{t_i},s - linear in the weights given the
    scenarios.  Conservative when the portfolio out-earns the money market.

    Budgets: gap CVaR at date i <= gamma_shortfall * base_i, with base_i
    the plan (deterministic) amount.  Returns (share allocations, dict).
    """
    paths = np.asarray(market_paths, dtype=float)[:n_optimization_scenarios]
    n_scenarios, n_steps, n_assets = paths.shape
    liabilities = np.atleast_2d(np.asarray(liability_scenarios, dtype=float))[:n_scenarios]
    base = np.asarray(liability_base, dtype=float).ravel()
    steps = np.asarray(payout_steps, dtype=int).ravel()
    growth = np.asarray(mm_growth_paths, dtype=float)[:n_scenarios]
    if liabilities.shape != (n_scenarios, len(steps)) or base.shape != steps.shape:
        raise ValueError("liability scenarios, bases and payout steps must align")
    if growth.shape != (n_scenarios, n_steps):
        raise ValueError("MM growth must be (n_scenarios, n_steps)")
    if np.any(steps < 1) or np.any(steps > n_steps):
        raise ValueError("payout steps must index into the path")
    if scenario_probs is None:
        log_probs = np.full(n_scenarios, -np.log(n_scenarios))
        probs = np.full(n_scenarios, 1.0 / n_scenarios)
    else:
        probs = np.asarray(scenario_probs, dtype=float).ravel()[:n_scenarios]
        probs = probs / probs.sum()
        log_probs = np.log(probs)

    prices = prices_vector.ravel()
    weights = cp.Variable(n_assets)
    # relative portfolio value path at each date that matters (linear in w)
    value_terminal = (paths[:, -1, :] / prices) @ weights
    rel_risk_tolerance = risk_tolerance / wealth

    # terminal net of provisioned payouts (constant per scenario)
    provision = np.zeros(n_scenarios)
    for i, step in enumerate(steps):
        provision += liabilities[:, i] * growth[:, -1] / growth[:, step - 1]
    rel_net = value_terminal - provision / wealth

    reference_net = 1.0 - float(np.mean(provision)) / wealth
    expected_disutility = cp.sum(cp.multiply(probs, cp.exp(-(rel_net - reference_net) / rel_risk_tolerance)))

    rel_loss = 1 - value_terminal
    t_loss = cp.Variable()
    cvar_loss = t_loss + cp.sum(cp.multiply(probs, cp.pos(rel_loss - t_loss))) / (1 - confidence_level)
    constraints = [cp.sum(weights) == 1, cvar_loss <= gamma_loss]
    if long_only:
        constraints.append(weights >= 0)

    # one funding-gap epigraph per payout date, on the wealth path at that date
    for i, step in enumerate(steps):
        value_at_step = (paths[:, step - 1, :] / prices) @ weights
        gap = cp.pos(liabilities[:, i] / wealth - value_at_step)
        t_gap = cp.Variable()
        cvar_gap = t_gap + cp.sum(cp.multiply(probs, cp.pos(gap - t_gap))) / (1 - confidence_level)
        constraints.append(cvar_gap <= gamma_shortfall * base[i] / wealth)

    # CML: CVaR of maximum initial-value loss over each entire path.
    # Enforce for every supplied posterior and the nominal measure. Because
    # the common-threshold RU bound is valid under mixtures, feasibility
    # extends to their convex hull. This is a finite-measure ambiguity set,
    # NOT an unrestricted entropy/Wasserstein distributional ball.
    if cml_budget is not None:
        if cml_budget < 0 or not np.isfinite(cml_budget):
            raise ValueError("cml_budget must be finite and nonnegative")
        flat = (paths / prices).reshape(n_scenarios * n_steps, n_assets)
        value_paths = cp.reshape(flat @ weights, (n_scenarios, n_steps), order="C")
        measures = [probs]
        for p_stress in stress_probabilities or []:
            ps = np.asarray(p_stress, float).ravel()[:n_scenarios]
            if ps.shape != probs.shape or not np.isfinite(ps).all() or (ps < 0).any() or ps.sum() <= 0:
                raise ValueError("stress probabilities must align, be finite, nonnegative and sum positively")
            measures.append(ps / ps.sum())
        # Shared eta ensures a single RU upper bound for every mixture.
        # Independent per-measure etas would cover the listed measures only;
        # CVaR is not convex in the probabilities.
        eta_cml = cp.Variable(nonneg=True)
        excess_cml = cp.Variable(n_scenarios, nonneg=True)
        for step in range(n_steps):
            constraints.append(excess_cml >= 1. - value_paths[:,step] - eta_cml)
        for ps in measures:
            cml = eta_cml + ps @ excess_cml / (1-confidence_level)
            constraints.append(cml <= cml_budget)
    elif stress_probabilities:
        raise ValueError("stress_probabilities requires cml_budget")

    problem = cp.Problem(cp.Minimize(expected_disutility), constraints)
    used_solver = solvers.solve_capped(problem, name="multi-period optimization")

    allocations = weights.value * wealth / prices
    diagnostics = {
        "status": problem.status,
        "solver": used_solver,
        "ce_in_solver": float(reference_net - rel_risk_tolerance * np.log(problem.value)) * wealth,
        "weights": weights.value.copy(),
    }
    return allocations, diagnostics


def surplus_scaled_cara_tolerance(base_tolerance: float, surplus_ratio: float, reference_ratio: float,
                          floor: float = 1e-3) -> float:
    """Illustrative surplus-scaled CARA tolerance, not CRRA power utility.

    Scaling absolute tolerance with surplus mimics one local comparative
    static of CRRA; a one-step rescale is not utility equivalence or a
    fixed-point solution. The floor is numerical, not an economic model of
    negative surplus. Exact CRRA can be concave on positive surplus, but
    requires an explicit domain and an infeasibility policy.
    """
    if base_tolerance <= 0 or reference_ratio <= 0:
        raise ValueError("tolerance and reference ratio must be positive")
    ratio = max(surplus_ratio, floor) / reference_ratio
    return base_tolerance * ratio


# Backward-compatible helper name. New code uses the accurate name above.
crra_scaled_tolerance = surplus_scaled_cara_tolerance
