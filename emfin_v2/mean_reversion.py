"""Research-only mean-reverting equity scenario law ("Siegel camp" scenario).

Optional scenario model `mixture_mean_reverting`: the default weekly Gaussian
scale mixture PLUS one shared transitory AR(1) price component (a slow "fad"
or market cycle) on the equity factor assets. Poterba-Summers (1988) style:
log price = random walk + transitory AR(1). Bad decades are partly offset by
later recoveries, so multi-year equity variance grows slower than iid.

The default law is unchanged; this model is selected only by an explicit
scenario_model='mixture_mean_reverting' config. Nothing here alters the iid
base, the fhs_ewma fifth law, or any frozen result.

Construction (weekly, per scenario, shared scalar state g_t across equity
members, stationary sigma_g = 1):

    r_i,t = mu_i + eps_i,t / scale_t + w_i * fr_t
    fr_t  = (phi - 1) * g_{t-1} + sqrt(1 - phi^2) * nu_t
    g_t   = phi * g_{t-1} + sqrt(1 - phi^2) * nu_t,   g_0 ~ N(0, 1)

    phi   = 0.5 ** (1 / (52 * half_life_years))
    w_i   = sqrt(share * cov_ii / (2 * (1 - phi)))

The permanent covariance loses exactly what the fad adds:

    cov_perm[eq, eq] = cov[eq, eq] - share * sigma sigma'

so the unconditional weekly mean and covariance equal the fitted iid moments
EXACTLY (algebra in variance_ratio; verified in tests). All long-horizon
variance reduction comes from negative return autocorrelation, never from
lower weekly variance. Finite price moments of every finite order hold:
Gaussian permanent mixture plus a stationary Gaussian AR(1).

Analytic T-week equity variance ratio (vs iid, same fitted moments):

    VR(T) = (1 - share) + share * (1 - phi**T) / (T * (1 - phi))

Calibration is DECLARED, not estimated: half-life and variance share are
chosen to sit inside the published US-equity range (Fama-French 1988 3-5y
return autocorrelations about -0.25 to -0.4; Poterba-Summers 1988 variance
ratios well below 1 at 3-8y; later and cross-country evidence weaker and
noisier). Sources and the implied VR table are reported by describe(). The
parameters are treated as KNOWN inside the scenario: Pastor-Stambaugh (2012)
show estimation uncertainty can more than offset the variance reduction, so
results under this law are a "if mean reversion is real and known" case, not
a forecast.
"""
import numpy as np

MODEL = 'mixture_mean_reverting'
DEFAULT = dict(half_life_years=2.0, variance_share=0.40)
SOURCES = [
    'Fama & French (1988) Permanent and Temporary Components of Stock Prices, JFE 22(1) https://doi.org/10.1016/0304-405X(88)90020-7',
    'Poterba & Summers (1988) Mean Reversion in Stock Prices: Evidence and Implications, JFE 22(1) https://www.nber.org/papers/w2343',
    'Pastor & Stambaugh (2012) Are Stocks Really Less Volatile in the Long Run?, J. Finance 67(2) https://doi.org/10.1111/j.1540-6261.2012.01722.x',
    'Blanchett, Finke & Pfau (2014) Required Savings: An International Analysis (mean-reversion evidence across 20 countries) https://ssrn.com/abstract=2422499',
    'Siegel, Stocks for the Long Run (5e) long-horizon real-return evidence; Dimson, Marsh & Staunton via https://www.london.edu/think/how-long-is-long-term',
]


def settings(c):
    x = dict(DEFAULT, **c.get('mean_reversion', {}))
    if set(x) != set(DEFAULT):
        raise ValueError('mean reversion settings keys are %s' % sorted(DEFAULT))
    if any(not isinstance(v, (int, float)) or not np.isfinite(v) for v in x.values()):
        raise ValueError('mean reversion settings must be finite numbers')
    if not 0 < x['half_life_years'] <= 10 or not 0 < x['variance_share'] < 1:
        raise ValueError('mean reversion needs 0<half_life_years<=10 and 0<variance_share<1')
    return x


def phi_weekly(params):
    return float(0.5 ** (1.0 / (52.0 * params['half_life_years'])))


def loadings(cov, members, params):
    """w_i per equity member so the fad carries share of each asset's variance."""
    cov = np.asarray(cov, float)
    phi = phi_weekly(params)
    s = params['variance_share']
    w = np.zeros(cov.shape[0])
    for i in members:
        if cov[i, i] <= 0:
            raise ValueError('mean reversion needs positive equity variance')
        w[i] = np.sqrt(s * cov[i, i] / (2.0 * (1.0 - phi)))
    return w


def permanent_covariance(cov, members, params):
    """cov minus exactly the fad's weekly covariance; fails loudly if not PSD."""
    cov = np.asarray(cov, float)
    s = params['variance_share']
    out = cov.copy()
    sd = np.sqrt(np.diag(cov))
    block = np.ix_(members, members)
    out[block] -= s * np.outer(sd[members], sd[members])
    eig = np.linalg.eigvalsh(out)
    tol = 1e-10 * max(1.0, float(np.abs(eig).max()))
    if eig.min() < -tol:
        raise ValueError('mean reversion variance_share too large: permanent covariance not PSD '
                         '(min eigenvalue %.3e); lower variance_share' % eig.min())
    return out


def fad_returns(rng, n, h, params):
    """(n, h) shared transitory-component return contribution fr_t."""
    phi = phi_weekly(params)
    g = rng.normal(size=n)
    nu = rng.normal(size=(n, h))
    out = np.empty((n, h))
    sd = np.sqrt(1.0 - phi * phi)
    for t in range(h):
        out[:, t] = (phi - 1.0) * g + sd * nu[:, t]
        g = phi * g + sd * nu[:, t]
    return out


def variance_ratio(params, weeks):
    """Exact T-week equity variance ratio vs the iid base with the same moments."""
    phi = phi_weekly(params)
    s = params['variance_share']
    t = np.asarray(weeks, float)
    if (t < 1).any():
        raise ValueError('whole positive weeks required')
    return (1.0 - s) + s * (1.0 - phi ** t) / (t * (1.0 - phi))


def describe(c):
    p = settings(c)
    phi = phi_weekly(p)
    years = [1, 3, 5, 8, 15, 30]
    vr = variance_ratio(p, [52 * y for y in years])
    return dict(
        model=MODEL,
        price_exponential_moments='finite at all finite orders: Gaussian-mixture permanent walk plus stationary Gaussian AR(1) transitory component',
        settings=p,
        weekly_phi=phi,
        implied_equity_variance_ratio={f'{y}y': float(v) for y, v in zip(years, vr)},
        calibration='DECLARED, not estimated: chosen inside the published US-equity mean-reversion range; parameters treated as known inside the scenario.',
        estimation_caveat='Pastor-Stambaugh (2012): with parameter/expected-return uncertainty, predictive variance per year at long horizons is at least ~1.3x the iid figure at 50y. This scenario omits that uncertainty; it is the "mean reversion real and known" case.',
        scope='Research-only optional scenario. Default iid mixture law unchanged. Shared equity fad only; gold, Treasuries, TIPS, bills, cash, FX and property keep their base dynamics (property keeps its configured equity correlation through the full equity innovation).',
        sources=SOURCES)
