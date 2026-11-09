# Studies index

Each directory is a self-contained study: code, results, and a report.
Dated names are `yyyymmdd` of the run. RUN_MANIFEST.* pins code, data and
hashes for the 8 Nov runs.

| Study | Question | Status |
|-------|----------|--------|
| [backtest_20261108](backtest_20261108/REPORT.md) | Walk-forward backtest: 78 quarterly folds 2007-2026, all decisions re-fit strictly on the past. First true out-of-sample evaluation. | Complete (ran on Actions, 8-9 Nov) |
| [offline_chained_20261109](offline_chained_20261109/REPORT.md) | Chained-wealth question answered offline from the backtest's own fold records: compounding with absolute payouts, plus a 5,000-sequence stationary bootstrap. | Complete (no solver cost) |
| [backtest_chained_20261109](backtest_chained_20261109/) | True chained-wealth backtest along one realized history. Code ready and dispatch-only; NOT run - deferred to the Dec CI-minute reset after design review showed the state-dependence never binds at 3%/yr payouts. | Not launched |
| [radius_20261108](radius_20261108/REPORT.md) | Empirical Wasserstein radius diagnostic: the statistically real W1 margin vs the placeholder. | Complete |
| [final5](final5/) | The five final questions (utility choice, rebalancing, horizon, etc.). | Complete, 8 Nov |
| [uif_20261108](uif_20261108/README.md) | Estimation uncertainty, inflation-indexed payouts, fees. | Complete, 8 Nov |
| [tbill](tbill/) | Real T-bill asset, 10y loss-limit matrix, diversification. | Complete, 8 Nov |
| [round2](round2/) | Unified scientific report, 5th edition. | Complete, 8 Nov |
| [fixes](fixes/) | Open-points fixes after the 3rd-edition report. | Complete, 8 Nov |
| [meanreversion](meanreversion/) | Mean-reversion carry scenario. | Complete, 8 Nov |

Headline across studies: hard limits, not utility choice, set the portfolio;
horizon is the biggest lever; the engine is insurance, not outperformance
(claim 4 in docs/paper/CLAIMS_EVIDENCE_MAP.md).
