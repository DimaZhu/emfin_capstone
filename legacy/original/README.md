# emfin_capstone

Portfolio optimization capstone project. The analysis lives in
`notebooks/portfolio_optimization.ipynb` and builds on a small library
(`emfin_capstone/`) for live price fetching and portfolio data types.

## Prerequisites

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
git clone https://github.com/DimaZhu/EMFin_2026_capstone_project.git
cd EMFin_2026_capstone_project

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
git clone https://github.com/DimaZhu/EMFin_2026_capstone_project.git
cd EMFin_2026_capstone_project

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
