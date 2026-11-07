"""Meucci (2012) integrated liquidity + market risk: scenario-dependent overlay.

Upgrade of ``toolbox.liquidity``'s state-independent beta-cost convolution to
the model of Meucci (2012), "A Fully Integrated Liquidity and Market Risk
Model", FAJ 68(6) - the conditional-convolution overlay in which each market
scenario j carries its own liquidity adjustment

    DeltaPi | scenario j  ~  N(mu(j), sigma(j)^2),                          (5)

whose parameters depend on the market state, the liquidated amounts and the
execution horizon.  VWAP-execution calibration (Eqs. 6-8, square-root
impact):

    mu_n    = -alpha_n e_n |dh_n| - beta_n e_n sigma_n |dh_n|^{3/2} / sqrt(v_n)   (6)
    sigma_n =  delta_n sqrt(v_n) e_n |dh_n|                                       (7)
    rho_n,m =  gamma + (1 - gamma) rho^M_n,m     (shrunk toward 1)                (8)

with e_n the per-unit exposure (price), |dh_n| the liquidated amount in
units, sigma_n the annualized per-unit P&L vol, v_n the market volume over
the execution window, and alpha/beta/delta calibration coefficients that
may vary with the market state x (liquidity dries up in stress scenarios).

Total P&L: Pi_tot = Pi + DeltaPi is a mixture of normals across scenarios
(Eq. 10), giving an analytic density, a CVaR decomposition into market and
liquidity contributions (Eq. 12) and a monetary liquidity score (Eq. 13).

What changes vs the previous beta convolution: costs are state-dependent
(liquidations in stressed scenarios cost more), superlinear in size
(square-root impact), uncertain with cross-asset correlation shrunk toward
1 (liquidity risk diversifies less than market risk), and the liquidation
schedule itself may depend on the scenario (funding risk).  The optimizer
interface is untouched: the output is still one net-price scenario matrix.

Calibration note: alpha/beta/delta/v are PLACEHOLDERS here (no volume data
in the snapshot); the module's job is the correct functional form, and the
parameters are communicable client inputs.  Reference code: Meucci's
MATLAB at mathworks.com/fileexchange/43243 (algorithm cross-checked
against the paper's formulas, not copied).

Reference:
    Meucci (2012), doi:10.2469/faj.v68.n6.6.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class MeucciLiquidityParams:
    """Per-asset VWAP liquidity calibration (Eqs. 6-7).

    alpha: commissions + half-spread as a fraction of unit exposure.
    beta:  square-root impact coefficient.
    delta: impact-uncertainty coefficient (units 1/sqrt(volume)).
    ann_vol: annualized P&L vol of one unit, as a fraction of exposure.
    adv:   market volume (units) over the execution window.
    """

    alpha: float
    beta: float
    delta: float
    ann_vol: float
    adv: float

    def __post_init__(self) -> None:
        if min(self.alpha, self.beta, self.delta, self.ann_vol) < 0 or self.adv <= 0:
            raise ValueError("need alpha,beta,delta,ann_vol >= 0 and adv > 0")


def adjustment_moments(
    amounts: np.ndarray,
    exposures: np.ndarray,
    params: list[MeucciLiquidityParams],
    market_corr: np.ndarray,
    gamma: float,
    state_multiplier: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-scenario mean and std of the portfolio liquidity adjustment.

    ``amounts``: (n_scenarios, n_assets) liquidated units per scenario
    (positive = selling); ``exposures``: (n_assets,) current unit prices;
    ``state_multiplier``: optional (n_scenarios,) stress multiplier applied
    to alpha/beta/delta - the state dependence x in Eqs. 6-8 (e.g. >1 when
    the scenario's equity drawdown is severe).  Returns (mu, sigma), each
    (n_scenarios,), of the total portfolio adjustment DeltaPi (Eq. 9).
    """
    dh = np.atleast_2d(np.asarray(amounts, dtype=float))
    e = np.asarray(exposures, dtype=float).ravel()
    n_scen, n_assets = dh.shape
    if len(params) != n_assets or e.shape[0] != n_assets:
        raise ValueError("one params entry and exposure per asset column")
    mult = np.ones(n_scen) if state_multiplier is None else np.asarray(state_multiplier, dtype=float).ravel()
    if mult.shape[0] != n_scen:
        raise ValueError("one state multiplier per scenario")

    a = np.array([p.alpha for p in params]) * mult[:, None]
    b = np.array([p.beta for p in params]) * mult[:, None]
    d = np.array([p.delta for p in params]) * mult[:, None]
    vol = np.array([p.ann_vol for p in params])
    v = np.array([p.adv for p in params])

    # Eq. 6 (expected impact: linear cost + square-root impact) and Eq. 7
    mu_assets = -a * e * np.abs(dh) - b * e * vol * np.abs(dh) ** 1.5 / np.sqrt(v)
    sigma_assets = d * np.sqrt(v) * e * np.abs(dh)

    # Eq. 8: liquidity correlations = market correlations shrunk toward 1
    corr_m = np.asarray(market_corr, dtype=float)
    if corr_m.shape != (n_assets, n_assets):
        raise ValueError("market_corr must be (n_assets, n_assets)")
    if not 0.0 <= gamma <= 1.0:
        raise ValueError("gamma must be in [0, 1]")
    corr_l = gamma + (1.0 - gamma) * corr_m

    mu = mu_assets.sum(axis=1)  # Eq. 9, mu = sum_n mu_n
    var = np.einsum("jn,nm,jm->j", sigma_assets, corr_l, sigma_assets)
    return mu, np.sqrt(np.maximum(var, 0.0))


def apply_meucci_liquidity(
    price_scenarios: np.ndarray,
    amounts: np.ndarray,
    params: list[MeucciLiquidityParams],
    market_corr: np.ndarray,
    gamma: float = 0.9,
    state_multiplier: np.ndarray | None = None,
    seed: int = 0,
) -> np.ndarray:
    """Convolve a price scenario matrix with the Meucci liquidity overlay.

    Full-liquidation convention: the ``amounts`` are the holdings sold in
    each scenario, and the per-asset adjustment DeltaPi_n / amount_n shifts
    that scenario's net liquidation price.  Correlated normal draws (Eqs.
    5-9) keep the cross-asset liquidity co-movement that independent cost
    draws miss.  Returns a net-price scenario matrix - the optimizer
    downstream is untouched.
    """
    prices = np.asarray(price_scenarios, dtype=float)
    dh = np.atleast_2d(np.asarray(amounts, dtype=float))
    if dh.shape != prices.shape:
        raise ValueError("amounts must match the scenario matrix shape")
    n_scen, n_assets = prices.shape

    mu_assets_parts = []
    # per-asset moments for the correlated draw
    e = prices.mean(axis=0)  # exposure reference: scenario-mean price
    mult = np.ones(n_scen) if state_multiplier is None else np.asarray(state_multiplier).ravel()
    a = np.array([p.alpha for p in params]) * mult[:, None]
    b = np.array([p.beta for p in params]) * mult[:, None]
    d = np.array([p.delta for p in params]) * mult[:, None]
    vol = np.array([p.ann_vol for p in params])
    v = np.array([p.adv for p in params])
    mu_assets = -a * e * np.abs(dh) - b * e * vol * np.abs(dh) ** 1.5 / np.sqrt(v)
    sigma_assets = d * np.sqrt(v) * e * np.abs(dh)

    corr_l = gamma + (1.0 - gamma) * np.asarray(market_corr, dtype=float)
    chol = np.linalg.cholesky(corr_l + 1e-12 * np.eye(n_assets))
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_scen, n_assets)) @ chol.T
    delta_pi = mu_assets + sigma_assets * z  # (n_scen, n_assets) money adjustments

    with np.errstate(divide="ignore", invalid="ignore"):
        per_unit = np.where(np.abs(dh) > 0, delta_pi / np.abs(dh), 0.0)
    return prices + per_unit


def total_pnl_density(
    y_grid: np.ndarray,
    pnl_scenarios: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    probs: np.ndarray | None = None,
) -> np.ndarray:
    """Eq. 10: the total liquidity-plus-market-risk P&L density on a grid.

    f(y) = sum_j p_j phi((y - pi_j - mu_j) / sigma_j) / sigma_j.  With zero
    liquidity adjustment this collapses to the empirical P&L distribution.
    """
    y = np.asarray(y_grid, dtype=float).ravel()
    pi = np.asarray(pnl_scenarios, dtype=float).ravel()
    mu = np.asarray(mu, dtype=float).ravel()
    sigma = np.asarray(sigma, dtype=float).ravel()
    n = pi.shape[0]
    p = np.full(n, 1.0 / n) if probs is None else np.asarray(probs, dtype=float).ravel()
    sigma_safe = np.maximum(sigma, 1e-12)
    out = np.empty_like(y)
    step = 2000  # chunk the (grid x scenarios) block to bound memory
    for s in range(0, len(y), step):
        z = (y[s:s + step, None] - pi - mu) / sigma_safe
        out[s:s + step] = stats.norm.pdf(z) @ (p / sigma_safe)
    return out


def liquidity_score(cvar_market: float, cvar_total: float) -> float:
    """Eq. 13: CVaR_market / CVaR_total, in (0, 1]; 1 = liquidity is free."""
    if cvar_market <= 0 or cvar_total <= 0:
        raise ValueError("CVaR losses must be positive to form the score")
    return float(cvar_market / cvar_total)


def cvar_liquidity_contribution(
    pnl_scenarios: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
    confidence: float,
    probs: np.ndarray | None = None,
) -> dict:
    """Eqs. 11-12: split total CVaR into market and liquidity contributions.

    Total CVaR is computed numerically from the Eq. 10 mixture; the
    liquidity contribution uses the closed form
        sum_j p_j [ mu_j Phi(z_j) - sigma_j phi(z_j) ],
    z_j = (VaR_total - pi_j - mu_j) / sigma_j, and the market contribution
    is the remainder.  Losses are positive numbers throughout.
    """
    pi = np.asarray(pnl_scenarios, dtype=float).ravel()
    mu = np.asarray(mu, dtype=float).ravel()
    sigma = np.asarray(sigma, dtype=float).ravel()
    n = pi.shape[0]
    p = np.full(n, 1.0 / n) if probs is None else np.asarray(probs, dtype=float).ravel()
    # total-P&L quantile by grid inversion of the mixture CDF; chunked over
    # the grid so the (grid x scenarios) block stays small
    lo, hi = float((pi + mu - 6 * sigma).min()), float((pi + mu + 6 * sigma).max())
    grid = np.linspace(lo, hi, 20001)
    sig = np.maximum(sigma, 1e-12)
    cdf = np.empty_like(grid)
    step = 1000
    for s in range(0, len(grid), step):
        cdf[s:s + step] = stats.norm.cdf((grid[s:s + step, None] - pi - mu) / sig) @ p
    var_total = grid[np.searchsorted(cdf, 1.0 - confidence)]
    z = (var_total - pi - mu) / sig
    # Euler decomposition of the mixture CVaR in LOSS terms (L = -P&L):
    # E[L 1_{tail}] = -sum_j p_j [(pi_j + mu_j) Phi(z_j) - sigma_j phi(z_j)],
    # so the liquidity part is the mu/sigma block, sign-flipped and
    # normalized by the tail probability (1 - confidence).
    liq_contrib = float(
        -(p @ (mu * stats.norm.cdf(z) - sig * stats.norm.pdf(z))) / (1.0 - confidence)
    )
    # total CVaR of the loss -Pi_tot: mixture weights on the grid left of VaR
    tail = grid <= var_total
    w = np.zeros(int(tail.sum()))
    idx = np.flatnonzero(tail)
    for s in range(0, len(idx), step):
        block = idx[s:s + step]
        w[s:s + step] = stats.norm.pdf((grid[block][:, None] - pi - mu) / sig) @ (p / sig)
    w = w / w.sum()
    cvar_total = float(-(w @ grid[tail])) if tail.any() else float("nan")
    return {
        "var_total": float(var_total),
        "cvar_total": cvar_total,
        "liquidity_contribution": liq_contrib,
        "market_contribution": cvar_total - liq_contrib,
    }
