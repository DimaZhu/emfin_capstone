import json
from pathlib import Path
import numpy as np
from emfin_v2.default_run import load_config,run
from emfin_v2.abu_dhabi import load_observed


def test_synthetic_re_fixture_is_not_private_data():
    path=Path(__file__).resolve().parents[1]/'emfin_v2/resources/configs/synthetic_re_import.json'
    got=load_observed(str(path));assert got['observations']==24
    assert got['first_month']=='2020-01'


def test_backcasts_and_forecasts_excluded(tmp_path):
    src=Path(__file__).resolve().parents[1]/'emfin_v2/resources/configs/synthetic_re_import.json'
    doc=json.loads(src.read_text());doc['tabs'][0]['values'] += [['2019-12',99,'',99,'Back-cast','Low'],['2022-01',200,'',200,'Extrapolation','Low']]
    path=tmp_path/'local.json';path.write_text(json.dumps(doc))
    got=load_observed(str(path));assert got['observations']==24 and got['last_month']=='2021-12'


def test_dashboard_funding_and_stress_are_generated(tmp_path):
    c=load_config();c.update(train_scenarios=100,validation_scenarios=200,evaluation_scenarios=300,validation_seeds=2,evaluation_seeds=2,multiplier_grid=[1.,.25],cash_mix_grid=[1.,.5,0.]);r=run(c,tmp_path);d=r['dashboard']
    assert d['wealth']==c['wealth'];assert d['sfo_inputs']['status'].startswith('Default placeholder')
    a=np.array(r['weights']['proposed'])*c['wealth']
    for stress in d['shocks']:
        assert stress['kind'].startswith('Simplified')
        assert len(stress['payouts'])==len(c['liabilities'])
        assert stress['funded']==all(p['funded'] for p in stress['payouts'])
    assert len(d['shocks'])==4
    assert len(d['payouts'])==12 and d['horizon_weeks']==52
    assert all(p['shortfall']>=0 for shock in d['shocks'] for p in shock['payouts'])
    assert all(row['wasserstein_buffer']>=0 for row in r['rows'])
    assert next(row for row in r['rows'] if row['method']=='proposed')['evaluation_pass']


def test_config_placeholder_fails_helpfully(tmp_path):
    import pytest
    p=tmp_path/'placeholder.json';p.write_text('{"status":"placeholder"}')
    with pytest.raises(ValueError,match='Incomplete'):load_config(p)
    p.write_text('{broken')
    with pytest.raises(ValueError,match='Cannot read'):load_config(p)


def test_nonfinite_config_rejected(tmp_path):
    import pytest
    c=load_config();c['real_estate']['annual_vol']=float('nan')
    p=tmp_path/'bad.json';p.write_text(json.dumps(c))
    with pytest.raises(ValueError,match='finite'):load_config(p)
