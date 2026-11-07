"""Meucci (2012) liquidity evaluator: market-plus-liquidity P&L of a fixed allocation.

The "Evaluator" box of the architecture and the pipeline's only liquidity
model: it grades a chosen allocation after the optimizer.  Given scenarios x_j with probabilities p_j (Fully
Flexible Probabilities), a liquidation policy decides per scenario what is
sold at the horizon; the sale's liquidity adjustment dPi | j is normal,
N(mu_j, sigma_j^2), with VWAP moments eqs. (6)-(9).  The total P&L
Pi = Pi_bar + dPi is then a mixture of normals, eq. (10) — "conditional
convolution" — and every statistic below is closed form in it.

Conventions: P&L in horizon dollars relative to initial wealth,
Pi_bar_j = P_j . h - w.  ``tail_probability`` is the paper's alpha = 1 - c.
CVaR is the left-tail mean E[Pi | Pi <= z] (negative = loss) as in the
paper; the liquidity score compares losses.  A scenario with nothing sold
has sigma_j = 0: a point mass at Pi_bar_j + mu_j, handled exactly (CDF step,
fractional boundary atom in the CVaR split), never as a 0/0.

The CVaR split uses the corrected liquidity contribution
(1/alpha) sum_j p_j (mu_j Phi(z_j) - sigma_j phi(z_j)), not the printed
eq. (12)/(58), which keeps the unconditional weights p_j where the tail
conditioning requires p_j Phi(z_j) / alpha — see
notes/meucci2012_liquidity_errata.md (verified there by brute-force Monte
Carlo).

References:
    Meucci (2012), "A Fully Integrated Liquidity and Market Risk Model",
        Financial Analysts Journal 68(6), 35-47 — eqs. (6)-(13), Example 4
        (funding policy), App. A.1-A.3.
    Almgren (2003), "Optimal Execution with Nonlinear Impact Functions and
        Trading-Enhanced Risk", Applied Mathematical Finance 10(1), 1-18 —
        the moments (23)-(24) behind (6)-(7).
    Toth et al. (2011), "Anomalous Price Impact and the Critical Nature of
        Liquidity in Financial Markets", Physical Review X 1, 021006 — the
        square-root impact law (impact coefficient of order one).
    Rockafellar & Uryasev (2002), see ``scenario_market`` — CVaR of a
        distribution with atoms (fractional boundary atom).
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import optimize, special, stats

# gamma in eq. (8), renamed so it cannot be confused with the CVaR budget gamma;
# 0.90 is the paper's case-study calibration (S&P 500 stocks), not ours
LIQUIDITY_CORRELATION_SHRINKAGE = 0.9

# relative tolerance (to the P&L scale) within which a point mass counts as
# sitting on the quantile.  The quantile search runs 1000x tighter, so that a
# near-degenerate component (tiny sigma_j) is not straddled by the search error
_ATOM_TOLERANCE = 1e-9
_QUANTILE_TOLERANCE = 1e-12


@dataclass(frozen=True)
class LiquidityParameters:
    """Per-asset inputs of the VWAP liquidity-adjustment moments, eqs. (6)-(8).

    All arrays have shape (n_assets,).  A costless asset (cash) has
    spread = impact = uncertainty = volatility = 0 and any finite positive volume.
    """

    spread: np.ndarray  # alpha_n: commissions + half bid-ask, fraction of exposure
    impact: np.ndarray  # beta_n: square-root impact coefficient (dimensionless)
    volatility: np.ndarray  # sigma_bar_n: unit P&L vol over the execution period, fraction of exposure
    volume: np.ndarray  # v_n: units traded by the whole market over the execution period
    uncertainty: np.ndarray  # delta_n in eq. (7), dimension 1/sqrt(units)
    market_correlation: np.ndarray  # rho_hat (n_assets, n_assets), market-risk correlations
    correlation_shrinkage: float = LIQUIDITY_CORRELATION_SHRINKAGE


def vwap_uncertainty_coefficient(volatility: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """delta_n of eq. (7) implied by the paper's own VWAP derivation, App. A.2.

    (46) gives the execution variance sigma^2 = gamma_v p0^2 v (dh)^2 / 3, and
    (31) ties gamma_v p0^2 v to the price variance over the execution period,
    (sigma_bar p0)^2.  So sigma_n = sigma_bar e |dh| / sqrt(3) — the price risk
    of a position that shrinks linearly to zero — i.e.
    delta_n = sigma_bar_n / sqrt(3 v_n).  (gamma_v is the paper's second gamma,
    the variance-per-volume coefficient — unrelated to the shrinkage.)
    """
    return np.asarray(volatility, dtype=float) / np.sqrt(3 * np.asarray(volume, dtype=float))


def liquidity_adjustment_moments(
    liquidated_units: np.ndarray,
    unit_exposures: np.ndarray,
    parameters: LiquidityParameters,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-scenario mean and std of the portfolio liquidity adjustment, eqs. (6)-(9).

    ``liquidated_units``: |dh_{j,n}|, (J, n_assets) units sold in scenario j.
    ``unit_exposures``: e_{j,n}, (J, n_assets) value of one unit when the sale
    starts — the horizon price in scenario j (the paper's e_n, evaluated in the
    scenario, so mu and sigma move with the market as well as with the sale).

        mu_n    = -alpha_n e |dh| - beta_n e sigma_bar_n |dh|^(3/2) / sqrt(v_n)   (6)
        sigma_n =  delta_n sqrt(v_n) e |dh|                                         (7)
        rho     =  gamma_rho + (1 - gamma_rho) rho_hat                              (8)
        mu = sum_n mu_n,  sigma^2 = sum_nm sigma_n sigma_m rho_nm                   (9)

    sigma_bar and v must refer to the same period (the execution period), so
    beta is the dimensionless coefficient of the square-root law,
    cost = beta sigma sqrt(Q / V) per unit of exposure.  (The paper calls
    sigma_bar "annualized" and lets beta absorb the units.)  The shrunk rho is
    a convex combination of two PSD matrices (all-ones and rho_hat), so PSD.
    Returns (mu, sigma), each of shape (J,); sigma = 0 where nothing is sold.
    """
    if not np.all(np.isfinite(parameters.volume)) or np.any(parameters.volume <= 0):
        raise ValueError("volume must be finite and positive (any value for costless assets)")
    traded = np.abs(liquidated_units)
    position_mean = -parameters.spread * unit_exposures * traded - (
        parameters.impact * unit_exposures * parameters.volatility * traded**1.5 / np.sqrt(parameters.volume)
    )  # (6)
    position_std = parameters.uncertainty * np.sqrt(parameters.volume) * unit_exposures * traded  # (7)
    shrinkage = parameters.correlation_shrinkage
    liquidity_correlation = shrinkage + (1 - shrinkage) * parameters.market_correlation  # (8)
    variance = np.einsum("jn,nm,jm->j", position_std, liquidity_correlation, position_std)  # (9)
    return position_mean.sum(axis=1), np.sqrt(np.clip(variance, 0, None))


# (market_pnl (J,), holdings (n_assets,), horizon_prices (J, n_assets)) -> units sold (J, n_assets), >= 0
LiquidationPolicy = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]


def funding_liquidation_policy(pnl_threshold: float) -> LiquidationPolicy:
    """Meucci (2012) Example 4: raise cash only where the market P&L breaches a threshold.

    In scenario j with Pi_bar_j < ``pnl_threshold`` (a negative number of
    dollars) the need is pnl_threshold - Pi_bar_j, met by selling the same
    fraction theta_j of every holding, sum_n theta_j |h_n| e_{j,n} = need
    (gross proceeds at horizon prices; the paper uses margins m_n, which for
    an unlevered long-only book are the prices).  theta_j is capped at 1: a
    need larger than the whole book is met only in part.  Elsewhere nothing
    is sold (sigma_j = 0, a point mass).  Proportional selling includes any
    cash holding — a cash-first waterfall is a different policy.
    """

    def policy(market_pnl: np.ndarray, holdings: np.ndarray, horizon_prices: np.ndarray) -> np.ndarray:
        book_value = horizon_prices @ np.abs(holdings)
        funding_need = np.clip(pnl_threshold - market_pnl, 0, None)
        liquidated_fraction = np.minimum(funding_need / book_value, 1)
        return liquidated_fraction[:, None] * np.abs(holdings)[None, :]

    return policy


def full_liquidation_policy(market_pnl: np.ndarray, holdings: np.ndarray, horizon_prices: np.ndarray) -> np.ndarray:
    """Meucci (2012) Example 2: sell everything at the horizon in every scenario (stress case)."""
    return np.broadcast_to(np.abs(holdings), horizon_prices.shape).copy()


@dataclass(frozen=True)
class TotalPnlDistribution:
    """Eq. (10): Pi ~ sum_j p_j N(Pi_bar_j + mu_j, sigma_j^2); sigma_j = 0 is a point mass."""

    market_pnl: np.ndarray  # Pi_bar_j
    liquidity_mean: np.ndarray  # mu_j (<= 0)
    liquidity_std: np.ndarray  # sigma_j (>= 0)
    probabilities: np.ndarray  # p_j


def total_pnl_distribution(
    holdings: np.ndarray,
    horizon_prices: np.ndarray,
    probabilities: np.ndarray,
    wealth: float,
    liquidation_policy: LiquidationPolicy,
    parameters: LiquidityParameters,
) -> TotalPnlDistribution:
    """Scenario P&L, the policy's sales and their liquidity moments, assembled into (10).

    ``holdings``: units per asset (the optimizer's alpha, cash included),
    ``horizon_prices``: (J, n_assets) scenario prices — the same matrix the
    allocation is graded on — with ``probabilities`` p_j.
    """
    holdings = np.asarray(holdings, dtype=float).ravel()
    market_pnl = horizon_prices @ holdings - wealth
    liquidated_units = liquidation_policy(market_pnl, holdings, horizon_prices)
    liquidity_mean, liquidity_std = liquidity_adjustment_moments(liquidated_units, horizon_prices, parameters)
    return TotalPnlDistribution(
        market_pnl=market_pnl,
        liquidity_mean=liquidity_mean,
        liquidity_std=liquidity_std,
        probabilities=np.asarray(probabilities, dtype=float).ravel(),
    )


def _component_locations(distribution: TotalPnlDistribution) -> np.ndarray:
    return distribution.market_pnl + distribution.liquidity_mean


def _pnl_scale(distribution: TotalPnlDistribution) -> float:
    return np.abs(_component_locations(distribution)).max() + distribution.liquidity_std.max() + 1.0


def total_pnl_cdf(distribution: TotalPnlDistribution, y: float | np.ndarray) -> float | np.ndarray:
    """P(Pi <= y), eq. (51), right-continuous: point masses enter as steps 1{m_j <= y}."""
    locations = _component_locations(distribution)
    std = distribution.liquidity_std
    smooth = std > 0

    def cdf_at(value: float) -> float:
        smooth_mass = distribution.probabilities[smooth] @ special.ndtr((value - locations[smooth]) / std[smooth])
        return smooth_mass + distribution.probabilities[~smooth] @ (locations[~smooth] <= value)

    if np.ndim(y) == 0:
        return cdf_at(float(y))
    return np.array([cdf_at(value) for value in np.ravel(y)]).reshape(np.shape(y))


def total_pnl_density(distribution: TotalPnlDistribution, y: float | np.ndarray) -> float | np.ndarray:
    """Density of the continuous part of (10), sum over sigma_j > 0 of p_j phi(.)/sigma_j.

    Point masses (scenarios with nothing sold) carry their probability as
    atoms and are *not* in this density; for a plot of the whole distribution
    bin it through ``total_pnl_cdf`` differences instead.
    """
    locations = _component_locations(distribution)
    std = distribution.liquidity_std
    smooth = std > 0

    def density_at(value: float) -> float:
        standardized = (value - locations[smooth]) / std[smooth]
        return distribution.probabilities[smooth] @ (stats.norm.pdf(standardized) / std[smooth])

    if np.ndim(y) == 0:
        return density_at(float(y))
    return np.array([density_at(value) for value in np.ravel(y)]).reshape(np.shape(y))


def total_pnl_quantile(distribution: TotalPnlDistribution, tail_probability: float) -> float:
    """z = F^-1(alpha) = inf{y : F(y) >= alpha}, eq. (52), by Brent's method on the exact CDF.

    No grid or interpolation (the paper's route).  F jumps at point masses:
    Brent then converges onto the jump, which is the generalized inverse.
    """
    locations = _component_locations(distribution)
    max_std = distribution.liquidity_std.max()
    scale = _pnl_scale(distribution)
    lower = locations.min() - 40 * max_std - 1.0
    upper = locations.max() + 40 * max_std + 1.0
    return optimize.brentq(
        lambda value: total_pnl_cdf(distribution, value) - tail_probability,
        lower,
        upper,
        xtol=_QUANTILE_TOLERANCE * scale,
        rtol=4 * np.finfo(float).eps,
    )


@dataclass(frozen=True)
class CVaRSplit:
    """Left-tail CVaR of the total P&L and its Euler split (11), dollars, negative = loss."""

    tail_probability: float  # alpha
    quantile: float  # z = F^-1(alpha), the VaR in P&L terms
    cvar: float  # E[Pi | Pi <= z]
    market_contribution: float  # d_PiBar CVaR = E[Pi_bar | Pi <= z]
    liquidity_contribution: float  # d_dPi CVaR = E[dPi | Pi <= z]


def total_pnl_cvar_split(distribution: TotalPnlDistribution, tail_probability: float) -> CVaRSplit:
    """CVaR{Pi} and its market / liquidity contributions in closed form (corrected eq. 58).

    With z_j = (z - Pi_bar_j - mu_j) / sigma_j, Bayes reweights scenario j in
    the tail by Phi(z_j): P(j | Pi <= z) = p_j Phi(z_j) / alpha, and
    E[dPi 1{Pi <= z} | j] = mu_j Phi(z_j) - sigma_j phi(z_j), so

        d_dPi CVaR   = (1/alpha) sum_j p_j (mu_j Phi(z_j) - sigma_j phi(z_j))
        d_PiBar CVaR = (1/alpha) sum_j p_j Pi_bar_j Phi(z_j)
        CVaR         = their sum.

    Point masses (sigma_j = 0) are in the tail with weight 1{m_j < z}; those
    sitting on z share the remaining tail mass fractionally (Rockafellar &
    Uryasev 2002), so the tail weights always total alpha.
    """
    locations = _component_locations(distribution)
    std = distribution.liquidity_std
    probabilities = distribution.probabilities
    smooth = std > 0
    quantile = total_pnl_quantile(distribution, tail_probability)
    atom_tolerance = _ATOM_TOLERANCE * _pnl_scale(distribution)

    tail_weights = np.zeros_like(probabilities)  # p_j P(Pi <= z | j), boundary atoms fractional
    standardized = (quantile - locations[smooth]) / std[smooth]
    tail_weights[smooth] = probabilities[smooth] * special.ndtr(standardized)
    atom_below = ~smooth & (locations < quantile - atom_tolerance)
    atom_on = ~smooth & (np.abs(locations - quantile) <= atom_tolerance)
    tail_weights[atom_below] = probabilities[atom_below]
    mass_on = probabilities[atom_on].sum()
    if mass_on > 0:
        fraction_on = np.clip((tail_probability - tail_weights.sum()) / mass_on, 0, 1)
        tail_weights[atom_on] = fraction_on * probabilities[atom_on]

    # E[dPi 1{Pi <= z} | j]: smooth components need the truncated-normal term
    liquidity_tail = tail_weights * distribution.liquidity_mean
    liquidity_tail[smooth] -= probabilities[smooth] * std[smooth] * stats.norm.pdf(standardized)
    liquidity_contribution = liquidity_tail.sum() / tail_probability
    market_contribution = tail_weights @ distribution.market_pnl / tail_probability
    return CVaRSplit(
        tail_probability=tail_probability,
        quantile=quantile,
        cvar=market_contribution + liquidity_contribution,
        market_contribution=market_contribution,
        liquidity_contribution=liquidity_contribution,
    )


def market_only(distribution: TotalPnlDistribution) -> TotalPnlDistribution:
    """The same scenarios with the liquidity adjustment switched off (mu = sigma = 0): Pi_bar alone."""
    zeros = np.zeros_like(distribution.market_pnl)
    return TotalPnlDistribution(distribution.market_pnl, zeros, zeros, distribution.probabilities)


def liquidity_score(distribution: TotalPnlDistribution, tail_probability: float) -> float:
    """LS = CVaR{Pi_bar} / CVaR{Pi}, eq. (13), on losses: 1 = perfectly liquid, -> 0 = illiquid.

    CVaR{Pi_bar} is the pure market CVaR at its own quantile (not the market
    contribution to CVaR{Pi}).  Defined only when the market tail is a loss;
    NaN otherwise (e.g. a cash-dominated book whose worst alpha-tail still
    gains — the ratio then has no "fraction of loss kept" reading).
    """
    market_cvar = total_pnl_cvar_split(market_only(distribution), tail_probability).cvar
    total_cvar = total_pnl_cvar_split(distribution, tail_probability).cvar
    if market_cvar >= 0:
        return np.nan
    return market_cvar / total_cvar


def total_pnl_certainty_equivalent(
    distribution: TotalPnlDistribution,
    wealth: float,
    risk_tolerance: float,
) -> float:
    """CARA CE of horizon wealth w + Pi under (10), closed form.

    E[exp(-(w + Pi)/zeta)] = sum_j p_j exp(-(w + Pi_bar_j + mu_j)/zeta + sigma_j^2 / (2 zeta^2)),
    so CE = -zeta log of that: each scenario contributes its liquidity-adjusted
    mean minus the CARA variance charge sigma_j^2 / (2 zeta).  Point masses
    have no charge.  Reduces to ``scenario_market.empirical_certainty_equivalent``
    when mu = sigma = 0.
    """
    exponents = (
        -(wealth + distribution.market_pnl + distribution.liquidity_mean) / risk_tolerance
        + distribution.liquidity_std**2 / (2 * risk_tolerance**2)
    )
    return -risk_tolerance * special.logsumexp(exponents, b=distribution.probabilities)
