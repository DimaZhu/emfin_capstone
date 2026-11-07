import numpy as np
import pytest
from emfin_capstone.toolbox import validation


def test_folds_never_touch_final_window():
    folds, cutoff = validation.chronological_folds(151)
    assert cutoff == 125
    assert all(f.train_stop < f.validation_stop <= cutoff for f in folds)
    assert all(b.train_stop >= a.validation_stop for a,b in zip(folds, folds[1:]))


def test_rolling_horizons_stay_inside_input_block():
    x = np.arange(40).reshape(20,2)
    got = validation.horizon_sums(x,13)
    assert got.shape == (8,2)
    np.testing.assert_allclose(got[0], x[:13].sum(0))
    np.testing.assert_allclose(got[-1], x[-13:].sum(0))


def test_nu_fit_distinguishes_fat_from_thin_tails():
    rng=np.random.default_rng(11)
    z=rng.normal(size=(10000,2))
    t=z/np.sqrt(rng.chisquare(6,(10000,1))/4)
    nu_t=validation.fit_student_nu(t, np.zeros(2),np.eye(2))
    nu_g=validation.fit_student_nu(z, np.zeros(2),np.eye(2))
    assert 4 < nu_t < 10
    assert nu_g > 30


def test_t_nll_requires_valid_nu():
    with pytest.raises(ValueError):
        validation.variance_matched_t_nll(np.ones((3,2)),np.zeros(2),np.eye(2),2)
