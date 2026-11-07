"""Explicit weekly innovation laws; no hidden tail clipping or model substitution."""
import numpy as np
from scipy.special import logsumexp

MODELS=('gaussian','gaussian_scale_mixture','legacy_student_t','fhs_ewma','bounded_ewma_mixture')
DEFAULT_MIXTURE=dict(probabilities=[.9,.1],variance_scales=[.75,3.25])


def validate(c):
    model=c.get('scenario_model','legacy_student_t' if c.get('student_nu') is not None else 'gaussian')
    if model not in MODELS:raise ValueError('unsupported scenario_model')
    c['scenario_model']=model
    if model in ('gaussian_scale_mixture','bounded_ewma_mixture'):
        mix=c.setdefault('innovation_mixture',dict(DEFAULT_MIXTURE));p=np.asarray(mix.get('probabilities'),float);v=np.asarray(mix.get('variance_scales'),float)
        if p.ndim!=1 or len(p)<2 or p.shape!=v.shape or not np.isfinite(p).all() or not np.isfinite(v).all() or (p<=0).any() or (v<=0).any() or abs(p.sum()-1)>1e-12 or abs(p@v-1)>1e-12:
            raise ValueError('mixture needs positive probabilities summing to1 and positive variance scales with weighted mean1')
    if model=='legacy_student_t' and (c.get('student_nu') is None or c['student_nu']<=4):raise ValueError('legacy Student-t model requires nu>4')
    if model=='bounded_ewma_mixture':
        from emfin_v2.bounded_volatility import settings
        c['bounded_volatility']=settings(c)
    return model


def divisor(c,rng,n,h):
    """Shared cross-asset variance state per week, independent across weeks.

The returned divisor applies to the joint listed/FX/property Gaussian shock,
so unconditional covariance and the chosen cross-asset dependence are retained.
"""
    model=validate(c)
    if model in ('gaussian','fhs_ewma'):return np.ones((n,h,1))
    if model=='legacy_student_t':return np.sqrt(rng.chisquare(c['student_nu'],(n,h,1))/(c['student_nu']-2))
    mix=c['innovation_mixture'];v=np.asarray(mix['variance_scales']);state=rng.choice(len(v),size=(n,h,1),p=mix['probabilities'])
    return 1/np.sqrt(v[state])


def log_gross_moment(c,mean,cov,exposure,weeks=1):
    """Log E[exp(exposure @ cumulative log-return)] under stated iid law.

Supports joint ETFs/FX and any Gaussian-linear property innovation once its
joint covariance is supplied. It does not silently convert log drift into an
arithmetic return target. Legacy t has no nonzero exponential moment.
"""
    model=validate(c)
    if model in ('fhs_ewma','bounded_ewma_mixture'):raise ValueError('analytic iid mixture moments do not apply to recursive conditional variance')
    b=np.asarray(exposure,float);mu=np.asarray(mean,float);cov=np.asarray(cov,float)
    if b.shape!=mu.shape or cov.shape!=(len(mu),len(mu)) or not np.isfinite(b).all() or not np.isfinite(mu).all() or not np.isfinite(cov).all() or type(weeks) is not int or weeks<1:raise ValueError('finite aligned moment inputs and positive whole weeks required')
    variance=float(b@cov@b)
    if variance < -1e-12:raise ValueError('covariance must give nonnegative exposure variance')
    if model=='legacy_student_t':return float('inf') if variance>1e-15 else weeks*float(b@mu)
    p=np.array([1.]);v=np.array([1.])
    if model=='gaussian_scale_mixture':p=np.asarray(c['innovation_mixture']['probabilities']);v=np.asarray(c['innovation_mixture']['variance_scales'])
    return float(weeks*(b@mu+logsumexp(np.log(p)+.5*v*max(variance,0))))


def describe(c):
    model=validate(c)
    if model=='bounded_ewma_mixture':return dict(model=model,price_exponential_moments='finite at every finite order/horizon by uniform conditional-MGF bound, not iid exact formula',settings=c['bounded_volatility'],scope='Research-only explicitly capped EWMA variance. Gaussian-mixture returns unbounded; floor/cap relative to past covariance diagonal. Cap changes extreme variance propagation and is not calibrated.')
    if model=='fhs_ewma':return dict(model=model,price_exponential_moments='finite at fixed finite horizons under bounded empirical standardized shocks and finite EWMA recursion, with Gaussian property residuals',scope='Past-only EWMA FHS variant; joint standardized residual rows, development decay0.94, simulated volatility recursion. Not fitted GARCH or a replication of published FHS parameters.')
    if model=='gaussian_scale_mixture':return dict(model=model,price_exponential_moments='finite at all finite orders for linear Gaussian-mixture log paths',mixture=c['innovation_mixture'],scope='Development-selected iid weekly variance mixture, not fitted regimes, not Student-t and not FHS. Log covariance preserved. A common state couples listed assets, FX and property shocks.')
    return dict(model=model,price_exponential_moments='not finite for nonzero-variance log-t legs' if model=='legacy_student_t' else 'finite for linear Gaussian log paths',scope='Explicit legacy compatibility model; not evidence of calibration.' if model=='legacy_student_t' else 'Gaussian iid weekly log shocks.')
