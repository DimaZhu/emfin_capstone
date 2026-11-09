# Claims-to-evidence map (living stub)

Method-paper claims, their evidence, and open gaps. Started 8 Nov 2026 from
the review doc's map; updated as P0 runs land. "Fact" = in the repo with a
source; "judgment" = review/plan interpretation.

| # | Claim | Evidence in hand (fact) | Gap to close | Status 8 Nov |
|---|-------|------------------------|--------------|--------------|
| 1 | Hard limits dominate preferences: four utility families pick the same mix within ~0.5% of score | Utility comparison (1y identical paths + 10y new model); payout-size sensitivity | None for the synthetic case | Strong as-is |
| 2 | Horizon is the biggest lever: safe share rises ~10-25% at 5y to ~45-68% at 20-30y; holding the 10y mix fails at 20y+ | Horizon sweeps under both carry views and both laws; mean-reversion scenario | Convergence curves for featured cells (P1-7) | Open (P1) |
| 3 | Nominal safety is partly an inflation illusion: $120.7M nominal = $79.4M real; no static mix passes 15% real | Real-terms repricing with bootstrapped CPI; TIPS at live real yield | Correlated-inflation sensitivity (P0-4) | Open (P0-4 not started) |
| 4 | Simple beats clever: no objective, forecast or trading rule beats the fixed mix under the safety judge; higher-scoring reserve rule fails validation | 19 annual holdouts, 152 refits, dynamic-policy attribution, benchmark table; **walk-forward backtest DONE** (78 folds 2007-2026, studies/backtest_20261108/REPORT.md) | Reframe claim: backtest complicates "simple beats clever" on wealth | **P0-1 COMPLETE, claim needs reframing**: on realized paths the model beats cash (paired +0.98%/fold) and min-var (+0.82%/fold), ties shrunk MV, but LOSES to 1/N on compounded wealth (1.149x vs 1.841x; 1.073x counting 9 calibration-abstention folds as cash). Zero unpaid payouts for ALL methods in ALL folds, so the safety-judge advantage did not differentiate here. Model's worst fold -7.1% vs 1/N -14.1%. Descriptive only, n=69 paired |
| 5 | Estimation uncertainty dominates: validated safe share spans 10-67.5%; point estimate at the optimistic edge | 16-refit bootstrap with full safe-share search per refit | Extend refits for featured cells; make the band the headline (P0-3) | Open (presentation) |
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
