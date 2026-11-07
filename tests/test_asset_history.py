import json,hashlib
import numpy as np
import pandas as pd
import pytest
from emfin_v2.assets import load_registry
from emfin_v2.asset_history import weekly_returns,load_total_return


def make_history(tmp_path,a,dates):
    p=tmp_path/(a['id']+'.csv');pd.DataFrame({'date':dates,'total_return_index':100*np.exp(np.arange(len(dates))*.0002)}).to_csv(p,index=False)
    manifest=tmp_path/(a['id']+'.json');manifest.write_text(json.dumps(dict(asset_id=a['id'],ticker=a['ticker'],currency=a['currency'],return_type='total_return',adjustment_method='synthetic TEST FIXTURE only',source_url='https://example.invalid/test',use_terms='test fixture',file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())))
    return manifest


def test_past_only_common_weekly_alignment_and_cash(tmp_path):
    d=load_registry();dates=pd.bdate_range('2020-01-01','2020-03-31');m={a['id']:make_history(tmp_path,a,dates) for a in d['assets'] if a['return_model']=='etf_total_return'}
    result=weekly_returns(d,m,end='2020-02-28');assert list(result)==['us_equity','em_equity','gold','treasury','cash']
    assert result.index[-1]==pd.Timestamp('2020-02-28')
    assert (result.index.to_series().diff().dropna()==pd.Timedelta(days=7)).all()
    assert np.allclose(result.cash,0)


def test_missing_three_weeks_not_treated_as_one(tmp_path):
    d=load_registry();dates=pd.bdate_range('2020-01-01','2020-03-31');dates=dates[(dates<'2020-02-01')|(dates>'2020-02-21')]
    m={a['id']:make_history(tmp_path,a,dates) for a in d['assets'] if a['return_model']=='etf_total_return'}
    with pytest.raises(ValueError,match='stale/missing'):weekly_returns(d,m)


def test_nav_without_distribution_evidence_is_not_total_return(tmp_path):
    a=load_registry()['assets'][0];p=make_history(tmp_path,a,pd.bdate_range('2020-01-01','2020-01-31'));m=json.loads(p.read_text());m['return_type']='nav';p.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='total-return'):load_total_return(a,p)
