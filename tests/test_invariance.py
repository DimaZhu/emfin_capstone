import numpy as np
import pytest
from emfin_v2.invariance import diagnose


def test_ar_and_volatility_dependence_are_not_hidden_by_mean():
    rng=np.random.default_rng(19);innov=rng.normal(size=8000);ar=np.zeros(len(innov))
    for t in range(1,len(ar)):ar[t]=.8*ar[t-1]+innov[t]
    # Independent signs conceal a strongly persistent variance state.
    signs=rng.choice([-1.,1.],size=len(ar));volatile=signs*np.sqrt(np.exp(ar/2))
    rows=diagnose(np.column_stack([ar,volatile]),['AR','Volatility'])['rows']
    assert rows[0]['lagged'][0]['returns']>.7
    assert abs(rows[1]['lagged'][0]['returns'])<.05
    assert rows[1]['lagged'][0]['squared_returns']>.5


def test_split_shift_and_constant_cash_are_explicit():
    x=np.column_stack([np.r_[np.arange(100.),1000+np.arange(100.)],np.zeros(200)])
    rows=diagnose(x,['shift','cash'])['rows']
    assert rows[0]['split_cdf_distance']==1
    assert rows[1]['deterministic'] and rows[1]['lagged'][0]['returns'] is None
    assert rows[1]['mean_shift_in_full_sample_sd'] is None


def test_diagnostics_do_not_mutate_inputs_or_claim_invariance():
    x=np.random.default_rng(12).normal(size=(2000,2));before=x.copy();r=diagnose(x,['a','b'])
    np.testing.assert_array_equal(x,before)
    assert 'not been established' in r['assumption'] and 'p-values' in r['scope']
    assert max(abs(z['lagged'][0]['returns']) for z in r['rows'])<.1


@pytest.mark.parametrize('x,names',[(np.ones((19,1)),['x']),(np.ones((50,1)),[]),(np.array([[np.nan]]*50),['x'])])
def test_invalid_diagnostic_inputs_are_rejected(x,names):
    with pytest.raises(ValueError):diagnose(x,names)
