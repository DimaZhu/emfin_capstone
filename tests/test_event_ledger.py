"""Unit tests for the shared event engine (Phase 1): within-week ordering,
arrears at the cash rate, property double-count guard, fee burn, and the
settlement queue. cash_first equivalence is pinned separately and bit-for-bit
by tests/test_golden_ledgers.py.
"""
import numpy as np
import pytest
from emfin_v2.real_estate import ScenarioDraw
from emfin_v2.event_ledger import LedgerSpec, run_event_ledger

NO_RE = dict(cash_index=0, real_estate=dict(enabled=False))


def draw1(paths, amounts, steps, growth=None, funding=None):
    paths = np.asarray(paths, float)
    n, h, d = paths.shape
    g = np.ones((n, h)) if growth is None else np.asarray(growth, float)
    return ScenarioDraw((paths, np.asarray(amounts, float), np.asarray(steps),
                         np.asarray(amounts, float), g),
                        paths if funding is None else np.asarray(funding, float))


def test_growth_before_payment_same_week_oracle():
    # cash 100 grows 10% in week 1, then pays 20+30; week 2 grows, pays 10.
    d = draw1([[[1.1], [1.21]]], [[20., 30., 10.]], [1, 1, 2], growth=[[1.1, 1.21]])
    r = run_event_ledger(NO_RE, d, [100.], LedgerSpec.cash_first())
    assert r['terminal_net'][0] == pytest.approx((110 - 20 - 30) * 1.1 - 10)
    np.testing.assert_allclose(r['payment_shortfalls'], 0)


def test_arrears_accrue_at_cash_ratio():
    # Week 1 pays 60 against 50 cash; arrears 10 grow 10% into week 2,
    # where a payment of 5 becomes due: due 16, cash 55-60+... hand oracle below.
    d = draw1([[[1.1], [1.21]]], [[60., 5.]], [1, 2], growth=[[1.1, 1.21]])
    r = run_event_ledger(NO_RE, d, [50.], LedgerSpec.cash_first())
    # week 1: cash 50 -> 55, pay 60 -> arrears 5. week 2: arrears grow to
    # 5.5, due 5 + 5.5 = 10.5, cash 0 -> shortfall 10.5, terminal net -10.5.
    np.testing.assert_allclose(r['payment_shortfalls'], [[5., 10.5]])
    assert r['terminal_net'][0] == pytest.approx(-10.5)
    assert not r['funded'][0]


def test_property_receipts_credited_once_and_removed_from_mark():
    # Property pays rent 2 in week 1, settles 90 in week 2, no liquid assets.
    paths = np.array([[[1., 102.], [1., 92.]]])
    spend = np.array([[[1., 2.], [1., 92.]]])
    d = draw1(paths, [[5., 10.]], [1, 2], funding=spend)
    c = dict(cash_index=0, real_estate=dict(enabled=True), asset_layout=dict(property_indices=[1]))
    r = run_event_ledger(c, d, [3., 1.], LedgerSpec.cash_first())
    assert r['funded'][0]
    assert r['terminal_net'][0] == pytest.approx(80.)
    assert r['cash_paths'][0, 0] == 0


def test_fee_burn_reduces_proceeds_and_is_accounted():
    # 100 bps fee, lag 0. Cash 0, one sleeve worth 1000, payment 100 in week 1.
    spec = LedgerSpec(fee_bps=100.)
    d = draw1([[[1., 1000.]]], [[100.]], [1])
    r = run_event_ledger(dict(NO_RE, asset_layout=dict(property_indices=[])), d, [0., 1.], spec)
    sold = r['sold_value_paths'][0, 0, 1]
    assert sold == pytest.approx(100. / 0.99)
    assert r['fee_burned'][0] == pytest.approx(sold * 0.01)
    np.testing.assert_allclose(r['payment_shortfalls'], 0)
    assert r['terminal_net'][0] == pytest.approx(1000. - sold)


def test_settlement_queue_delays_spendability():
    # lag 1: a sale forced in week 1 settles in week 2; the week-1 payment
    # misses, week-2 payment can use the settled proceeds.
    spec = LedgerSpec(settlement_lag_weeks=1)
    paths = np.array([[[1., 100.], [1., 100.]]])
    d = draw1(paths, [[50., 50.]], [1, 2])
    c = dict(cash_index=0, real_estate=dict(enabled=False), asset_layout=dict(property_indices=[]))
    r = run_event_ledger(c, d, [10., 1.], spec)
    # week 1: cash 10, due 50, sell 40 of sleeve but proceeds settle week 2:
    # paid 10, shortfall 40. Week-1 wealth still marks the in-flight 40.
    assert r['payments'][0, 0] == pytest.approx(10.)
    assert r['payment_shortfalls'][0, 0] == pytest.approx(40.)
    assert r['net_wealth_paths'][0, 0] == pytest.approx(60. + 40. - 40.)
    # week 2: 40 settles; arrears 40 + due 50 = 90; the week-2 sale (50)
    # settles beyond the horizon, so payment is 40, shortfall 50.
    assert r['payments'][0, 1] == pytest.approx(40.)
    assert r['payment_shortfalls'][0, 1] == pytest.approx(50.)
    assert not r['funded'][0]
    # terminal: sleeve 10 + pending 50 - arrears 50.
    assert r['terminal_net'][0] == pytest.approx(10.)


def test_pending_terminal_counts_in_marked_wealth():
    spec = LedgerSpec(settlement_lag_weeks=1)
    d = draw1([[[1., 100.]]], [[50.]], [1])
    c = dict(cash_index=0, real_estate=dict(enabled=False), asset_layout=dict(property_indices=[]))
    r = run_event_ledger(c, d, [0., 1.], spec)
    # sale of 50 in flight at horizon: terminal_net = 50 remaining sleeve + 50 pending - 50 arrears.
    assert r['pending_terminal'][0] == pytest.approx(50.)
    assert r['terminal_net'][0] == pytest.approx(50.)


def test_spec_validation():
    with pytest.raises(ValueError):
        run_event_ledger(NO_RE, draw1([[[1.]]], [[0.]], [1]), [1.], LedgerSpec(liquidation='twins'))
    with pytest.raises(ValueError):
        LedgerSpec(fee_bps=-1.).validate()
    with pytest.raises(ValueError):
        LedgerSpec(settlement_lag_weeks=-1).validate()
    with pytest.raises(ValueError):
        LedgerSpec(rebalance_calendar=(4,)).validate()


# --- Phase 3 (part 2): dynamic execute modes on the shared engine ---------

def test_dynamic_specs_match_legacy_execute():
    """run_event_ledger with the dynamic specs reproduces
    dynamic_policy.execute(modes cash_first and pro_rata) bit-for-bit on the
    Phase 0 golden scenarios (same tolerance as the golden fixtures)."""
    from emfin_v2.dynamic_policy import execute
    from tests.test_golden_ledgers import scenarios, CONFIG, ALLOC, TOL, _draw
    calm, stress = scenarios()
    for name, spec_d in (('calm', calm), ('stress', stress)):
        draw = _draw(spec_d)
        for mode, factory in (('cash_first', LedgerSpec.dynamic_cash_first),
                              ('pro_rata', LedgerSpec.dynamic_pro_rata)):
            legacy = execute(CONFIG, draw, ALLOC, mode=mode, fee=.0005, delay=1)
            r = run_event_ledger(CONFIG, draw, ALLOC, factory(fee_bps=5.0, settlement_lag_weeks=1))
            pairs = [('net_wealth_paths', 'net_wealth_paths'),
                     ('shadow_wealth_paths', 'shadow_wealth_paths'),
                     ('shortfalls', 'payment_shortfalls'),
                     ('terminal_net', 'terminal_net'),
                     ('cost', 'cost'), ('turnover', 'turnover'),
                     ('trades', 'trades'), ('cash_paths', 'cash_paths'),
                     ('pending_terminal', 'pending_terminal'),
                     ('units_terminal', 'terminal_units')]
            for lk, rk in pairs:
                np.testing.assert_allclose(np.asarray(r[rk], float),
                                           np.asarray(legacy[lk], float),
                                           err_msg=f'{name}/{mode}/{lk}', **TOL)
            np.testing.assert_array_equal(r['funded'], legacy['funded'])


def test_metrics_executable_matches_manual_ledger_score():
    """Phase 4: the experimental executable-ledger scorer sources every
    number from the engine (cash_first ledger), same shape as metrics()."""
    import numpy as np
    from emfin_v2.default_run import metrics_executable
    from emfin_v2.ledger import cash_first
    from scipy.special import logsumexp
    c = dict(cash_index=0, wealth=10000., confidence=.95, risk_tolerance=5000.,
             real_estate=dict(enabled=False), asset_layout=dict(property_indices=[]))
    n, h, d = 6, 10, 3
    rng = np.random.default_rng(3)
    prices = np.cumprod(1 + rng.normal(0, .01, (n, h, d)), axis=1)
    prices[:, :, 0] = 1.
    growth = np.full((n, h), 1.001) ** np.arange(1, h + 1)
    amounts = np.full((n, 2), 100.)
    steps = np.array([4, 9])
    draw = (prices, amounts, steps, amounts.copy(), growth)
    a = np.array([4000., 3000., 3000.])
    gaps, ce = metrics_executable(c, draw, a)
    r = cash_first(c, draw, a)
    manual_ce = float(-c['risk_tolerance'] * (logsumexp(-r['terminal_net'] / c['risk_tolerance'])
                                              - np.log(n)))
    assert gaps.shape == (2,)
    assert ce == manual_ce
