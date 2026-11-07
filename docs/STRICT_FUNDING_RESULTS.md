# Strict funding and empirical radius results
7 November 2026. Private research only. Scientific code:7aa113e;
`artifacts/strict-funding-20261107/corrected/summary.json` records exact code,
source hashes, configuration and selection locks. Later presentation/input
validation changes do not rerun or tune final outcomes.

## What changed
- Optional `funding_mode=pay_all_99`: joint every-payment cash-first event,
  alongside original tail funding, loss and holdings checks.
- Reference exact one-sided95% Clopper-Pearson lower bound >=99%; separately
  require nominal and stressed weighted minimum-batch funded fractions >=99%.
  Weighted EP fractions are NOT binomial confidence bounds. Imported archives
  are refused: their independent-path assumption is not verified.
- Fixed candidate/anchor grid1,.75,.5,.25,0; first validation funding pass,
  not a global chance-constrained optimum. Existing optimizer still uses
  cumulative cash provisioning, not the selling ledger (#1 remains parked).
- Optional `radius_calibration_mode=past_empirical`: past-only annual blocks,
  exact max-path assignment half-splits, fixed90th percentile stress policy.
  No future-law confidence coverage claim and no radius truncation.
- Dashboard shows both verdicts, liquidity/CE grid and calibration conflicts.
  Mobile uses stacked cards; static/live controls share fields. Selection
  weights/configuration persist before any independent final draw.

## Bounded evidence
Corrected batch3.39s:100training,200validation/batch,400final/batch,4batches;
coarse pilot100/200/300x2. Default iid Gaussian mixture law, same seeds and
holdings. These are illustrative schedules, not user obligations.

|Schedule|Strict result|Separate final all-risk result|
|---|---|---|
|$3M in12monthly calls|Raw candidate;1600/1600 final fully paid; lower99.8129%|FAIL path loss, not repaired|
|$95M week52|No candidate; all5validation fractions fail|No safe substitute|
|$60M week13+$30M week52|90%cash+10%unsold-property anchor;1600/1600 final fully paid|PASS under fitted law only|

The95Mfixture paid-all validation rates are34.25%,19.25%,5.875%,0%,0%as cash
rises35.54%to90%. The anchor misses5M on every path. More cash is not always
monotonic when risky growth is needed to cross a funding threshold.
For the3Mmonthly case all validation fractions fund, while uniform-reference
cash-ledger terminal CE falls99.98M→97.38M as cash rises. These are not the
optimizer objective or economic return forecasts.

One path is one trial, not each asset/date. Zero misses needs at least299
independent generated paths to reach a99%one-sided95%lower bound. Conditional
on frozen fitted inputs/portfolio only. Validation calculation is a selection
screen, not post-selection coverage. No economic or W1 cash-ledger guarantee.

## Radius findings
21complete52week blocks through2026-10-30 yield radius0.4067441129520647.
At95%CVaR this entails813.488M unavoidable buffer on100Mwealth against the
smallest50kmonthly-payment budget. No candidate is returned; no cap is applied.
2006-2012snapshots have<8blocks and remain unavailable.2013-2024all have8-19
blocks and radius~.393-.628; all conflict with budgets. The manual default
remains.00002. Latest-vintage quarterly property uses assumed45day release lag,
not revision-safe vintages. Deterministic observed cash/liabilities do not
establish that future uncertainty is zero. The current unrestricted-support
W1envelope needs economic support/metric redesign and stronger calibration
before this can become a useful confidence policy. Reducing the radius until
something passes would hide the conflict.

## Validation and preserved errors
349tests pass,3recorded warnings. Independent binomial/assignment oracles,
joint-date/weighted/archive/sample-size checks,95Mfailure, default preservation,
representation invariance, cutoff exclusion. Wheel installed/run outside source.
Live strict/radius controls and full-config endpoint verified; desktop/320px
and static layouts inspected with no JS error or document overflow.

Initial counterfactual output labels were INVALID: default recurring payments
expanded over the intended schedule. Originals are preserved and marked invalid;
corrected fixtures clear recurring_payout. A final printing-only ndarray JSON
error occurred after the initial summary had saved; corrected. Mobile table
overflow was fixed with cards. No failing final judge was tuned or rerun away.

Sources read:
- https://search.r-project.org/CRAN/refmans/GenBinomApps/html/clopper.pearson.ci.html
- https://support.minitab.com/en-us/minitab/help-and-how-to/statistics/basic-statistics/how-to/1-proportion/methods-and-formulas/methods-and-formulas/
- https://arxiv.org/pdf/1809.00210
- https://link.springer.com/article/10.1007/s10107-017-1172-1

Default law, funding mode, radius, budgets and fixed property remain unchanged.
No client data, spending, public sharing, external contact or upstream change.
