from emfin_v2.default_run import LEGACY_CONFIG
import numpy as np
import pytest
from emfin_v2.singapore import history
from emfin_v2.real_estate import calibration,history_statistics
from emfin_v2.default_run import load_config,setup,draw_paths,probabilities


def test_public_ura_is_quarterly_price_index_not_rent():
    x,m=history();assert len(x)==206 and m['observations']==207
    assert m['first_period']=='1975-Q1' and m['last_period']=='2026-Q3'
    assert m['frequency']=='quarterly' and m['periods_per_year']==4
    assert 'not HDB, rent, total return' in m['limitations']
    assert m['licence_url']=='https://data.gov.sg/open-data-licence'
    assert all(len(history(t)[0])==206 for t in ['Landed','Non-Landed'])


def test_quarterly_annualization_and_separate_forward_view():
    x,m=history();c=calibration(dict(source='singapore_ura',annual_drift=.04,annual_vol=.12))
    assert c['sample_implied_log_drift']==pytest.approx(np.mean(x)*4)
    assert c['annual_vol']==pytest.approx(np.std(x,ddof=1)*2)
    assert c['forward_log_drift']==.04
    assert '4-period blocks' in c['method']
    assert 'not observed weekly' in c['history_note']


def test_singapore_source_is_default_but_rent_remains_an_assumption():
    c=load_config(LEGACY_CONFIG);assert c['real_estate']['source']=='singapore_ura'
    assert c['real_estate']['net_rental_yield']==0
    c['real_estate']['enabled']=True
    draw=draw_paths(c,setup(c),100,23);q,qs=probabilities(c,draw[0],draw.re_price_logs)
    assert q@draw.re_price_logs[:,-1]==pytest.approx(.04,abs=1e-6)
    assert qs@draw.re_price_logs[:,-1]==pytest.approx(.04,abs=1e-6)


def test_unknown_property_type_fails():
    with pytest.raises(ValueError):history('HDB')
