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


# ---------- review-brief small fixes (8 Nov 2026) ----------

def _minimal_result(with_proposed):
    cfg = dict(liabilities=[dict(name='p', week=4, amount=1000.)], real_estate=dict(
        enabled=False, minimum_weight=0., fixed_weight=0., holding_mode='fixed', sg_property_type='All Residential',
        smoothing_alpha=0., net_rental_yield=0., equity_correlation=.3, sale_week=0, sale_delay_weeks=12,
        history_case='central', liquidation_haircut=.1, forward_mode='view', forward_log_drift=.04),
        view_spread=.005, stress_mean_path_loss_increment=.01, scenario_model='gaussian_scale_mixture',
        student_nu=None, sequential_ep=True, recurring_payout=None, funding_budget_fraction=.2,
        funding_mode='tail_allowance', objective_kind='cara', radius_calibration_mode='manual')
    judge = dict(worst_funding_index=0, checks=[dict(payout_index=0, upper=1.)])
    row = dict(method='proposed' if with_proposed else 'shrunk MV', net_ce=dict(mean=[1.]), gap_cvar=dict(mean=[0.]),
               stressed_gap_cvar=dict(mean=[0.]), training_gap=[0.], wasserstein_gap_upper=[0.], budgets=[1.],
               evaluation=judge, overall_pass=with_proposed)
    fan = {'shrunk MV': [[0.]]}
    if with_proposed:
        fan['proposed'] = [[0.]]
    return dict(config=cfg, rows=[row], net_wealth_fan=fan, weights={}, points={}, frontier={},
                dashboard=None, assets=[], snapshot='2026-11-08', seconds=1.,
                status=dict(kind='optimized' if with_proposed else 'no calibration candidate passed'),
                caveats=['c'], strict_tradeoff=[])


def test_dashboard_never_shows_comparator_as_proposed():
    from emfin_v2.explorer import from_default
    ok = from_default(_minimal_result(True))
    assert ok['fan_state'] == 'approved_candidate'
    assert 'NO APPROVED CANDIDATE' not in ok['fan_note']
    no = from_default(_minimal_result(False))
    assert no['fan_state'] == 'no_approved_candidate_comparator_shown'
    assert 'NO APPROVED CANDIDATE' in no['fan_note']
    assert 'not a recommendation' in no['fan_note']


def test_vol_cap_instrument_membership_validated():
    c = load_config(DEFAULT)
    c['view_vol_cap'] = 0.2
    c['view_vol_cap_instrument'] = 99
    import numpy as np
    from emfin_v2.default_run import setup, draw_paths, probabilities
    fit = setup(c)
    d = draw_paths(c, fit, 40, 1)
    with pytest.raises(ValueError):
        probabilities(c, d[0], d.re_price_logs)


def test_property_equity_dependence_pinned_per_law():
    """Review-brief dependence audit: the configured property/equity correlation
    (0.30 latent weekly shocks) realizes differently per scenario law - the FHS
    branch derives the property factor differently and realizes LOWER weekly
    dependence. Labeled assumption, not a proven defect; this test pins current
    behaviour so any change is deliberate. Tolerances are change-detectors, not
    correctness proofs."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studies' / 'tbill'))
    import numpy as np
    import study_tips_charts as S
    expected = {'gaussian_scale_mixture': (0.25, 0.45), 'fhs_ewma': (0.05, 0.35),
                'bounded_ewma_mixture': (0.15, 0.40)}
    for law, (lo, hi) in expected.items():
        c = S.nm_config()
        c['scenario_model'] = law
        fit = S.setup(c)
        d = S.draw_paths(c, fit, 400, c['seed'] + 42)
        ids = c['asset_layout']['ids']
        pi = c['asset_layout']['property_indices'][0]
        ei = ids.index('us_equity')
        lp = np.log(d[0][:, 1:, pi] / d[0][:, :-1, pi]).ravel()
        le = np.log(d[0][:, 1:, ei] / d[0][:, :-1, ei]).ravel()
        corr = float(np.corrcoef(lp, le)[0, 1])
        assert lo <= corr <= hi, (law, corr)
