"""Gate tests for the chained-wealth walk-forward backtest study.

Covers the chained-specific invariants: wealth scaling in fold_config,
absolute liabilities, state schema with per-method wealth, and the fold
calendar shared with the reference-wealth study.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bt = _load('backtest_chained', ROOT / 'studies/backtest_chained_20261109/backtest.py')
bt1 = _load('backtest_ref', ROOT / 'studies/backtest_20261108/backtest.py')


def test_fold_calendar_matches_reference_study():
    assert bt.FOLD == bt1.FOLD == 13
    assert bt.TRAIN_MIN == bt1.TRAIN_MIN == 104
    assert bt.BASE_SEED == bt1.BASE_SEED  # same seeds -> paired draws vs v1
    assert bt.METHODS == bt1.METHODS


def test_fold_config_scales_wealth_and_keeps_liabilities_absolute():
    c = bt.build_config()
    cf = bt.fold_config(c, '2010-06-01', 5e7)
    assert cf['wealth'] == 5e7
    assert cf['risk_tolerance'] == 0.1 * 5e7
    cf1 = bt1.fold_config(c, '2010-06-01')
    assert [l['amount'] for l in cf['liabilities']] == [l['amount'] for l in cf1['liabilities']]
    assert cf['real_estate']['history_end'] == '2010-06-01'


def test_chained_config_at_100m_equals_reference_config():
    c = bt.build_config()
    cf = bt.fold_config(c, '2007-03-16', 1e8)
    cf1 = bt1.fold_config(c, '2007-03-16')
    for k in ['wealth', 'risk_tolerance', 'multiplier_grid', 'train_scenarios',
              'validation_scenarios', 'validation_seeds']:
        assert cf[k] == cf1[k], k


def test_initial_state_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(bt, 'STATE', tmp_path / 'state.json')
    s = bt.load_state()
    assert s['fold'] == 0 and s['stage'] == 'solve' and s['mult_index'] == 0
    assert s['ruined'] is False
    assert set(s['wealth']) == set(bt.METHODS)
    assert all(v == 1e8 for v in s['wealth'].values())
    s['wealth']['proposed'] = 9e7
    bt.save_state(s)
    assert json.loads((tmp_path / 'state.json').read_text())['wealth']['proposed'] == 9e7


def test_docstring_declares_sequential_and_abstain_to_cash():
    doc = (ROOT / 'studies/backtest_chained_20261109/backtest.py').read_text()
    assert 'Strictly sequential' in doc
    assert 'holds cash for the fold' in doc
