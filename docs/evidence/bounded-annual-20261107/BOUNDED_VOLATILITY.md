# Research-only annual capped conditional volatility
7 November2026. Default remains gaussian_scale_mixture. No promotion decision.

## What was added
A selectable `bounded_ewma_mixture` scenario law for the actual-instrument
adapter. The same shrunk past means/correlation, common mixture shape, latent
property link, cash account, holdings, funding budgets and independent judge
are retained. Conditional listed/FX variance now changes predictably and is
explicitly clipped between0.05x and9x each origin's baseline variance.
This is a new capped EWMA specification, NOT ordinary GARCH or a fitted cap.
At cap9, standard deviation cannot exceed3x the annual-origin baseline.
Returns and prices are not clipped; the Gaussian-mixture support is unbounded.

The cap solves the multistep exponential-moment domain problem. Every finite
linear exposure has a uniformly bounded one-step conditional MGF; iterated
conditioning proves finite moments at52weeks (and every finite horizon).
This does not give the iid exact moment formula or tail/calibration guarantees.
See BOUNDED_VOLATILITY_MOMENTS.md and the frozen study protocol.

## Use explicitly, not by changing the default

```python
from emfin_v2.default_run import load_config,validate_config,run
c=load_config()
c['scenario_model']='bounded_ewma_mixture'
c['bounded_volatility']={'decay':0.94,'floor':0.05,'cap':9.0}
c=validate_config(c)
run(c,'artifacts/my-bounded-research')
```

The legacy yield-repricing universe is rejected; it is not silently substituted.
The normal UI recompute toggle still chooses the existing default Gaussian/iid
mixture modes, not this experimental configuration. The research CLI/generated
output records the selected bounded model and finite-moment-domain status.
There is no promise of cancellation, live data or production approval.

## Evidence and verdict
- Weekly2019-2025 normalized CRPS improves about1.43% from iid on mechanically
  past-only forecasts, but tail exceptions remain imperfect. Known historical
  dates mean retrospective testing, not blind preregistration.
-19annual2007-2025 paths: modest/mixed multihorizon scores, no demonstrated
  portfolio improvement. Annual52week marginal CRPS is about0.20% lower;
 26week is worse. Five asset marginals are not independent annual replications.
- The declared coarse2-batch annual judge was too imprecise to accept any
  validation blend, even cash+fixed-property. All raw historical outcomes
  remain labelled non-approved. No failure was rerun away or threshold changed.
- Current4-batch confirmation: raw bounded CARA fails the path-loss limit under
  both laws. Its validation-selected25%risky-candidate/75%cash-anchor blend
  passes all five final sensitivity laws. This is conditional model evidence,
  not a recommendation, a globally optimal robust solution or full funding.
- The counterfactual95M final call again passes the funding budget for the
 90%cash+10%illiquid-property portfolio while leaving5M unpaid on every path.
  The default3M schedule is too small against100M to challenge liquidity much.
- Solver first-formulation failures remain visible; existing alternate
  formulation succeeds. The model does not eliminate numerical sensitivity.

Caps4/16 are fixed sensitivity cases, not a selection grid. Rare cap hits in
recent realized data do not mean the cap is economically irrelevant: it limits
simulated crisis persistence. Property conditional risk/dependence is still the
existing assumed latent link. Cash carry, settlement/costs, W1 calibration and
an optimizer that matches the cash ledger remain open. User chooses promotion.
