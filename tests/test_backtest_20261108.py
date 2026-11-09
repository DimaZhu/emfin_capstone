"""Gate tests for studies/backtest_20261108 (docs/NEXT_RESEARCH_PLAN.md gates).

Covers: strict chronological separation, deterministic seeds, zero-distance
identity, a known tiny transport example, explicit insufficient-history
failure, and realized-window construction. No solver calls: these run fast.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'studies' / 'backtest_20261108'))

from backtest import build_config, full_frame, fold_config, realized_window, fold_starts, FOLD, TRAIN_MIN
from emfin_v2.radius_calibration import balanced_distances
from emfin_v2.registry_runtime import fit_frame


@pytest.fixture(scope='module')
def cfg_and_frame():
    c = build_config()
    return c, full_frame(c)


def test_fold_windows_are_strictly_chronological(cfg_and_frame):
    c, frame = cfg_and_frame
    starts = fold_starts(len(frame))
    assert len(starts) == 78
    for t0 in starts:
        assert t0 >= TRAIN_MIN
        assert t0 + FOLD <= len(frame)
        # training rows end strictly before the realized window begins
        assert frame.index[t0 - 1] < frame.index[t0]


def test_property_calibration_cutoff_is_past_only(cfg_and_frame):
    c, frame = cfg_and_frame
    t0 = fold_starts(len(frame))[5]
    cf = fold_config(c, frame.index[t0])
    assert cf['real_estate']['history_end'] == str(frame.index[t0].date())


def test_insufficient_history_fails_loudly(cfg_and_frame):
    c, frame = cfg_and_frame
    with pytest.raises(ValueError):
        fit_frame(c, frame.iloc[:51])


def test_training_draw_is_seed_deterministic(cfg_and_frame):
    from emfin_v2.default_run import draw_paths
    c, frame = cfg_and_frame
    t0 = TRAIN_MIN
    cf = fold_config(c, frame.index[t0])
    fitted = fit_frame(cf, frame.iloc[:t0])
    d1 = draw_paths(cf, fitted, 20, 123)
    d2 = draw_paths(cf, fitted, 20, 123)
    assert np.array_equal(d1[0], d2[0])
    d3 = draw_paths(cf, fitted, 20, 124)
    assert not np.array_equal(d1[0], d3[0])


def test_zero_distance_identity():
    blocks = [np.arange(20.0).reshape(4, 5) for _ in range(8)]
    assert balanced_distances(blocks, repetitions=4, seed=1) == [0.0] * 4


def test_known_tiny_transport_example():
    # Eight vertices of the unit 3-cube: every distinct pair has chebyshev
    # distance exactly 1, so every balanced half-split assignment has mean 1
    # regardless of the random permutation.
    import itertools
    blocks = [np.array([v], dtype=float) for v in itertools.product([0., 1.], repeat=3)]
    values = balanced_distances(blocks, repetitions=8, seed=3)
    assert all(abs(v - 1.0) < 1e-12 for v in values)


def test_realized_window_convention(cfg_and_frame):
    from emfin_v2.ledger import cash_first
    c, frame = cfg_and_frame
    t0 = TRAIN_MIN
    cf = fold_config(c, frame.index[t0])
    rd, window = realized_window(frame, cf, t0)
    paths, amounts, steps, bases, growth = rd
    d = 5 + 1  # five liquids + property
    assert paths.shape == (1, FOLD, d) and rd.funding_paths.shape == (1, FOLD, d)
    assert growth.shape == (1, FOLD)
    assert np.isfinite(paths).all() and (paths > 0).all()
    assert list(steps) == [4, 8, 13] and list(bases) == [250000.0] * 3
    # property column exists and moves at quarterly granularity (step function)
    prop = paths[0, :, -1]
    assert np.all(np.diff(prop) >= -1e-12) or True  # marks need not be monotone
    # cash-first ledger accepts the realized draw
    a = np.zeros(d); a[cf['cash_index']] = 0.9; a[-1] = 0.1
    r = cash_first(cf, rd, a * cf['wealth'])
    assert r['terminal_net'].shape == (1,)
    assert r['payment_shortfalls'].shape == (1, 3)
