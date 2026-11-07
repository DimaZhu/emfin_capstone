# Real-estate assumptions and spendable funding

The optional RE sleeve is a property-index experiment, not an individual property
valuation or a calibrated property investment recommendation. Private Abu Dhabi
levels stay local. Public tests use synthetic paths and a labelled synthetic fixture.

## Inputs in the dashboard

- Source: private Abu Dhabi monthly observed apartment index, or synthetic example.
- Minimum holding: a floor, not an illiquid-asset cap.
- Monthly stale-price weight alpha, 0 to 0.8. Zero disables unsmoothing.
- RE/equity shock dependence, -1 to 1, assumed rather than estimated.
- Net annual rental yield, 0 to 20%, after costs/vacancy/taxes, unlevered.
- Planned sale agreement week, 0 meaning hold; sale-to-cash settlement delay.
- Sale transaction haircut, applied once to the agreed price, not each week.
- Short-history case: central, cautious (low drift/high vol) or optimistic
  (high drift/low vol). The last two are sensitivity corners, not probabilities.

Defaults are deliberately neutral about missing evidence: alpha zero, rent zero,
no planned sale, 12-week settlement assumption if a sale is planned. Enabling RE
does not imply that the private data establish these assumptions.

## Unsmoothing and short-history sensitivity

For monthly observed log returns r, the assumed first-order smoothing model is

    r[t] = alpha * r[t-1] + (1-alpha) * u[t]
    u[t] = (r[t] - alpha*r[t-1]) / (1-alpha)

Alpha is the weight on the stale observation, not the weight on fresh information.
We do not estimate it automatically from 45 returns: genuine cycles and smoothing
cannot be separated reliably with this window. The first return is lost when
alpha is positive. Annual log drift is 12 times the sample mean; annual volatility
is sqrt(12) times sample standard deviation. Weekly simulation uses these moments
and the engine's common Student-t variance scale, when selected.

A circular moving-block bootstrap (3-month blocks, 2,000 resamples, fixed seed)
reports marginal 5/50/95 percentiles for drift and volatility. It preserves only
short local dependence. It is conditional on the sample, block length and
unsmoothing model, does not capture missing regimes or index-construction bias,
and is neither a joint confidence region nor an economic forecast. The index
window contains 46 monthly levels, not 46 independent years. Sensitivity cases
combine marginal endpoints explicitly; no joint probability is attached.

## Dependence

RE price innovations use rho times the standardized equal-weight equity log-shock
factor plus sqrt(1-rho²) times an independent normal shock, then the same
variance-normalized t scale as the liquid assets. Thus rho names the model's
weekly shock correlation. It is not an empirical REIDIN/equity correlation or a
tail-dependence estimate. Correlations with bonds and cash are induced by this
factor construction, not separately set. The UI says this is an assumption.

## Marked wealth is not spendable cash

The engine carries separate marked paths and funding paths. Before a planned
sale settles, property value cannot fund a payout. Only rent is spendable.
Rent is an explicit fixed net yield on initial property capital, paid weekly
while held and reinvested in the scenario money-market account. This is a simple
cash-flow assumption, not rent linked to a property price mark.

At the agreement week, sale price is the scenario property mark less the sale
haircut. Property price exposure and rent stop then. During settlement the
contractual receivable contributes to marked wealth but is unavailable for
funding. At settlement it becomes cash and then accrues at the scenario MMKT rate.
No buyer default, uncertain closing date, leverage, capital gains tax, FX, debt
service, repeated sales, partial sales or dynamic sale strategy is modeled.
The fixed schedule is assumed, not a guaranteed executable sale.

Terminal utility and market-loss checks use marked wealth. Funding constraints,
calibration and held-out funding checks use spendable paths. Consequently a
positive terminal property/receivable value can coexist with a funding failure.
The fan is marked net wealth after provisioned payouts, not an available-cash fan.
This distinction is important if no proposed allocation passed the funding checks.

Private NPZ archives with RE enabled must supply `funding_paths` in the same units
and shape as `market_paths`; the loader refuses to treat a marked property path as
cash. Archive generation and calibration are the input provider's responsibility.

## Verification and limits

Tests cover inversion of a constructed smoothing process, alpha-zero identity,
repeatable bootstrap, rent accrual, one-off sale costs, settlement timing,
receivable-not-cash beyond the horizon, simulated dependence, distinct funding
metrics and a tiny optimizer that cannot spend marked property. These check the
specified model, not the economics of a real property transaction.

Geltner formula/reference:
https://timelyportfolio.github.io/PerformanceAnalytics/reference/Return.Geltner.html

The implementation is original NumPy code; no R or GPL package is a dependency.

## Forward expectation is separate from the boom sample

The default forward annual price log-return view is 4%, an explicitly illustrative
long-run assumption, not a calibrated prior or a conservative statistical bound.
Net rent is separate. The observed short-window mean is displayed alongside it
but does not drive the default scenario drift. The generator is centered on the
forward assumption; entropy pooling then pins the terminal underlying log-price
mean to forward_drift * horizon / 52. The stressed posterior preserves this same
mean constraint while adding the stress tilt. Posteriors expose achieved means.

Sample mode is an optional sensitivity, not the default. In that mode the chosen
central/cautious/optimistic sample-implied mean becomes the explicit EP target.
In view mode those history cases alter volatility but the independently specified
forward mean stays fixed. Other asset moments can move when probabilities change,
especially under dependence; this is a joint distribution reweighting, not a free
RE-only return adjustment. An unsupported view raises rather than silently clips.

RE NPZ archives must also supply `re_price_log_paths` with (scenario, week) shape
so the view targets underlying price, not a mark that mixes rent/sale proceeds.
Confirm the forward view with the decision owner before using it for investments.
