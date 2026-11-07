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

## Real-data status (as of 2026-11-07)

Landed: BIS UAE residential property price index (REIDIN-derived national
source - verified against bis.org/statistics/pp-sources.pdf) via FRED
series QAEN628BIS, quarterly 2003Q1-2024Q1, nominal, 2010=100, at
data/raw/fred/2026-11-07/ with a manifest entry.  BIS terms allow download,
reproduction and dissemination with the national source quoted.  Caveats:
UAE-wide not Abu Dhabi (composition effects), stale by ~2.5 years (refresh
from the BIS Data Portal), nominal.
scripts/build_re_observer.py runs the Layer 2/3 machinery on it: raw lag-1
ACF 0.68 (heavy smoothing/momentum signature), FGW unsmoothing lifts vol
1.81x (consistent with the pension-LDI desmoothing literature), and the
crude moment-fit state-space leaves Ljung-Box rejections on the invariant -
the honest finding is that separating smoothing from genuine momentum needs
joint (EM/Bayesian) estimation, which is deferred; FGW passes its own
diagnostic by construction but risks over-unsmoothing (Delfim).

Terms findings for the other sources (2026-11-07):
- REIDIN (reidin.com/terms-conditions): standard website terms, materials
  copyright-protected; no licence to redistribute stitched data - their
  public PDFs can inform analysis but a stitched index must NOT be
  committed or redistributed.
- ValuStrat (valustrat.com VPI page): proprietary research/valuations; free
  quarterly reviews to read, no reproduction rights stated - observer only
  with permission.
- ADREC (adrec.gov.ae market reports): biannual reports published; terms
  not found - read/cite only until terms are confirmed.
- DLD Dubai Pulse (dubaipulse.gov.ae dld-transactions): access appears
  gated (the page mentions a confirmation step within 14 days); not clearly
  open for bulk download - request access first; not pulled.

## Current boundary

The BIS/FRED UAE series and its manifest are present, and the observer script
uses them. Synthetic tests remain necessary because the latent truth is unknown
in real observations. A stale national index is not an Abu Dhabi client valuation.
REIDIN derivation was verified against the BIS national-source document, as noted
above. Client exposures and licensed local observations remain missing.
