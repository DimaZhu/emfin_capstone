import numpy as np
import pandas as pd
import pytest
from emfin_v2.yahoo_import import total_return_from_adjusted,fetch_private


def test_adjusted_close_dates_and_normalization():
    f=pd.DataFrame({'Adj Close':[20.,22.,21.]},index=['2020-02-01T00:00:00-05:00','2020-03-01T00:00:00-05:00','2020-04-01T00:00:00-04:00'])
    r=total_return_from_adjusted(f);np.testing.assert_allclose(r.total_return_index,[100,110,105]);assert str(r.date.iloc[2].date())=='2020-04-01'


def test_no_automatic_network_without_risk_acknowledgement(tmp_path):
    with pytest.raises(ValueError,match='acknowledgement'):fetch_private(['VTI'],tmp_path)
    with pytest.raises(ValueError,match='new-universe'):fetch_private(['SECRET'],tmp_path,True)


def test_default_is_new_offline_universe_with_fx_and_actual_sources():
    from emfin_v2.default_run import load_config,setup,draw_paths
    c=load_config();frame,mu,cov=setup(c)
    assert c['asset_layout']['ids']==['us_equity','em_equity','gold','treasury','cash','sg_property']
    assert c['fx']['enabled'] and cov.shape==(6,6)
    assert frame.index[0].year==2005 and str(frame.index[-1].date())=='2026-10-30'
    assert 'PRIVATE RESEARCH' in c['history_evidence']['label']
    assert 'not an actual-history backtest' in c['history_evidence']['label']
    assert c['cash_index']==4 and not cov[4].any()
    c['horizon_weeks']=52  # deliberate pin (8 Nov 2026): universe/FX wiring check stays at the original 1y scale after the owner's 10y default change
    d=draw_paths(c,(frame,mu,cov),20,3);assert d[0].shape==(20,52,6)
    assert not d.funding_paths[:,:,5].any()
