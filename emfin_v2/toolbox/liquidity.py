"""Legacy liquid-asset convolution benchmark.

The active research engine uses the separate Meucci overlay. The default uses
explicit proportional scenario haircuts. The unused time-to-cash illustration
was moved intact to legacy/research/liquidity_time_to_cash.py and is not shipped.
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
