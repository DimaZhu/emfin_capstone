# Illustrative funding-risk engine: current status

This is an illustrative implementation, not a calibrated SFO recommendation.
The default branch is `engine-v2` in TijsdeBoer/emfin_capstone. The dated development
history is in CHANGELOG_ENGINE.md; its old numbers are superseded, not current results.

## One argument

How do scenario-tail and liquidity assumptions change funding-risk allocations
for an illiquid family balance sheet? Compare 1/N, a common shrunk MV benchmark
and a liability-aware model, then test one stress. See PAPER_STRUCTURE.md.

## Current pipeline

Pinned weekly equity/yield/spread/cash invariants -> time/state flexible weights
-> unit-invariant correlation shrinkage and structural mean shrinkage -> scenarios
-> exact synthetic-bond repricing and illustrative liquidity overlay -> view pooling
-> CARA allocation with CVaR/funding constraints -> paired fresh Monte Carlo evaluation.

- SeqEP implements class-ordered view heuristics from the public paper.
- MPEP applies views to actual path probabilities, including multiple CML views.
  Its tail-count search is our approximate coordinate search, not proprietary code.
- TSDR is empirical successor-state resampling. Transition updates are simultaneous.
  Chosen-state convergence is not strict stationary initialization.
- Robust CML constrains maximum loss from initial wealth, not peak-to-trough drawdown,
  under a finite convex hull of nominal/stressed measures using one shared tail threshold.
  It is not unrestricted entropy-ball or Wasserstein DRO. The reference uses 500 paths.
- Surplus-scaled CARA is a one-step preference sensitivity, not exact CRRA power utility.
  A separate experimental finite-scenario positive-domain CRRA solver now exists
  in toolbox/power_utility.py; it is not the default CARA model. The surrogate
  negative-surplus floor is numerical and has no economic interpretation.
- Real-estate observation/unsmoothing machinery is merged. Client-calibrated real estate
  is not part of the default six-sleeve optimization. A seven-sleeve synthetic RE
  example now runs through the actual optimizer with optional minimum holdings;
  the family company remains absent because no inputs were supplied.

## Evidence versus assumptions

|Input|Status|What it establishes|
|---|---|---|
|Pinned DFUS/DFAI/DFAE, Treasury yield, IG OAS, 3-month rate|Real historical series|Reproducible historical inputs, not predictive truth|
|BIS/FRED UAE RPPI|Real, UAE-wide, ends 2024Q1|Observer-method example, not current Abu Dhabi pricing|
|$35M/$60M obligations, payout dates and stochastic shocks|Illustrative|Exercises funding constraints, not a real client's needs|
|Committee views, BL/reference weights, risk tolerance and budgets|Illustrative|Sensitivity experiments only|
|Liquidity costs/volume parameters and state multipliers|Illustrative|Model behavior, not an execution-cost estimate|
|Real estate latent truth tests|Synthetic known truth|Method checks, not empirical calibration|
|Family company holdings/cash flows|Not supplied|No conclusion about client exposure|

## Validation and limits

Fresh paired Gaussian/Student-t Monte Carlo draws test allocations under a fitted
model. The empirical regime judge overlaps estimation history; its differing
rankings show model sensitivity, not proven predictive edge. The SAA study uses
12 independent 2k training sets and one 50k common holdout. Its t intervals are
conditional on that holdout and model, not generalization guarantees.

Chronological development folds reserve the final 26 weeks without evaluating
them in that protocol. The current-allocation runner uses full history, so its
outputs are not a sealed historical test. Development-fold tail estimates have
only 1-2 nonoverlapping quarterly paths: insufficient for a 95% tail guarantee.
Failed candidate solves are explicitly unavailable, never treated as safe scores.

Correlation shrinkage preserves each invariant's units/variance. The former raw
scaled-identity target inflated money-market variance and is superseded. Refit nu:
development conditional fits are about 6.3-7.3; validation selects nu=8. Conditional
MLE is not joint t MLE, and weekly t draws do not aggregate to a t with unchanged nu.

Solver results must pass status, finite-value and normalized residual checks.
Some optional TSDR/fat-tail/large-path robust cases remain numerically unavailable.
The CML row's funding target may fail fresh Monte Carlo evaluation: path-loss risk
and liability funding risk are separate constraints. No blanket safety claim.

## Run and inspect

- `python scripts/run_v2_engine.py`: current illustrative comparison.
- `--student-t=8` or `--student-t=auto`: fat-tail sensitivity (auto is constrained nu MLE).
- `--tsdr`: optional resampled-path contrast; numerical failure is reported honestly.
- `--no-surplus-cara`: skip the preference approximation (`--no-crra` remains an alias).
- `python scripts/validate_chronological.py`: development selection, sealed final window.
- `python scripts/surplus_sensitivity.py`: imposed CARA-preference sensitivity, not a causal client effect.
- `python scripts/run_real_estate_allocation.py`: seven-sleeve synthetic RE allocation.
- `artifacts/report/`: structured JSON, benchmark/allocation CSV and appendix text.

After installing the package, `emfin-run` is the same engine entry point. The
repo-root CI workflow is still blocked by the token's missing workflow scope;
the misplaced template remains at ci/.github/workflows/tests.yml until web-UI repair.
No GPL dependency or source has been incorporated. Nothing is pushed upstream.

## Visual companion

`python -m emfin_capstone.explorer --precompute` starts the local explorer.
`--export artifacts/report/explorer.html` creates a standalone static snapshot.
It offers views, funding-tail budget, liability, Student-t, SeqEP and stress controls,
allocation bars, a mean/variance frontier with benchmark points, CE/gap tables,
and a gross funding-ratio fan. Nine main-slider configurations can be precomputed;
all repeated configurations are cached in memory. The example uses a 1k training
set and 8k fresh nominal evaluation set, so it is fast but not the full engine.
It does not contain the full multi-period liability, robust CML or RE pipeline.

## Exact positive-surplus utility experiment

`python scripts/power_utility_sensitivity.py` exercises a separate exact CRRA
objective on strictly positive surplus. Power and log utilities are expressed
directly as concave CVXPY objectives, with explicit surplus >= epsilon constraints
on every supplied scenario. Infeasible domains fail loudly; there is no clipping
of negative surplus into the utility. Tests verify risk-aversion comparative
statics and rejection of an impossible funding domain.

This is a different economic model: it forbids every simulated shortfall, whereas
CARA can assign utility to negative surplus and permit a funding-gap budget.
Finite-scenario feasibility does not guarantee positive surplus for an unbounded
population model. Results use a synthetic two-asset example, not a client case.
