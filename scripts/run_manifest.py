"""Automatic manifest block for results JSONs (refactor Phase 5).

manifest(c) records the provenance of one study run: code commit, source
tree SHA-256, config SHA-256, bundled-data manifest SHAs, seed family and
package versions. experiments.robustness.save attaches it automatically to
every results JSON it writes - never by hand.
"""
import hashlib
import json
import subprocess
from pathlib import Path


def _sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_tree_hash():
    sha = hashlib.sha256()
    for folder in ('emfin_v2', 'experiments'):
        for file in sorted(Path(folder).rglob('*.py')):
            sha.update(str(file).encode())
            sha.update(file.read_bytes())
    return sha.hexdigest()


def manifest(config=None):
    m = {}
    try:
        m['code_commit'] = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception as error:  # installed wheel outside a checkout
        m['code_commit'] = f'unavailable: {error}'
    m['source_sha256'] = source_tree_hash()
    if config is not None:
        m['config_sha256'] = hashlib.sha256(
            json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()
        m['seed_family'] = {k: config.get(k) for k in
                            ('seed', 'train_scenarios', 'validation_scenarios',
                             'evaluation_scenarios') if k in config}
        m['data_manifest_sha256'] = {
            name: _sha_file(path) for name, path in
            (config.get('history_manifests') or {}).items()}
    for package in ('numpy', 'scipy', 'pandas'):
        try:
            mod = __import__(package)
            m.setdefault('package_versions', {})[package] = mod.__version__
        except Exception:
            pass
    return m


if __name__ == '__main__':
    print(json.dumps(manifest(), indent=2))
