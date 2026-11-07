# Prespecified retrospective forecast protocol,7 November2026

Owner approved a past-only model-adequacy and conditional-volatility comparison,
not a better allocation. Protocol frozen before the study outputs are run.
Production defaults, risk limits, holdings and original final portfolio judge
are not changed. This is a one-week marginal forecast study, not an annual
funding or joint multivariate validation claim.

## Data and split

Pinned common weekly log total returns: VTI,VWO,GLD,IEF and USD-per-SGD, cash
excluded as deterministic. No synthetic weekly property or private client input.
Data before each forecast only; mean/variance parameters refit once at the start
of each calendar year using expanding history through the prior observation.
Within each year, variance state may update only AFTER the observed return is
scored. No observation trimming, event-year removal or post-result retry grid.

- Initial fit/scaling: all available common rows through2006-12-31.
- Descriptive development:2007-2013, including2008. These years cannot be
  described as new unseen stress evidence.
- Validation selection:2014-2018, lowest equal-asset mean normalized CRPS among
  three conditional candidates; deterministic method-name order breaks ties.
- Final comparison:2019-2025. The chosen conditional candidate and study settings
  are locked in a saved file BEFORE computing final scores. All competitors
  remain visible. An annual refit can use earlier observed holdout outcomes,
  as a real prequential forecast would, but cannot reselect the model class.

These dates/data were already viewed in earlier project development. Exclusion
from a mechanical fit or selection stage is not genuinely blind preregistration,
and it does not remove researcher's retrospective selection or data-vintage bias.

## Fixed competitors

1. iid_mix: current iid Gaussian-scale mixture, probabilities0.9/0.1 and
   variance scales0.75/3.25, fixed covariance within an annual refit.
2. ewma_mix: same marginal mixture shape, but EWMA variance, decay0.94, warm-up
   first52 past rows. Centering follows the existing EWMA filter's warm-up mean.
3. garch_mix: Gaussian-QML GARCH(1,1) conditional variance with positive omega,
   alpha>=0,beta>=0,alpha+beta<=0.999. Three fixed starts,<=200 optimizer
   iterations each, all statuses saved. QML variance fit is NOT mixture maximum
   likelihood. Predictive innovations use the same fixed mixture shape. No
   leverage/asymmetry term is fitted; no post-result model additions.
4. ewma_fhs: existing EWMA filter, decay0.94, frozen standardized empirical
   residual rows from that year's training window. Marginal scores evaluated
   exactly on its empirical support, no Gaussian-kernel density invented.

All four use the SAME current shrinkage-based mean estimate refitted on past
rows (FX zero log drift). This isolates variance/innovation differences, not a
search for the best mean forecast. The EWMA/FHS empirical variance state is
identical and forecast means are shared. GARCH fitting rescales return units
for numerical conditioning without changing the objective. A failed annual
GARCH fit makes that comparison unavailable for that year and disqualifies its
validation selection; failed cases are never silently removed from an average.

## Scores and diagnostics

Primary score: negative-orientation CRPS (lower is better), exactly evaluated
for each Gaussian mixture or empirical residual distribution. Divide by each
asset's standard deviation estimated only in the initial fit period and freeze
that scale for all dates. Average assets equally per week, then average dates.

Secondary: QLIKE = log(forecast variance/initial variance) + squared mean
forecast error/forecast variance. Squared weekly return residuals are a noisy
variance proxy; unknown conditional means and model errors limit QLIKE's
interpretation. Do not call realized squared returns the true variance.

Report assetwise1%/5% lower-tail exception counts/rates, quantile pinball loss,
PIT histogram, out-of-sample standardized squared-return lag correlations,
annual scores and2008/2020/2022 slices. No exception-rate-only model selection,
ES-only scoring shortcut, unadjusted parade of p-values or claim of economic
coverage. Finite-support FHS has discrete PIT/support limitations and no
comparable Lebesgue log-density score, so log score is not the primary metric.

A saved validation winner is compared with iid_mix on2019-2025 using paired
weekly asset-average score differences. Exploratory circular moving-block
bootstrap,20-week blocks,2000 draws, fixed seed20261107. A prespecified10/40
week block sensitivity is also reported. Do not infer independent asset counts
or use the five assets as five independent time-series replications. Intervals
are descriptive, not selection-adjusted/formal confidence guarantees. No
winner is established solely because its point score is smallest.

## Tests, cost and promotion gate

Independent analytic CRPS/empirical-support examples, Gaussian-quadrature score
checks, recurrence hand oracles, past/future truncation invariance and failure
handling tests precede study execution. Pilot one annual refit first, measure
seconds; estimate each remaining staged batch before running it. No batch over
30min, no multi-hour grid. Save source/config/data hashes and all fits/statuses.

Even a favorable one-week result does not authorize production model promotion.
Joint dependence, horizon propagation, price exponential-moment domain,
property/FX integration, executable cash ledger and annual held-out risk checks
would require separate validation. Unbounded recursive conditional variance does
not inherit the iid finite-mixture annual price-moment guarantee automatically.
No deployment, portfolio recommendation or funding-rule change in this study.

## Method sources to verify

Meucci(2005), printed pp.103-105,123-125,233-234; Gneiting/Raftery(2007) proper
scores; Gneiting/Balabdaoui/Raftery(2007) calibration; Bollerslev(1986) GARCH;
Patton(2011) noisy variance proxies; arch forecast documentation; Federal Reserve
historical-simulation cautions. Exact observed URLs accompany the result.
