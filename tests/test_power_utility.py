import numpy as np
import pytest
from emfin_v2.toolbox.power_utility import allocate_positive_surplus


def test_exact_power_utility_has_expected_risk_aversion_effect():
    rng=np.random.default_rng(123)
    market=np.column_stack([np.exp(rng.normal(.02,.06,500)),np.full(500,1.005)])
    shares=[]
    for gamma in (.5,1.,3.):
        a,d=allocate_positive_surplus(market,np.ones(2),1e6,900000.,gamma)
        assert d['minimum_scenario_surplus']>0
        assert d['surplus_ce']>0
        assert a.sum()==pytest.approx(1e6,abs=1.)
        shares.append(a[0])
    assert shares[0]>shares[1]>shares[2]


def test_impossible_positive_domain_fails_loudly():
    market=np.full((20,2),.8)
    with pytest.raises(RuntimeError):
        allocate_positive_surplus(market,np.ones(2),1e6,900000.)
