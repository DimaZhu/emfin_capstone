import json
import numpy as np
import pytest
from emfin_v2.payouts import expand_recurring
from emfin_v2.default_run import load_config,draw_paths,setup,metrics
from emfin_v2.explorer import Controls


def test_one_year_default_is_twelve_small_separate_obligations():
    c=load_config();assert c['horizon_weeks']==52;assert Controls().horizon==52
    assert len(c['liabilities'])==12
    assert sum(p['amount'] for p in c['liabilities'])==3000000
    assert [p['week'] for p in c['liabilities']]==[4,8,13,17,21,26,30,34,39,43,47,52]
    assert c['one_off_liabilities']==[]


def test_one_off_batches_add_and_equal_week_order_is_stable():
    got=expand_recurring(dict(amount=20,months=2,first_week=4,spacing_weeks=4),12,[dict(name='Call',week=4,amount=50)])
    assert [x['amount'] for x in got]==[50,20,20]
    assert [x['week'] for x in got]==[4,4,8]


@pytest.mark.parametrize('change',[dict(amount=float('nan')),dict(months=0),dict(first_week=0),dict(spacing_weeks=0),dict(months=13)])
def test_invalid_or_outside_horizon_never_truncated(change):
    base=dict(amount=250000,months=12,first_week=4,spacing_weeks=52/12);base.update(change)
    with pytest.raises(ValueError):expand_recurring(base,52)


def test_repeated_payments_are_cumulative_not_twelve_independent_pots():
    c=load_config();c['real_estate']['enabled']=False;draw=draw_paths(c,setup(c),20,1);a=np.zeros(6);a[5]=c['wealth']
    gap,ce=metrics(c,draw,a);assert len(gap)==12;assert (gap==0).all()
    assert ce<c['wealth']*1.1


def test_shortened_horizon_does_not_rescale_due_weeks():
    with pytest.raises(ValueError,match='outside'):Controls(horizon=13).validate()
    Controls(horizon=13,recurring_months=0,payouts=(('Call',10,1.),)).validate()


def test_resolved_config_roundtrip_does_not_duplicate_monthly_payments(tmp_path):
    c=load_config();p=tmp_path/'config.json';p.write_text(json.dumps(c));d=load_config(p)
    assert len(d['liabilities'])==12 and d['liabilities']==c['liabilities']
