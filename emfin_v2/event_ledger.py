"""Shared event ledger engine (Phase 1 of the shared-accounting refactor).

One vectorized within-week event engine parameterized by a LedgerSpec.
Canonical order per week (docs/LEDGER_EVENT_ORDER.md):
1. grow cash and arrears at the money-market ratio;
2. settle in-flight trade proceeds and credit property receipts;
3. execute declared trades (proceeds settle after the declared lag);
4. pay due payments (scheduled amount plus arrears; unpaid persists);
5. mark wealth: cash + holdings at marks + property mark net of credited
   receipts + in-flight proceeds at face value - arrears.

Phase 1 migrates ledger.cash_first onto this engine as a thin wrapper; the
Phase 0 golden fixtures (tests/test_golden_ledgers.py) pin its outputs
bit-for-bit. Later phases re-express dynamic_policy.execute modes as further
specs; the engine is dimension-agnostic (no four-sleeve restriction).
"""
import numpy as np
from dataclasses import dataclass

from emfin_v2.contracts import ScenarioBatch
from emfin_v2.real_estate import funding_paths


@dataclass(frozen=True)
class LedgerSpec:
    """Declared accounting choices for one run of the shared event engine.

    liquidation: 'cash_first_pro_rata' - cash first, then one common fraction
        of every liquid sleeve by current value (a declared trading rule, not
        an optimal policy).
    fee_bps: fee in basis points charged on trade value (0 for cash_first,
        whose unit values are already haircut-netted).
    settlement_lag_weeks: weeks before trade proceeds are spendable (0 for
        cash_first's immediate within-week settlement).
    arrears_rate: 'cash' - arrears accrue at the money-market ratio.
    property_receipts: 'credit_delta' - credit the weekly delta of the
        property funding path and remove it from the property mark.
    rebalance_calendar: reserved for Phase 3; must be empty in Phase 1.
    """
    liquidation: str = 'cash_first_pro_rata'
    fee_bps: float = 0.0
    settlement_lag_weeks: int = 0
    arrears_rate: str = 'cash'
    property_receipts: str = 'credit_delta'
    rebalance_calendar: tuple = ()

    @staticmethod
    def cash_first():
        """The spec that reproduces emfin_v2.ledger.cash_first exactly."""
        return LedgerSpec()

    def validate(self):
        if self.liquidation != 'cash_first_pro_rata':
            raise ValueError('Phase 1 supports only cash_first_pro_rata liquidation')
        if not np.isfinite(self.fee_bps) or not 0 <= self.fee_bps < 10000:
            raise ValueError('fee_bps must be in [0, 10000)')
        if type(self.settlement_lag_weeks) is not int or self.settlement_lag_weeks < 0:
            raise ValueError('settlement_lag_weeks must be a nonnegative int')
        if self.arrears_rate != 'cash':
            raise ValueError('Phase 1 supports only the cash arrears rate')
        if self.property_receipts != 'credit_delta':
            raise ValueError('Phase 1 supports only the credit_delta property convention')
        if self.rebalance_calendar:
            raise ValueError('rebalancing arrives with Phase 3')


def run_event_ledger(c, draw, allocation, spec):
    """Run one event ledger. Returns generic results; callers map to their
    legacy result dicts. In-flight proceeds count in marked wealth at face
    value but cannot pay before settlement (dynamic_policy convention); for
    lag-0 specs the pending queue is always exactly zero at marking time."""
    spec.validate()
    if isinstance(draw, ScenarioBatch):
        draw = draw.to_draw()
    paths, amounts, steps, bases, growth = draw
    prices = np.asarray(paths, float)
    a = np.asarray(allocation, float)
    n, h, d = prices.shape
    cash_index = c['cash_index']
    fee = spec.fee_bps * 1e-4
    lag = spec.settlement_lag_weeks
    # Match the final holdings judge's explicit absolute weight tolerance.
    # Numerical near-zero negatives are clipped for this execution audit only,
    # disclosed in dollars, never used to repair optimizer risk.
    tolerance = 1e-7 * float(c.get('wealth', max(float(np.abs(a).sum()), 1.)))
    if a.shape != (d,) or not np.isfinite(a).all() or (a < -tolerance).any() \
            or not np.isfinite(prices).all() or (prices < 0).any():
        raise ValueError('finite nonnegative aligned holdings and prices required')
    negative_roundoff = float(np.maximum(-a, 0).sum())
    a = np.maximum(a, 0)
    if not np.isfinite(amounts).all() or (amounts < 0).any():
        raise ValueError('finite nonnegative liabilities required')
    properties = c.get('asset_layout', {}).get(
        'property_indices', [6] if c['real_estate']['enabled'] and d == 7 else [])
    liquid = [i for i in range(d) if i != cash_index and i not in properties]
    units = np.broadcast_to(a, (n, d)).copy()
    units[:, cash_index] = 0.
    cash = np.full(n, a[cash_index])
    arrears = np.zeros(n)
    values = np.zeros((n, h))
    cash_path = np.zeros((n, h))
    shortfalls = np.zeros_like(amounts)
    paid = np.zeros_like(amounts)
    units_path = np.zeros((n, h, d))
    sold = np.zeros((n, h, d))
    pending = np.zeros((n, h + lag + 2))
    fee_burned = np.zeros(n)
    last_property_cash = np.zeros(n)
    funding = funding_paths(draw)
    for t in range(h):
        ratio = growth[:, t] / (growth[:, t - 1] if t else 1.)
        cash *= ratio
        arrears *= ratio
        cash += pending[:, t]
        pending[:, t] = 0.
        property_cash = funding[:, t, properties] @ a[properties] if properties else np.zeros(n)
        received = property_cash - last_property_cash * ratio
        if (received < -1e-5).any():
            raise ValueError('property funding path removes previously settled cash')
        cash += np.maximum(received, 0.)
        last_property_cash = property_cash
        for k in np.flatnonzero(steps == t + 1):
            due = amounts[:, k] + arrears
            # cash first, then one common fraction of all liquid units.
            need = np.maximum(due - cash, 0.)
            available = prices[:, t, liquid] * units[:, liquid]
            total = available.sum(1)
            gross_need = need / (1. - fee)
            fraction = np.minimum(1., np.divide(gross_need, total, out=np.zeros(n), where=total > 0))
            liquidation = available * fraction[:, None]
            proceeds = liquidation * (1. - fee)
            sold[:, t, liquid] += liquidation
            fee_burned += (liquidation - proceeds).sum(1)
            units[:, liquid] *= 1 - fraction[:, None]
            if lag == 0:
                cash += proceeds.sum(1)
            else:
                pending[:, t + lag] += proceeds.sum(1)
            payment = np.minimum(cash, due)
            cash -= payment
            arrears = due - payment
            paid[:, k] = payment
            shortfalls[:, k] = arrears
        # Property cash is now held in cash, not marked a second time.
        property_mark = prices[:, t, properties] @ a[properties] - property_cash if properties \
            else np.zeros(n)
        values[:, t] = cash + (prices[:, t, liquid] * units[:, liquid]).sum(1) + property_mark \
            + pending[:, t + 1:].sum(1) - arrears
        cash_path[:, t] = cash
        units_path[:, t] = units
    return dict(numerical_negative_holdings_clipped=negative_roundoff,
                net_wealth_paths=values, cash_paths=cash_path, units_paths=units_path,
                sold_value_paths=sold, payment_shortfalls=shortfalls, payments=paid,
                terminal_unpaid=arrears, terminal_net=values[:, -1],
                funded=np.all(shortfalls <= 1e-6, axis=1),
                fee_burned=fee_burned, pending_terminal=pending.sum(1), spec=spec)
