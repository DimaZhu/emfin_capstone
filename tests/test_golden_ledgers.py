"""Phase 0 golden-path fixtures (refactor plan): freeze current outputs of the
two executable accountings (ledger.cash_first and dynamic_policy.execute)
bit-for-bit on two small deterministic scenarios - one calm, one drawn-down
with a missed payment. Tolerance 1e-9 relative. These tests must pass
unchanged after Phase 1 migrates cash_first onto the shared event engine.

Fixtures were generated from the unmodified engine-v2 code (6bb8047) by
tests/golden/generate_golden.py; regenerate only intentionally.
"""
import json
from pathlib import Path

import numpy as np
import pytest
from emfin_v2.real_estate import ScenarioDraw
from emfin_v2.ledger import cash_first
from emfin_v2.dynamic_policy import execute

FIX = Path(__file__).parent / 'golden'
TOL = dict(rtol=1e-9, atol=1e-12)


def _draw(spec):
    return ScenarioDraw((np.array(spec['prices']), np.array(spec['amounts']),
                         np.array(spec['steps']), np.array(spec['bases']),
                         np.array(spec['growth'])), np.array(spec['funding']))


def _flat(obj):
    if isinstance(obj, dict):
        return {k: _flat(v) for k, v in obj.items() if isinstance(v, (dict, list, np.ndarray))}
    return np.asarray(obj, float).ravel().tolist()


def _compare(actual, expected):
    ae, ee = _flat(actual), _flat(expected)
    assert ae.keys() == ee.keys()
    for k in ae:
        np.testing.assert_allclose(np.array(ae[k]), np.array(ee[k]), err_msg=k, **TOL)


def scenarios():
    # Calm: cash + 3 liquid sleeves, gentle growth, two payments, fully funded.
    h, n = 8, 2
    eq = np.array([[1 + .002 * t for t in range(h)], [1 + .0015 * t for t in range(h)]])
    bond = np.array([[1 + .001 * t for t in range(h)]] * n)
    reit = np.array([[1 + .0012 * t for t in range(h)]] * n)
    gold = np.array([[1 - .0005 * t for t in range(h)]] * n)
    prices = np.stack([np.ones((n, h)), eq, bond, reit, gold], axis=2)
    growth = np.full((n, h), 1.0004 ** np.arange(h + 1)[1:])
    amounts = np.array([[100., 150.]] * n)
    steps = np.array([4, 8])
    calm = dict(prices=prices.tolist(), amounts=amounts.tolist(), steps=steps.tolist(),
                bases=amounts.tolist(), growth=growth.tolist(), funding=prices.tolist())
    # Stress: sleeve 0 drops 40% in week 1 and stays down; first payment
    # exceeds cash so arrears persist to the second payment.
    eqs = np.array([[1., .6, .62, .64, .66, .68, .70, .72]] * n)
    prices_s = np.stack([np.ones((n, h)), eqs, bond, reit, gold], axis=2)
    amounts_s = np.array([[12000., 200.]] * n)
    stress = dict(prices=prices_s.tolist(), amounts=amounts_s.tolist(), steps=steps.tolist(),
                  bases=amounts_s.tolist(), growth=growth.tolist(), funding=prices_s.tolist())
    return calm, stress


CONFIG = dict(cash_index=0, real_estate=dict(enabled=False, sale_week=0, annual_rent_yield=0.,
                                             net_rental_yield=0.),
              asset_layout=dict(property_indices=[]))
ALLOC = [4000., 2000., 1500., 1000., 500.]


def test_cash_first_golden():
    calm, stress = scenarios()
    for name, spec in (('calm', calm), ('stress', stress)):
        expected = json.loads((FIX / f'cash_first_{name}.json').read_text())
        _compare(cash_first(CONFIG, _draw(spec), ALLOC), expected)


def test_dynamic_execute_cash_first_mode_golden():
    calm, stress = scenarios()
    for name, spec in (('calm', calm), ('stress', stress)):
        expected = json.loads((FIX / f'dynamic_cash_first_{name}.json').read_text())
        _compare(execute(CONFIG, _draw(spec), ALLOC, mode='cash_first'), expected)
