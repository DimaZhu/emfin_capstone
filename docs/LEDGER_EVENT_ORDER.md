# Canonical ledger event order (Phase 0 of the shared-accounting refactor)

Owner: Tijs de Boer. Status (8 Nov 2026): pins current behavior; changes nothing.
Companion to docs/REFACTOR_PLAN_SHARED_ACCOUNTING.md.

## Canonical within-week order

1. Grow cash and arrears at the money-market (cash) ratio for the week.
2. Credit property receipts (rent and settled sale proceeds) into cash.
3. Execute declared trades; proceeds settle per the declared settlement lag.
4. Pay due payments (scheduled amount plus accrued arrears); unpaid remainder
   persists as arrears.
5. Mark wealth: cash + holdings at marks + property mark (net of receipts
   already credited to cash) - arrears.

## How each existing accounting maps onto it

### 1. Optimizer provisioning (`default_run.py:440`)

No event order at all: each future payment is grown to the horizon at the
money-market rate (`amount * growth[terminal]/growth[step-1]`) and netted
against terminal wealth. Skips steps 1-4 entirely; only a terminal valuation.
Declared convention: money-market opportunity cost, not a trading ledger.

### 2. Judge accounting (`emfin_v2/evaluation.py`)

Step 4 only, evaluated on spendable funding paths: at each payment week the
funding check compares the required amount against `funding_paths(draw) @ a`
at that week. Frozen holdings, no trading (step 3 absent), no cash growth or
arrears mechanics (steps 1-2, 5 absent). Docstring: "current provisioning
convention, not a trading ledger." Marked property is not spendable cash;
only property receipts are.

### 3. Executable audit ledger (`emfin_v2/ledger.py:cash_first`)

Follows the canonical order exactly, with these declared choices:
- Step 3 trades: cash first, then one common fraction of every liquid sleeve
  (pro rata by current value) at haircut-netted unit values. Immediate
  within-week settlement (lag 0). No buy side, no rebalancing.
- Step 2: property receipts are credited as the weekly delta of the property
  funding path; the credited amount is removed from the property mark at
  step 5 to prevent double counting.
- Step 4: arrears accrue at the cash rate.
- Step 5: `net wealth = cash + liquid holdings at marks + property mark
  (net of credited receipts) - arrears`.
- Numerical guard: negative holdings up to 1e-7 of wealth are clipped and
  disclosed in dollars (`numerical_negative_holdings_clipped`), never used to
  repair optimizer risk.

### 4. Policy experiment engine (`emfin_v2/dynamic_policy.py:execute`)

Follows the canonical order with these declared choices:
- Step 3 trades: mode-dependent (feedback softmax targets, static targets,
  cash-first sales, pro-rata, calendar rebalancing). Fee (default 5 bps) on
  both sells and buys. Proceeds enter a pending queue and settle after
  `delay` weeks (default 1).
- Step 1 also grows `paid_carry` (past payments shadow-accrued at cash) for
  the shadow-wealth comparison.
- Step 4: multiple payments due the same week are summed first; arrears
  accrue at the cash rate.
- Step 5: pending fixed receivables count in marked wealth but cannot pay
  before settlement.
- Restrictions the shared engine must lift: exactly four liquid risky
  sleeves required; property must be unsold with zero rent.

## Deviations the refactor must name, not hide

- Provisioning (1) and the judge (2) are valuation conventions; cash_first (3)
  and execute (4) are trading ledgers. Phase 4 makes provisioning a declared
  valuation of the same liability schedule, leaving exactly one named
  residual: trading vs no-trading.
- Settlement lag differs: 0 weeks in cash_first, `delay` (default 1) in
  execute. Becomes a `LedgerSpec` field in Phase 1.
- Fees differ: none in cash_first (unit values pre-netted), explicit bps in
  execute. Becomes a `LedgerSpec` field.
- Payment timing convention differs within the week: cash_first pays dues
  declared at step index `t+1` after growth; execute pays dues at step `t`
  after growth and settlement. Golden fixtures pin both.
