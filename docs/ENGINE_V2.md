# Current default: one funding-risk argument

This is an illustrative implementation, not a calibrated SFO recommendation.
The active/default branch is `engine-v2` in TijsdeBoer/emfin_capstone.

## One command, one config

After installing `requirements.txt`, run:

```
python -m emfin_capstone --config configs/default.json
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
The final evaluation reports net CE about $6.866M for the proposed model, with
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
