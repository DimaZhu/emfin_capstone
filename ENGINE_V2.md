# Engine v2 — liability-aware, view-driven, reproducible

Branch `engine-v2` integrates the six work streams from the 7 Nov review.
Everything runs off the **pinned snapshot** (`data/snapshot/`), so every
number here is reproducible byte-for-byte: `python scripts/run_v2_engine.py`.

## Pipeline

```
pinned snapshot (CSV, manifest, scripts/pin_data_snapshot.py)
  -> weekly invariants (toolbox/snapshot.py: equity log returns, 10Y yield changes, cash accrual)
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
- **Bonds**: weekly changes in 10Y yield as the invariant; exact flat-curve
  repricing, roll-down falls out of the pricing equation. No credit-spread
  layer yet (second factor, same machinery).
- **Liquidity**: liquid assets get a random-cost convolution (beta cost,
  documented mean/cap); illiquid assets get a time-to-cash haircut, matching
  the Ballast mockup. Cost parameters are placeholders - calibrate with data.
- **Liabilities**: deterministic schedule, aggregated to one outflow at the
  horizon. Key finding: with translation-invariant preferences (CARA, CVaR),
  deterministic liabilities change the optimal mix ONLY through
  shortfall-type constraints - or via stochastic amounts / multi-period
  funding (both future work). The funding-gap constraint uses the one-sided
  gap max(0, L - W); a surplus never offsets a shortfall.
- **Cash sleeve is required**: without a riskless asset, a near-total payout
  is infeasible (10Y duration risk). Cash is a T-bill proxy accruing at the
  lagged 10Y yield.
- **SAA tail noise**: CVaR-of-gap constraints bind in-solver but realize
  looser out-of-sample (~2x on 10k solver scenarios). Use a buffer or more
  solver scenarios - open calibration decision.
- **Judging framing**: grading view-based allocations under the no-view
  prior measures the cost of wrong views by construction. The paper should
  discuss this rather than hide it.

## Placeholders (replace with team/client inputs)

- Views (currently illustrative: DFAI +50bp vs DFUS, DFAE vol 6.5%)
- Liability schedule (currently an example $95M funding event)
- BL market weights (40/22/9/18/11), risk aversion 2.5, tau 0.05
- Liquidity cost parameters; quarterly CVaR budget (0.15) and gap budget
  (0.2% of liability)

## Tests

`python -m pytest tests/` - 33 tests covering every module.
