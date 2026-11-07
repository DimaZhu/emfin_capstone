"""Chronological development folds. Final window is excluded from selection.

Short history cannot validate a 95% tail budget reliably. All scores returned
here are exploratory; overlapping validation horizons are identified explicitly.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import gammaln

@dataclass(frozen=True)
class Fold:
    train_stop: int
    validation_stop: int


def chronological_folds(n, min_train=52, validation_size=26, final_size=26):
    if min_train < 2 or validation_size < 1 or final_size < 1:
        raise ValueError('positive fold lengths and at least two training observations required')
    dev_stop = n - final_size
    if dev_stop < min_train + validation_size:
        raise ValueError('not enough history for development plus sealed final window')
    folds = []
    for start in range(min_train, dev_stop, validation_size):
        end = min(start + validation_size, dev_stop)
        if end - start >= 13:
            folds.append(Fold(start, end))
    return folds, dev_stop


def horizon_sums(weekly, horizon=13):
    x = np.asarray(weekly, float)
    if len(x) < horizon:
        raise ValueError('validation block is shorter than horizon')
    cs = np.vstack([np.zeros(x.shape[1]), np.cumsum(x, axis=0)])
    return cs[horizon:] - cs[:-horizon]


def variance_matched_t_nll(samples, mean, cov, nu):
    """Mean negative log density, multivariate t with covariance cov (nu>2)."""
    if nu <= 2 or not np.isfinite(nu):
        raise ValueError('nu must be finite and >2')
    x = np.asarray(samples, float) - np.asarray(mean, float)
    cov = np.asarray(cov, float)
    d = x.shape[1]
    chol = np.linalg.cholesky(cov)
    z = np.linalg.solve(chol, x.T).T
    r2 = np.sum(z*z, axis=1)
    log_norm = gammaln((nu+d)/2) - gammaln(nu/2) - d/2*np.log((nu-2)*np.pi) - np.log(np.diag(chol)).sum()
    return float(np.mean(-log_norm + (nu+d)/2*np.log1p(r2/(nu-2))))


def fit_student_nu(samples, mean, cov, bounds=(2.1, 200.0)):
    """Conditional MLE of nu given location/covariance; not a joint t MLE."""
    result = minimize_scalar(lambda nu: variance_matched_t_nll(samples, mean, cov, nu),
                             bounds=bounds, method='bounded')
    if not result.success:
        raise RuntimeError('nu fit failed')
    return float(result.x)
