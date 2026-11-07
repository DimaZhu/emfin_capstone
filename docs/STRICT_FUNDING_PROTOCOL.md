# Strict all-payments mode and past-only radius calibration
7 November2026. Approved research priorities#2/#5. Default remains tail allowance
and manual radius. Fixed property/sale policy unchanged; optimizer still uses
provisioning. No dynamic or cash-ledger optimizer added (#1parked).

## 99% all-payments mode
`funding_mode=pay_all_99` adds a CASH-LEDGER joint event: every dated payment
paid within$1e-6 roundoff, on at least99%of modeled paths. Not one separate99%
test per date, not a tail-size allowance. Existing tail funding/path/terminal
budgets stay in force alongside it. This screens a fixed finite candidate grid,
not a global chance-constrained optimum. Candidate+cash/fixed-property anchor
fractions1,.75,.5,.25,0; select first satisfying existing validation funding
budgets, joint-event reference lower bound and nominal/stressed weighted rates.
No property holding or obligation change to make infeasible cases pass.

One-sided95%Clopper-Pearson bound applies ONLY to unweighted, independent
GENERATED final scenario paths conditional on the frozen fitted model/inputs
and fixed validation-selected portfolio. The same calculation on validation
is a conservative screen, not post-selection coverage. Archive/IID assumptions
must not be hidden. Joint assets/dates within a path are NOT separate trials.
EP-weighted rates are descriptive model estimates, not binomial observations.
Require their minimum nominal/stressed rates>=.99 as a separate screen.
Nothing here certifies99%economic or W1-robust cash-ledger funding. Current
W1CVaR envelopes do not apply automatically to a discontinuous chance indicator
or nonlinear cash ledger. This limitation stays in UI/JSON/report. Final
all-risk pass also requires the separate existing loss/holdings/W1 checks.

Tradeoff curves use the SAME frozen candidate/anchor fractions on validation
paths: cash share vs modeled paid-all fraction and net terminal CE. No final
selection, cap/risk-limit tuning or monotonicity promise. The$95Mcall can be
infeasible with10%unsellable property:90%cash leaves5Munpaid. Display failure,
never force a candidate or call its benchmark safe. UI default is unchanged.

## W1 radius calibration, optional and explicitly empirical
`radius_calibration_mode=past_empirical` forms nonoverlapping52week historical
path blocks using ONLY observations through each fit cutoff. Include marked
and spendable primitive prices, actual listed/FX, latest-vintage quarterly
property under45day release-lag convention. Deterministic liabilities/cash mean
no observed liability/cash displacement; this does not prove no uncertainty.
At least8complete blocks;64fixed-seed balanced random half-splits, each exact
uniform empirical max_path Wasserstein assignment distance; choose the90th
percentile. This is a declared empirical distribution-shift stress policy,
NOT statistically calibrated confidence coverage or a claim about the true
full future law. Half-split distances are not independent economic samples.
No scaling down to make budgets feasible. Report number/dates,distances,
selected radius, dollar reserve and unavoidable funding-budget conflict.

Retrospective annual calibration snapshots use expanding past-only2006-2024
cutoffs, preserving unavailable early years. Show what remains unresolved, not
zero-radius fallback. Existing defaultmanual.00002 stays until user decision.
No radius choice based on final allocation utility or pass/fail. Recompute
primitive histories after UI property/FX/cost assumptions change.

## Planned evidence and tests
Independent Clopper-Pearson allsuccess formula and binomial inversion, all-date
vs per-date fixture, weighted-rate caveat, archive refusal, funded95Mfailure,
reference paths<299allfull insufficient99%at95%, validation/final separation,
unchanged default and fixed property. Radius exact two-point transportation,
duplicate sleeve/repeated-time invariance, future-data exclusion, incomplete
block refusal, no cap-to-feasible truncation. UI and slider/static/live parity.
One current tier100/200/300x2 then4batch diagnostic100/200/400; fixed fixtures
3M,95Mfinal,60Mearly+30Mfinal. No user obligation inference. Pilot estimates
before batches, no batchover30minutes/no spend/contact/public sharing.
