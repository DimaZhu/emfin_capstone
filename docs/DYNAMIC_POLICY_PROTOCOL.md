# Dynamic execution-policy experiment
7 November2026. User23:09:49asks for mathematical optimization, not a
bucket/playbook. The only confirmed payment amount is250k/month. Other
inputs remain research assumptions; no trade, default or account mutation.

## Formulation and scope
Finite-horizon constrained stochastic control:
    maximize CE_T(X_H) = -T log E[exp(-X_H/T)], T=.1W0
    controls measurable using observed state only; joint paid-all target99%.
State: liquid units, settled cash, pending sale receipts, marked unsold
property, arrears, remaining schedule, observed prices and past returns.
Actions: desired sleeve dollars, clipped long-only; sell overweights, then buy
underweights with SETTLED cash only. No borrowing or property sale. All due
payments debit cash; arrears persist. X_H includes cash/units/property/pending
receivables minus arrears. Payments already deducted, never deducted twice.

The production ledger assumed immediate listed settlement. This experiment
adds explicit proportional per-trade fees and weekly settlement queue. Existing
net unit-price haircuts are not charged again. Central fee5bps each way and
one-week sale settlement are declared assumptions, NOT broker evidence; check
0/10/25bps and0/2week delay. Weekly data cannot certify actual day-level
settlement. Pending sale receivables are nominal fixed cash, not market risk;
buys instant only from settled cash, fees burn wealth, no margin/netting.

## Tractable causal policy class, no global-optimum claim
Four risky liquid sleeves +cash; fixed initial10%property, no ongoing rebalance
of property. A policy maps observed funding/market state into softmax liquid
weights. Four risky logits relative to cash are intercepts plus:
- shared beta_f*(current liquid wealth/initial liquid wealth-1)
- shared beta_l*(remaining obligations/initial liquid wealth)
- shared beta_d*(equity price / observed running maximum-1)
- beta_m*each sleeve's observed trailing4week log return.
All features are known at decision time. At time0, features use initial prices,
not the first future weekly observation. Decision weeks0and the modeled
payment weeks shifted back by the configured sale-settlement lag. This is an
approximation to monthly decisions, not calendar-level implementation.

Eight learned parameters:4intercepts in[-8,8],4slopes in[-4,4]. Cash logit0.
Softmax targets can learn any initial liquid mix (within bounded logit range),
not an imposed months-of-cash target. Training parameters use deterministic
seeded differential evolution, population40,8generations (<=360evaluations),
no polishing. Two initial seeds:static CARA raw and its previously all-risk
validated25%blend, both translated to logits with zero slopes. Remaining
population uniformly seeded in parameter bounds. Same raw-return paths.

Training criterion: maximize reference CARA-ledger CE minus explicit penalty
100W0*(mean unpaid due amounts/W0 + max(0,unfunded_fraction-.01)
+ sum of risk-limit excesses in normalized dollars). This is a SEARCH score,
not exact chance-constrained optimality or a calibrated Lagrange multiplier.
Save every candidate. Select highest CE among the TRAINING feasible evaluated
policies only (joint fraction>=.99, dated tail gaps and shadow path/terminal
tails within original budgets), else no candidate. Validation then screens
frozen training candidates in descending training CE; select first all-risk
and strict pass. Never tune using final outcomes. If none, retain failure.

## Fair baselines, judge and interpretation
Same initial holdings/costs/draws: frozen portfolio with cash-first pro-rata
sales, proportional withdrawal of every liquid sleeve, and static target
monthly rebalancing. Initial holdings for primary comparison:the existing
validation25%blend, not independently optimized for this new policy. A
separate jointly-optimized initial mix experiment may follow, but not conflate
allocation with control. Dynamic candidates' first action IS a trade; all
baselines permit the same decision times and charge the same fees.

Dynamic risk judge uses executed net wealth PLUS cumulative paid withdrawals
accrued at cash as a shadow total-wealth path (pending receivables included).
This lets identical tail definitions apply to ALL dynamic/baseline policies;
it is NOT silently the old static gross-price path. Dated shortfall losses
are actual ledger arrears, not static provisioning gaps. Same confidence,
budgets, reference/nominal/stress measures, Bonferroni batch bounds and joint
all-date CP/weighted screens. Strict CP on final frozen independent generated
paths only. Ledger accounting differences remain explicit.

Stage1:deterministic accounting/no-lookahead tests and exact2period2asset
Bellman discrete-control oracle. Global optimum ONLY in that tiny fixed model
and enumerated action grid; full5liquid-sleeve policy result has no certificate.
Stage2:100training paths,200validation/batch,400final/batch x4, same seeded IID
and boundedcap9 laws; optimize nominal IID class first, validate both laws,
freeze then final judge. Fixed sensitivity drifts+-2pp/year, covariance scale
.8/1.2,fees/settlement and W1-informed adverse shocks are diagnostics, not a
nonlinear-ledger W1certificate. No confidence ball or universal-best claim.

Initial pilot <=40candidate evaluations, timing estimate before batch; full
search wall budget180s, study300s, no batches>30minutes. Preserve failures and
report if a trivial cash/static policy matches or wins. Provide CE difference
and MC error, turnover, costs, settlement misses, payment rate/CP, all-risk
outcome. This is retrospective simulation, not proof of economic superiority.

Before pilot/results: validation compute is capped to the top12training-feasible
candidates by trainingCE, plus separately labelled baselines. This limits the
policy class actually compared; it is not a global optimum certificate. A
legacy W1 additive reserve is retained as an explicitly heuristic stress
screen for shared dynamic judgment, never represented as a nonlinear policy
DRO bound. Both raw empirical tails and the reserve are reported separately.

## Post-result attribution diagnostic (not selection)
The primary final results were seen before this addition. To distinguish
changing the initial target from valuable later feedback, add two comparators
DERIVED FROM THE FROZEN selected policy's first action: apply its same time0
trade, then cash-first only; and fix that initial target for later monthly
rebalancing. Same original paths/costs/judge, no parameter or policy reselection.
This is post-hoc attribution, not a fresh confirmatory test. Preserve original
summary unchanged and save these diagnostics separately. Paired CE difference
uncertainty uses frozen per-path outcomes, not an independent economic interval.

## Prespecified robust variant, after primary/attribution results
The primary -2ppdrift failure and post-hoc attribution were already seen.
This extension is exploratory model redesign; it is not a confirmatory test
of the original policy. New training/validation/final seeds use original base
seed+200000/+210000/+220000; no original final paths reused or selected.
Fixed model set:IIDnominal, boundedcap9nominal, IIDlisteddrift-2pp/year,
and IIDdrift-2pppluscovariancex1.2. Other assumptions unchanged. This finite
set is NOT a confidence region for the economic law or W1robust optimization.

Same8parameters/bounds/360evaluations. Training objective is WORST-law CE
plus100times WORST-law constraint-violation penalty. Training-feasible means
pass the declared training screens under ALL4laws. Rank by worst-law CE;
validate top12unique candidates across ALL4validationlaws; first passing
all-risk/strict judge is frozen, else no candidate. Initial population includes
the original trained feedback, its time0-equivalent static target and original
initial holdings, remaining members use a fixed new seeded uniform draw.

Fresh final comparisons are frozen before final generation:original starting
cash-first, pro-rata, static monthly target; original feedback and its same
first-action-only comparator; robust feedback and its same-first-action-only
comparator. All initial wealth/holdings/costs/draws/judge match. Report joint
all-payment rate, all-risk under every law, common ledgerCE/cost/turnover,
paired4batchCEdifferences. If robust feedback equals/loses to its static
first-action comparator or matches cash-first, say so. No final repair.
Preserve all earlier results and source/selection locks.360evaluationsx4laws,
search budget180s, whole study300s; estimate before execution.

## Post-result sample relaxation bound, not an executable policy
After the robust search failed validation, add an analytical diagnostic only:
remove nonanticipativity, all trading fees/delays, loss limits and monthly
frequency restrictions. Each week a clairvoyant liquid portfolio invests in
the next realized best gross-return sleeve (including free unit cash), pays
the fixed liability; property units stay fixed. Induction gives a PATHWISE
upper terminal wealth bound for every admissible experimental policy. Its
sampleCE is an upper bound on the sample utility problem, not an implementable
strategy or a confidence bound on the true-law optimum. A large gap explicitly
means no near-optimality certificate. This does not select/change any policy.

## Rebalancing frequency follow-up, frozen before new paths

User request 7 Nov 2026 23:17 Singapore: compare monthly, quarterly,
semiannual and annual rebalancing. Fixed target = the original common starting
holdings, not the learned time-zero target. All retain 12 monthly 250k payments,
unsold 10% property, 5bps per buy/sell, one-week settlement and the same judge.
At time zero and months k=1..11 divisible by the frequency, rebalance the liquid
portfolio. Execution is one week before the modeled month boundary so receipts
can settle. At all other monthly decision dates use cash-first funding. There
is no gratuitous end-of-horizon rebalance. Annual thus means hold over the
one-year window, not evidence for multi-year annual rebalancing.

No new fitting. Four already fixed return laws from robust extension. Fresh
4x200 validation paths with offset310000; select highest worst-model CE among
frequencies passing all four laws, ties under $100 labelled practically tied.
Then freeze before fresh 4x400 final paths with offset320000. Compare all four
on shared paths within each law. Report paired4batch MC intervals only as
conditional diagnostics, not economic confidence or global horizon proof.
Compute budget 60seconds. This is a new exploratory question, not a repair of
the failed feedback search. Frequency is conditional on this unusually
cash-heavy starting target and one-year horizon.
