# EMFin V2

Tijs de Boer's standalone funding-risk engine, version 2.0.0.
It compares 1/N, shrunk mean-variance and a funding-aware model using cumulative
payout accounting, Student-t paths and nominal/stressed posterior risk checks.

## Run it on your machine

Python 3.10-3.13 is declared; tested here on Python 3.10.12. From this clone:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
python -m emfin_capstone
emfin-explore
# Open http://127.0.0.1:8765
```

`python -m emfin_v2` and `emfin-run` also run V2. `emfin_capstone` is only a
compatibility launch name. The installed implementation is `emfin_v2`; the
Python distribution is `emfin-v2`. You can run it from any working directory.
Do not install `legacy/original` for V2.

The default config, historical CSVs, provenance manifests and HTML template ship
inside the wheel. A normal default run does not need the original repo, notebook,
Yahoo, Fortitudo, a network connection or credentials. Dependency installation
needs a package index or predownloaded wheels. The explorer binds only to your
own machine. Its synthetic RE controls do not connect to any property service.

Reports go to `artifacts/default/` in your current directory, not site-packages.
The default took about 2.2 seconds in this environment; RE exploration can take
longer. Results include JSON, CSV, Markdown and self-contained HTML. For a custom
config, copy the bundled example before editing:

```bash
python -c "from emfin_v2.default_run import DEFAULT_CONFIG; from shutil import copyfile; copyfile(DEFAULT_CONFIG, 'my-config.json')"
python -m emfin_capstone --config my-config.json --output my-report
```

## Model limits

Historical market series are real, with source terms in bundled manifests.
Liabilities, views, liquidity and RE assumptions are illustrative, not client data.
Fresh stressed validation selects an explicit optimizer/cash mixture in the
pinned example. It is not a globally optimal allocation or a safety guarantee.
Zero observed Monte Carlo losses are not an upper bound on unseen tail losses.
Older multi-period results were withdrawn after correcting cumulative payouts.

Read [model details](docs/ENGINE_V2.md), [client input format](docs/CLIENT_INPUTS.md)
and [paper scope](docs/PAPER_STRUCTURE.md). Optional research catalogue:
`python -m emfin_v2 --research --help`. Its original stochastic payout example
is infeasible under corrected accounting and reports unavailable.

## Package and test it

```bash
python -m pip wheel . --no-deps --wheel-dir dist
python -m pip install -r requirements-dev.txt
python -m pytest tests/ -q
python scripts/smoke_installed.py
```

The smoke test builds a wheel, installs into a separate temporary virtual
environment, leaves the clone, runs both launch names and installed console
commands, and verifies the report and bundled resources. It uses available
runtime dependencies through system-site-packages; use a fresh venv without that
option to check dependency downloading on your own machine.

## V2 and legacy boundary

`emfin_v2/` is the active installed model. `emfin_capstone/` is a small launcher.
`legacy/original/` preserves the original `main` tree at the recorded commit;
`legacy/notebooks/` and `legacy/README-before-v2.md` preserve the older workflow.
They are excluded from the wheel. Git history and the GitHub fork relationship
are preserved. This version does not alter or contact the upstream project.

Some shared utilities in the active V2 package are derived from the inherited
project. A new package name does not erase that provenance. See [NOTICE](NOTICE.md)
and [legacy attribution](legacy/ATTRIBUTION.md). No new open-source licence is
granted here. This local/fork version is for Tijs's environment; licensing and
data redistribution should be settled before a separate public release. The
`v2.0` tag identifies a reproducible code state, not a licence grant.
