"""Cash-first executable fixed-policy ledger, separate from provisioning optimizer.

No borrowing, dynamic rebalancing, or forced sale of unscheduled property.
After cash is exhausted, sell every liquid noncash sleeve pro rata by its
current value. This is a declared trading rule, not an optimal trading policy.
Input unit values already include configured liquidation haircuts; do not
charge them a second time. Property spendable value is credited when received
and removed from the marked holding to prevent double counting.

Phase 1 of the shared-accounting refactor: cash_first is a thin wrapper over
the shared event engine (emfin_v2/event_ledger.py) with LedgerSpec.cash_first()
- zero fees, immediate within-week settlement, arrears at the cash rate,
property receipts credited as the weekly delta of the funding path. The
Phase 0 golden fixtures (tests/test_golden_ledgers.py) pin its outputs
bit-for-bit against the pre-refactor implementation.
"""
import numpy as np
from emfin_v2.event_ledger import LedgerSpec, run_event_ledger


def cash_first(c, draw, allocation):
    r = run_event_ledger(c, draw, allocation, LedgerSpec.cash_first())
    return dict(numerical_negative_holdings_clipped=r['numerical_negative_holdings_clipped'],
                net_wealth_paths=r['net_wealth_paths'], cash_paths=r['cash_paths'],
                units_paths=r['units_paths'], sold_value_paths=r['sold_value_paths'],
                payment_shortfalls=r['payment_shortfalls'], payments=r['payments'],
                terminal_unpaid=r['terminal_unpaid'], terminal_net=r['terminal_net'],
                funded=r['funded'],
                policy='Cash first, then proportional liquidation of liquid sleeves at configured net unit values, assumed immediately spendable within the modeled week; no rebalance/borrowing; property only scheduled rent/sale receipts.',
                scope='Independent executable policy audit. Optimizer still uses money-market provisioning, not this policy. Unit values already include configured liquidity haircuts.')


def summarize_execution(c, draws, allocation):
    """Reference-scenario outcomes, never a statistical/full-funding certificate.

    Keep the paid-in-full outcome separate from the declared allowed-gap rule.
    The per-date unpaid amount includes arrears at that date. Zero observations
    of unpaid calls is not proof that the policy funds all future obligations.
    """
    if not draws: raise ValueError('execution audit requires evaluation draws')
    audits = [cash_first(c, draw, allocation) for draw in draws]
    steps = draws[0][2]
    if any(not np.array_equal(d[2], steps) or not np.array_equal(d[3], draws[0][3]) for d in draws): raise ValueError('execution audit schedules must align')
    funded = np.concatenate([r['funded'] for r in audits]); unpaid = np.concatenate([r['payment_shortfalls'] for r in audits]); terminal = np.concatenate([r['terminal_net'] for r in audits]); count = len(funded); missed = int(np.count_nonzero(~funded))
    dates = [dict(payout_index=i, week=int(step), paid_in_full_fraction=float(np.mean(unpaid[:, i] <= 1e-6)), largest_observed_unpaid=float(unpaid[:, i].max())) for i, step in enumerate(steps)]
    return dict(numerical_negative_holdings_clipped=max(r['numerical_negative_holdings_clipped'] for r in audits), available=True, funded_fraction=float(np.mean(funded)), paths=count, paths_with_unpaid_calls=missed, observed_unpaid_calls=bool(missed), outcome='Unpaid calls observed' if missed else 'No unpaid calls observed', largest_observed_unpaid=float(unpaid.max()), payment_outcomes=dates, terminal_net_quantiles=np.quantile(terminal, [.05, .5, .95]).tolist(), policy=audits[0]['policy'], scope=audits[0]['scope'], wasserstein_certified=False, full_funding_guarantee=False, interpretation='Reference-scenario execution outcome only, not a probability guarantee. Budget pass may permit shortfalls; zero unpaid observations does not bound unseen tails.')
