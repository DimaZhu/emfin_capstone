# Claims-to-evidence map (living stub)

Method-paper headline: claim 5 (estimation uncertainty and the validated safe-share band), supported by claims 1-2, with claim 4 as a plain cost-and-delivery result.

Method-paper claims, their evidence, and open gaps. Started 8 Nov 2026 from
the review doc's map; updated as P0 runs land. "Fact" = in the repo with a
source; "judgment" = review/plan interpretation.

| # | Claim | Evidence in hand (fact) | Gap to close | Status 8 Nov |
|---|-------|------------------------|--------------|--------------|
| 1 | Hard limits dominate preferences: four utility families pick the same mix within ~0.5% of score | Utility comparison (1y identical paths + 10y new model); payout-size sensitivity | None for the synthetic case | Strong as-is |
| 2 | Horizon is the biggest lever: safe share rises ~10-25% at 5y to ~45-68% at 20-30y; holding the 10y mix fails at 20y+ | Horizon sweeps under both carry views and both laws; mean-reversion scenario | Convergence curves for featured cells (P1-7) | Open (P1) |
| 3 | Nominal safety is partly an inflation illusion: $120.7M nominal = $79.4M real; no static mix passes 15% real | Real-terms repricing with bootstrapped CPI; TIPS at live real yield | Correlated-inflation sensitivity (P0-4) | Open (P0-4 not started) |
| 4 | REVISED 9 Nov (cost and delivery, not "insurance"): **the engine delivers a certified, model-based funding guarantee at a cost in expected growth.** Out of sample it matches simple shrunk mean-variance and gives up about half of 1/N's terminal wealth for a modestly smaller drawdown. It has not beaten shrunk MV on any realized measure. Not expected to beat 1/N on compounded wealth (DeMiguel, Garlappi & Uppal 2009, RFS 22(5):1915) | 78-fold walk-forward backtest (studies/backtest_20261108/REPORT.md); offline chaining + stationary bootstrap (studies/offline_chained_20261109); abstention analysis (studies/backtest_20261108/ABSTENTIONS.md). Chained terminal wealth: proposed 1.122x, 1/N 2.154x, shrunk_MV 1.217x, min_var 0.516x, cash 0.415x. Peak-to-trough on quarter-end wealth: proposed -18.7%, shrunk MV -17.8%, 1/N -22.9%. In 1/N's 10 quarters below -3%: 1/N -6.0%, proposed -2.4%, shrunk MV -1.6%; in its 22 quarters above +3%: 1/N +5.4%, proposed +1.4% (beta to 1/N about 0.2). Protected in 2008 (fold 6: -1.6% vs -14.1%); did not in 2022 (fold 60: -7.1% vs -7.3%, bond-heavy when stocks and bonds fell together). Bootstrap: P(proposed > 1/N) = 3.6%, > shrunk_MV 42%. 0 unpaid payouts in 78 folds for every method, even all-cash (0.75%/fold = 3%/yr), so realized funding does not separate the methods; the guarantee holds by construction in the model | Payout-stress run (2x/3x payouts), deferred to the Dec CI-minute reset: the only variant that could show the guarantee mattering vs shrunk MV. Say plainly that the engine has not beaten the simple benchmark on any realized measure. Drawdown is on quarter-end wealth, not weekly paths | **REVISED**: drop "insurance" as the headline word. Paired diffs reported both ways (n=69 flatters proposed; with 9 abstentions as cash: vs 1/N -0.75%, vs shrunk MV -0.03%). Referee notes: 0% cash placeholder (cash/min_var are one comparison), min_var on model-fitted covariance, full-notional haircut convention |
| 5 | **HEADLINE.** Estimation uncertainty, not preferences or the optimizer, sets the limit: the validated safe share spans 10-67.5% across bootstrap refits (point estimate at the optimistic edge), and out of sample the engine could not certify any portfolio in 9 of 78 quarters (11.5%), flipping between adjacent quarters with near-identical weights | 16-refit bootstrap with full safe-share search per refit; walk-forward abstentions: folds 7, 9, 41, 43, 49, 62, 63, 68, 69 (2008-12, 2009-06, 2017-06, 2017-12, 2019-05, 2022-08, 2022-11, 2024-02, 2024-05), counted as cash in every headline number. Fold 8 (certified) and fold 7 (abstains) have near-identical weights; 7 of the 9 abstention quarters were up quarters for 1/N, so abstention is not market timing | Extend refits for featured cells (P0-3). Re-run one abstention fold with per-multiplier validation logged, to split real funding-gap tails from borderline solver numerics (the multiplier-1.0 validation record was overwritten) | **Headline decision 9 Nov**. Caveats that stay next to it: (a) the 10-67.5% band comes from only 16 refits; (b) the lower multipliers (0.5/0.25/0.1) can never pass with the placeholder radius (W1 buffer $40k vs payment budgets of $25k or less), so only multiplier 1.0 can certify, with about $10k of slack; (c) the radius study puts that placeholder about 23,000x below the empirical radius, so a calibrated radius would likely make abstention more common; (d) abstentions earn 0% here, real T-bills would narrow the gap vs 1/N a little |
| 6 | Robustness is a budget: a statistically real Wasserstein margin is far above the placeholder and unaffordable under the payout budget | Radius calibration study; feasibility cliff at 0.00003; **empirical-radius diagnostic DONE** (studies/radius_20261108/REPORT.md) | None for the diagnostic itself; bootstrap instability +/-25% bounds precision | **P0-2 COMPLETE**: empirical train radius q50 0.410 / q90 0.462 / q95 0.474 vs placeholder 2e-05 (~23,000x); bootstrap q90 CI [0.25, 0.57]; 7/7 heldout blocks covered at q50 (nearest 0.18-0.36), n=7 so suggestive only |

## Literature to read and cite

Verified during the project (docs/ROBUSTNESS_SOURCES.md, docs/MEAN_REVERSION.md):
Michaud & Michaud (resampled efficiency); Jacquier (parameter vs Monte Carlo
uncertainty); Shiraishi/Taniguchi (dependence-aware resampling); Esfahani &
Kuhn 2018 (Wasserstein CVaR bound); Politis & Romano 1994 (stationary
bootstrap); FEDS 2001-27 (hidden dangers of historical simulation);
Barone-Adesi et al. (FHS); Fama & French 1988; Poterba & Summers 1988;
Samuelson 1963/69; Bodie 1995; Pastor & Stambaugh 2012; Blanchett, Finke &
Pfau 2014; Dimson-Marsh-Staunton ("How long is long term"); Meucci (book
audit done).

To add (review judgment): safe-withdrawal-rate / sequence-of-returns
literature (Kitces, Pfau, Morningstar) for the payout side; one LDI reference
for framing.

## Risks

- Team: engine is the private fork; agree with Dmitry/Julian what the paper
  presents as "the system" before any draft circulates (owner decision (c),
  not yet made).
- Supervisor: keep the simple MV baseline and the judging protocol prominent
  and early.
- Scope: studies beyond claims 1-6 go to the appendix or stay in the repo.
- Data rights: Yahoo-sourced histories are private-use; derived figures and
  tables only in any shared artifact.
