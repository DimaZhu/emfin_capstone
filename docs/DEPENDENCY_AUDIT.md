# Dependency audit - 7 November 2026

## What was checked

This is a point-in-time advisory scan, not a claim that software is secure.
The V2 application and the preserved original environment are different things.
Never install `legacy/original` to run V2.

| Scope | Result |
| --- | --- |
| Active runtime, 17 installed dependencies | No known vulnerabilities in pip-audit |
| Active venv including upgraded pip/setuptools/wheel/packaging, 21 packages | No known vulnerabilities in pip-audit |
| Optional research/notebook resolution on Python 3.11, 115 packages | No known vulnerabilities in pip-audit |
| GitHub open Dependabot alerts | 18, all on `legacy/original/poetry.lock` |

GitHub's 18 include one critical, seven high, eight moderate and two low alerts.
The scanner's separate historical-lock scan returned 17 entries in six packages,
including a duplicate certifi advisory. It missed GitHub's nbconvert finding.
Scanner feeds and alias handling differ; the smaller count does not override
GitHub's alerts. No alerts were dismissed or hidden.

| Archived package | GitHub alerts | Severities |
| --- | --- | --- |
| certifi | 1 | critical |
| jupyterlab | 4 | high, medium |
| nbconvert | 1 | high |
| notebook | 2 | high, medium |
| setuptools | 1 | low |
| tornado | 6 | high, low, medium |
| urllib3 | 3 | high, medium |

## Safe changes made

- Raised build-tool floors to setuptools 84.1 and wheel 0.48; README bootstrap
  also upgrades pip to at least 26.2. Existing environments must run that command.
- `requirements-dev.txt` now installs core test tools only.
- `requirements-data.txt` adds optional live-data and plotting tools, with certifi,
  urllib3 and setuptools security floors.
- `requirements-notebook.txt` adds notebooks, JupyterLab >=4.6.4,
  nbconvert >=7.17.2 and Tornado >=6.6. This optional stack requires Python 3.11+.
  Tornado 6.6 is published but is incompatible with Python 3.10; a 3.10 resolver
  only showing 6.5.10 does not mean the fixed release is unpublished.
- Original archive and provenance hashes were preserved byte-for-byte.

The engine itself remains Python 3.10-compatible. Do not weaken the notebook
security floor to install that optional stack on 3.10. Use a separate 3.11+ venv.
Do not expose a notebook server or convert untrusted notebooks casually.

## CI repair

The root workflow is active, created by Tijs at a33d37d. Its first run passed all
196 tests but failed the installed-wheel path assertion. With system-site-packages,
pip could see the already installed V2 package and skip the temporary install.
The smoke test now creates a genuinely isolated venv, installs dependencies and
the built wheel there, and checks actual import/resource locations outside the
clone. Subprocess failures now print their captured diagnostics. The redundant
inactive `ci/.github/workflows/tests.yml` template was removed; the root workflow
was preserved unchanged. Local 3.10 and 3.11 tests both passed (196); the new
isolated 3.11 smoke test passed. GitHub rerun outcome is tracked separately.

## Reproduce

```bash
python -m pip install --upgrade "pip>=26.2" "setuptools>=84.1" "wheel>=0.48"
python -m pip install . -r requirements-dev.txt
python -m pytest tests/ -q
python scripts/smoke_installed.py
# Install pip-audit in an audit environment, not as an application dependency.
python -m pip freeze > resolved-environment.txt
# Remove the local emfin-v2 line (not a PyPI package) before auditing dependencies.
python -m pip_audit -r resolved-environment.txt --no-deps --disable-pip
```

Scan the actual installed/resolved versions rather than only four top-level pins.
`--no-deps` is valid only when the file already contains the complete environment.
The optional stack was resolved and scanned on Python 3.11.17. Security floors are
not a lockfile, so future resolutions and platforms need fresh scans.

## Sources

- Live repository alerts: https://github.com/TijsdeBoer/emfin_capstone/security/dependabot
- Initial CI run: https://github.com/TijsdeBoer/emfin_capstone/actions/runs/42354543938
- https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w
- https://github.com/tornadoweb/tornado/security/advisories/GHSA-pcg2-g6cj-q92c
- https://github.com/tornadoweb/tornado/security/advisories/GHSA-r4j5-9xpp-3985
- https://github.com/tornadoweb/tornado/security/advisories/GHSA-pw9p-v7r6-gx4p
- https://pypi.org/project/tornado/
- https://github.com/jupyter/nbconvert/security/advisories/GHSA-pjvx-prjx-h659

## Final reproducibility check, 7 November 2026

The newest CI run at viewer commit 387641a returned a verified cash fallback on the multithreaded hosted linear-algebra stack. Three pre-existing tests assumed the default was always an optimized/non-cash allocation. Local single-threaded rerun passed all 224 tests in 52.42 seconds. The test bootstrap now fixes OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and MKL_NUM_THREADS to 1, matching the grid execution environment; no risk tolerances or solver feasibility checks were weakened. A verified fallback remains a supported, explicitly reported outcome, not an optimized allocation. A new CI result is still required after this change.

## Resolution - 8 November 2026

`legacy/original/poetry.lock` was deleted (owner decision, 8 Nov 2026), removing
the source of all 18 GitHub Dependabot alerts. The deleted file's SHA-256 is
recorded in `legacy/original-provenance.json` under `removed_files`. The legacy
workflow documentation already instructed regenerating the lock with
`poetry lock`; `pyproject.toml` stays because it is that workflow's manifest,
carries no alerts, and resolving from it pulls current patched versions.
Alerts close on GitHub's side once this lands on the default branch.
