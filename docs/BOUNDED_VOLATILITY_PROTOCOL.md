# Prespecified bounded conditional-volatility study
7 November 2026. Private research. Frozen before new outputs. Default unchanged.

## Model: explicitly capped EWMA variance, Gaussian-mixture shocks
This is a new declared engineering specification, NOT ordinary GARCH, not a
replication of RiskMetrics and not a fitted cap. For each listed/FX factor,
let s_j^2 be the expanding-past shrunk covariance diagonal. Initialize h_j to
s_j^2, process the past log shocks centered on the common past shrunk mean,
and update h_next=clip(.94 h+.06 shock^2,.05 s_j^2,9 s_j^2).
The first52 past rows initialize the state without being scored. The baseline
variance scales, mean, correlation matrix and bounds freeze at each annual
origin. No future realized row enters a state/parameter estimate.

In simulation epsilon_t=D_t Gaussian(R) sqrt(V_t), D_jj=sqrt(h_j), with
V in{.75,3.25} probabilities{.9,.1}, shared across factors/property each week.
Only the realized simulated epsilon_t updates h_next. Returns are not clipped,
not Student-t and not finite-support. The conditional variance is bounded;
this changes extreme variance propagation and must stay visible.

Property keeps its existing annual dispersion/drift, same shared Gaussian
listed-equity latent factor plus Gaussian residual and common mixture state.
Property correlation is still an assumed latent-factor link, not an estimated
quarterly joint conditional model. Listed/FX covariance is D R D, where R is
fixed past shrunk correlation. Cash remains deterministic0%. No rent or sales.

Cap9 means a3x standard-deviation ceiling relative to the annual origin's
baseline; floor.05 means sqrt(.05)x. These are not calibrated truths. Cap4/16
are declared sensitivity checks, never winner selection. Decay.94 is inherited
weekly development setting, not a claim that the original daily RiskMetrics
recommendation directly applies to weekly data.

## Finite moments
The cap gives a uniform bound on every one-step conditional Gaussian-mixture
MGF for every finite linear exposure. Iterated conditioning bounds the
finite-horizon MGF by a finite product. This covers listed/FX/property log-price
linear combinations, hence their positive/negative finite power moments.
It is not the iid exact MGF formula and not a numerical-overflow guarantee.
Proof and independent hand/quadrature tests precede scientific runs.

## Weekly evidence, retrospective
No cap/decay model selection.2014-2018 is descriptive validation,2019-2025 is
final comparison;2008 development stress is separate. Exact normalized CRPS,
QLIKE,1/5% exceptions, squared residual lag, state bounds/hit frequencies and
all assetwise/yearly scores. Scales use common history through2006 only.
These dates have already been viewed: past-only is not blind preregistration.
Use paired weekly CRPS differences and exploratory20-week circular block2000
replicate interval,10/40 sensitivity, not formal economic coverage.

## Full-year funding checks
Primary current-snapshot run: models iid baseline and bounded cap9 train
separately, same seed/counts/property/means/EP/risk limits. Equal-weight,
cash-reserve and cash+fixed-property anchors plus CARA and same-constraint MV
are retained, including failed solves.100 training,200 validation per batch,
400 final per batch,2batches each in pilot; after measuring, a fixed larger
200/400/800x4 confirmatory run. No grid or tune-to-pass.
Validation selects the first blend fraction{1,.75,.5,.25,0} to the same cash
anchor passing BOTH iid and bounded-cap9 judges. Final independent sets under
BOTH laws test every frozen allocation; own-law pass is not cross-law pass.
FHS final law is additional model-risk sensitivity. No final-set repairs.
Cap4/16 final stress judges use the frozen portfolios, not reselection.

Cash-first execution audit and independent provisioning-budget judge are
reported separately. Nominal/stressed posterior probabilities and W1 envelopes
remain as in the existing evaluator. Report model-based funded fraction, not
empirical guarantee or statistically calibrated likelihood of full funding.
Default schedule12x$250k, funding allowance20%, loss limits unchanged.
Separate fixed frozen equal/cash-reserve/anchor portfolios also face two
counterfactual schedules: $95M atweek52, and$60M week4+$30M week52. These
are stress fixtures, not user obligations, never used for parameter selection.

Historical annual validation:19 common year-end origins2006-2024 yielding
2007-2025 outcomes, past-only listed/FX and assumed45-day property release lag.
Use100/200/400x2 tier after pilot estimate. Compare baseline/bounded candidates
on common actual histories and cross-law final judges, record all failures.
Actual listed paths are historical; property uses latest-vintage quarterly
index and publication-lag convention, not true revision-safe tradable prices.
Annual evidence small/dependent. No superiority by best average alone.
At4/13/26/52week endpoints, also score the simulated cumulative listed/FX log
return forecasts against actual held-out returns, using exact empirical-support
CRPS normalized by frozen initial weekly SD times sqrt(endpoint). This is a
multihorizon marginal diagnostic, not a joint path score or annual tail proof.
Pre-output addition: cash-reserve and equal-weight duplicates can be reported
once by unique weights but names remain explicit. Raw candidates and validation
blends remain distinct; failed numeric solves do not silently become optimized.
If resource limits prevent all19, report exact incomplete scope, no cherry pick.

## Tests, cost, delivery and release gate
Independent recurrence/clamp hand fixtures, large-shock bounds, exact zero
cash, same-seed and horizon-prefix invariance, future-perturbation exclusion,
conditional covariance/moment inequalities, explicit iid-MGF rejection,
unchanged-default regression and package integration checks. Green tests
before private push. Initial pilot then measured estimates before each batch,
no batch over30min and no multi-hour grid. Artifacts hold source/config/data
hashes, all bounds/hits, selection provenance and failures. ReportPDF/evidence.
No production default replacement, new risk allowance, spending, external
contact, publication, new package dependency or GPL. User chooses promotion.

Pilot cost plan recorded before execution: weekly score sweep is small vector
arithmetic, expected<5s, hard60s; current-snapshot pilot involves four solves
and five final laws, expected<30s, hard120s. Pilot is correctness/cost only,
not parameter selection. If either fails, fix implementation errors transparently
before completing the unchanged design; preserve failure text.
