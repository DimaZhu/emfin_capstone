"""Manifest-resolved, hash-verified raw data, independent of dated paths."""
from pathlib import Path
import hashlib,json
from emfin_capstone import config


def series_file(series_id,root=None):
    root=Path(root) if root is not None else config.DATA_DIR.parent
    entries=json.loads((root/'data/raw/manifest.json').read_text())
    found=[e for e in entries if e['series'].split(':',1)[0]==series_id]
    if len(found)!=1:raise ValueError(f'exactly one manifest entry required for {series_id}')
    entry=found[0];path=(root/entry['path']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('manifest path escapes repo')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        raise ValueError(f'raw data hash mismatch for {series_id}')
    return path
