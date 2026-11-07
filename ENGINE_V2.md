# Engine v2 — liability-aware, view-driven, reproducible

Branch `engine-v2` integrates the six work streams from the 7 Nov review.
Everything runs off the **pinned snapshot** (`data/snapshot/`), so every
number here is reproducible byte-for-byte: `python scripts/run_v2_engine.py`.

## Pipeline

```
pinned snapshot (CSV, manifest, scripts/pin_data_snapshot.py)
  -> weekly invariants (toolbox/snapshot.py: equity log returns, 10Y yield changes, IG OAS changes, cash accrual)
  -> joint moments -> horizon projection (square-root rule)
  -> Gaussian invariant scenarios (seeded)
  -> market map (equities lognormal; bond exact repricing with roll-down - toolbox/bonds.py)
  -> views via entropy pooling (toolbox/entropy_pooling.py) -> posterior probabilities q
  -> liquidity convolution (toolbox/liquidity.py) -> net liquidation scenarios
  -> allocation (vanilla MV / Black-Litterman / EP-SAA / liability-aware EP)
  -> paired-seed out-of-sample judging (toolbox/benchmark.py)
```

The optimizer's scenario-matrix interface is untouched: views and liquidity
change only scenario probabilities and scenario values, upstream.

## Design decisions and honest caveats

- **Entropy pooling**: joint mode for consistent views (one KL projection,
  all views hold exactly), sequential mode for priority-ordered/conflicting
  views (later view wins; per-view achieved moments always reported).
  BL is the mean-views-only special case - kept as a benchmark method.
  Equality AND inequality views (the classic A q = b, G q <= h form):
  means, vol caps, mean floors, relative (ranking) views, skewness,
  kurtosis, correlation - pooled in one dual (Newton for pure equalities,
  bound-constrained L-BFGS-B once inequalities enter). Volatility views use
  the centered squared feature, so a vol cap bounds the realized std
  regardless of mean drift. Confidence-in-views blending (Meucci 2010):
  q = (1-c) p + c q_EP. Diagnostics: relative entropy and the effective
  number of scenarios (ENS ratio exp(-KL)) - the standard EP stress-test
  summary. Cross-validated against Fortitudo Technologies' reference
  implementation (BSD-3-Clause "entropy-pooling" package as a test-only
  dependency; posteriors match to ~1e-6, incl. a mixed equality+inequality
  problem. Their GPL-3.0 "fortitudo.tech" package is deliberately NOT a
  dependency - copyleft; used only as a one-off local check. Their
  sequential-EP heuristics are proprietary and not in either open-source
  package - ours is our own implementation).
- **FFR prior (Fully Flexible Resampling)**: the moment estimates behind the
  scenario set are computed under flexible probabilities over the historical
  weeks - exponential time decay (half-life scaled to ~half the estimation
  window) combined with a Gaussian kernel on trailing 13-week DFUS realized
  vol, so recent weeks in a similar vol regime count more.  Kish effective
  sample size is reported.  **ESS floor**: an over-tight kernel on a short
  window burns the effective sample below what the covariance needs and the
  prior collapses into chasing the latest rally (this actually happened on
  the OAS-shortened window: ESS 28/151, 100% corner allocations).  The
  runner therefore widens the kernel bandwidth until ESS >= 60 and reports
  the widening.  **Window note**: with the credit sleeve, the estimation
  window shortens to the common history of the FRED OAS series (151 weeks
  from 2023-11; OAS is the binding constraint).  `toolbox/ffr.py` also provides the
  non-parametric option: weighted block-free bootstrap of weekly invariants
  into horizon scenarios.  Honest caveat: the judge's data-generating
  process is the full-sample Gaussian, so it cannot reward a better prior -
  FFR's value is a real-data non-stationarity property, and its CE gap
  under the judge is the price of regime robustness.  The uniform-prior
  contrast allocation is available via `--with-uniform-contrast` (off by
  default: its unweighted solve intermittently falls back to the slow SCS
  path - an open solver-robustness item).
- **Bonds**: two sleeves, same machinery.  *Government* (`UST10`): weekly
  changes in 10Y yield as the invariant; exact flat-curve repricing,
  roll-down falls out of the pricing equation.  *Credit* (`USIG`): weekly
  changes in the IG option-adjusted spread as the invariant (FRED
  `BAMLC0A0CM`, ICE BofA US Corporate Master, in the pinned snapshot);
  the excess-return scenario stacks spread repricing (same
  duration/convexity engine), carry (earned spread) and roll-down, so
  Treasury and credit premia stay separable.  Cash flows accrue between
  coupon dates (fractional-period interest compounded, not dropped).
  Honest finding at current placeholder calibration: the IG sleeve earns a
  ~90bp spread with equity-correlated downside and gets zero weight in
  every optimized allocation - equity + Treasury barbells dominate it on a
  CE basis.  That is a property of the premia, not a bug; the paper should
  say so.
- **Liquidity**: Meucci (2012, FAJ 68(6), doi:10.2469/faj.v68.n6.6)
  integrated liquidity+market risk overlay (`toolbox/meucci_liquidity.py`):
  per-scenario liquidity adjustment ~ N(mu(j), sigma(j)^2) with VWAP
  square-root impact in the liquidated amount (superlinear in size),
  state-dependent parameters (stressed scenarios pay up to ~3x), liquidity
  correlations shrunk toward 1 (gamma=0.9), and the analytic Eq. 10 total
  P&L density with CVaR decomposition (market vs liquidity contribution)
  and liquidity score.  Reference schedule: full liquidation of the
  documented reference portfolio; allocation-dependent schedules need an
  outer loop (future work).  alpha/beta/delta/ADV are PLACEHOLDERS -
  calibrate with volume data.  The earlier state-independent beta-cost
  convolution and the illiquid time-to-cash haircut remain in
  `toolbox/liquidity.py` (tests + illiquid holdings).
- **Liabilities**: deterministic schedule, aggregated to one outflow at the
  horizon. Key finding: with translation-invariant preferences (CARA, CVaR),
  deterministic liabilities change the optimal mix ONLY through
  shortfall-type constraints - or via stochastic amounts / multi-period
  funding (both future work). The funding-gap constraint uses the one-sided
  gap max(0, L - W); a surplus never offsets a shortfall.
- **Cash sleeve is required**: without a riskless asset, a near-total payout
  is infeasible (10Y duration risk). Cash is a T-bill proxy accruing at the
  lagged 10Y yield.
- **SAA tail noise - fixed by calibration**: a CVaR-of-gap constraint that
  binds in-solver on 10k scenarios realizes looser out-of-sample (~2x in
  this engine), so the nominal budget cannot be trusted directly.  The
  runner calibrates it (`liabilities.calibrate_shortfall_budget`):
  binary-search the budget multiplier for the loosest in-solver budget
  whose realized out-of-sample gap CVaR (paired fresh judge seeds) still
  respects the target, printing every probe.  When tightening was needed,
  the nominal-budget allocation stays in the benchmark table so the cost of
  the fix is visible.  `--no-tail-calibration` skips the loop.
- **Judging framing**: grading view-based allocations under the no-view
  prior measures the cost of wrong views by construction. The paper should
  discuss this rather than hide it.

## Placeholders (replace with team/client inputs)

- Views (currently illustrative: DFAI +50bp vs DFUS, DFAE vol 6.5%)
- Liability schedule (currently an example $95M funding event)
- BL market weights (6-sleeve, illustrative), risk aversion 2.5, tau 0.05
- Liquidity cost parameters; quarterly CVaR budget (0.15) and gap budget
  (0.2% of liability; in-solver value, OOS-calibrated at runtime)

## Tests

`python -m pytest tests/` - 73 tests covering every module.
