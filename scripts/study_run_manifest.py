"""Run manifest with hashes (review brief P1-4, owner ask 8 Nov 2026 12:20).

Stamps every study evidence bundle with:
  - code: git commit SHA, branch, dirty-state hash of tracked diffs
  - environment: python/numpy/scipy/pandas/cvxpy versions
  - configs: SHA-256 of every studies/**/*.json config and the bundled default config
  - data: SHA-256 of every shipped history CSV/JSON plus the recorded source
    manifest SHAs (data/manifest files already carry source provenance)
  - results: SHA-256 of each results JSON
Writes studies/RUN_MANIFEST.json (machine) and studies/RUN_MANIFEST.md (human).

Deterministic: no timestamps in the manifest content itself; the generator
version is pinned. Re-run after any study refresh; diff shows exactly what
moved. Private research provenance only - not a legal audit.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN_VERSION = 'run_manifest 1.0 (8 Nov 2026)'


def sha256(p, _buf=bytearray(1 << 20)):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.readinto(_buf)
            if not b:
                break
            h.update(_buf[:b])
    return h.hexdigest()


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT)] + list(args),
                          capture_output=True, text=True, check=True).stdout.strip()


def code_state():
    commit = git('rev-parse', 'HEAD')
    branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    diff = subprocess.run(['git', '-C', str(ROOT), 'diff', 'HEAD'],
                          capture_output=True, check=True).stdout
    untracked = git('ls-files', '--others', '--exclude-standard').splitlines()
    return dict(commit=commit, branch=branch,
                clean=not diff and not untracked,
                worktree_diff_sha256=hashlib.sha256(diff).hexdigest(),
                untracked_files=sorted(untracked))


def env_state():
    import numpy, scipy, pandas, cvxpy
    return dict(platform=sys.version.split()[0], numpy=numpy.__version__,
                scipy=scipy.__version__, pandas=pandas.__version__, cvxpy=cvxpy.__version__)


def hashed(paths, base=ROOT):
    out = {}
    for p in sorted(paths):
        p = Path(p)
        if p.is_file():
            out[str(p.relative_to(base))] = dict(sha256=sha256(p), bytes=p.stat().st_size)
    return out


def main():
    code = code_state()
    env = env_state()

    configs = list(ROOT.glob('studies/**/*.json'))
    configs = [p for p in configs if '/results/' not in str(p)]
    configs += list(ROOT.glob('emfin_v2/resources/configs/*.json'))

    data_files = []
    for sub in ('snapshot', 'singapore', 'fx', 'actual_etfs', 'raw', 'science'):
        data_files += list((ROOT / 'emfin_v2/resources/data' / sub).rglob('*'))
    data_files = [p for p in data_files if p.is_file()]
    data_files += list((ROOT / 'studies/tbill/data').rglob('*.json'))
    data_files += list((ROOT / 'studies/tbill/data').rglob('*.csv'))

    studies = {}
    for res in sorted(ROOT.glob('studies/*/results/*.json')):
        study = res.parts[-3]
        entry = studies.setdefault(study, {})
        entry[res.name] = dict(sha256=sha256(res), bytes=res.stat().st_size)

    manifest = dict(generator=GEN_VERSION, code=code, environment=env,
                    configs=hashed(configs), data=hashed(data_files),
                    study_scripts=hashed(list(ROOT.glob('studies/*/*.py')) +
                                         list(ROOT.glob('experiments/*.py')) +
                                         list(ROOT.glob('emfin_v2/*.py'))),
                    results=studies)
    out = ROOT / 'studies' / 'RUN_MANIFEST.json'
    out.write_text(json.dumps(manifest, indent=1) + '\n')

    lines = ['# Run manifest (generated, do not edit)', '',
             f"Generator: {GEN_VERSION}", '',
             f"- code: `{code['commit']}` on `{code['branch']}` "
             f"(clean: {code['clean']}; worktree diff sha256 `{code['worktree_diff_sha256'][:16]}...`)",
             f"- python {env['platform']}, numpy {env['numpy']}, scipy {env['scipy']}, "
             f"pandas {env['pandas']}, cvxpy {env['cvxpy']}",
             f"- {len(manifest['configs'])} config files, {len(manifest['data'])} data files, "
             f"{len(manifest['study_scripts'])} study/engine scripts hashed (SHA-256)", '',
             '## Evidence bundles (SHA-256 per results file)', '']
    for study, files in studies.items():
        lines.append(f'### studies/{study}/results')
        for name, h in files.items():
            lines.append(f"- `{name}` `{h['sha256'][:16]}...` ({h['bytes']} bytes)")
        lines.append('')
    lines += ['Full hashes: RUN_MANIFEST.json. Regenerate: `python scripts/study_run_manifest.py` '
              'after any study refresh; the git diff of this file shows exactly what moved.', '']
    (ROOT / 'studies' / 'RUN_MANIFEST.md').write_text('\n'.join(lines))
    print(f"wrote {out} and RUN_MANIFEST.md: {len(studies)} bundles, "
          f"{sum(len(v) for v in studies.values())} results files")


if __name__ == '__main__':
    main()
