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
    # Phase 3 mechanics (defaults preserve the Phase 1 cash_first behavior):
    need_rule: str = 'due_now'        # 'due_now' | 'windowed' (window to next decision)
    decision_rule: str = 'payment_weeks'  # 'payment_weeks' | 'before_settlement'
    sale_rule: str = 'cash_first'     # 'cash_first' | 'pro_rata'
    shadow_carry: bool = False        # track paid Carry shadow wealth (dynamic_policy)
    proceeds_rounding: str = 'elementwise'  # 'elementwise' | 'aggregate' (legacy execute op order)
    # Target rules (dynamic_policy.execute's feedback/static modes). A target
    # rule sets a full [cash, *liquid] allocation target at a decision week,
    # trading both ways (sell what exceeds target, buy what falls short);
    # 'none' falls back to the sell-only sale_rule.
    target_rule: str = 'none'         # 'none' | 'feedback' | 'static_target'
    initial_rule: str = 'same'        # 'same' | 'none' | 'feedback' | 'static_target'
    capture_weights_at_initial: bool = False  # feedback_static_target's path-0 weights quirk
    feedback_theta: tuple = ()        # eight softmax feedback parameters
    rebalance_every_payments: int = 0  # static_frequency: 0 = target at every decision

    @staticmethod
    def cash_first():
        """The spec that reproduces emfin_v2.ledger.cash_first exactly."""
        return LedgerSpec()

    @staticmethod
    def dynamic_cash_first(fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='cash_first') mechanics."""
        return LedgerSpec(fee_bps=fee_bps, settlement_lag_weeks=settlement_lag_weeks,
                          need_rule='windowed', decision_rule='before_settlement',
                          sale_rule='cash_first', shadow_carry=True,
                          proceeds_rounding='aggregate')

    @staticmethod
    def dynamic_pro_rata(fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='pro_rata') mechanics."""
        return LedgerSpec(fee_bps=fee_bps, settlement_lag_weeks=settlement_lag_weeks,
                          need_rule='windowed', decision_rule='before_settlement',
                          sale_rule='pro_rata', shadow_carry=True,
                          proceeds_rounding='aggregate')

    @staticmethod
    def _dynamic(fee_bps, settlement_lag_weeks, **kw):
        base = dict(fee_bps=fee_bps, settlement_lag_weeks=settlement_lag_weeks,
                    need_rule='windowed', decision_rule='before_settlement',
                    shadow_carry=True, proceeds_rounding='aggregate')
        base.update(kw)
        return LedgerSpec(**base)

    @staticmethod
    def dynamic_feedback(theta, fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='feedback') mechanics."""
        return LedgerSpec._dynamic(fee_bps, settlement_lag_weeks,
                                   target_rule='feedback', feedback_theta=tuple(theta))

    @staticmethod
    def dynamic_static_target(fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='static_target') mechanics."""
        return LedgerSpec._dynamic(fee_bps, settlement_lag_weeks,
                                   target_rule='static_target')

    @staticmethod
    def dynamic_feedback_initial_only(theta, fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='feedback_initial_only') mechanics."""
        return LedgerSpec._dynamic(fee_bps, settlement_lag_weeks,
                                   target_rule='none', initial_rule='feedback',
                                   sale_rule='cash_first', feedback_theta=tuple(theta))

    @staticmethod
    def dynamic_feedback_static_target(theta, fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='feedback_static_target') mechanics."""
        return LedgerSpec._dynamic(fee_bps, settlement_lag_weeks,
                                   target_rule='static_target', initial_rule='feedback',
                                   capture_weights_at_initial=True,
                                   feedback_theta=tuple(theta))

    @staticmethod
    def dynamic_static_frequency(rebalance_months, fee_bps=5.0, settlement_lag_weeks=1):
        """dynamic_policy.execute(mode='static_frequency') mechanics: a static
        target at every rebalance_every_payments-th payment's decision week
        (and the initial trade), cash_first sales at the other decisions."""
        return LedgerSpec._dynamic(fee_bps, settlement_lag_weeks,
                                   target_rule='static_target', sale_rule='cash_first',
                                   rebalance_every_payments=rebalance_months)

    def validate(self):
        if self.liquidation != 'cash_first_pro_rata':
            raise ValueError('only cash_first_pro_rata liquidation is supported')
        if not np.isfinite(self.fee_bps) or not 0 <= self.fee_bps < 10000:
            raise ValueError('fee_bps must be in [0, 10000)')
        if type(self.settlement_lag_weeks) is not int or self.settlement_lag_weeks < 0:
            raise ValueError('settlement_lag_weeks must be a nonnegative int')
        if self.arrears_rate != 'cash':
            raise ValueError('only the cash arrears rate is supported')
        if self.property_receipts != 'credit_delta':
            raise ValueError('only the credit_delta property convention is supported')
        if self.rebalance_calendar:
            raise ValueError('rebalancing arrives with Phase 3 target rules')
        if self.need_rule not in ('due_now', 'windowed'):
            raise ValueError('unknown need rule')
        if self.decision_rule not in ('payment_weeks', 'before_settlement'):
            raise ValueError('unknown decision rule')
        if self.sale_rule not in ('cash_first', 'pro_rata'):
            raise ValueError('unknown sale rule')
        if self.proceeds_rounding not in ('elementwise', 'aggregate'):
            raise ValueError('unknown proceeds rounding convention')
        if self.need_rule == 'windowed' and self.decision_rule != 'before_settlement':
            raise ValueError('windowed needs require the before_settlement decision rule')
        if self.sale_rule == 'pro_rata' and self.need_rule != 'windowed':
            raise ValueError('the pro_rata sale rule requires windowed needs')
        if self.target_rule not in ('none', 'feedback', 'static_target'):
            raise ValueError('unknown target rule')
        if self.initial_rule not in ('same', 'none', 'feedback', 'static_target'):
            raise ValueError('unknown initial rule')
        uses_target = self.target_rule != 'none' or (
            self.initial_rule not in ('same', 'none'))
        if uses_target and self.decision_rule != 'before_settlement':
            raise ValueError('target rules require the before_settlement decision rule')
        uses_feedback = 'feedback' in (self.target_rule, self.initial_rule)
        if uses_feedback:
            th = np.asarray(self.feedback_theta, float)
            if th.shape != (8,) or not np.isfinite(th).all():
                raise ValueError('eight finite feedback parameters required')
        if self.capture_weights_at_initial and not (
                self.initial_rule == 'feedback' and self.target_rule == 'static_target'):
            raise ValueError('weights capture requires feedback initial into static target')
        if type(self.rebalance_every_payments) is not int or self.rebalance_every_payments < 0:
            raise ValueError('rebalance_every_payments must be a nonnegative int')
        if self.rebalance_every_payments and self.target_rule != 'static_target':
            raise ValueError('a rebalance calendar requires the static_target rule')


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
    dynamic = spec.decision_rule == 'before_settlement'
    if dynamic:
        # dynamic_policy.execute decision calendar, in execute weeks: the
        # initial trade plus one decision (payment week - settlement lag) per
        # payment. Execute week tau is engine week tau - 1; the initial trade
        # (tau = 0, at initial prices) runs before the loop.
        decisions = sorted(set([0, *[max(0, int(w) - lag)
                                     for w in steps if int(w) - lag < h]]))
        decision_weeks = set(tau - 1 for tau in decisions if tau >= 1)
        initial_rule = spec.target_rule if spec.initial_rule == 'same' else spec.initial_rule
        if initial_rule == 'none':
            initial_rule = spec.sale_rule
        if spec.rebalance_every_payments:
            m = spec.rebalance_every_payments
            rebal_exec = set([0, *[max(0, int(steps[k - 1]) - lag)
                                   for k in range(1, len(steps)) if k % m == 0]])
            rebalance_weeks = set(tau - 1 for tau in rebal_exec if tau >= 1)
        else:
            rebalance_weeks = decision_weeks
        # Static-target weights run over [cash, *liquid], matching
        # dynamic_policy.execute's liquid list and base.
        cash_liquid = [cash_index, *liquid]
        base_liquid = float(a[cash_liquid].sum())
        weights = a[cash_liquid] / base_liquid
        running = np.ones(n)
        paid_carry = np.zeros(n)
        shadow = np.zeros((n, h))
        cost = np.zeros(n)
        turnover = np.zeros(n)
        trades = np.zeros(n, int)

        def windowed_need(tau):
            later = [z for z in decisions if z > tau]
            next_decision = min(later) if later else h + 1
            mask = (steps >= tau + lag) & (steps < next_decision + lag)
            return amounts[:, mask].sum(1) + arrears

        def declared_trade(px, tau, rule):
            # dynamic_policy.execute's trade block, float op order preserved.
            nonlocal cash, cost, turnover, trades, weights
            val = units[:, liquid] * px[:, liquid]
            spendable = cash + val.sum(1)
            if rule == 'feedback':
                from scipy.special import softmax
                th = np.asarray(spec.feedback_theta, float)
                if len(liquid) != 4:
                    raise ValueError('the feedback target rule requires four liquid sleeves')
                remaining = amounts[:, steps >= max(1, tau)].sum(1)
                past = np.ones((n, len(liquid))) if tau <= 4 else prices[:, tau - 5, liquid]
                momentum = np.log(np.maximum(px[:, liquid], 1e-300) / np.maximum(past, 1e-300))
                feature = th[4] * (spendable / base_liquid - 1) + th[5] * remaining / base_liquid \
                    + th[6] * (px[:, liquid[0]] / running - 1)
                target = softmax(np.c_[np.zeros(n), np.broadcast_to(th[:4], (n, 4))
                                       + feature[:, None] + th[7] * momentum],
                                 axis=1) * spendable[:, None]
                if tau == 0 and spec.capture_weights_at_initial:
                    weights = target[0] / spendable[0]
            elif rule == 'static_target':
                target = spendable[:, None] * weights[None, :]
            else:
                need = windowed_need(tau)
                if rule == 'cash_first':
                    sale = np.minimum(np.maximum(need - cash, 0) / (1 - fee), val.sum(1))
                else:
                    sale = np.minimum(need * np.divide(val.sum(1), spendable, out=np.zeros(n),
                                                       where=spendable > 0) / (1 - fee), val.sum(1))
                fraction = np.divide(sale, val.sum(1), out=np.zeros(n), where=val.sum(1) > 0)
                target = np.c_[cash + sale, val * (1 - fraction[:, None])]
            sell = np.maximum(val - target[:, 1:], 0)
            sell = np.minimum(sell, val)
            units[:, liquid] -= np.divide(sell, px[:, liquid], out=np.zeros_like(sell),
                                          where=px[:, liquid] > 0)
            proceeds = sell.sum(1) * (1 - fee)
            cost += sell.sum(1) * fee
            turnover += sell.sum(1)
            trades += (sell > 1e-6).sum(1)
            if lag:
                pending[:, tau + lag - 1] += proceeds
            else:
                cash += proceeds
            if rule in ('feedback', 'static_target'):
                after = units[:, liquid] * px[:, liquid]
                buy = np.maximum(target[:, 1:] - after, 0)
                buy_need = buy.sum(1) * (1 + fee)
                bfraction = np.minimum(1., np.divide(cash, buy_need, out=np.zeros(n),
                                                     where=buy_need > 0))
                buy *= bfraction[:, None]
                spent = buy.sum(1) * (1 + fee)
                cash -= spent
                units[:, liquid] += np.divide(buy, px[:, liquid], out=np.zeros_like(buy),
                                              where=px[:, liquid] > 0)
                cost += buy.sum(1) * fee
                turnover += buy.sum(1)
                trades += (buy > 1e-6).sum(1)

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
    if dynamic:
        # execute-week-0 trade: the initial-price rebalance.
        declared_trade(np.ones((n, d)), 0, initial_rule)
    for t in range(h):
        ratio = growth[:, t] / (growth[:, t - 1] if t else 1.)
        cash *= ratio
        arrears *= ratio
        if dynamic and spec.shadow_carry:
            paid_carry *= ratio
        cash += pending[:, t]
        pending[:, t] = 0.
        # Property receipts are a cash_first-ledger convention; the dynamic
        # specs share dynamic_policy.execute semantics (no property receipts).
        property_cash = np.zeros(n)
        if not dynamic:
            property_cash = funding[:, t, properties] @ a[properties] if properties else np.zeros(n)
            received = property_cash - last_property_cash * ratio
            if (received < -1e-5).any():
                raise ValueError('property funding path removes previously settled cash')
            cash += np.maximum(received, 0.)
            last_property_cash = property_cash
        if dynamic:
            running = np.maximum(running, prices[:, t, liquid[0]]) if liquid else running
            # One declared trade per decision week; payments then paid from
            # cash in due order, unpaid persisting as arrears.
            if t in decision_weeks:
                rule = spec.target_rule
                if rule == 'static_target' and spec.rebalance_every_payments \
                        and t not in rebalance_weeks:
                    rule = 'none'
                if rule == 'none':
                    rule = spec.sale_rule
                declared_trade(prices[:, t, :], t + 1, rule)
            for k in np.flatnonzero(steps == t + 1):
                required = amounts[:, k] + arrears
                payment = np.minimum(np.maximum(cash, 0), required)
                cash -= payment
                arrears = required - payment
                paid_carry += payment
                paid[:, k] = payment
                shortfalls[:, k] = arrears
        else:
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
        if dynamic:
            # dynamic_policy.execute marking: property units never trade and
            # carry no receipts under its validation, so all units mark at
            # price; settled pending entries are exactly zero.
            net = cash + (units * prices[:, t, :]).sum(1) + pending.sum(1) - arrears
            values[:, t] = net
            if spec.shadow_carry:
                shadow[:, t] = net + paid_carry
        else:
            # Property cash is now held in cash, not marked a second time.
            property_mark = prices[:, t, properties] @ a[properties] - property_cash if properties \
                else np.zeros(n)
            values[:, t] = cash + (prices[:, t, liquid] * units[:, liquid]).sum(1) + property_mark \
                + pending[:, t + 1:].sum(1) - arrears
        cash_path[:, t] = cash
        units_path[:, t] = units
    result = dict(numerical_negative_holdings_clipped=negative_roundoff,
                  net_wealth_paths=values, cash_paths=cash_path, units_paths=units_path,
                  sold_value_paths=sold, payment_shortfalls=shortfalls, payments=paid,
                  terminal_unpaid=arrears, terminal_net=values[:, -1],
                  funded=np.all(shortfalls <= 1e-6, axis=1),
                  fee_burned=fee_burned, pending_terminal=pending.sum(1), spec=spec)
    if dynamic:
        result.update(shadow_wealth_paths=shadow, cost=cost, turnover=turnover,
                      trades=trades, terminal_units=units.copy())
    return result
