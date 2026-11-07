import json,sqlite3
from pathlib import Path
import pytest
from experiments.grid import configs,digest,initialize,canonical
from experiments.evidence import proof_points
ROOT=Path(__file__).resolve().parents[1]


def test_grid_is_729_distinct_synthetic_configurations():
    spec=json.loads((ROOT/'experiments/configs/grid729.json').read_text());items=list(configs(spec))
    assert len(items)==729 and len({digest(c) for _,c in items})==729
    for point,c in items:
        assert c['real_estate']['source']=='synthetic' and c['real_estate']['enabled']
        assert len(c['liabilities'])==12 and c['horizon_weeks']==52
        assert sum(p['amount'] for p in c['liabilities'])==pytest.approx(point['monthly_payout_k']*12000)
        assert c['liabilities'][0]['week']==point['first_due_week']
        assert c['real_estate']['minimum_weight']==point['re_min']


def test_hashes_stable_and_inputs_change_key():
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})
    assert digest({'a':1})!=digest({'a':2})


def test_grid_initialization_resumes_and_preserves_study_labels():
    spec=json.loads((ROOT/'experiments/configs/sensitivities.json').read_text());db=sqlite3.connect(':memory:')
    prov=dict(code_sha256='c',data_sha256='d')
    initialize(db,spec,prov);initialize(db,spec,prov)
    assert db.execute('SELECT count(*) FROM jobs').fetchone()[0]==32
    assert db.execute("SELECT count(DISTINCT json_extract(point,'$.study')) FROM jobs").fetchone()[0]==11


def test_shared_grid_rejects_private_archives_and_study_source():
    spec=json.loads((ROOT/'experiments/configs/reference.json').read_text());spec['engine']['scenario_archives']={'training':'secret.npz'}
    with pytest.raises(ValueError):list(configs(spec))
    spec=json.loads((ROOT/'experiments/configs/sensitivities.json').read_text());spec['cases'][0]['overrides']['real_estate.source']='abu_dhabi_private'
    with pytest.raises(ValueError):list(configs(spec))


def test_numerical_proof_points_pass_their_stated_tolerances():
    checks,transport=proof_points()
    assert len(checks)>=10 and all(c['passed'] for c in checks)
    assert all(t['gap']>=0 for t in transport)
    assert transport[-1]['gap']<transport[0]['gap']
