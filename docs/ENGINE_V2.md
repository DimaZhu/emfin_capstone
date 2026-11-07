# Current default: one funding-risk argument

> Active default:52-week horizon, editable$250k/month x12 placeholder, W1 on with a visible20% per-payment tail-gap budget. Interactive dashboard uses an explicitly coarse tier. Earlier13-week reference/grid/lookup artifacts are archived, not current one-year evidence. No new grid has been run. See docs/ONE_YEAR_MONTHLY.md (or ONE_YEAR_MONTHLY.md from docs).

This is an illustrative implementation, not a calibrated SFO recommendation.
The active/default branch is `engine-v2` in TijsdeBoer/emfin_capstone.

## One command, one config

After installing `requirements.txt`, run:

```
python -m emfin_capstone --config emfin_v2/resources/configs/default.json
```

The compatibility script `python scripts/run_v2_engine.py` and installed
`emfin-run` use the same default. Outputs: `artifacts/default/results.json`,
`benchmarks.csv`, `report.md` and self-contained `report.html`. Keep the cloned
repo and its pinned inputs available. Everything runs offline.

The main comparison is 1/N, common shrunk MV, and ONE proposed model, with a
single 'without posterior stress' sensitivity. Additional methods belong to
research/appendices (`--research`), not the main comparison. See PAPER_STRUCTURE.md.

## Proposed model

- Joint weekly Student-t shocks (nu=8 selected on development folds), summed
  into paths. Quarterly shocks are NOT assumed to retain Student-t nu.
- Unit-invariant correlation shrinkage and structural mean shrinkage.
- Exact synthetic fixed-coupon bond repricing; stated illustrative haircuts.
- Views pooled on the very same scenario paths being optimized.
- CARA utility of terminal wealth NET of all provisioned payouts.
- Cumulative funding requirements at each due date, not separate claims on
  the same gross wealth. Earlier payouts accrue at money-market opportunity cost.
- Shared-threshold funding/CML constraints under nominal and stressed posterior
  measures, covering their finite convex hull. This is not unrestricted KL/Wasserstein DRO.
- Funding-budget multiplier selected on independent validation seeds; final
  evaluation seeds are untouched by selection. Failed final evaluation stays
  reported as a failure, never silently retuned.

The default preserves the illustrative $35M/$60M schedule but explicitly sets
amount uncertainty to ZERO. The older 15%/8% stochastic case becomes infeasible
once cumulative payouts are correctly counted. It is not made feasible by
loosening solver checks or pretending every payment can use the original cash.

## Corrected result and uncertainty

On the current pinned example, calibration mixes 50% of the optimized
allocation with 50% verified cash after the unblended model fails fresh stressed
validation. It is explicitly a calibrated mixture, not globally optimal weights.
The final evaluation reports net CE about $6.857M with the illustrative W1 risk buffer enabled for the proposed model, with
no observed funding gap under nominal or freshly tilted stress measures in the
8 evaluation batches. 1/N and shrunk MV fail the final-date risk budgets.
The without-posterior-stress comparison uses the SAME cash-mixing fraction.
Regenerate JSON for exact values. Budget multiplier=1 is accepted; no tightening
of that multiplier is falsely claimed. The exposure mix, not just the in-solver
budget, is part of the calibration protocol.

Zero observed tail loss gives a degenerate batch-mean interval at zero; it is
NOT a distribution-free upper bound on unseen losses. The JSON and report state
this limit rather than equating an empty observed tail with guaranteed safety.

These intervals are across independent Monte Carlo batches conditional on the
fitted model. They exclude parameter, model and economic forecast uncertainty.
Historical development has only 1-2 nonoverlapping quarterly outcomes per fold;
that cannot establish a credible real-world 95% tail guarantee. The empirical
regime judge overlaps estimation history and shows sensitivity, not predictive edge.

## Safety and numerical status

Solver status, finite outputs and normalized constraint residuals are checked.
Funding epigraphs are scaled to their budgets and unnecessary positive-part layers
were removed. The tested default runs in about 2 seconds here. If an optimizer
fails, a cash allocation is used ONLY after stronger pointwise budget/CML checks;
its status says 'verified cash fallback', never 'optimal'. If that fails too,
no proposed allocation is returned. Invalid cases write an unavailable report.
No software can promise every possible input or machine will solve successfully.

The independent `test_reference_balance_sheet.py` suite covers hand-computable
payout netting, accrual, one-period reduction, MPEP binary-group probabilities,
weighted CML atoms, and deterministic TSDR transitions. Infeasible cumulative
funding has an explicit regression test. ALL multi-period results from before
this correction are withdrawn. Historical artifacts under `artifacts/report/`
are superseded; use `artifacts/default/` for the current main comparison.

## Client evidence versus assumptions

|Input|Status|
|---|---|
|Pinned equities, Treasury yield, IG OAS, 3-month rate|Real historical data, not predictive truth|
|$35M/$60M schedule, views, haircuts, budgets, preferences|Illustrative, not client-approved inputs|
|BIS/FRED UAE RPPI|Real UAE-wide observer series through 2024Q1, not current Abu Dhabi prices|
|RE allocation sleeve|Synthetic stated assumptions; optional minimum holding|
|Family-company model|Requires supplied scenario data; no fabricated calibration|

See CLIENT_INPUTS.md for the exact checklist, JSON format and private NPZ path
interface. Arbitrary property/company columns can enter without optimizer changes;
source data, currencies, sale restrictions and scenario alignment remain essential.
Default benchmarks honor the same minimum holdings; equal weight is adjusted
across the remaining free budget when a minimum binds.

## Explorer

```
python -m emfin_capstone.explorer --precompute
```

Open http://127.0.0.1:8765. Multi-period mode now runs the default cumulative-payout
pipeline, with optional synthetic RE and minimum-holding controls. Single-date
companion mode remains available by unchecking multi-period. Repeated settings
are cached; main liability/budget grids can be precomputed. Exported HTML is
self-contained and disables controls rather than pretending to run Python.

The multi-period fan is NET wealth / initial wealth AFTER cumulative payouts,
not gross wealth falsely labeled as a post-payment funding ratio. Table figures
show the final payout; JSON contains all payout dates and uncertainty intervals.
SeqEP and ordinary EP coincide for the default single-class rank view; use a
non-null `view_vol_cap` for a mixed-class sensitivity rather than inventing a gap.

## Appendix methods and provenance

SeqEP, MPEP/CML, TSDR, positive-domain CRRA, real-estate observers and the legacy
full research run remain available. TSDR transitions are simultaneous; all path
probabilities belong to their actual path rows. Positive-surplus CRRA is exact
on its explicit finite-scenario domain, not equivalent to the surplus-scaled
CARA approximation. It prohibits simulated shortfalls, a different economic model.

No GPL code/dependency or upstream changes. CI still needs root `.github/workflows/`
installation via web UI because the token lacks workflow scope. Historical notes
in CHANGELOG_ENGINE.md are not current claims or reusable result tables.

## Reproducibility and audit notes

Raw series resolve through `emfin_v2/resources/data/raw/manifest.json` with SHA-256 checks, not
date-coded paths. `scripts/fetch_raw_drop.py` only stages a user-selected CSV;
review its source and terms before changing the manifest. Snapshot refresh
preserves pre-existing manifest notes. Refreshing data is a manual action.

Generated outputs are ignored, not committed. Run the default to reproduce them;
solve timing is environment-dependent. Historical generated multi-period output
is withdrawn. The current default fan includes configured synthetic proportional
liquidity haircuts. The appendix research funding fan is gross of its Meucci
liquidity overlay; it must not be read as liquid cash available to pay obligations.
The old single-date companion fan is also before payouts.

The unused `IlliquidHolding` time-to-cash helper was moved intact to
`legacy/research/liquidity_time_to_cash.py`, outside the installed V2 package.
It is not an active client valuation model. The synthetic RE sleeve
uses an explicit configured proportional haircut. Do not interpret it as an
empirically validated property sale-delay model.

See NOTICE.md and legacy/ATTRIBUTION.md. V2 is packaged as emfin-v2 2.1.0;
config/data/template resources travel with its wheel. The old emfin_capstone
command is a launch alias, not a dependency on the notebook.

No licence is assigned here to inherited project code: rightsholder consent is
needed before choosing a project licence. Dependency/data provenance does not
settle that choice. No GPL dependency has been added. The CI workflow remains a
template under `ci/`; activating a root GitHub workflow needs separate GitHub
workflow-write permission, which the current credential does not have.

## Ballast presentation and Wasserstein extension

The active UI now follows the Ballast design reference, but every model number
and plain-language verdict is generated from engine results. Capital, whole-week
horizon, named payout batches, risk-tolerance presets, RE source/minimum, EP
view strength and W1 risk-buffer controls are real local model inputs. No
instant solve or annual/ten-year forecast is implied by the 13-week default.

Named crisis-style cards are transparent simplified deterministic shocks, not
historically calibrated replays. The 2008-style illustrative equity shock can
produce a payout shortfall even when the stochastic calibration passes. That
conflict is displayed in red, not hidden. No invented time-to-cash or recurring
payout runway is supplied. Cash coverage is a ratio to the finite planned
payout schedule, not years of income support.

See [Wasserstein formulation](WASSERSTEIN.md): the default epsilon=0.00002 adds
robust RU risk envelopes under an explicit unrestricted-support L1 metric.
The current proposed example uses a 50/50 optimizer/cash blend, CE about
$6.857M, and about $30,979 per-date W1 gap buffer despite zero observed tail
gaps. Re-run for exact JSON. The radius is illustrative, not coverage-calibrated;
nominal CARA utility is NOT made distributionally robust.

See [Abu Dhabi private input](ABU_DHABI_PRIVATE_INPUT.md): the local private
observed apartment index replaces synthetic marginal calibration only when
selected. No workbook contents are shipped in the wheel or committed. The
public synthetic fixture stays separate. SFO dashboard inputs are labelled
placeholders until evidence is supplied; a full private model JSON can be run
on the local server, including the documented NPZ scenario-archive format.
