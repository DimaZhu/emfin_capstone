# Prespecified utility comparison
7 November2026. No default change. All definitions and parameters below are
frozen BEFORE the utility-comparison outcomes are computed. Existing annual
and strict-funding results were already seen; this is retrospective research,
not a fresh economic holdout or an estimated client preference.

## Wealth arguments and parameters
Let G be terminal marked wealth under the existing provisioning convention,
L the terminal value of all scheduled payments at the cash rate, and X=G-L.
CARA currently uses X. Never put L as a floor on X again: that double counts.
All optimization arguments are scaled by initial wealth W0 for numerics.

Four PRIMARY labels, not four disjoint mathematical families:
1. CARA-surplus: u(X)=-exp(-X/T), current T=.1W0 (Balanced).
2. CRRA-gross: u(G)=(G/W0)^(1-gamma)/(1-gamma), gamma=W0/T=10;
   log when gamma=1. This is the total-wealth benchmark in the proposed
   comparison; it ignores payments IN THE OBJECTIVE, not in constraints.
3. HARA-payment-floor: shifted power u(G)=[(G-L)/S0]^(1-gamma)/(1-gamma),
   S0=W0-L0; gamma=S0/T, where L0 is deterministic scheduled payments grown
   at the stated deterministic cash rate. This matches initial local dollar
   absolute aversion to CARA/CRRA-gross at G=W0, when S0>0. At3M/90M/95Mtotal
   payments and zero cash rate, gamma=9.7/1/.5. These are mechanical matching
   rules, not fitted preference estimates. If S0<=0, report unavailable;
   never replace gamma with an invented positive number. Domain X>0.
4. Kinked-shortfall: u(X)=X/W0-4*max(-X/W0,0), so the marginal penalty below
   the payment target is5times the upside slope. Concave piecewise linear,
   not S-shaped prospect theory and not a probability-of-payment guarantee.

HARA(G,L,gamma) is EXACTLY CRRA(X,gamma) up to a positive affine
normalization. Test/report that identity explicitly. Changing gross to net
wealth is the economic distinction, not the HARA family name. If one meant
CRRA already on net wealth with the same gamma, HARA would not be a distinct
alternative. CEs across gross/surplus arguments are not directly comparable.

Power utilities: positive argument on EVERY training reference path, with
explicit numerical domain margin1e-8W0 (=$1at100M). No clipping or replacing
negative outcomes. A finite training domain does not prove model-support
admissibility; on final or historical paths at/below zero report native CE
unavailable and violation counts. No final domain repair or silent floor.
Use logsumexp inverse power CE to avoid overflow; report nonfinite scores.

## Shared study and judge
- Same actual-input past fit, same training/validation/final generated return
  arrays and nominal/stress EP measures, fixed10%unsellable SGproperty, zero
  rent/cash rate, no holdings/budget/default changes.
- Primary current law iid Gaussian scale mixture. Bounded annual variance
  cap9 is a fixed second judge/model sensitivity, not selected by results.
- Three illustrative schedules: default3Mmonthly,60Mweek13+30Mweek52,
  95Mweek52. Explicitly clear recurring schedule for counterfactuals.
-100training,200validation/batch,400final/batch,4independent batches; same
  seed20261107and disjoint+1000/+10000validation/final offsets for every
  objective. These are bounded diagnostics, not empirical forecasts.
- Frozen grid1,.75,.5,.25,0candidate+cash/fixed-holdings anchor. Select first
  candidate passing SAME validation all-risk judge AND strict joint payment
  screen. Preserve raw and selected variants distinctly. Raw solve/domain
  failure has no safe fallback label, but may still evaluate the declared
  anchor as a separately labelled comparator. No global chance optimum.
- Persist weights, configurations, objective/domain and validation trials
  before final draws. Final judge uses existing funding/path/terminal/holdings
  diagnostics AND strict screen. No final repair/model/radius selection.
- Common comparison columns: same-law final reference paid-all fraction and
  binomial bound, all-risk pass/breaches, cash share, net ledger mean/quantiles,
  common CARA-net-ledger CE at T=.1W0, plus each native utility CE with explicit
  argument/domain. Raw expected-utility numbers are NOT cross-family scores.
- Report sampling/solver status, domain violations and failed formulations.
  Include in findings and dashboard science view: definition, rewards/omissions,
  parameters, same-path results, numerical failures and honest takeaway.

## Tests and bounded compute
Hand CE inversion, HARA/CRRA-surplus identity, local Arrow-Pratt match,
translation/scale/Jensen properties where valid, negative/singular domain
refusal, kink slopes/concavity and a brute-force2asset oracle. Defaults and
CARA results preserved. Whole study wall budget300s checked between solves;
existing per-solver60s caps. Estimate before batch. No batch>30minutes,
public sharing, client data, spending or third-party contact.
