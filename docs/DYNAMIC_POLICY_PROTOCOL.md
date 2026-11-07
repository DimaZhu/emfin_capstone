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
