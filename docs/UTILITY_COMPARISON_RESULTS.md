# Utility comparison findings
7 November2026. Lead case: user confirmed250k/month,12modeled payments total3M.
Approximate weekly due dates and the100Mresearch balance sheet are not full
client calibration. Other monthly sizes are sensitivities. Extreme fixtures
are CHECK STRESS TESTS, NOT the user's payments. No default changes.

## Side-by-side definitions
G=terminal marked wealth; L=terminal value of payments; X=G-L; W0=initial
wealth100M; T=10M; S0=W0-L. All objective parameters were fixed before results.

|Preference|Definition|Parameter|Rewards / ignores|
|---|---|---|---|
|CARA surplus|-exp(-X/T)|T=.1W0|Surplus; constant dollar aversion, no special floor curvature|
|CRRA gross|(G/W0)^(1-g)/(1-g)|g=W0/T=10|Relative aversion on gross wealth; obligations only in constraints|
|HARA payment floor|((G-L)/S0)^(1-g)/(1-g)|g=S0/T=9.7 for3M|Surplus near payment floor; undefined at/below it|
|Kinked shortfall|X/W0-4max(-X/W0,0)|downside/upside slope5:1|Extra shortfall penalty; risk neutral above target|

Use log for g=1. HARA(G,L,g) IS CRRA(X,g) up to scaling. Do not subtract L
twice or claim the families are disjoint. Gross/native and surplus/native CEs
are not common ranking scores. Common comparisons below use CARA-net-ledger CE.
The kink is concave, not S-shaped prospect theory.

## Confirmed250k/month: same-path results
100train/200validation/400final x4. Same paths/EP/risk budgets/holdings and
all-risk+strict joint-payment judge across all four utilities. Frozen finite
blend grid; selection saved before final draws; no final repair.

|Preference|IID cash|IID common CE|Bounded cash|Bounded common CE|
|---|---:|---:|---:|---:|
|CARA surplus|76.39%|98.253M|72.82%|98.693M|
|CRRA gross|76.39%|98.253M|72.82%|98.693M|
|HARA payment floor|76.39%|98.253M|72.82%|98.693M|
|Kinked shortfall|76.71%|98.247M|72.82%|98.693M|

Every selected row uses25%candidate/75%anchor, pays all on1600/1600final
reference paths, lower95%bound99.8129%, and PASSES final all-risk checks.
Raw portfolios FAIL path loss and remain visible. Native domain failures:0
for the confirmed plan. No utility winner is established: hard constraints
and the fixed validation grid mostly dominate. These CE differences are not
economic forecasts or a law/model-selection criterion.

## Monthly sensitivity, not obligations
Additional500k/1M/2.5Mmonthly (2x/4x/10x,6M/12M/30Mtotal) was prespecified
after the user's23:00:49scope clarification, before those outcomes. Every
utility again selects25%candidate, passes final all-risk under each law,
funds1600/1600reference paths and has0observed power-domain violations.
IID common net CE ranges95.247-95.253M /89.247-89.253M /71.247-71.253M;
bounded95.693M /89.693M /71.693M. Not a maximum-affordable-payment result.

## Check stress tests, not realistic user scenarios
90Msplitweek13/52: all preferences select90%cash+10%property anchor, pass
final judge. Raw HARA has2/1600nonpositive-surplus final paths under each law,
so raw native CE is unavailable.95Mfinal: no preference has a validation
candidate; anchor misses5M on EVERY path. Raw HARA native CE unavailable,
30/1600IID and23/1600bounded domain violations. No clipping.

## Execution and limits
48/48solves optimized with CLARABEL; no solver fallback/formulation failure.
Primary6.80s, sensitivity7.74s.356tests pass with3recorded warnings, including
CE/aversion/identity/domain/kink tests and3independent two-asset grid oracles.
Training power-domain margin is explicit1dollar at100Mwealth; finite-sample
positivity does not establish all-support admissibility. Final native CE is
absent at/below floor, not repaired. Utility CE uses provisioning; common
comparison uses cash-first ledger. No client preference estimation, economic
99%guarantee, dynamic optimization, costs/settlement/tax calibration.

Dashboard research/science has a fixed12-case snapshot, law/schedule filters,
side-by-side definitions/parameters/current and raw outcomes/domain failures,
common-vs-native CE labels and the honest takeaway. It does NOT recompute when
current inputs change. A separate current-objective selector runs the labelled
alternative and displays independent-final native CE/domain failures. CLI,
static and live use shared data. Default remains CARA/tail_allowance/manual
radius; no property, risk-budget or annual-law promotion.

Sources:
- Meucci2005, printed272-274, user-provided textbook; no pages redistributed.
- https://arxiv.org/pdf/1809.05961
- https://ar5iv.labs.arxiv.org/html/1501.07480
- https://toddbwalker.com/HMW_Disparity.pdf
- http://aeconf.com/Articles/Nov2000/aef010202.pdf
- https://www.cvxgrp.org/cvx_short_course/docs/applications/notebooks/portfolio_optimization.html
- https://stanford.edu/~boyd/papers/pdf/cvx-finance-slides.pdf
