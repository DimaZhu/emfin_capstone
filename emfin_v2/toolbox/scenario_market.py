"""Scenario-based (simulation) counterpart of ``normal_market``.

Here the market distribution is represented only by a matrix of sampled
horizon prices — the optimization and the satisfaction/risk evaluators work
for any distribution that can produce such samples (Sample Average
Approximation).  Under normal invariants the samples are exactly lognormal,
and the ``normal_market`` closed forms serve as validation anchors.

"Scenario" is used in the stochastic-programming sense: any row of a
discrete representation of the market distribution, with a probability
attached — whether 200,000 Monte Carlo draws, bootstrapped historical
weeks, quadrature nodes, or a handful of handcrafted stress cases.  The
stress-testing usage (few, named, deliberately extreme states of the
world) is the small-N special case, not a different concept: this module
deliberately does not know where its scenarios came from.

References:
    Rockafellar & Uryasev (2000), "Optimization of Conditional Value-at-Risk",
        Journal of Risk 2(3), 21-41 — the CVaR minimization formula, under
        continuous loss distributions.
    Rockafellar & Uryasev (2002), "Conditional Value-at-Risk for General Loss
        Distributions", Journal of Banking & Finance 26(7), 1443-1471,
        doi:10.1016/S0378-4266(02)00271-6 — extends it to discrete/empirical
        distributions (our case): fractional atom-splitting, argmin is an
        interval.
"""

import cvxpy as cp
import numpy as np
from scipy import special


def sample_market_scenarios(
    prices_vector: np.ndarray,
    projected_mean_vector: np.ndarray,
    projected_cov_matrix: np.ndarray,
    n_scenarios: int,
    seed: int,
) -> np.ndarray:
    """Sample horizon prices P = p * exp(X), X ~ N(mu, Sigma) — lognormal market.

    Correlation is induced in log space via the Cholesky factor of Sigma;
    an elementwise lognormal sampler cannot do this (no covariance argument).
    Returns an (n_scenarios, n_assets) array of prices.
    """
    rng = np.random.default_rng(seed)
    cholesky_factor = np.linalg.cholesky(projected_cov_matrix)  # Sigma = L L'
    invariant_scenarios = (
        projected_mean_vector.ravel()
        + rng.standard_normal((n_scenarios, len(prices_vector))) @ cholesky_factor.transpose()
    )
    return prices_vector.ravel() * np.exp(invariant_scenarios)


def empirical_certainty_equivalent(wealth_samples: np.ndarray, risk_tolerance: float) -> float:
    """CE of the empirical wealth distribution under CARA utility (dollars in, dollars out)."""
    return -risk_tolerance * (
        special.logsumexp(-wealth_samples / risk_tolerance) - np.log(len(wealth_samples))
    )


def empirical_cvar(loss_samples: np.ndarray, confidence_level: float) -> float:
    """Tail average of the worst (1-c) fraction of losses (sort-based evaluation form).

    Exact only when (1-c) * len(loss_samples) is an integer; otherwise the
    straddling atom needs fractional weighting (Rockafellar & Uryasev 2002)
    and this raises rather than return a silently-wrong number.
    """
    tail_count = (1 - confidence_level) * len(loss_samples)
    if abs(tail_count - round(tail_count)) > 1e-9:
        raise ValueError(f"(1-c)*N = {tail_count} is not an integer; tail average is not exact")
    return np.sort(loss_samples.ravel())[-round(tail_count):].mean()


def optimization_with_cvar_constrain(
    market_samples: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma: float = 0.041,
    n_optimization_scenarios: int = 10_000,
) -> np.ndarray:
    """Maximize the empirical CARA CE subject to an empirical CVaR budget (SAA).

    Only the first ``n_optimization_scenarios`` rows enter the solver:
    CLARABEL certifies "optimal" cleanly at ~10k scenarios and strains above;
    the SAA optimum error is O(1/sqrt(N)) anyway.  Evaluate the returned
    allocation on the full sample set and a fresh seed (``evaluate_allocation``).
    """
    solver_samples = market_samples[:n_optimization_scenarios]
    n_scenarios, n_assets = solver_samples.shape

    # weights formulation: weight_i = price_i * alpha_i / wealth, unit budget
    gross_return_scenarios = solver_samples / prices_vector.ravel()
    relative_risk_tolerance = risk_tolerance / wealth

    weights = cp.Variable((n_assets, 1))
    relative_wealth_goal = gross_return_scenarios @ weights  # psi_s / w, symbolic
    relative_loss = 1 - relative_wealth_goal  # L_s / w, loss convention

    ce_rel = -relative_risk_tolerance * (
        cp.log_sum_exp(-relative_wealth_goal / relative_risk_tolerance) - np.log(n_scenarios)
    )

    # CVaR via Rockafellar-Uryasev: min over t of  t + E[(L - t)+] / (1 - c),
    # written symbol-for-symbol with cp.pos; the free variable performs the min
    # implicitly (a feasibility witness — see module docstring references)
    var_proxy = cp.Variable()
    cvar_rel = var_proxy + cp.sum(cp.pos(relative_loss - var_proxy)) / (
        (1 - confidence_level) * n_scenarios
    )

    constraints = [
        cp.sum(weights) == 1,
        cvar_rel <= gamma,
    ]
    problem = cp.Problem(cp.Maximize(ce_rel), constraints)
    problem.solve(solver="CLARABEL")

    alpha_scenario = weights.value * wealth / prices_vector.reshape((-1, 1))  # back to shares
    print(f"status: {problem.status}")
    print(f"Allocations: {alpha_scenario.ravel().round()}")
    print(f"CE (in-solver, optimistically biased): {problem.value * wealth:,.0f}")
    print(f"VaR proxy t*: {var_proxy.value * wealth:,.0f}")  # argmin is an interval on discrete data
    return alpha_scenario


def evaluate_allocation(
    allocations: np.ndarray,
    market_samples: np.ndarray,
    prices_vector: np.ndarray,
    projected_mean_vector: np.ndarray,
    projected_cov_matrix: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma: float,
    out_of_sample_seed: int,
) -> None:
    """Empirical CE/CVaR of a fixed allocation: full sample set + a fresh seed.

    The yardsticks are computed outside the solver — a solver status is a
    claim; these numbers are the verdict.  The fresh-seed line is the honest
    risk report: the in-sample one is the quantity the optimizer was allowed
    to flatter.
    """
    wealth_samples = market_samples @ allocations
    print(
        f"full set     : CE {empirical_certainty_equivalent(wealth_samples, risk_tolerance):,.0f}   "
        f"CVaR {empirical_cvar(wealth - wealth_samples, confidence_level):,.0f}"
    )

    out_of_sample_samples = sample_market_scenarios(
        prices_vector=prices_vector,
        projected_mean_vector=projected_mean_vector,
        projected_cov_matrix=projected_cov_matrix,
        n_scenarios=len(market_samples),
        seed=out_of_sample_seed,
    )
    out_of_sample_wealth = out_of_sample_samples @ allocations
    print(
        f"out-of-sample: CE {empirical_certainty_equivalent(out_of_sample_wealth, risk_tolerance):,.0f}   "
        f"CVaR {empirical_cvar(wealth - out_of_sample_wealth, confidence_level):,.0f}   "
        f"(budget {gamma * wealth:,.0f})"
    )
