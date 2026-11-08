"""Phase 2 contract tests: construction-time validation, legacy adapters, and
the engine boundary running on ScenarioBatch bit-for-bit against the tuple
interface."""
import numpy as np
import pytest
from emfin_v2.contracts import Allocation, LiabilitySchedule, ModelSpec, ScenarioBatch, Verdict
from emfin_v2.event_ledger import LedgerSpec, run_event_ledger


def batch(**kw):
    h, n, d, k = 4, 2, 2, 1
    base = dict(prices=np.ones((n, h, d)), amounts=np.array([[10.]] * n),
                steps=np.array([2]), bases=np.array([10.]), growth=np.ones((n, h)))
    base.update(kw)
    return ScenarioBatch(**base)


def test_valid_batch_and_schedule():
    b = batch(seed=7, law='gaussian_scale_mixture', draw_tag='t')
    assert b.shape == (2, 4, 2)
    assert b.schedule.steps == (2,) and b.schedule.bases == (10.,)
    assert b.seed == 7 and b.law == 'gaussian_scale_mixture'


def test_batch_validation():
    with pytest.raises(ValueError):
        batch(prices=np.ones((2, 4)))  # not 3-D
    with pytest.raises(ValueError):
        batch(amounts=np.array([[-1.]] * 2))  # negative liability
    with pytest.raises(ValueError):
        batch(steps=np.array([0]))  # outside horizon
    with pytest.raises(ValueError):
        batch(steps=np.array([5]))  # beyond horizon
    with pytest.raises(ValueError):
        batch(growth=np.zeros((2, 4)))  # nonpositive growth
    with pytest.raises(ValueError):
        batch(prices=np.full((2, 4, 2), np.nan))
    with pytest.raises(ValueError):
        batch(steps=np.array([2, 1]), amounts=np.array([[10., 5.]] * 2),
              bases=np.array([10., 5.]))  # non-monotone weeks


def test_schedule_validation():
    with pytest.raises(ValueError):
        LiabilitySchedule((2, 1), (10., 5.))
    with pytest.raises(ValueError):
        LiabilitySchedule((1,), (-3.,))
    with pytest.raises(ValueError):
        LiabilitySchedule((1.5,), (3.,))


def test_draw_round_trip():
    b = batch()
    draw = b.to_draw()
    b2 = ScenarioBatch.from_draw(draw)
    np.testing.assert_array_equal(b2.prices, b.prices)
    np.testing.assert_array_equal(b2.amounts, b.amounts)
    np.testing.assert_array_equal(b2.growth, b.growth)
    r1 = run_event_ledger(dict(cash_index=0, real_estate=dict(enabled=False)),
                          draw, [100., 0.], LedgerSpec.cash_first())
    r2 = run_event_ledger(dict(cash_index=0, real_estate=dict(enabled=False)),
                          b, [100., 0.], LedgerSpec.cash_first())
    np.testing.assert_array_equal(r1['net_wealth_paths'], r2['net_wealth_paths'])
    np.testing.assert_array_equal(r1['payment_shortfalls'], r2['payment_shortfalls'])


def test_allocation_validation():
    a = Allocation([60., 40.], ('tbill', 'sp500'))
    assert a.wealth == pytest.approx(100.)
    np.testing.assert_array_equal(a.as_vector(), [60., 40.])
    with pytest.raises(ValueError):
        Allocation([60., 40.], ('tbill', 'tbill'))  # duplicate ids
    with pytest.raises(ValueError):
        Allocation([60.], ('tbill', 'sp500'))  # misaligned
    with pytest.raises(ValueError):
        Allocation([110., -20.], ('tbill', 'sp500'))  # beyond tolerance
    Allocation([100., -1e-8], ('tbill', 'sp500'))  # within judge tolerance


def test_modelspec_and_verdict():
    m = ModelSpec(law='fhs_ewma', view='fitted', cml_budget=0.40, loss_budget=0.15,
                  wasserstein_radius=0.001)
    assert m.law == 'fhs_ewma'
    with pytest.raises(ValueError):
        ModelSpec(law='x', view='y', cml_budget=-0.1, loss_budget=0.15, wasserstein_radius=0.)
    v = Verdict(overall_pass=True, funding_pass=True, breaches=[])
    assert v.breaches == ()


def test_judge_and_engine_end_to_end_on_contracts():
    """Study-style flow on contracts only: provenance-tagged batches judged
    via evaluate_batches and executed via the engine, no legacy dicts."""
    from emfin_v2.evaluation import evaluate_batches
    c = dict(wealth=100., confidence=.5, cml_budget=.1, loss_budget=.15,
             funding_budget_fraction=.2, cash_index=0,
             real_estate=dict(enabled=False), minimum_weights=[0., 0.],
             fixed_weights={}, wasserstein_radius=0.)
    paths = np.tile(np.array([[[.8, 1.], [1., 1.]]]), (4, 1, 1))
    steps = np.array([1, 2])
    base = np.array([10., 10.])
    amounts = np.tile(base, (4, 1))
    growth = np.ones((4, 2))
    batches = [ScenarioBatch(paths, amounts, steps, base, growth, seed=11,
                             law='gaussian_scale_mixture', draw_tag='unit'),
               ScenarioBatch(paths, amounts, steps, base, growth, seed=12,
                             law='gaussian_scale_mixture', draw_tag='unit')]
    a = Allocation([50., 50.], ('cash', 'risky'), wealth=100.)
    q = np.full(4, .25)
    v = evaluate_batches(c, batches, a, [q, q], [q, q])
    assert isinstance(v.breaches, tuple)
    assert v.funding_pass
    r = run_event_ledger(c, batches[0], a.as_vector(), LedgerSpec.cash_first())
    assert r['terminal_net'].shape == (4,)
    with pytest.raises(TypeError):
        evaluate_batches(c, [batches[0].to_draw()] * 2, a, [q, q], [q, q])
