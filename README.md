# EMFin capstone - liability-aware funding engine (v2)

Private research fork of the INSEAD EMFin capstone: a scenario-based engine that
allocates wealth across risky and safe assets so that a stream of planned payouts
is funded within explicit loss limits. Owner: Tijs de Boer. Private use only;
nothing here is cleared for public redistribution (market-data terms, no LICENSE
on inherited code).

The engine compares three policies under one accounting core:

- **1/N** equal weighting,
- **shrunk mean-variance** (Ledoit-Wolf style shrinkage),
- **the funding-aware model**: cumulative payout accounting, finite-moment
  Gaussian variance-mixture return paths, and an independent final all-risk
  judge that can reject the optimizer's choice.

Explicit legacy Student-t modes remain available for archived reproducibility,
not for finite population price moments. Older multi-period results were
withdrawn after the cumulative payout-accounting correction.

## Install and run

Python 3.10-3.13 (developed and tested on 3.10). From this clone:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install .
python -m emfin_capstone           # default run, writes reports to ./artifacts/default/
emfin-explore                      # interactive dashboard on http://127.0.0.1:8765
```

`python -m emfin_v2` and `emfin-run` are equivalent entry points. The installed
implementation is the `emfin_v2` package (distribution name `emfin-v2`);
`emfin_capstone` is only a compatibility launch name. Do not install
`legacy/original` for v2.

The default config, historical CSVs, provenance manifests and HTML template ship
inside the wheel: a default run needs no network, credentials or external data.
To customize, copy the bundled config and edit:

```bash
python -c "from emfin_v2.default_run import DEFAULT_CONFIG; from shutil import copyfile; copyfile(DEFAULT_CONFIG, 'my-config.json')"
python -m emfin_capstone --config my-config.json --output my-report
```

Reports are JSON, CSV, Markdown and self-contained HTML.

## Repository map

| Path | Contents |
|------|----------|
| `emfin_v2/` | The engine (installed package). One accounting core: `event_ledger.run_event_ledger`. |
| `emfin_capstone/` | Compatibility launcher only. |
| `tests/` | Full pytest suite (430 tests). Golden fixtures pin the accounting bit-for-bit. |
| `studies/` | Dated, self-contained research studies with code, results and reports. See `studies/README.md`. |
| `docs/` | Engine reference, protocols, audits and planning docs. See `docs/README.md`. |
| `docs/paper/` | Paper outline and claims-to-evidence map (living documents). |
| `docs/evidence/` | Frozen evidence bundles (reports, logs, hashes) per study date. |
| `scripts/` | Data-ingest and utility scripts (raw data is pinned and hashed). |
| `experiments/`, `prototype/` | Exploratory configs and prototypes, not part of the engine. |
| `legacy/` | Original fork material and notebooks, kept for attribution; not installed. |
| `.github/workflows/` | CI (below). |

## Testing and CI

```bash
python -m pip install -r requirements-dev.txt   # adds pytest and entropy-pooling
python -m pytest tests/ -q
```

- `tests.yml` runs the suite on every push and pull request.
- The two study runners (`backtest_20261108.yml`, `backtest_chained_20261109.yml`)
  are **manual `workflow_dispatch` only**. Nothing launches a solver run
  automatically; each run consumes significant Actions minutes and is started
  explicitly by the owner.

## Current evidence (9 Nov 2026)

- Walk-forward backtest, 78 quarterly folds 2007-2026: `studies/backtest_20261108/REPORT.md`.
- Offline chained-wealth analysis + stationary bootstrap: `studies/offline_chained_20261109/REPORT.md`.
- Empirical Wasserstein-radius diagnostic: `studies/radius_20261108/REPORT.md`.
- Claims and what supports them: `docs/paper/CLAIMS_EVIDENCE_MAP.md`.

Headline: the engine is insurance, not outperformance - it funds every payout
with controlled drawdowns and is not expected to beat 1/N on compounded wealth.

## Model limits

Historical market series are real, with source terms in the bundled manifests.
Liabilities, views, liquidity and real-estate assumptions are illustrative, not
client data. Validation may select an explicit optimizer/cash mixture; the final
all-risk check can still reject it, and a failed final test never silently
triggers recalibration. Zero observed Monte Carlo losses are not an upper bound
on unseen tail losses. This is research, not an investment recommendation.

See `docs/ENGINE_V2.md` for the model reference and `NOTICE.md` for attribution.
