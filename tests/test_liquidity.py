import numpy as np
import pytest

from emfin_capstone.toolbox import liquidity as liq


def test_zero_cost_returns_input_unchanged():
    prices = np.array([[100.0, 50.0], [110.0, 48.0]])
    out = liq.apply_liquidation_cost(prices, [liq.LiquidationCostParams(0.0, 0.0)] * 2, seed=1)
    np.testing.assert_array_equal(out, prices)


def test_cost_lowers_proceeds_and_respects_cap():
    rng_prices = np.full((10000, 1), 100.0)
    params = [liq.LiquidationCostParams(mean_cost=0.002, max_cost=0.02)]
    out = liq.apply_liquidation_cost(rng_prices, params, seed=42)
    assert (out <= 100.0).all()
    assert (out >= 98.0).all()  # cap
    assert out.mean() == pytest.approx(100 * (1 - 0.002), rel=0.05)


def test_param_validation():
    with pytest.raises(ValueError):
        liq.LiquidationCostParams(mean_cost=0.05, max_cost=0.01)
    with pytest.raises(ValueError):
        liq.LiquidationCostParams(mean_cost=-0.01, max_cost=0.01)


def test_time_to_cash_full_beyond_orderly_sale():
    h = liq.IlliquidHolding("villa", 1_000_000, time_to_cash_weeks=13, fire_sale_haircut=0.08)
    assert liq.time_to_cash_multiplier(13, h) == 1.0
    assert liq.time_to_cash_multiplier(52, h) == 1.0


def test_time_to_cash_ramp():
    h = liq.IlliquidHolding("villa", 1_000_000, time_to_cash_weeks=10, fire_sale_haircut=0.10)
    assert liq.time_to_cash_multiplier(0, h) == pytest.approx(0.90)
    assert liq.time_to_cash_multiplier(5, h) == pytest.approx(0.95)
    assert liq.funding_value(5, h) == pytest.approx(950_000)


def test_cost_column_count_must_match():
    with pytest.raises(ValueError):
        liq.apply_liquidation_cost(np.ones((3, 2)), [liq.LiquidationCostParams(0.001, 0.01)], seed=1)
