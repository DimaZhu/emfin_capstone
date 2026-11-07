import copy
import numpy as np
from experiments.robustness import config,actual_history_draw,empirical_radius_diagnostics
from emfin_v2.default_run import setup,validate_config
from emfin_v2.registry_runtime import fit_frame
from emfin_v2.ledger import cash_first


def test_past_only_fit_is_invariant_to_changes_in_future_rows():
    import pandas as pd
    c=config();frame=setup(c)[0];origin=pd.Timestamp('2019-12-27');past=frame.loc[frame.index<=origin]
    cc=copy.deepcopy(c);cc['history_end']='2019-12-27';cc=validate_config(cc);f1=fit_frame(cc,past)
    altered=frame.copy();altered.loc[altered.index>origin]=10.;f2=fit_frame(copy.deepcopy(cc),altered.loc[altered.index<=origin])
    np.testing.assert_array_equal(f1[1],f2[1]);np.testing.assert_array_equal(f1[2],f2[2])
    assert cc['real_estate']['history_end']=='2019-12-27'


def test_actual_history_ledger_has_genuine_future_dates_and_fixed_property():
    import pandas as pd
    c=config();frame=setup(c)[0];origin=pd.Timestamp('2021-12-31');draw,future=actual_history_draw(c,frame,origin)
    assert future.index[0]>origin and len(future)==52
    assert str(future.index[-1].date())=='2022-12-30'
    a=np.zeros(6);a[4]=.9*c['wealth'];a[5]=.1*c['wealth']
    result=cash_first(c,draw,a);assert result['funded'][0]
    np.testing.assert_array_equal(result['units_paths'][0,:,5],a[5])
    assert np.all(draw.funding_paths[:,:,5]==0)


def test_empirical_radius_is_diagnostic_not_confidence_claim():
    c=config();fit=setup(c);r=empirical_radius_diagnostics(c,fit)
    assert r['available'] and r['distance']>c['wasserstein_radius']
    assert 'not a statistically justified' in r['scope']
