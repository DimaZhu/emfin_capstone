"""Scaffolding for the normal (Gaussian) market-distribution assumption.

Every routine here presumes market prices at the horizon are jointly normal:
the closed-form mean-variance allocation (6.39) and the VaR/CVaR coefficients
(``erfinv``-based normal quantiles) are only valid under that assumption. This
is a deliberate placeholder — once the projection step carries a non-normal
scenario distribution, these are replaced by their simulation-based analogues.
"""

from dataclasses import dataclass

import cvxpy as cp
import numpy as np
from scipy import special


@dataclass
class AnalyticalSolution:
    allocations: np.ndarray
    certainty_equivalent: np.ndarray
    value_at_risk: np.ndarray


def analytical_solution(
    market_mean_vector: np.ndarray,
    market_cov_matrix: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
) -> AnalyticalSolution:
    inv_market_cov_matrix = np.linalg.inv(market_cov_matrix)
    alpha = (
        risk_tolerance * inv_market_cov_matrix @ market_mean_vector
        + (wealth - risk_tolerance * (prices_vector.transpose() @ inv_market_cov_matrix @ market_mean_vector))
        / (prices_vector.transpose() @ inv_market_cov_matrix @ prices_vector)
        * inv_market_cov_matrix @ prices_vector
    )
    print(f"Allocations: {alpha}")

    certainty_equivalent = (
        market_mean_vector.transpose() @ alpha
        - 1 / (2 * risk_tolerance) * alpha.transpose() @ market_cov_matrix @ alpha
    )
    print(f"Certain equivalent: {certainty_equivalent}")

    value_at_risk = (
        (prices_vector - market_mean_vector).transpose() @ alpha
        + np.sqrt(2 * alpha.transpose() @ market_cov_matrix @ alpha)
        * special.erfinv(2 * confidence_level - 1)
    )
    print(f"VaR: {value_at_risk}")

    return AnalyticalSolution(
        allocations=alpha,
        certainty_equivalent=certainty_equivalent,
        value_at_risk=value_at_risk,
    )


def optimization_with_var_constrain(
    market_mean_vector: np.ndarray,
    market_cov_matrix: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma: float = 0.041,
) -> np.ndarray:
    var_coeff = np.sqrt(2) * special.erfinv(2 * confidence_level - 1)

    # weights formulation: weight_i = price_i * alpha_i / wealth, unit budget
    gross_return_vector = market_mean_vector / prices_vector
    weight_cov_matrix = market_cov_matrix / (prices_vector @ prices_vector.transpose())
    cholesky_factor = np.linalg.cholesky(weight_cov_matrix)
    relative_risk_tolerance = risk_tolerance / wealth

    weights = cp.Variable((3, 1))
    relative_sigma = cp.norm(cholesky_factor.transpose() @ weights, 2)
    objective = cp.Maximize(
        gross_return_vector.transpose() @ weights
        - cp.square(relative_sigma) / (2 * relative_risk_tolerance)
    )
    var_rel = (1 - gross_return_vector.transpose() @ weights) + var_coeff * relative_sigma
    constraints = [
        cp.sum(weights) == 1,
        var_rel <= gamma,
        # weights >= 0,
    ]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver="CLARABEL")

    alpha_numerical = weights.value * wealth / prices_vector  # back to shares
    print(f"Allocations: {alpha_numerical}")
    print(f"CE: {prob.value * wealth:,.0f}")  # objective is CE/wealth
    print(f"budget shadow price (CE gained per extra dollar of budget): {constraints[0].dual_value:.4f}")
    return alpha_numerical


def optimization_with_cvar_constrain(
    market_mean_vector: np.ndarray,
    market_cov_matrix: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma: float = 0.041,
) -> np.ndarray:
    cvar_coeff = 1 / (np.sqrt(2 * np.pi) * (1 - confidence_level)) * np.exp(
        -(special.erfinv(2 * confidence_level - 1)) ** 2)

    # weights formulation: weight_i = price_i * alpha_i / wealth, unit budget
    gross_return_vector = market_mean_vector / prices_vector
    weight_cov_matrix = market_cov_matrix / (prices_vector @ prices_vector.transpose())
    cholesky_factor = np.linalg.cholesky(weight_cov_matrix)
    relative_risk_tolerance = risk_tolerance / wealth

    weights = cp.Variable((3, 1))
    relative_sigma = cp.norm(cholesky_factor.transpose() @ weights, 2)
    objective = cp.Maximize(
        gross_return_vector.transpose() @ weights
        - cp.square(relative_sigma) / (2 * relative_risk_tolerance)
    )
    cvar_rel = (1 - gross_return_vector.transpose() @ weights) + cvar_coeff * relative_sigma
    constraints = [
        cp.sum(weights) == 1,
        cvar_rel <= gamma,
        # weights >= 0,
    ]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver="CLARABEL")

    alpha_numerical = weights.value * wealth / prices_vector  # back to shares
    print(f"Allocations: {alpha_numerical}")
    print(f"CE: {prob.value * wealth:,.0f}")  # objective is CE/wealth
    print(f"budget shadow price (CE gained per extra dollar of budget): {constraints[0].dual_value:.4f}")
    return alpha_numerical
