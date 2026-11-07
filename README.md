# emfin_capstone

Scenario-based funding-risk capstone engine. The default is an offline,
config-driven comparison with cumulative payouts and explicit validation.
The original notebook is retained as background, not the current entry point.

## Quickstart: one default, offline

Python >=3.10,<3.14 (dependency support; tests run on 3.10 here), from this clone:

```bash
pip install -r requirements.txt
python -m emfin_capstone --config configs/default.json
```

This compares 1/N, shrunk MV and one funding-aware model plus one stress panel.
It writes JSON, CSV, a text report and a self-contained HTML chart report to
`artifacts/default/`. The same config controls all input assumptions.
`python scripts/run_v2_engine.py` and installed `emfin-run` are equivalent.

For the local interactive multi-period/RE explorer:

```bash
python -m emfin_capstone.explorer --precompute
# Open http://127.0.0.1:8765
```

Tests: install `requirements-dev.txt`, then `python -m pytest tests/`.
Read [current model/status](docs/ENGINE_V2.md), [real-client input format](docs/CLIENT_INPUTS.md)
and [paper scope](docs/PAPER_STRUCTURE.md). Default data are real historical series;
liabilities, views, liquidity and RE assumptions are illustrative, not client evidence.
Earlier multi-period figures were withdrawn after fixing cumulative payout accounting.
Optional methods use `--research` and belong in appendices, not the headline default.

## Prerequisites (Poetry workflow, optional)

The Poetry workflow below remains supported for the notebook and live-data
work; regenerate the lock file with `poetry lock` on your own Python (the
committed lock was removed - it pinned Python 3.12-only builds and drifted).
For the reproducible engine runs prefer the Quickstart above.

Install the tooling once.

### macOS / Linux

```bash
# macOS (Homebrew)
brew install pyenv poetry
# add pyenv to your shell (zsh); then restart the shell or `source ~/.zshrc`
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
```

On Linux, install pyenv via the [official installer](https://github.com/pyenv/pyenv#installation)
and Poetry via the [official installer](https://python-poetry.org/docs/#installation).

### Windows (PowerShell)

```powershell
# pyenv-win — manages Python versions
Invoke-WebRequest -UseBasicParsing `
  -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" `
  -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
# then close and reopen PowerShell so pyenv is on PATH

# Poetry — dependency management
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

## Installation

Steps 1, 2 and 4 are identical on every platform; only creating/activating the
virtualenv in step 3 differs.

### macOS / Linux

```bash
# 1. Clone the repository
git clone https://github.com/TijsdeBoer/emfin_capstone.git
cd emfin_capstone

# 2. Install the required Python version and select it for this shell
pyenv install 3.12.2        # skip if already installed
pyenv shell 3.12.2

# 3. Create a virtualenv in .env/ and activate it
python -m venv .env
source .env/bin/activate

# 4. Install runtime + dev dependencies (includes Jupyter Notebook)
poetry install
```

### Windows (PowerShell)

```powershell
# 1. Clone the repository
git clone https://github.com/TijsdeBoer/emfin_capstone.git
cd emfin_capstone

# 2. Install the required Python version and select it for this shell
pyenv install 3.12.2        # skip if already installed
pyenv shell 3.12.2

# 3. Create a virtualenv in .env\ and activate it
python -m venv .env
.\.env\Scripts\Activate.ps1

# 4. Install runtime + dev dependencies (includes Jupyter Notebook)
poetry install
```

> On Windows **cmd.exe** instead of PowerShell, activate with `.\.env\Scripts\activate.bat`.
> If PowerShell blocks the activation script, allow it for the current user with
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Step 3 creates the `.env/` virtualenv (backed by the pyenv Python from step 2)
and activates it. Because the environment is already active, `poetry install`
installs into `.env/` rather than creating its own — populating it with the
runtime packages (pandas, numpy, scipy, plotly, cvxpy, yfinance) and the dev
tooling (Jupyter Notebook and its kernel stack). The `.env/` directory is
git-ignored.

To reactivate the environment in a new shell later, run `source .env/bin/activate`
(macOS/Linux) or `.\.env\Scripts\Activate.ps1` (Windows).

## Running the notebook

With the `.env` environment activated:

```bash
jupyter notebook notebooks/portfolio_optimization.ipynb
```

## Notes

- **Live prices.** The `emfin_capstone.toolbox.price` module fetches prices live
  (via yfinance) and caches responses under `data/cache/`, which is created
  automatically on first run. The `data/` directory is git-ignored.

## Current interfaces

- Default: `python -m emfin_capstone --config configs/default.json`.
- Explorer: `python -m emfin_capstone.explorer --precompute`.
- Static explorer export: `python -m emfin_capstone.explorer --export /tmp/explorer.html`.
- Chronological development study: `python scripts/validate_chronological.py`.
- Exact positive-domain CRRA experiment: `python scripts/power_utility_sensitivity.py`.
- Legacy research catalogue: `python scripts/run_v2_engine.py --research` (may be infeasible;
  its older multi-period headline results are superseded).

No new web framework is required. The app binds only to localhost; no external
CDN or analytics. Keep private client inputs out of this repository. No live
account access is needed for any default run.
