"""Illiquid real estate layer: noisy observers, latent true return, IID residual.

Implements the codeable core of the Abu Dhabi plan (2026-11-07):

* Layer 2 baselines - Geltner (1993) AR(1) reverse filter and the
  Fisher-Geltner-Webb zero-autocorrelation variant (choose the smoothing
  parameter so the unsmoothed series has zero lag-1 autocorrelation);
* Layer 2 accurate core - a linear-Gaussian state-space model: latent true
  quarterly log return r_t with AR(1) momentum (kept, not forced to zero -
  real estate momentum is genuine), observed through several smoothed,
  noisy observers o_i,t = (1 - c_i) r_t + c_i r_{t-1} + eps_i (appraisal
  smoothing per observer).  Kalman filter + RTS smoother recover the
  latent path; parameters are supplied or crudely moment-fitted (EM is
  future work - documented);
* Layer 3 diagnostics - ACF, Ljung-Box, ARCH-LM on the residual invariant
  (the invariant must be IID, not normal);
* Layer 4 - stationary block bootstrap of residual vectors with parameter
  uncertainty: smoothing/momentum parameters are jittered per scenario
  batch and the residuals re-derived, so scenario sets propagate parameter
  uncertainty instead of fixing one desmoothing choice (the plan's main
  robustness feature, echoing Couts-Goncalves-Rossi 2024);
* Scalability - ``MarketAdapter`` registry: each market plugs in a loader
  and observer mapping, with a manifest entry (URL, access date, licence,
  hash).  No data ships here: the licensed/non-bulk sources (REIDIN,
  ADREC, ValuStrat) cannot be pulled programmatically, and third-party
  dashboards are not scraped.  Validation is therefore SYNTHETIC (known
  truth) until a licensed source lands in data/raw/<source>/<date>/ with
  its manifest.  BIS/FRED UAE quarterly series is the intended free
  backbone (licence check pending).

Layer 5 (state-dependent liquidity) lives in toolbox/meucci_liquidity.py:
time-to-sell and cost as state-dependent random variables convolved with
the market distribution - the adapter passes market-state series through.

References: Geltner (1993) doi:10.1111/1540-6229.00605; Fisher-Geltner-
Webb (1994); Couts, Goncalves & Rossi (RFS 2024); the Abu Dhabi plan of
2026-11-07 (repo docs).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Layer 2 baselines: reverse-filter unsmoothing
# ---------------------------------------------------------------------------

def geltner_unsmooth(observed: np.ndarray, smoothing: float) -> np.ndarray:
    """Geltner AR(1) reverse filter: r_t = (o_t - c o_{t-1}) / (1 - c).

    Recovers the latent return from an observed series smoothed as
    o_t = (1 - c) r_t + c o_{t-1}.  c in [0, 1).  The first observation is
    dropped (no o_0 history).
    """
    o = np.asarray(observed, dtype=float).ravel()
    if not 0 <= smoothing < 1:
        raise ValueError("smoothing must be in [0, 1)")
    return (o[1:] - smoothing * o[:-1]) / (1.0 - smoothing)


def fgw_unsmooth(observed: np.ndarray) -> tuple[np.ndarray, float]:
    """Fisher-Geltner-Webb: pick the smoothing parameter that zeroes lag-1 ACF.

    Grid-searches c in [0, 0.99] for the unsmoothed series with lag-1
    autocorrelation closest to zero.  Returns (unsmoothed, c).  Documented
    risk (Delfim): this can OVER-unsmooth when the observed autocorrelation
    is partly genuine momentum - always report the vol range across c.
    """
    o = np.asarray(observed, dtype=float).ravel()
    grid = np.linspace(0.0, 0.99, 200)
    best_c, best_acf = 0.0, np.inf
    for c in grid:
        r = geltner_unsmooth(o, c)
        acf1 = np.corrcoef(r[1:], r[:-1])[0, 1]
        if abs(acf1) < abs(best_acf):
            best_c, best_acf = c, acf1
    return geltner_unsmooth(o, best_c), float(best_c)


# ---------------------------------------------------------------------------
# Layer 2 core: multi-observer state-space (Kalman filter + RTS smoother)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LatentReturnModel:
    """Latent r_t = mu + rho (r_{t-1} - mu) + eta_t, eta ~ N(0, q).

    Observer i: o_i,t = (1 - c_i) r_t + c_i r_{t-1} + eps_i, eps ~ N(0, r_i).
    rho in (-1, 1) keeps genuine momentum as a forecastable component; the
    invariant is taken after removing it (the plan's Layer 3 requirement).
    """

    mu: float
    rho: float
    q: float  # innovation variance of the latent return
    smoothing: tuple[float, ...]  # c_i per observer
    obs_var: tuple[float, ...]  # r_i per observer

    def __post_init__(self) -> None:
        if not -1 < self.rho < 1 or self.q <= 0:
            raise ValueError("need |rho| < 1 and q > 0")
        if len(self.smoothing) != len(self.obs_var):
            raise ValueError("one smoothing weight and obs variance per observer")


def kalman_smooth(observations: np.ndarray, model: LatentReturnModel) -> dict:
    """Kalman filter + RTS smoother for the latent return path.

    ``observations``: (T, n_observers) observer series (NaN = missing -
    thin quarters simply drop that observer for that period).  State
    x_t = (r_t, r_{t-1}).  Returns filtered/smoothed latent means and the
    smoothed residual (invariant) series.
    """
    obs = np.atleast_2d(np.asarray(observations, dtype=float))
    if obs.shape[1] != len(model.smoothing):
        raise ValueError("one observation column per observer")
    T, k = obs.shape
    F = np.array([[model.rho, 0.0], [1.0, 0.0]])
    const = np.array([model.mu * (1 - model.rho), 0.0])
    Q = np.diag([model.q, 1e-12])
    c = np.asarray(model.smoothing)
    H_full = np.column_stack([1 - c, c])  # (k, 2)
    R = np.asarray(model.obs_var)

    x_filt = np.array([model.mu, model.mu])
    P_filt = np.diag([model.q / (1 - model.rho**2), model.q / (1 - model.rho**2)])
    xs, Ps, x_pred, P_pred = [], [], [], []
    for t in range(T):
        if t > 0:
            x_filt = const + F @ x_filt
            P_filt = F @ P_filt @ F.T + Q
        x_pred.append(x_filt.copy())
        P_pred.append(P_filt.copy())
        row = obs[t]
        ok = ~np.isnan(row)
        if ok.any():
            H, y, Rv = H_full[ok], row[ok], R[ok]
            S = H @ P_filt @ H.T + np.diag(Rv)
            K = P_filt @ H.T @ np.linalg.inv(S)
            x_filt = x_filt + K @ (y - H @ x_filt)
            P_filt = (np.eye(2) - K @ H) @ P_filt
        xs.append(x_filt.copy())
        Ps.append(P_filt.copy())
    # RTS smoother (backwards)
    sm_x, sm_P = [None] * T, [None] * T
    sm_x[-1], sm_P[-1] = xs[-1], Ps[-1]
    for t in range(T - 2, -1, -1):
        J = Ps[t] @ F.T @ np.linalg.inv(P_pred[t + 1])
        sm_x[t] = xs[t] + J @ (sm_x[t + 1] - x_pred[t + 1])
        sm_P[t] = Ps[t] + J @ (sm_P[t + 1] - P_pred[t + 1]) @ J.T
    latent = np.array([x[0] for x in sm_x])
    # invariant: innovation of the smoothed latent after removing momentum
    innov = latent[1:] - (model.mu + model.rho * (latent[:-1] - model.mu))
    return {
        "latent_smoothed": latent,
        "latent_var": np.array([P[0, 0] for P in sm_P]),
        "invariant": innov,
    }


def moment_fit(observations: np.ndarray) -> LatentReturnModel:
    """Crude moment fit for a single-observer series (placeholder for EM).

    Sets mu to the sample mean, rho to zero (momentum off until estimated
    honestly), q so the implied observed variance matches, smoothing from
    the observed lag-1 autocorrelation (c = acf1 / (1 + acf1), the AR(1)
    implied appraisal weight), and a small observer noise floor.  Clearly a
    starting point, flagged in the plan as replace-by-EM.
    """
    o = np.atleast_2d(np.asarray(observations, dtype=float))
    if o.shape[1] != 1:
        raise ValueError("moment_fit handles one observer; fit the state-space jointly instead")
    series = o[:, 0]
    series = series[~np.isnan(series)]
    acf1 = float(np.corrcoef(series[1:], series[:-1])[0, 1])
    c = float(np.clip(acf1 / (1 + acf1), 0.0, 0.95))
    mu = float(series.mean())
    var_obs = float(series.var(ddof=1))
    q = max(var_obs * (1 - c) ** 2, 1e-8)
    # Momentum estimate: FGW-unsmooth first (removes the smoothing-induced
    # ACF), then take the residual lag-1 autocorrelation as rho.  Still
    # crude - the smoothing split between c and rho is exactly what EM
    # would estimate jointly - but it stops rho from being pinned at zero
    # when the market genuinely trends.
    unsmoothed, c_fgw = fgw_unsmooth(series)
    rho = float(np.clip(np.corrcoef(unsmoothed[1:], unsmoothed[:-1])[0, 1], -0.9, 0.9))
    return LatentReturnModel(mu=mu, rho=rho, q=q, smoothing=(c_fgw,), obs_var=(var_obs * 0.05,))


# ---------------------------------------------------------------------------
# Layer 3 diagnostics (no statsmodels dependency)
# ---------------------------------------------------------------------------

def acf(series: np.ndarray, nlags: int) -> np.ndarray:
    x = np.asarray(series, dtype=float).ravel()
    x = x - x.mean()
    denom = x @ x
    return np.array([1.0] + [(x[k:] @ x[:-k]) / denom for k in range(1, nlags + 1)])


def ljung_box(series: np.ndarray, nlags: int) -> dict:
    """Ljung-Box Q test for residual autocorrelation up to ``nlags``."""
    x = np.asarray(series, dtype=float).ravel()
    n = len(x)
    r = acf(x, nlags)[1:]
    q_stat = n * (n + 2) * np.sum(r**2 / (n - np.arange(1, nlags + 1)))
    return {"Q": float(q_stat), "df": nlags, "p_value": float(stats.chi2.sf(q_stat, nlags))}


def arch_lm(series: np.ndarray, nlags: int = 5) -> dict:
    """Engle's ARCH-LM: regress squared residuals on their lags (TR^2 ~ chi2)."""
    x = np.asarray(series, dtype=float).ravel()
    e2 = (x - x.mean()) ** 2
    n = len(e2) - nlags
    y = e2[nlags:]
    X = np.column_stack([np.ones(n)] + [e2[nlags - k - 1: len(e2) - k - 1] for k in range(nlags)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    r2 = 1.0 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    lm = n * r2
    return {"LM": float(lm), "df": nlags, "p_value": float(stats.chi2.sf(lm, nlags))}


# ---------------------------------------------------------------------------
# Layer 4: block bootstrap with parameter uncertainty
# ---------------------------------------------------------------------------

def block_bootstrap_with_parameter_uncertainty(
    residuals: np.ndarray,
    horizon_periods: int,
    n_scenarios: int,
    block_length: int,
    seed: int,
    param_draws: tuple[np.ndarray, ...] = (),
    refit_fn=None,
) -> np.ndarray:
    """Stationary-style block bootstrap of residual vectors, with parameter
    uncertainty propagated per scenario batch.

    residuals: (T, d) invariant vectors (cross-dependence preserved by
    resampling whole rows in blocks).  ``param_draws``: optional tuple of
    parameter arrays (e.g. smoothing weights) - each scenario batch draws
    one parameter value and, when ``refit_fn`` is given, re-derives the
    residual set under that parameter before resampling.  Horizon scenarios
    are sums of ``horizon_periods`` resampled residual vectors (log returns
    aggregate by summation).
    """
    x = np.atleast_2d(np.asarray(residuals, dtype=float))
    T, d = x.shape
    if not 1 <= block_length <= T:
        raise ValueError("bad block length")
    rng = np.random.default_rng(seed)
    n_batches = max(1, len(param_draws[0])) if param_draws else 1
    per_batch = n_scenarios // n_batches
    out = []
    for b in range(n_batches):
        pool = x
        if param_draws and refit_fn is not None:
            pool = np.atleast_2d(refit_fn(*[pd[b] for pd in param_draws]))
        starts = rng.integers(0, len(pool), size=(per_batch, horizon_periods))
        lengths = rng.geometric(1.0 / block_length, size=(per_batch, horizon_periods))
        idx = (starts + np.cumsum(lengths, axis=1) - lengths) % len(pool)
        out.append(pool[idx.reshape(-1)].reshape(per_batch, horizon_periods, d).sum(axis=1))
    scenarios = np.concatenate(out, axis=0)
    if scenarios.shape[0] < n_scenarios:  # top up from the last batch
        scenarios = np.concatenate([scenarios, scenarios[: n_scenarios - scenarios.shape[0]]])
    return scenarios


# ---------------------------------------------------------------------------
# Scalability: market adapters + manifest/licence registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DataManifest:
    """Provenance for one raw data drop (the plan's pull protocol)."""

    source: str  # e.g. "BIS", "FRED", "REIDIN", "ValuStrat", "ADREC", "DLD"
    url: str
    access_date: str  # ISO date
    licence: str  # what the terms allow; "pending" until verified
    sha256: str
    path: str  # data/raw/<source>/<date>/...

    def save(self, registry_path: Path) -> None:
        entries = []
        if registry_path.exists():
            entries = json.loads(registry_path.read_text())
        entries.append(self.__dict__)
        registry_path.write_text(json.dumps(entries, indent=2))


class MarketAdapter:
    """Interface one market plugs into: loader + observer mapping.

    Abu Dhabi is adapter one, Dubai (DLD open data) adapter two.  Real data
    lands only via licensed/open files dropped into data/raw/ with a
    DataManifest - never via scraping.
    """

    name: str = "abstract"

    def observer_series(self) -> dict[str, np.ndarray]:  # observer name -> quarterly log returns
        raise NotImplementedError

    def market_state(self) -> np.ndarray | None:  # optional state series for the liquidity layer
        return None


class SyntheticAdapter(MarketAdapter):
    """Validation adapter: synthetic observer of a known latent truth."""

    name = "synthetic"

    def __init__(self, observations: np.ndarray, truth: np.ndarray):
        self._obs = np.atleast_2d(np.asarray(observations, dtype=float))
        self._truth = np.asarray(truth, dtype=float).ravel()

    def observer_series(self) -> dict[str, np.ndarray]:
        return {f"observer_{i}": self._obs[:, i] for i in range(self._obs.shape[1])}

    @property
    def truth(self) -> np.ndarray:
        return self._truth


def simulate_smoothed_observations(
    n_periods: int,
    mu: float,
    rho: float,
    q: float,
    smoothing: tuple[float, ...],
    obs_var: tuple[float, ...],
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Known-truth synthetic world for validation: latent AR(1) return plus
    per-observer appraisal smoothing and noise.  Returns (observations, truth)."""
    rng = np.random.default_rng(seed)
    innov = rng.normal(0.0, np.sqrt(q), n_periods + 1)
    r = np.empty(n_periods + 1)
    r[0] = mu
    for t in range(1, n_periods + 1):
        r[t] = mu + rho * (r[t - 1] - mu) + innov[t]
    obs = np.column_stack([
        (1 - c) * r[1:] + c * r[:-1] + rng.normal(0.0, np.sqrt(rv), n_periods)
        for c, rv in zip(smoothing, obs_var)
    ])
    return obs, r[1:]


class CsvIndexAdapter(MarketAdapter):
    """Adapter for a licensed/open CSV price-index drop with a DataManifest.

    First concrete adapter: the BIS UAE residential property price index
    (REIDIN-derived national source) via FRED, landed at
    data/raw/fred/2026-11-07/ with its manifest entry.  Converts index
    levels to quarterly log returns - the observer series for the
    state-space layer.  UAE-wide, not Abu Dhabi-only: composition effects
    are a known data-quality caveat (see docs/ABU_DHABI_REAL_ESTATE.md).
    """

    name = "bis-uae-rppi"

    def __init__(self, csv_path):
        self._path = Path(csv_path)

    def observer_series(self) -> dict[str, np.ndarray]:
        import pandas as pd

        frame = pd.read_csv(self._path, index_col=0, parse_dates=True)
        values = frame.iloc[:, 0].astype(float)
        log_levels = np.log(values.to_numpy())
        returns = np.diff(log_levels)  # quarterly log returns
        return {self.name: returns}
