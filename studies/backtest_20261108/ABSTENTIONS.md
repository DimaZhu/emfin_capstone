# The 9 abstention folds (analysis, 9 Nov 2026)

Source: studies/backtest_20261108/results/part_*/fold_*.json and backtest.py. Read-only re-analysis, no new solves.

Folds 7, 9, 41, 43, 49, 62, 63, 68, 69 (2008-12, 2009-06, 2017-06, 2017-12, 2019-05, 2022-08, 2022-11, 2024-02, 2024-05): 9 of 78 (11.5%). Scored as cash in every headline number.

## What happens

- The solve at multiplier 1.0 returns a portfolio (all 9 are "optimal_inaccurate"), but it fails validation. The multipliers 0.5, 0.25 and 0.1 then fail at once: "W1 buffer is at least $40,000, above the smallest payment budget".
- That buffer comes from the placeholder Wasserstein radius and does not depend on the quarter. Payment budgets are $50k at 1.0 and $25k or less at 0.5 and below, so only multiplier 1.0 can ever pass, with about $10k of slack.
- Fold 8 (certified, weights ~73% IEF, 10% property) and fold 7 (abstains, ~78% IEF, 10% property) are near-identical. 35 other folds are also "optimal_inaccurate" and pass. So abstention is a knife-edge validation outcome, not a crash or a logic error.
- 7 of the 9 quarters were up quarters for 1/N (average +1.71% vs +0.87% over all 78). Abstention is not market timing.

## Limits

- The multiplier-1.0 validation record was overwritten by the later multipliers (one select file per fold), so the failing gap check is not recorded. Real funding-gap tail vs borderline solver numerics (same CLARABEL inaccuracy as the CI flake) cannot be separated without re-running a fold.
- Abstentions earn the 0% registry cash account; the T-bill fallback exists on the chained branch.

## To do

- Log per-multiplier validation records. Re-run one abstention fold (for example fold 7) when CI minutes reset.
- Report the abstention rate as a result next to the estimation band (claim 5).
