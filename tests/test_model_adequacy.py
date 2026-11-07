import copy
import numpy as np
import pandas as pd
import pytest
from scipy.integrate import quad
from scipy.special import ndtr
from experiments.model_adequacy import mixture_crps,empirical_crps,garch_variances,fit_garch,select,summarize,P,V


def test_mixture_crps_matches_direct_integral():
    y=.7;mu=.1;var=1.3
    cdf=lambda x:P@ndtr((x-mu)/np.sqrt(var*V))
    oracle=quad(lambda x:cdf(x)**2,-20,y,epsabs=1e-10)[0]+quad(lambda x:(cdf(x)-1)**2,y,20,epsabs=1e-10)[0]
    assert mixture_crps(y,mu,var)==pytest.approx(oracle,abs=1e-9)


def test_empirical_crps_matches_pairwise_formula_with_atoms():
    samples=np.array([-3.,0.,0.,8.]);y=1.
    oracle=np.mean(abs(samples-y))-.5*np.mean(abs(samples[:,None]-samples[None,:]))
    assert empirical_crps(y,samples)==pytest.approx(oracle)
    assert empirical_crps(5.,[2.])==3.


def test_conditional_variance_timing_hand_oracle():
    # v0=2, v1=.5+.1*4+.7*2=2.3, v2=.5+.1*9+.7*2.3=3.01
    v=garch_variances([2.,3.],.5,.1,.7,2.)
    np.testing.assert_allclose(v,[2.,2.3,3.01])
    assert garch_variances([2.,300.],.5,.1,.7,2.)[1]==v[1]


def test_garch_unit_scaling_and_bounded_parameters():
    x=np.random.default_rng(18).normal(size=200)*.02
    a=fit_garch(x);b=fit_garch(100*x)
    assert a['available'] and b['available']
    assert a['alpha']+a['beta']<=.99900001
    assert b['next_variance']==pytest.approx(a['next_variance']*10000,rel=2e-4)


def test_future_returns_cannot_change_earlier_forecasts():
    from experiments.model_adequacy import annual_forecasts
    from emfin_v2.default_run import load_config,setup
    c=load_config();frame=setup(c)[0];year=2014;short=frame.loc[frame.index<'2014-02-01'].copy()
    before,_=annual_forecasts(short,c,year)
    changed=frame.copy();changed.loc[changed.index>='2014-02-01','us_equity']+=1.
    after,_=annual_forecasts(changed,c,year)
    cutoff=[r for r in after if r['date']<'2014-02-01']
    assert before==cutoff


def test_selection_never_sees_final_and_disqualifies_missing_candidate(tmp_path):
    records=[dict(year=2014,method=m,normalized_crps=v) for m,v in [('iid_mix',1),('ewma_mix',.9),('ewma_fhs',.95)]]
    result=dict(years=[2014],records=records,protocol_sha256='protocol',source_sha256='source')
    lock=select(result,tmp_path/'lock.json');assert lock['selected']=='ewma_mix'
    assert not lock['final_scores_computed'] and 'garch_mix' not in lock['validation_scores']
