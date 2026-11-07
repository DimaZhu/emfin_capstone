import json
from emfin_capstone.toolbox.reporting import write_report


def test_export_has_machine_readable_tables_and_caveats(tmp_path):
    bundle=dict(snapshot_end='2026-11-04',assets=['cash'],weights={'1/N':[1.]},
       benchmarks=[dict(method='1/N',parametric_ce=100.,empirical_ce=99.,parametric_gap_cvar=0.,budget=1.,solve_seconds=0.)],
       caveats=['illustrative only'])
    dest=write_report(bundle,tmp_path)
    assert json.loads((dest/'results.json').read_text())['assets']==['cash']
    assert 'illustrative only' in (dest/'appendix.md').read_text()
    assert '1/N' in (dest/'allocations.csv').read_text()
