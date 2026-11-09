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
    assert 'T-bill fallback' in doc


def test_equal_weight_sums_to_one_with_binding_minimums():
    import numpy as np
    # Two minimums bind simultaneously: the water-filling must subtract both
    # (pre-review bug: only the last locked minimum was subtracted, silently
    # leveraging the portfolio).
    mins = np.array([0.4, 0.4, 0.0, 0.0, 0.0])
    w = bt.equal_weight_allocation(mins, {}, 5)
    assert abs(w.sum() - 1.0) < 1e-12
    assert w[0] == 0.4 and w[1] == 0.4
    assert abs(w[2] - 0.2 / 3) < 1e-12
    # With a fixed property holding the free mass shrinks accordingly.
    w2 = bt.equal_weight_allocation(np.zeros(7), {6: 0.1}, 7)
    assert abs(w2.sum() - 1.0) < 1e-12
    assert w2[6] == 0.1
    assert all(abs(w2[i] - 0.9 / 6) < 1e-12 for i in range(6))


def test_tbill_growth_matches_committed_series():
    import pandas as pd
    p = ROOT / 'emfin_v2/resources/data/actual_etfs/tbill-total-return.csv'
    s = pd.read_csv(p, parse_dates=['date']).set_index('date')['total_return_index']
    fridays = s.index[s.index.dayofweek == 4]
    window = fridays[500:513]
    g = bt.tbill_growth(window)
    assert g[0] == 1.0
    assert abs(g[-1] - (s.loc[window[-1]] / s.loc[window[0]])) < 1e-12
    assert (g > 0).all()


def test_split_ruined_freezes_only_nonpositive():
    active, ruined = bt.split_ruined({'proposed': 9e7, 'cash': 0.0, '1/N': -1e6,
                                      'min_var': 5e7, 'shrunk_MV': 1.2e8})
    assert set(active) == {'proposed', 'min_var', 'shrunk_MV'}
    assert set(ruined) == {'cash', '1/N'}  # exactly 0 counts as ruined too


def test_realized_window_tbill_swaps_cash_sleeve():
    import numpy as np
    from emfin_v2.real_estate import ScenarioDraw
    d = 6
    cash_index = 4
    paths = np.ones((1, 13, d))
    funding = np.ones((1, 13, d))
    growth = np.ones((1, 13))
    rd = ScenarioDraw((paths, np.ones((1, 3)), np.array([4, 8, 13]),
                       np.ones(3) * 250000.0, growth), funding)
    tb = np.linspace(1.0, 1.012, 13)
    rd2 = bt.realized_window_tbill(rd, tb, cash_index)
    assert np.allclose(rd2[0][0, :, cash_index], tb)  # cash marks now tbill
    assert np.allclose(rd2[4][0], tb)  # growth numeraire swapped
    assert np.allclose(rd2.funding_paths[0, :, cash_index], tb)  # funding sleeve swapped
    assert np.allclose(rd[0][0, :, cash_index], 1.0)  # original untouched
    assert np.allclose(rd2[0][0, :, 0], 1.0)  # other sleeves untouched
