# Current engine: model, accounting and evidence

Private research, not an investment recommendation. Current as of7 November2026.
This replaces stale mixed-generation notes; the previous text is preserved in
[the archived notes](ARCHIVED_ENGINE_V2_PRE_BOOK_AUDIT.md), not current evidence.

## Run and reproduce

After installing this package, `python -m emfin_v2` or `emfin-run` runs the
bundled default offline. `emfin-explore` opens the local dashboard. Historical
CSV inputs, source manifests, defaults and templates travel in the wheel.
Reports go to the selected output directory in your working folder.

The UI uses100 training,200 validation and300 final paths with two batches.
It is a coarse preview, not the larger separately saved research tier. Local
HTTP computation has one solve slot, rejects concurrent requests with429,
and leaves larger CLI research work out of the UI. Closing a page does not
currently cancel a running solver.

## Current universe and scenario law

- VTI, VWO, GLD, IEF, an explicit0%-rate cash account, fixed initial10%
  Singapore private residential property; USD reporting with joint SGD/USD.
- Actual listed total-return histories, not aliases for the older instruments.
  Property is a quarterly URA price index, not a tradable property total return.
- Default weekly Gaussian scale mixture: probabilities0.9/0.1, variance
  scales0.75/3.25, independently sampled over weeks and shared across assets.
  It preserves fitted log covariance and has finite price moments. Its shape
  is development-selected, not estimated regimes, fitted tail shape or FHS.
- Correlation shrinkage in standardized coordinates; an explicit156-observation
  strength cross-listed-mean shrinkage heuristic. This is not the exact
  James-Stein/Jorion estimator or a calibrated Bayesian posterior. FX log
  drift is explicitly set to zero. See the book audit for the distinction.
- The new invariance panel reports early/late CDF distance, return and squared
  return lag correlations, and sample shape. It is descriptive, not an iid
  certification, test p-value or automatic model selector. Observed volatility
  clustering is not captured by the iid mixture default.
- IEF is a rolling Treasury ETF. Its total-return history is not the same
  economic object as a fixed-maturity bond converging to par. The legacy
  yield-based bond repricer remains in the explicit legacy universe.

The legacy Student-t law is explicitly named and retained for reproducibility.
Exponentiating its nondegenerate unbounded log shocks does not give finite
population price moments. FHS is a separate past-only EWMA residual-bootstrap
variant, not fitted GARCH or an original-paper replication.

## Investor objective and constraints

CARA certainty equivalent is measured in dollars of terminal marked wealth
NET of all provisioned payments, not expected investment profit. Risk tolerance
also has dollar units. Mean-variance is a matched comparator/approximation,
not an exact CARA identity for non-Gaussian horizon wealth.

The editable default is$250,000 each month for12 approximate weekly due dates,
$3M total on$100M capital over52 weeks. This is a placeholder schedule, not
verified client obligations. Stochastic liabilities are disabled until a causal,
calibrated model exists. Recurring dates never move silently when the horizon
changes. Every final edited configuration uses one validation boundary.

The optimizer uses cumulative money-market provisioning, not dynamic optimal
liquidation. Earlier payments reduce later available wealth with money-market
opportunity costs. Property has no planned sale or rent by default. Fixed10%
is an initial equality, not a floor or ongoing rebalancing target.

The tail-shortfall allowance is20% of each payment at95% confidence. It is
NOT a requirement to make all payments with95% or99% probability. Path loss
is loss relative to initial capital, before payouts; it is not peak-to-trough
maximum drawdown. The tail guardrails and terminology are defined separately
from consumption utility or a lifetime financial plan.

## Independent final judge

Frozen candidates are checked against every payment, terminal loss, maximum
path loss and holdings on independent final scenarios under reference,
nominal, stressed and common-threshold finite posterior-hull envelopes.
Funding pass and overall pass are distinct. No final failure triggers repair.
Conditional batch Student-t/Bonferroni diagnostics do not include parameter,
model or economic uncertainty. Zero observed loss does not bound unseen tails.

Validation alone selects declared budget multipliers and feasible cash-anchor
blends. If a numerical solve fails, a fallback must pass its stronger pointwise
checks and is named fallback, never optimized. No candidate means no silent
substitution of a benchmark fan.

## Execution audit and W1

A separate cash-first units/cash ledger uses cash, then proportional listed
sales, then only scheduled property receipts. Arrears persist. Listed sale
proceeds are assumed spendable within the week, not verified settlement facts.
The audit is not a dynamic-policy optimizer or W1-certified execution policy.
It names observed unpaid calls and every date's paid-in-full fraction separately
from the model budget verdict. Missing audits are unavailable, not passed.

Tiny negative solver holdings within the existing1e-7 weight tolerance are
clipped only for the long-only execution arithmetic and disclosed in dollars;
no portfolio normalization or final-risk repair is performed.

The active W1 metric is max_path, invariant to duplicate-sleeve and repeated-date
representations. Radius0.00002 is a development placeholder, not statistically
calibrated. These are sufficient risk envelopes, not Meucci's minimax-regret
allocation, unrestricted robust exponential utility or a confidence guarantee.
See W1_METRIC.md, FINAL_EVALUATION.md and CASH_LEDGER.md for exact scope.

## Scientific evidence and rights

See SCIENTIFIC_STATUS.md and evidence/robustness-20261107/ for the frozen
19 annual holdouts, matched objectives,32-refit pilot,152 historical outer
refits, FHS, reduced sensitivity cases, failures and payout stresses. Source,
config and data hashes stay with each study. They are not recomputed merely
because a UI or helper changes. Bounded studies did not prove method superiority.

BOOK_AUDIT.md records the review against the user's Meucci book, including
printed/PDF page references, new diagnostic evidence, fixes and open limits.
The book PDF itself and third-party book pages are not committed or distributed.

Private use only; no GPL dependency, public hosting, client data or upstream
writes. The inherited archive, attribution and history remain. A new identity
or private fork does not settle inherited code/data redistribution rights.
