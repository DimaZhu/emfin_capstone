"""Tests for the T-bill asset addition (studies/tbill).

Identities are hand-computed; the default bundled registry must be untouched.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_builder_constant_rate_identity():
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_tbill', ROOT / 'scripts/build_tbill_history.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rate = pd.Series(0.04, index=pd.date_range('2020-01-03', periods=20, freq='W-FRI'))
    index = mod.build(rate)
    # constant rate -> no rate-change term; weekly growth exp(0.04/52) exactly
    ratios = np.diff(np.log(index.to_numpy()))
    np.testing.assert_allclose(ratios, 0.04 / 52, rtol=0, atol=1e-15)


def test_builder_rate_step_identity():
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_tbill', ROOT / 'scripts/build_tbill_history.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rate = pd.Series([0.04] * 10 + [0.05] + [0.05] * 9,
                     index=pd.date_range('2020-01-03', periods=20, freq='W-FRI'))
    index = mod.build(rate)
    logs = np.diff(np.log(index.to_numpy()))
    # the step week (Friday 10 -> 11): carry at the prior rate minus duration * +1pp
    np.testing.assert_allclose(logs[8], 0.04 / 52 - 0.25 * 0.01, rtol=0, atol=1e-15)
    np.testing.assert_allclose(logs[9], 0.05 / 52, rtol=0, atol=1e-15)


def test_bundled_registry_and_bundle_unchanged():
    # No silent default change: the bundled registry has no tbill and the
    # bundled history bundle has no tbill manifest.
    reg = json.loads((ROOT / 'emfin_v2/resources/configs/assets.json').read_text())
    assert 'tbill' not in [a['id'] for a in reg['assets']]
    index = json.loads((ROOT / 'emfin_v2/resources/data/actual_etfs/index.json').read_text())
    assert 'tbill' not in index


def test_tbill_manifest_and_csv_contract():
    from emfin_v2.asset_history import load_total_return
    reg = json.loads((ROOT / 'studies/tbill/registry_tbill.json').read_text())
    asset = next(a for a in reg['assets'] if a['id'] == 'tbill')
    s = load_total_return(asset, ROOT / 'emfin_v2/resources/data/actual_etfs/tbill-manifest.json')
    assert s.index.is_monotonic_increasing and (s > 0).all()
    # sanity on the constructed series: never a weekly move beyond +/-1%
    weekly = np.diff(np.log(s.resample('W-FRI').last().to_numpy()))
    assert np.abs(weekly).max() < 0.01


def test_tbill_fit_carry_unshrunk_and_window_unchanged():
    from emfin_v2.default_run import validate_config, setup
    base = validate_config(json.loads((ROOT / 'studies/tbill/config_baseline.json').read_text()))
    tb = validate_config(json.loads((ROOT / 'studies/tbill/config_tbill.json').read_text()))
    frame_b, mu_b, _ = setup(base)
    frame_t, mu_t, _ = setup(tb)
    # same weekly window: the 1981 T-bill history must not shift the common grid
    assert frame_b.index.equals(frame_t.index)
    assert 'tbill' in frame_t.columns and 'tbill' not in frame_b.columns
    # carry is structural, not shrunk toward the risky cross-asset mean
    raw_mean = frame_t['tbill'].to_numpy().mean()
    i = list(frame_t.columns).index('tbill')
    np.testing.assert_allclose(mu_t[i], raw_mean, rtol=1e-12, atol=1e-15)
    # and it is far from the shrunk risky target (would be pulled up otherwise)
    assert mu_t[i] * 52 < 0.07  # ~4-5% annualized, not equity-like


def test_anchor_resolution_default_and_tbill(tmp_path):
    from emfin_v2.default_run import validate_config
    base = validate_config(json.loads((ROOT / 'studies/tbill/config_baseline.json').read_text()))
    tb = validate_config(json.loads((ROOT / 'studies/tbill/config_tbill.json').read_text()))
    assert 'anchor_asset_id' not in base
    assert tb['anchor_asset_id'] == 'tbill'
    reg_ids = [a['id'] for a in tb['asset_registry']['assets'] if a['enabled']]
    assert 'tbill' in reg_ids


def test_anchor_rejects_unknown_and_property(tmp_path):
    from emfin_v2.default_run import run
    for bad in ('nope', 'sg_property'):
        c = json.loads((ROOT / 'studies/tbill/config_tbill.json').read_text())
        c['anchor_asset_id'] = bad
        c['train_scenarios'] = c['validation_scenarios'] = c['evaluation_scenarios'] = 20
        with pytest.raises(ValueError):
            run(c, output=str(tmp_path / bad))
