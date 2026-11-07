# Conditional-volatility comparison: useful evidence, not a model release

7 November 2026. Private research. No allocation, production default, risk
budget or funding requirement changed. Read MODEL_ADEQUACY_PROTOCOL.md first.

## Result

The conditional GARCH-variance/fixed-mixture candidate selected on 2014-2018
validation forecasts scored better than the iid-mixture baseline on 2019-2025
one-week marginal forecasts. Mean normalized CRPS fell from 0.675607 to 0.663306,
a 1.82% relative reduction. Smaller is better. It beat the baseline in each of
the seven calendar years and each of the five asset-average point scores.
This is evidence for conditional-variance modeling, not proof of superiority
in the annual portfolio engine or a license to promote this candidate.

A key mathematical blocker remains: unbounded Gaussian GARCH/EWMA recursion
with positive ARCH feedback can give infinite exponential price moments over
three weeks despite finite one-week moments. The independent derivation is in
CONDITIONAL_PRICE_MOMENTS.md. No recursive GARCH path generator is installed.
The existing iid finite mixture and empirical EWMA-FHS defaults/competitors
are unchanged. A hidden volatility cap is not used to make this problem vanish.

## How this differs from the earlier portfolio study

This study forecasts only weekly marginal log returns for VTI,VWO,GLD,IEF and
USD-per-SGD. It does not optimize allocations, compare investment profits,
model weekly property observations, apply EP stress, validate cross-asset
joint tails or establish annual all-payments-made probabilities.

Parameters/means are refit on expanding past history at each calendar-year
start. Conditional variance states update only after each observed week has
been scored. Four fixed model classes were committed before the score runs.
One validation-selected class was saved before final scoring. The initial
2005-2006 per-asset scale is frozen so each asset has equal primary-score weight.

The calendar periods were already inspected in earlier work. Thus these are
mechanically past-only forecasts with a fixed retrospective protocol, not
blind independent preregistration. In later final years, annual refits can use
outcomes already observed in earlier final years, but model class is not reselected.

## Fixed-model comparison, final 2019-2025

|Forecast|Normalized CRPS|QLIKE|1% exceptions|5% exceptions|
|---|---:|---:|---:|---:|
|iid mixture|0.675607|1.387168|18 /1825|71 /1825|
|EWMA mixture|0.665920|1.296088|35 /1825|107 /1825|
|GARCH variance + mixture|0.663306|1.231433|21 /1825|101 /1825|
|EWMA empirical FHS|0.665087|1.296088|25 /1825|90 /1825|

There are365 weekly dates and five correlated assets, not1825 independent
time observations. CRPS measures distribution forecasts, not returns earned.
QLIKE uses noisy squared mean-forecast residuals, not directly observed true
conditional variance. EWMA mixture/FHS have identical variance states, so
identical QLIKE is expected; their different CRPS comes from different shapes.

Validation normalized CRPS was0.574018 EWMA-mixture,0.573587 GARCH-mixture
and 0.574723 EWMA-FHS. The small validation difference is itself a warning
against treating the chosen class as settled. The iid baseline was not an
eligible replacement candidate; all methods are still shown in the final table.

For the locked candidate minus iid baseline, the paired weekly asset-average
normalized CRPS difference is-0.012301. Exploratory circular-block 2000-draw
percentile intervals:

|Block length|Descriptive 95% interval|
|---|---|
|10 weeks|[-0.020025,-0.006124]|
|20 weeks, primary|[-0.019437,-0.005627]|
|40 weeks|[-0.019734,-0.005936]|

Negative favors the conditional candidate. These intervals preserve paired
weeks and cross-asset averaging, but are not selection-adjusted, formally
validated economic confidence intervals or protection against model/regime bias.

## Clustering improved, tail adequacy not established

|Series|iid squared standardized lag1|GARCH squared standardized lag1|GARCH 5% exceptions|GARCH 1% exceptions|
|---|---:|---:|---:|---:|
|VTI|0.373|-0.029|20 /365|4 /365|
|VWO|0.371|0.090|21 /365|3 /365|
|GLD|0.158|0.081|21 /365|4 /365|
|IEF|0.177|0.095|23 /365|5 /365|
|SGD/USD|0.267|0.053|16 /365|5 /365|

At nominal 5% and 1%, expected counts per asset under an ideal model would be
18.25 and 3.65, but small dependent counts are not a probability certificate.
The iid baseline's pooled 3.89% 5%-exception rate hides very different asset
counts:14,7,10,31,9. A convenient pooled rate is not full calibration.
PIT histograms and exception-transition/run counts are retained, without a
p-value parade or simple iid/PIT pass label. Marginal calibration does not
establish correct dependence, joint tails or annual crisis behavior.

## Stress slices and failures stay visible

The 2008 slice is descriptive development evidence only. Its 5% pooled exception
rates were 21.54% iid and 13.85% GARCH; the GARCH rate is still far above 5%.
EWMA-FHS was 8.85% and EWMA mixture 10.77%. No candidate handled that crisis
as if the nominal tail frequency were reliable. Do not bury this behind the
better 2019-2025 average.

In 2020 the iid/GARCH 5% rates were 7.69%/8.46%; in 2022 they were 9.62%/6.92%.
GARCH had lower CRPS than iid in each, but a lower general score does not
mean every tail statistic or every stress slice improves.

2007 had only94 common past weeks, below the fixed104-week GARCH minimum.
The first development run aborted on that condition. The runner was then
improved to record unavailable years rather than aborting, and to withhold
comparative summaries if any required year or method is incomplete. The
minimum, forecasts, scores and selection were not changed. Development 2008-2013
completed with 2007 explicitly unavailable. Earlier validation/final outputs
remain byte-preserved at their original clean4be65c0 implementation basis.

All25 validation and 35 final marginal GARCH fits succeeded, all three fixed
starts in each case. All30 available development fits also succeeded. Solver
bound-step clipping warnings were saved; this is an internal SLSQP proposal
mechanism, not permission to accept out-of-range final parameters. Recursion,
unit-scaling and past/future invariance have independent tests.

## What improved and what comes next

- Exact marginal mixture/empirical-support CRPS and a locked-selection runner.
- Past-only annual refits and sequential variance states, with an explicit test
  that changing later returns cannot change earlier predictions.
- Independent integrated-CDF and pairwise-CRPS oracles, variance recurrence hand
  checks, parameter scaling, missing-model failure tests and moment-domain check.
- A reproducible record of protocol, code/data/source hashes, every forecast,
  every optimizer start, failed 2007 run, selection lock and score/CI evidence.
-332 tests pass; production model and original portfolio evidence are unchanged.

The next modeling step would need a prespecified conditional annual model with
a defensible finite-moment domain, then joint listed/FX/property dependence,
multihorizon forecasts and untouched executable-policy/funding evaluation.
Do not automatically install the one-week GARCH winner. Cash carry, property
vintages/publication, actual settlement/costs and W1 radius calibration also
remain open. None of these forecast results turns a 20% shortfall allowance
into a full-funding promise.

## Sources used

- Meucci, *Risk and Asset Allocation* (2005), user-supplied book. Printed
  pp.103-105,123-125,233-234; PDF pp.125-127,145-147,254-255. Invariance,
  projection and conditional-variance context. No PDF pages redistributed.
- Gneiting & Raftery(2007), proper scoring rules, exact CRPS and discrete support:
  https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting 2007jasa.pdf
- Patton(2011), QLIKE and noisy variance proxies, with conditional-unbiasedness
  qualifications:
  https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf
- Bollerslev(1986), GARCH recursion and stationarity, not an annual exponential-
  price moment guarantee:
  https://public.econ.duke.edu/%7Eboller/Published_Papers/joe_86.pdf
- Gneiting, Balabdaoui & Raftery(2007), calibration/sharpness and PIT limits:
  https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting 2007jrssb.pdf
- Official arch forecast documentation, timing/analytical/simulation distinction:
  https://arch.readthedocs.io/en/stable/univariate/forecasting.html
- Federal Reserve, historical-simulation cautions:
  https://www.federalreserve.gov/Pubs/feds/2001/200127/200127pap.pdf

All public sources fetched and read. No source code copied or new package/GPL
dependency added. Everything stayed private; no spend, contact or public hosting.
