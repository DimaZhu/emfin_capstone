import json,hashlib
import numpy as np
import pandas as pd
import pytest
import cvxpy as cp
from emfin_capstone.toolbox import raw_data,moneymarket,solvers
from emfin_capstone.engine import parse_options

@pytest.mark.parametrize('flag,field',[('--tsdr','tsdr'),('--no-tail-calibration','no_tail_calibration'),('--no-crra','no_surplus_cara'),('--no-surplus-cara','no_surplus_cara'),('--with-uniform-contrast','with_uniform_contrast')])
def test_research_boolean_flags(flag,field):assert getattr(parse_options([flag]),field)

@pytest.mark.parametrize('nu',[8.,30.])
def test_research_numeric_t_flag(nu):assert parse_options(['--student-t',str(nu)]).student_t==nu


def test_research_auto_and_tiny_n_flags():
    opts=parse_options(['--student-t=auto','--scenarios=32'])
    assert opts.student_t=='auto' and opts.scenarios==32

@pytest.mark.parametrize('args',[['--unknown'],['--student-t=3'],['--student-t=nan'],['--scenarios=2']])
def test_unknown_or_invalid_flags_rejected(args):
    with pytest.raises(SystemExit):parse_options(args)


def test_money_market_constant_and_rate_change():
    idx=pd.date_range('2020-01-01',periods=3,freq='W')
    rate=pd.Series([.052,.052,.062],index=idx)
    got=moneymarket.money_market_weekly_returns(rate)
    np.testing.assert_allclose(got.to_numpy(),[.001,.001-.25*.01])


def test_raw_manifest_relocates_and_checks_hash(tmp_path):
    folder=tmp_path/'data/raw';folder.mkdir(parents=True)
    file=folder/'different-date.csv';file.write_text('date,x\n2020,1\n')
    row=dict(series='X: Example',path='data/raw/different-date.csv',sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    (folder/'manifest.json').write_text(json.dumps([row]))
    assert raw_data.series_file('X',tmp_path)==file
    file.write_text('changed')
    with pytest.raises(ValueError,match='hash mismatch'):raw_data.series_file('X',tmp_path)


def test_pinned_loader_and_missing_series():
    assert raw_data.series_file('DGS3MO').is_file()
    with pytest.raises(ValueError):raw_data.series_file('NOT_A_SERIES')


def test_capped_solver_rejects_nonfinite_status_and_residual(monkeypatch):
    class Bad:
        value=float('nan');status=cp.OPTIMAL
        def solve(self,**kwargs):pass
        def variables(self):return []
    with pytest.raises(RuntimeError):solvers.solve_capped(Bad())
    class Violation:
        def violation(self):return np.array([.1])
    class InfeasiblePoint(Bad):
        value=1.;constraints=[Violation()]
    with pytest.raises(RuntimeError,match='constraint residual'):solvers.solve_capped(InfeasiblePoint())


def test_capped_solver_refuses_infeasible_optimization():
    x=cp.Variable();p=cp.Problem(cp.Minimize(x),[x>=1,x<=0])
    with pytest.raises(RuntimeError):solvers.solve_capped(p)


def test_research_main_tiny_n_smoke_stops_at_documented_infeasible_case(capsys):
    from emfin_capstone import engine
    with pytest.raises(RuntimeError,match='multi-period optimization failed validation'):
        engine.main(['--scenarios','64','--no-crra','--no-tail-calibration'])
    assert '64 scenarios' in capsys.readouterr().out or engine.N_SCENARIOS==64


def test_research_help_and_default_dispatch(capsys):
    from emfin_capstone import default_run
    with pytest.raises(SystemExit) as e:default_run.main(['--research','--help'])
    assert e.value.code==0
    assert '--with-uniform-contrast' in capsys.readouterr().out
