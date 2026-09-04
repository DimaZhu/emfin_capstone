from datetime import date
from dataclasses import dataclass
from typing import List

import numpy as np

from emfin_capstone.toolbox import price


@dataclass
class EquityReturn:
    date: date
    equity_return: float


@dataclass
class EquityReturnsCollection:
    symbol: str
    equity_returns: List[EquityReturn]


def convert_history_prices_to_weekly_returns(
    price_history: price.PriceHistory,
) -> EquityReturnsCollection:
    """Convert a daily close history into weekly compounded (log) returns.

    Returns are computed Wednesday-to-Wednesday: for each Wednesday close, a
    return is emitted only when the previously kept close is exactly 7 calendar
    days earlier. Weeks whose Wednesday falls on an exchange holiday are skipped,
    since no 7-day pair can be formed across the gap. Each element pairs the
    closing Wednesday's date with the log return ln(P_t / P_{t-1}) for that week,
    so callers can align the series on its own dates rather than on the full
    daily index.
    """
    last_date = price_history.closes[0].date
    last_price = price_history.closes[0].close
    weekly_return_list: list[EquityReturn] = []
    for price_observation in price_history.closes:
        current_date = price_observation.date
        current_price = price_observation.close
        if current_date.weekday() == 2:
            if (current_date - last_date).days == 7:
                weekly_return = np.log(current_price / last_price)
                weekly_return_list.append(
                    EquityReturn(
                        date=current_date,
                        equity_return=weekly_return
                    )
                )
            last_date = current_date
            last_price = current_price
    return EquityReturnsCollection(symbol=price_history.symbol, equity_returns=weekly_return_list)
