"""Inactive research illustration, not a V2 optimizer API.

Moved from V2 liquidity.py without changing its math. These parameters were
never client-calibrated. The active RE sleeve uses explicit scenario haircuts.
"""
from dataclasses import dataclass

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
