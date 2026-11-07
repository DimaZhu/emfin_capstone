"""Descriptive checks of assumed market invariants, never an iid certificate.

Meucci (2005), printed pp.103-105: compare early/late distributions and
lagged observations before treating returns as iid invariants. Squared-return
lags also expose dependence hidden by nearly zero ordinary autocorrelation.
No observations are removed and no fitted parameter or risk limit is changed.
"""
import numpy as np
from scipy.stats import ks_2samp,skew,kurtosis


def _correlation(left,right):
    if np.std(left)<=1e-15 or np.std(right)<=1e-15:return None
    return float(np.corrcoef(left,right)[0,1])


def diagnose(samples,names,lags=(1,4,8)):
    x=np.asarray(samples,float)
    if x.ndim!=2 or len(x)<20 or x.shape[1]!=len(names) or not np.isfinite(x).all():
        raise ValueError('finite aligned matrix with at least20 chronological rows required')
    if not lags or any(type(k) is not int or not 1<=k<len(x)//2 for k in lags):
        raise ValueError('lags must be positive whole numbers shorter than half the history')
    half=len(x)//2;rows=[]
    for name,series in zip(names,x.T):
        early,late=series[:half],series[half:];sd=float(np.std(series,ddof=1));deterministic=bool(np.ptp(series)<=1e-15)
        lagged=[dict(lag=k,returns=_correlation(series[:-k],series[k:]),squared_returns=_correlation((series-series.mean())[:-k]**2,(series-series.mean())[k:]**2)) for k in lags]
        rows.append(dict(name=str(name),observations=len(series),deterministic=deterministic,early_count=len(early),late_count=len(late),early_mean=float(early.mean()),late_mean=float(late.mean()),early_vol=float(np.std(early,ddof=1)),late_vol=float(np.std(late,ddof=1)),sample_skewness=None if deterministic else float(skew(series,bias=False)),sample_excess_kurtosis=None if deterministic else float(kurtosis(series,bias=False)),mean_shift_in_full_sample_sd=None if deterministic else float((late.mean()-early.mean())/sd),split_cdf_distance=float(ks_2samp(early,late,method='asymp').statistic),lagged=lagged))
    return dict(available=True,rows=rows,observations=len(x),assumption='Raw weekly log returns are modeled iid by the Gaussian-mixture default; this assumption has not been established.',scope='Descriptive split-distribution and lag diagnostics, inspired by Meucci (2005), pp.103-105. No p-values, multiple-test pass label or economic coverage claim. Low linear autocorrelation alone does not imply independence; squared-return dependence can remain. No data cleaning, parameter adjustment or model selection is performed.',book=dict(title='Risk and Asset Allocation',author='Attilio Meucci',year=2005,printed_pages='103-105',pdf_pages='125-127'))
