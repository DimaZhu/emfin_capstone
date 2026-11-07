# Abu Dhabi real estate layer - status and honest caveats

Plan of 2026-11-07 (user-supplied markdown) implemented as far as code can
go without licensed data. Everything is validated on SYNTHETIC data with
known truth (tests/test_real_estate.py); no real market series is in the
repo yet.

## Implemented (toolbox/real_estate.py, 12 tests)

- Layer 2 baselines: Geltner AR(1) reverse filter; Fisher-Geltner-Webb
  zero-autocorrelation grid search.
- Layer 2 core: multi-observer state-space model (latent AR(1) true return
  with momentum kept, per-observer appraisal smoothing + noise), Kalman
  filter + RTS smoother, missing-observer robust. Parameter estimation is a
  crude moment fit - EM/Bayesian MCMC (Sijp-style) is future work.
- Layer 3 diagnostics: ACF, Ljung-Box, ARCH-LM, no new dependencies.
- Layer 4: block bootstrap of residual vectors with per-batch parameter
  draws (parameter uncertainty propagated, Couts-Goncalves-Rossi motivated).
- Scalability: MarketAdapter interface + DataManifest registry (URL, access
  date, licence, hash). SyntheticAdapter for validation.
- Layer 5: state-dependent liquidity already lives in
  toolbox/meucci_liquidity.py (Meucci 2012 overlay, state multipliers);
  a real-estate adapter passes market state (volume/off-plan share) through
  once data exists.

## NOT implemented yet (explicitly deferred)

- Layer 1 index construction (hedonic/repeat-sales): needs real ADREC/DLD
  transaction data.
- EM/MCMC estimation of the state-space parameters; time-varying smoothing.
- Structural-break tests beyond ACF/LB/ARCH-LM; GARCH standardization.
- Pseudo-out-of-sample validation on Dubai (needs the DLD CSV, licence
  check first), stress-period exhibits, ENS tracking wired into a runner.
- REIDIN PDF stitching, ValuStrat extraction: terms-of-use review pending
  before any download.

## Data status (as of 2026-11-07)

- All tests validate against simulate_smoothed_observations (known truth).
- Free backbone candidate: BIS/FRED UAE residential property prices
  (quarterly from ~2003). The claim that BIS's UAE series is REIDIN-derived
  is NOT yet verified from sources - check the BIS series metadata before
  relying on it.
- REIDIN public monthly PDFs / ADREC reports / ValuStrat quarterly reviews:
  terms of use must be read before use; no scraping of third-party
  dashboards (Daar etc.) per the plan.
- When a file lands: data/raw/<source>/<date>/ + DataManifest entry.
