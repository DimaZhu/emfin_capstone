> Private research fork. Default: VTI, VWO, GLD, IEF, an explicit0%-rate cash
> account, and fixed initial10% Singapore property with SGD/USD risk.
> Data calibrate simulated paths, not an actual-history backtest. Yahoo terms
> risk accepted by owner for private use; no public redistribution approved.
> `legacy.json` explicitly retains the former liquid universe. See
> [asset/data notes](docs/ASSET_REGISTRY.md) and [FX model](docs/FX_MODEL.md).

# EMFin V2

> Active default:52-week horizon, editable$250k/month x12 placeholder, W1 on with a visible20% per-payment tail-gap budget. Interactive dashboard uses an explicitly coarse tier. Earlier13-week reference/grid/lookup artifacts are archived, not current one-year evidence. No new grid has been run. See docs/ONE_YEAR_MONTHLY.md (or ONE_YEAR_MONTHLY.md from docs).

Tijs de Boer's standalone funding-risk engine, version 2.1.0.
It compares 1/N, shrunk mean-variance and a funding-aware model using cumulative
payout accounting, Student-t paths and nominal/stressed posterior risk checks.

## Run it on your machine

Python 3.10-3.13 is declared; tested here on Python 3.10.12. From this clone:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install --upgrade "pip>=26.2" "setuptools>=84.1" "wheel>=0.48"
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
The Wasserstein-enabled default took about 9 seconds in this environment; RE exploration can take
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
commands, and verifies the report and bundled resources. It installs runtime dependencies
into a fresh venv without system-site-packages. This check needs package-index
access (or a configured local wheel cache).

Core test tools do not install Jupyter. For optional live-data/plot tooling use
`requirements-data.txt`. Optional notebooks use `requirements-notebook.txt` in a
separate **Python 3.11+** environment so patched Tornado 6.6 can be installed.
The engine itself still supports Python 3.10. See the [dependency audit](docs/DEPENDENCY_AUDIT.md)
for scan scope, security floors and historical archive findings.

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

## Ballast dashboard and new risk/data controls

The dashboard follows the Ballast design reference: situation, plain-language
brief, allocation buckets, expected outcome, risk/stress, guardrails and SFO
inputs. Values come from the engine, not the reference's toy numbers. It has
explicit Recompute, expandable evidence and baseline overlays; static exports
disable model inputs. Fonts fall back to local system fonts, with no CDN.

Wasserstein W1 risk bounds are enabled at an illustrative radius in the default;
see [metric, derivation and limits](docs/WASSERSTEIN.md). This is not a robust
exponential-utility objective or a statistical coverage guarantee.

The RE source picker defaults to a local private Abu Dhabi sheet import when RE
is enabled. No REIDIN/ValuStrat data are shipped in the public wheel. The RE sleeve
is off in the ordinary default, so the default runs without that import. See
[private import instructions](docs/ABU_DHABI_PRIVATE_INPUT.md). Missing imports
are reported, not replaced silently by synthetic data.

The SFO section contains a default placeholder and evidence checklist, template
download, and a live-local full JSON config runner. Real client evidence remains
absent until supplied. The small public synthetic fixture is only for testing.

## RE sensitivity and sale timing

The RE panel now includes assumed monthly unsmoothing, explicit equity dependence,
net rent, a planned sale/settlement schedule and short-history bootstrap cases.
Property marks are separate from spendable funding: unsold property cannot pay a
due obligation. See [assumptions, equations and limits](docs/REAL_ESTATE.md).
