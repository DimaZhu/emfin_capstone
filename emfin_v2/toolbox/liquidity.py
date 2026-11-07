"""Liquidity: convolution for liquid assets, time-to-cash haircuts for illiquid ones.

Two regimes, matching the Ballast mockup's time-to-cash column and the
15 Oct decision:

*Liquid assets* (the ETFs): liquidation proceeds per unit are
``P * (1 - C)`` with the cost ``C`` a random variable — the *liquidity
convolution*: the distribution of net proceeds is the market distribution
convolved with a cost distribution.  Cost = half-spread + price impact.
Without volume data we do not pretend a participation model; ``C`` is a
scaled beta with documented mean/cap parameters, drawn independently per
scenario.  (Meucci's point stands: the optimizer downstream sees only a
scenario matrix, so this plugs in upstream without touching the solver.)

*Illiquid assets* (real estate, the family company): there is no continuous
price to convolve.  Instead each holding carries a *time to cash* — how
long an orderly sale takes — and a *fire-sale haircut*.  The value
available to fund a liability at horizon t is ``V * m(t)`` with
``m(t) = 1`` once t >= time-to-cash and a linearly ramping haircut before.
This is deliberately simple and honest: the parameters are communicable to
a client ("selling the Dubai flat in 3 months costs about 8%"), and the
sensitivity to them is a paper exhibit, not a hidden assumption.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LiquidationCostParams:
    """Random liquidation cost for a liquid asset.

    ``mean_cost`` = expected round-trip cost as a fraction of value
    (half-spread + average impact, e.g. 0.002 = 20bp);
    ``max_cost`` = stressed cost cap (e.g. 0.02 = 200bp in a disorderly
    market).  The beta shape is fixed so ~95% of mass sits below
    2.5x the mean — a mildly right-skewed cost distribution.
    """

    mean_cost: float
    max_cost: float

    def __post_init__(self) -> None:
        if not (0 <= self.mean_cost <= self.max_cost <= 1):
            raise ValueError("need 0 <= mean_cost <= max_cost <= 1")


def _cost_samples(params: LiquidationCostParams, n: int, rng: np.random.Generator) -> np.ndarray:
    if params.mean_cost == 0:
        return np.zeros(n)
    # Beta with mean mu = a/(a+b); fix a=2 (right skew), solve b from mean.
    mu = params.mean_cost / params.max_cost
    a = 2.0
    b = a * (1 - mu) / mu
    return params.max_cost * rng.beta(a, b, size=n)


def apply_liquidation_cost(
    price_scenarios: np.ndarray,
    cost_params: list[LiquidationCostParams],
    seed: int,
) -> np.ndarray:
    """Convolve an (n_scenarios, n_assets) price matrix with random costs.

    Cost draws are independent across scenarios and assets (systematic
    liquidity spirals belong in the market scenarios themselves, via
    entropy-pooled stress views — not smuggled in here).
    """
    if len(cost_params) != price_scenarios.shape[1]:
        raise ValueError("one LiquidationCostParams per asset column")
    rng = np.random.default_rng(seed)
    net = price_scenarios.copy()
    for j, params in enumerate(cost_params):
        net[:, j] = price_scenarios[:, j] * (1 - _cost_samples(params, len(net), rng))
    return net


@dataclass(frozen=True)
class IlliquidHolding:
    """An asset that cannot be marked-to-market daily.

    ``time_to_cash_weeks``: weeks an orderly sale takes.
    ``fire_sale_haircut``: fractional value lost if forced to sell
    immediately (0.08 = 8%).
    """

    name: str
    value: float
    time_to_cash_weeks: float
    fire_sale_haircut: float


def time_to_cash_multiplier(horizon_weeks: float, holding: IlliquidHolding) -> float:
    """Fraction of value realizable by ``horizon_weeks``.

    1.0 once the horizon covers an orderly sale; before that a linear ramp
    down to ``1 - fire_sale_haircut`` at horizon 0.  Linear is a modeling
    choice, flagged for the limitations section — the exhibit to run is the
    sensitivity of the allocation to ``fire_sale_haircut``.
    """
    if horizon_weeks >= holding.time_to_cash_weeks:
        return 1.0
    if holding.time_to_cash_weeks <= 0:
        return 1.0
    ramp = 1 - horizon_weeks / holding.time_to_cash_weeks
    return 1.0 - holding.fire_sale_haircut * ramp


def funding_value(horizon_weeks: float, holding: IlliquidHolding) -> float:
    """Value this holding can contribute to funding a liability at the horizon."""
    return holding.value * time_to_cash_multiplier(horizon_weeks, holding)
