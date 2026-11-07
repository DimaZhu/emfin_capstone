"""Packaging boundary and byte-faithful preservation of the inherited tree."""
from pathlib import Path
import hashlib,json
import emfin_v2
from emfin_v2 import config
from emfin_v2.default_run import DEFAULT_CONFIG


def test_v2_identity_and_bundled_resources():
    assert emfin_v2.__version__=='2.1.0'
    assert DEFAULT_CONFIG.is_relative_to(config.PACKAGE_DIR)
    assert (config.DATA_DIR/'raw/manifest.json').is_file()
    assert (config.PACKAGE_DIR/'web/explorer.html').is_file()
    assert json.loads(DEFAULT_CONFIG.read_text())['wealth']>0


def test_original_archive_preserves_every_byte():
    root=Path(__file__).resolve().parents[1]
    provenance=json.loads((root/'legacy/original-provenance.json').read_text())
    for entry in provenance['files']:
        archived=root/'legacy/original'/entry['path']
        assert hashlib.sha256(archived.read_bytes()).hexdigest()==entry['sha256']


def test_compatibility_launcher_is_v2_only():
    root=Path(__file__).resolve().parents[1]
    text=(root/'emfin_capstone/__main__.py').read_text()
    assert 'emfin_v2.default_run' in text
    assert 'legacy.' not in text
