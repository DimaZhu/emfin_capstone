# Cash-first policy audit

`ledger.cash_first` is a separate executable fixed trading policy, not an
optimizing policy. Cash earns the scenario cash rate. At a payment it uses
cash first, then sells all liquid noncash sleeves proportionally to their
current net unit value, only as needed. Listed-sleeve sale proceeds are assumed spendable within the modeled week; actual trade/settlement calendars and market depth are not calibrated. It does not borrow or rebalance back
to target weights. Property cannot be sold except through the explicit
agreement/settlement plan. Its received rent/settled cash is credited to cash
and removed from the property mark exactly once. Unpaid calls remain arrears.
Same-week payments follow input order. The returned paths include units sold,
cash, net wealth, due-date shortfalls and unpaid terminal obligations.

The independent hand oracle is deliberately different from provisioning:
cash20,80 shares, prices1.25 then1.50, payments30 then10 leaves72 then65.333
shares, terminal net98. Money-market provisioning reports100. Tests also
cover cash interest, same-week order, property rent/settlement, unsold property
and persistent arrears. Path unit values already carry configured liquidation
haircuts, so the ledger does not charge the same haircut again.

The optimizer still uses provisioning. The ledger is a policy audit alongside
it, not a false claim that the optimizer solves a dynamic trading problem.
W1 provisioning risk buffers are not asserted to bound this nonlinear selling
policy. Its cash-flow results must be checked on the matched judge/history;
any gap between the two models must be shown. Converting the optimization
itself to a dynamic self-financing policy remains further work.
