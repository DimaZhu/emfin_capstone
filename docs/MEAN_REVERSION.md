# Mean-reverting equity scenario law (research-only, optional)

Owner ask 8 Nov 2026 ~16:32 SGT ("Yes!" to the offered scenario after the
long-horizon literature answer). Branch `scenario-mean-reversion-20261108`.
Nothing here changes the default: the iid weekly Gaussian scale mixture
remains the engine's law; this model runs only when a config explicitly sets
`scenario_model: mixture_mean_reverting`.

## Question it answers

"A downward cycle never lasts 30 years - how would results move if that is
true?" The scenario shows the headline numbers under the strong version of
that claim, with the reversion parameters treated as known.

## Model

One shared transitory AR(1) component (a "fad"/market cycle, Poterba-Summers
1988 style) added to the log prices of the equity factor assets (VTI, VWO):

    r_i,t = mu_i + eps_i,t / scale_t + w_i * fr_t
    fr_t  = (phi - 1) * g_{t-1} + sqrt(1 - phi^2) * nu_t
    g_t   = phi * g_{t-1} + sqrt(1 - phi^2) * nu_t,  g_0 ~ N(0,1)

The permanent random-walk covariance is reduced by exactly what the fad adds
(`cov_perm = cov - share * sigma sigma'` on the equity block), so the
unconditional weekly mean and covariance equal the fitted iid moments
EXACTLY (tested). All long-horizon effects come from negative
autocorrelation, never from lower weekly variance. Finite price moments of
all orders. Property keeps its configured equity correlation through the
full equity innovation; gold, Treasuries, TIPS, bills, cash and FX keep
their base dynamics. The fhs_ewma fifth law is untouched.

Exact T-week equity variance ratio vs the iid base:

    VR(T) = (1 - share) + share * (1 - phi**T) / (T * (1 - phi))

## Calibration (declared, not estimated)

| setting | half-life | equity variance share | VR 1y | VR 5y | VR 8y | VR 30y |
|---------|-----------|-----------------------|-------|-------|-------|--------|
| weak    | 3.0y      | 0.20                  | 0.98  | 0.92  | 0.89  | 0.83   |
| central | 2.0y      | 0.40                  | 0.94  | 0.79  | 0.74  | 0.64   |
| strong  | 1.5y      | 0.50                  | 0.88  | 0.64  | 0.56  | 0.44   |

The central column sits inside the published US-equity range; Poterba-Summers
(1988) VR(8y) about 0.58 lies between central and strong. `variance_share`
above ~0.5 is rejected by the permanent-covariance PSD guard on the fitted
universe. Simulated 8y VR 0.727 vs analytic 0.736 (2000 paths).

Under the central setting the transitory price component has a 15% stationary
standard deviation for VTI: prices can sit ~30% from trend for years before
reverting. Mean reversion here is NOT insurance against long drawdowns;
Japan-style paths exist in the scenario. It tightens TERMINAL outcomes, not
any-point ones.

Sources: Fama & French (1988, JFE, doi:10.1016/0304-405X(88)90020-7);
Poterba & Summers (1988, JFE, nber.org/papers/w2343); Pastor & Stambaugh
(2012, J. Finance, doi:10.1111/j.1540-6261.2012.01722.x); Blanchett, Finke &
Pfau (2014, ssrn.com/abstract=2422499); Siegel / Dimson-Marsh-Staunton via
london.edu/think/how-long-is-long-term.

## What changes under the scenario (dual-law judging MR + fhs_ewma, frozen
sleeves, $250k/month, seed families 20261109 + 20261111; every cell mirrored
against the frozen iid cells)

- **Horizon effect: qualitatively unchanged.** Safe share still rises with
  horizon (payouts eating capital drive it, not equity risk). Same shape at
  5/10/15/20/30y under both carry views.
- **CE: modestly higher in 16 of 20 horizon cells**, typically +1-5M/yr at
  10y+, but the move is about as wide as the seed-noise band, so no robust
  claim on the required safe share.
- **Terminal left tail at 20-30y: much better.** Upper bound on terminal
  loss of the frozen 10y mix (all execution policies) drops from >100%
  (can lose everything) to negative (bounded gain) under MR; e.g. fitted 30y
  buy-and-hold 1.04 -> -0.64, cash-first 1.82 -> 0.86. At 10y the bound is
  roughly unchanged (within batch noise).
- **Tight terminal-loss limits relax materially at 10y (fitted view):** 5%
  terminal limit needs 77.5% bills under iid vs the 10% grid floor under MR.
- **Any-point (cml) cells at 30y slightly stricter:** 40%-cap cells move
  0.675 -> 0.75 safe share (fitted) - the fad lets prices sit far from trend
  for years, so interim losses are not tamed.
- **Payout dial unchanged in shape:** 50k/100k-per-month cells move with the
  same pattern as the 250k base (safe share roughly flat, CE +1-5M, except
  30y fitted where the any-point cap dominates).

## Honest caveats

- The scenario treats the reversion parameters as KNOWN. Pastor & Stambaugh
  (2012) show that once expected-return and parameter uncertainty are
  included, predictive variance per year at long horizons is at least ~1.3x
  the iid figure - so these results are the BEST case for mean reversion,
  not a forecast.
- Calibration is declared, not fitted to the engine's data window; published
  estimates vary widely and are mostly US-only. Japan (1989-2024) shows the
  claim fails in individual markets.
- MR-vs-iid differences at a single seed family are partly Monte Carlo
  noise; the second seed family bounds that.
- Loss-limit dials were mirrored at 10y and 30y (owner default and long
  end), not the full five-horizon grid of the base study; the fitted view
  has extra partial 5/15/20y cells.

## Reproduce

```bash
PYTHONPATH=. python3 studies/meanreversion/study_mr_diagnostics.py
PYTHONPATH=. python3 studies/meanreversion/study_mr_horizon.py     # checkpointed, resumable
PYTHONPATH=. python3 studies/meanreversion/study_mr_strength.py
PYTHONPATH=. python3 studies/meanreversion/study_mr_limits.py
PYTHONPATH=. python3 studies/meanreversion/study_mr_payouts.py
PYTHONPATH=. python3 studies/meanreversion/study_mr_policies.py
```

Results: `studies/meanreversion/results/`. Tests:
`tests/test_mean_reversion.py` (8 tests: algebra, PSD guard, calibration
validation, weekly moment match, simulated VR, determinism, registry guard).
