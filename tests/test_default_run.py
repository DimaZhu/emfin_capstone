import json
import numpy as np
import pytest
from emfin_v2.default_run import load_config,run,draw_paths,setup,metrics


def test_default_end_to_end_calibration_and_heldout_report(tmp_path):
    c=load_config();result=run(c,tmp_path)
    assert result['status']['kind'] in ('optimized','calibrated optimizer/cash mixture')
    proposed=next(row for row in result['rows'] if row['method']=='proposed')
    assert proposed['evaluation_pass']
    assert np.array(proposed['gap_cvar']['high'])[-1] <= proposed['budgets'][-1]
    assert (tmp_path/'report.html').exists()
    assert 'Net wealth after cumulative payouts' in (tmp_path/'report.html').read_text()
    assert (tmp_path/'benchmarks.csv').exists()


def test_infeasible_real_estate_minimum_never_returns_fake_solution(tmp_path):
    c=load_config();c['real_estate']['source']='synthetic';c['real_estate']['enabled']=True;c['real_estate']['minimum_weight']=.3
    c['liability_vol']=.3;c['multiplier_grid']=[1.]
    result=run(c,tmp_path)
    # Status and validation must be explicit; no allocation may be relabeled
    # successful merely because the baseline itself has valid weights.
    if result['status']['kind']=='no calibration candidate passed':
        assert 'proposed' not in result['weights']
    else:
        assert result['weights']['proposed'][-1]>=.3-1e-5


def test_cumulative_net_terminal_matches_explicit_cash_accounting():
    c=load_config();draw=draw_paths(c,setup(c),20,7)
    a=np.zeros(6);a[5]=c['wealth']
    gaps,ce=metrics(c,draw,a)
    assert ce>0
    assert (gaps==0).all()
