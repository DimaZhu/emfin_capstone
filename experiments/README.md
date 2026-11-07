# Reproducible grid and scientific evidence

> Active default:52-week horizon, editable$250k/month x12 placeholder, W1 on with a visible20% per-payment tail-gap budget. Interactive dashboard uses an explicitly coarse tier. Earlier13-week reference/grid/lookup artifacts are archived, not current one-year evidence. No new grid has been run. See docs/ONE_YEAR_MONTHLY.md (or ONE_YEAR_MONTHLY.md from docs).

## Commands

```bash
python -m pip install . -r requirements-science.txt
# List the exact 729 points without solving.
python -m experiments.grid --dry-run
# Resumable full grid. Start with one worker; benchmark memory before increasing.
python -m experiments.grid --output artifacts/grid729 --workers 3 --max-jobs 6
# Repeat the same command to run the next six pending cells.
# One command for a small reference report plus one-factor studies and tests:
python -m experiments.scientific_report --config experiments/configs/reference.json --output artifacts/scientific --workers 3
```

The reference uses reduced scenario counts to make a reproducible demonstration,
not publication-quality results. `grid729.json` preserves the engine's ordinary
scenario counts. One command runs all nine reference cells, 32 explicit one-factor
studies, the test suite, benchmark evaluation, proof checks and report rendering.
`--stage grid` runs only the grid; `--stage analysis` rebuilds figures from stored
rows; `--skip-tests` visibly records tests not run. `--skip-studies` skips the
additional study grid, not the grid itself. `--max-jobs` bounds new work per grid.
No upload, Google Sheet mutation or deployment is performed by these commands.
`grid729-prototype.json` is a separate coarse lookup tier (100 training / 200
validation / 300 evaluation scenarios, two seeds for each held-out split). It
must not be presented as the full-fidelity grid. Each cell has an 80-second
hard process timeout, recorded as a numerical error, not an infeasibility verdict.
Reports render separately from simulation hashes, so a chart formatting fix does
not rerun unchanged simulations; report-code provenance is also recorded.

## Six-axis design

3 risk profiles x 3 total payout/capital ratios x 3 timing profiles x 3 minimum
RE holdings x 3 W1 radii x 3 RE/equity dependence assumptions = 729 points.
Capital is $100M, horizon 13 weeks. Every generated config records exact payout
amounts and weeks. RE is synthetic, with an explicit 4% annual forward log-price
view, 12% volatility, 3% net rent and no planned sale by default. None is client
calibration. The generator refuses private archives and forces synthetic RE.

The scientific report's 2-D map is one fixed slice, not an average across hidden
inputs. Parallel-coordinate plots preserve the six axes. The reference grid is
nine cells at one profile/timing/radius/dependence setting. It is not a completed
729-point grid. Pending/error/unavailable cells must remain visible.

## Storage and resumption

- `grid.sqlite`: job ID, canonical config, exact provenance, status, runtime,
  error and result path. An OS file lock prevents concurrent writers.
- `manifest.json`: current experiment definition, code/data/dependency hashes
  and job IDs. Changing point/config/code/data versions creates new IDs.
- Per-job `results.json`, dashboard HTML and matched `benchmarks.json`.
- `summary.csv`, `summary.json`, `summary.parquet`: analysis/lookup tables.
- Figure SVG/PNG, raw benchmark batches, proof tables, test XML/log and report HTML.

A killed local writer leaves running jobs; the next owning writer resets those
to pending and reruns them. No money or external writes are involved. Completed
rows remain. Old versions stay in the ledger, but exports use only the current
manifest's IDs. An error is never relabelled a feasible allocation. `--retry-errors`
is explicit. For portability, move the whole output folder and update stored
absolute paths if needed; a path is not a data backup.

The runner pins BLAS threads to one per worker. More workers can increase memory,
solver contention and wall time. The model may retry solvers with a time cap;
a small reference's timing cannot be multiplied into a reliable full-grid ETA.
Report measured completed count, total wall time and per-cell timing distribution.

## Four scientific sections

1. Testing: actual pytest XML/log, claim-to-test mapping, entropy-pooling residual
   sweep and a tiny known-solution solver-tolerance study.
2. Benchmarks: 1/N, shrunk MV, proposed where available, cash respecting the same
   RE floor and minimum variance. All are scored on identical held-out scenario
   seeds. Benchmarks share minima/no-leverage, but do not all enforce risk budgets.
   Funding feasibility is reported separately from return. Paired CE differences
   and conditional Student-t batch intervals are exported.
3. Proof points: payout conservation, smoothing inversion, no spendable unsettled
   receivable, one-off sale costs, EP residuals, a known analytic portfolio plus
   exhaustive two-asset grid, zero-radius limit and finite W1 transport LP.
4. Sensitivities: 1-D curves/tornado, 2-D funding map, six-axis grid view, RE drift,
   vol/dependence/rent/sale cost/settlement, W1 radius, funding budget, scenario count,
   seeds and explicit 4% forward vs 12.6% illustrative boom-sample scenarios.
   A synthetic 45-return history shows assumed-alpha bootstrap uncertainty.

The synthetic boom comparison is not a copy of the private Abu Dhabi series.
No Sobol indices are asserted without a justified joint input distribution.
Scenario count/seed panels are small numerical checks, not asymptotic convergence
proof. Fresh Monte Carlo held-out paths are not chronological historical OOS.
Mathematical bounds, numerical verification and economic forecasting claims are
kept separate. Passing tests and zero observed losses never establish future safety.

## Shared viewer boundary

Only a synthetic-source export may enter the prepared Apps Script lookup viewer.
A Google Sheet mirror is an optional future authorized destination, not a side
channel for the private import. Store the compact summary table, not scenario
paths. The viewer must state requested versus matched inputs, refuse out-of-range
requests, show nearest-point distance and never interpolate a funding verdict.
No Apps Script deployment or third-party sharing is authorized yet.
