import copy,json
import pytest
from emfin_v2.default_run import load_config,validate_config,run


def test_final_boundary_is_identical_and_does_not_mutate_source(tmp_path):
    c=load_config();before=copy.deepcopy(c);direct=validate_config(c)
    p=tmp_path/'config.json';p.write_text(json.dumps(c));loaded=load_config(p)
    assert direct==loaded and c==before
    assert len(direct['liabilities'])==12
    assert len(validate_config(direct)['liabilities'])==12


def test_invalid_post_ui_mutation_rejected_before_setup(tmp_path,monkeypatch):
    c=load_config();c['confidence']=1.
    def forbidden(*args):raise AssertionError('fit called before validation')
    monkeypatch.setattr('emfin_v2.default_run.setup',forbidden)
    with pytest.raises(ValueError,match='confidence'):run(c,tmp_path)


def test_unsafe_liability_option_disabled_at_final_boundary_and_draw_api(tmp_path):
    c=load_config();c['liability_vol']=.1
    with pytest.raises(ValueError,match='disabled'):validate_config(c)


def test_re_disable_and_source_switch_cannot_retain_stale_fx():
    c=load_config();assert c['fx']['enabled']
    c['real_estate']['enabled']=False;c['fx_evidence']={'stale':True}
    c=validate_config(c);assert not c['fx']['enabled'] and 'fx_evidence' not in c
    assert len(c['asset_names'])==5
    c['real_estate']['enabled']=True;c['real_estate']['source']='synthetic'
    c=validate_config(c);assert not c['fx']['enabled']
