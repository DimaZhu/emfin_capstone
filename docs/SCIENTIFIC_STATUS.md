# Research status,7 November2026

Private use only. This is not an investment recommendation.

## Implemented and checked

- Independent frozen final all-risk judge, not the old funding-only pass.
- Default finite-moment Gaussian variance mixture; legacy log-t explicitly named.
- Final input-validation boundary and disabled unsafe stochastic liabilities.
- Cash-first self-financing policy audit with independently checked cash/units.
- Split-sleeve/time-grid invariant W1 metric with explicit new economic cost.
- Serial-aware quarterly property annual dispersion and assumed publication lag.
- Matched constrained MV, simple policies and validation-calibrated comparisons.
-19 nonoverlap annual episodes2007-2025, including2008/2020/2022, on actual ETF,
 FX and quarterly property observations (latest vintages, not point-in-time).
-19 matched FHS episodes and19 episodes with8 outer refits each; all152 refits
 succeeded under the final numerical formulation. A separate32-refit current
 pilot also succeeded. Intermediate numerical failures are retained in evidence.
- Bounded seed/sample/radius matrix and800/1200/2400-path,8-batch pilot.
- Four larger/early-payment counterfactual schedules, not changed user obligations.

The raw machine results, source/config/data hashes, solver statuses, declarations
and measured compute notes are in `evidence/robustness-20261107/machine-results.zip`.
Open its adjacent `report.html` for the report or read the standalone PDF supplied
with the milestone. Method references are in `ROBUSTNESS_SOURCES.md`.

## What the tests say

CARA and same-constraint MV are close in the conditional judge. In19 annual
reset-wealth episodes, same-constraint MV's average terminal wealth change was
about0.20 percentage points above CARA, but a small exploratory block-bootstrap
interval touches zero. FHS had about0.02 percentage points lower mean wealth
change than mixture CARA, with a wide exploratory interval. Bagging had about
0.12 percentage points lower mean but a less severe worst observed episode.
These are not confirmatory economic significance claims or proof of superiority.
All annual terminal-wealth changes include the3% scheduled withdrawals.

More importantly, a pass of the declared tail-shortfall budget is not a
paid-in-full promise. A$95M counterfactual final call can pass the20% allowance
while a cash+unsold-property portfolio misses$5M on every path. A$60M early call
plus$30M final call passed the declared model limits for a calibrated portfolio
while making every payment on only about84% of reference paths. The default
$3M schedule was not changed. The UI now exposes this separate execution audit.

## Still unresolved, not silently marked done

- The optimizer itself still uses money-market provisioning, not the dynamic
 cash-first trading policy. The policy audit does not transfer W1 certification.
- The W1 radius remains a development placeholder. Earlier-versus-recent
 empirical annual-path discrepancy0.339 is not a valid replacement radius or
 confidence set. It shows why0.00002 has no demonstrated statistical coverage.
- No genuine point-in-time property vintages, actual release calendar, fitted
 cross-frequency property/ETF/FX dependence, transaction depth or liquid-sale
 settlement calendar.45-day property publication delay is an explicit assumption.
- Cash carry is a0% placeholder, not a calibrated money-market forecast.
- EWMA FHS is a declared variant, not fitted GARCH or an original-paper replica.
 Its shared judge is the mixture model, not a neutral economic truth.
- Whole-fit resampling refits all estimated listed/FX moments and property
 dispersion, but cross-frequency joint dependence remains assumed. Fixed views,
 liability schedule and risk preferences are not spuriously treated as data.
- Small sample sizes, overlapping estimation windows, method development and
 regime shifts prevent formal economic coverage or strong tail-frequency claims.
- Typed configuration records and process-based cancellation remain later work.

No budgets or numerical acceptance tolerances were loosened to get these tests
to pass. CARA uses equivalent conic formulations and exact positive budget
normalization for conditioning. The previous failures are part of the record.

## Additional model-adequacy study,7 November2026

A fixed retrospective one-week marginal forecast protocol compares iid mixture,
EWMA mixture, GARCH-variance mixture and empirical EWMA-FHS. Validation2014-2018
selected GARCH before final2019-2025 scoring. Its normalized CRPS is1.82% lower
than iid in that final slice, with lower residual volatility clustering. This
is not an annual portfolio result or independent blind preregistration. Crisis
tail exceptions remain imperfect; unbounded Gaussian conditional-variance
recursion has a serious multistep price-moment problem. No default was changed.
See MODEL_ADEQUACY_PROTOCOL.md, MODEL_ADEQUACY_RESULTS.md and
CONDITIONAL_PRICE_MOMENTS.md. New independent test total:332pass.

## Research-only bounded conditional annual model

A declared capped-EWMA Gaussian-mixture model preserves finite-horizon price
moments by a uniform conditional-MGF bound. Default/risk limits unchanged.
One-week improvement does not carry into clear annual superiority:19annual
histories show mixed multihorizon scores and slightly lower raw mean ledger
returns for the bounded model. The coarse2-batch all-risk judge accepted no
historical blend, including the cash/property anchor; these remain failures,
not certified investments. A current4-batch cross-law study validates frozen
cash blends, not raw bounded CARA. BOUNDED_VOLATILITY.md gives scope and limits.
