"""Round-2 engine capabilities (owner plan 8 Nov 2026): current-quotes carry
view as second default view, and multi-law judging (regime/bootstrap variant
fhs_ewma as a fifth law)."""
import json
from pathlib import Path

import numpy as np
import pytest

from emfin_v2.current_rates import apply_carry_view, validate_carry_view, QUOTES_20261105
from emfin_v2.multi_law import all_laws, validate_laws, draw_extra_splits
from emfin_v2.default_run import load_config, run, setup, validate_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'emfin_v2/resources/configs/default.json'


def fit_stub(ids):
    import pandas as pd
    frame = pd.DataFrame(columns=ids)
    return frame, np.full(len(ids), 0.001), np.eye(len(ids)) * 0.01


def test_carry_view_replaces_only_named_safe_means():
    c = {'carry_view': 'current_quotes'}
    frame, mu, cov = fit_stub(['us_equity', 'treasury', 'tips', 'cash'])
    q = QUOTES_20261105
    frame2, mu2, cov2 = apply_carry_view(c, (frame, mu, cov))
    assert mu2[0] == mu[0] and mu2[3] == mu[3]  # risky and cash untouched
    assert mu2[1] == np.log1p(q['dgs10']) / 52
    assert mu2[2] == np.log1p(q['dfii10'] + (q['dgs10'] - q['dfii10'])) / 52
    assert c['_carry_applied'] == {'treasury': q['dgs10'], 'tips': q['dfii10'] + (q['dgs10'] - q['dfii10'])}
    assert cov2 is cov  # vols and correlations stay fitted


def test_carry_view_requires_a_safe_asset():
    with pytest.raises(ValueError):
        apply_carry_view({'carry_view': 'current_quotes'}, fit_stub(['us_equity', 'gold']))


def test_carry_view_fitted_is_identity():
    frame, mu, cov = fit_stub(['treasury'])
    assert apply_carry_view({'carry_view': 'fitted'}, (frame, mu, cov))[1] is mu


def test_carry_view_validation_rejects_bad_values():
    with pytest.raises(ValueError):
        validate_carry_view({'carry_view': 'guessing'})
    with pytest.raises(ValueError):
        validate_carry_view({'carry_view': 'current_quotes', 'secondary_carry_view': 'current_quotes'})
    with pytest.raises(ValueError):
        validate_carry_view({'carry_view': 'current_quotes', 'carry_quotes': {'dgs3mo': 9.0, 'dgs10': 0.05, 'dfii10': 0.02, 'asof': '2026-11-05'}})


def test_validation_laws_validation():
    from emfin_v2.innovations import MODELS
    assert 'fhs_ewma' in MODELS
    validate_laws({'scenario_model': 'gaussian_scale_mixture', 'validation_laws': ['fhs_ewma'], 'asset_registry': {'x': 1}})
    with pytest.raises(ValueError):
        validate_laws({'scenario_model': 'gaussian_scale_mixture', 'validation_laws': ['not_a_law'], 'asset_registry': {'x': 1}})
    with pytest.raises(ValueError):
        validate_laws({'scenario_model': 'gaussian_scale_mixture', 'validation_laws': ['fhs_ewma'],
                       'asset_registry': {'x': 1}, 'scenario_archives': {'training': 'a', 'validation': ['b', 'c'], 'evaluation': ['d', 'e']}})
    assert all_laws({'scenario_model': 'gaussian_scale_mixture', 'validation_laws': ['fhs_ewma', 'gaussian_scale_mixture']}) == ['gaussian_scale_mixture', 'fhs_ewma']


def small_registry_config():
    c = load_config(DEFAULT)
    c.update(train_scenarios=60, validation_scenarios=100, evaluation_scenarios=120,
             validation_seeds=2, evaluation_seeds=2, multiplier_grid=[1.], cash_mix_grid=[1., 0.])
    return c


@pytest.mark.slow
def test_run_second_view_and_fifth_law(tmp_path):
    c = small_registry_config()
    assert c['secondary_carry_view'] == 'current_quotes'
    assert c['validation_laws'] == ['fhs_ewma']
    result = run(c, tmp_path)
    assert result['carry_view'] == 'fitted'
    assert result['validation_laws'] == ['gaussian_scale_mixture', 'fhs_ewma']
    secondary = result['secondary_view']
    assert secondary['carry_view'] == 'current_quotes'
    assert '_secondary_view_done' not in secondary['config'] or not secondary['config'].get('secondary_carry_view')
    assert 'secondary_view' not in secondary  # no infinite recursion
    for row in result['rows'] + secondary['rows']:
        assert row['law_verdicts'] is not None
        assert set(row['law_verdicts']['per_law']) == {'fhs_ewma'}
        primary = row['evaluation']
        assert row['overall_pass'] == bool(primary['overall_pass'] and row['law_verdicts']['overall_pass'])
    assert any('Multi-law judging' in x for x in result['caveats'])
    assert any('current market quotes' in x for x in secondary['caveats'])


@pytest.mark.slow
def test_extra_law_draws_are_distinct_and_reproducible(tmp_path):
    c = small_registry_config()
    c['recurring_payout'] = None
    c['liabilities'] = [dict(name='y1', week=52, amount=0.0)]
    fit = setup(c)
    laws = all_laws(c)
    first = draw_extra_splits(c, fit, laws, 'validation')
    second = draw_extra_splits(c, fit, laws, 'validation')
    assert set(first) == {'fhs_ewma'}
    a = first['fhs_ewma'][0][0]
    b = second['fhs_ewma'][0][0]
    np.testing.assert_array_equal(a, b)  # deterministic under the fixed seed family
    from emfin_v2.default_run import draw_paths
    primary = draw_paths(c, fit, c['validation_scenarios'], c['seed'] + 1000)
    assert not np.allclose(a, primary[0])  # extra law is not a relabeled primary draw
