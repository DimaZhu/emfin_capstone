"""Fully Flexible Resampling (FFR): state-conditioned prior probabilities.

So far the engine's prior is uniform over history: every weekly observation
of the invariants enters the moment estimates with weight 1/T.  Fully
Flexible Resampling (Meucci 2010, "Factors on Demand"; Meucci 2012,
"Effective Number of Scenarios in Fully Flexible Probabilities") replaces
that uniform prior over historical observations with *flexible
probabilities* p_t that reflect:

* time decay - recent observations count more (exponential half-life);
* state conditioning - observations whose market state resembles today
  count more (a Gaussian kernel on a state variable, e.g. trailing
  realized volatility or the yield level), the "crisp conditioning"
  special case of FFR.

The weights feed the pipeline at two points, both already probability-aware:

1. weighted moment estimation (``weighted_moments``) - the projected
   horizon mean/covariance are estimated under p instead of uniformly,
   so the parametric (Gaussian) scenario set already reflects the
   state-conditioned prior;
2. weighted bootstrap resampling (``bootstrap_horizon_invariants``) -
   the fully non-parametric option: horizon scenarios are sums of weekly
   invariants resampled from history with probabilities p.  Sums of log
   returns and of yield changes are the correct horizon invariants, so the
   resampled paths project exactly like the i.i.d. Gaussian case.

Entropy pooling then tilts these priors with views as before (its
``prior_probs`` argument exists precisely for this), and the optimizer
already accepts scenario probabilities - FFR changes the prior, nothing
downstream.

Honest caveats, stated for the paper:
* FFR buys robustness when the conditioning state predicts (vol regimes
  persist; the yield level means-reverts slowly).  Under a truly i.i.d.
  world it only adds estimation noise - the paired-seed judge, whose data-
  generating process is the full-sample Gaussian, CANNOT reward a better
  prior, so FFR shows up there as a small CE cost by construction.  Its
  value is a real-data property, and the paper should say so.
* ``effective_sample_size`` (Kish) reports how much history survives the
  tilting; aggressive conditioning on ~270 weekly observations burns
  effective sample fast.

References:
    Meucci (2010), "Factors on Demand - Fully Flexible Probabilities".
    Kish (1965) for the effective sample size 1 / sum p_t^2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def time_decay_weights(n_obs: int, half_life: float) -> np.ndarray:
    """Exponential time-decay weights over T ordered observations.

    ``half_life`` in observations (weeks for weekly data): an observation
    that many periods old carries half the weight of the latest one.
    ``half_life = np.inf`` reproduces the uniform prior exactly.
    """
    if n_obs < 1:
        raise ValueError("need at least one observation")
    if half_life <= 0:
        raise ValueError("half_life must be positive (np.inf = uniform)")
    if np.isinf(half_life):
        return np.full(n_obs, 1.0 / n_obs)
    ages = np.arange(n_obs - 1, -1, -1, dtype=float)  # 0 = most recent
    w = 0.5 ** (ages / half_life)
    return w / w.sum()


def kernel_weights(state: np.ndarray, target: float, bandwidth: float) -> np.ndarray:
    """Gaussian-kernel weights conditioning on a state variable.

    ``state`` is one value per historical observation (e.g. trailing
    13-week realized vol); ``target`` is today's value; ``bandwidth`` is in
    the same units.  Observations whose state sits at the target get full
    weight, decaying as exp(-((z - target) / h)^2 / 2).  A large bandwidth
    (relative to the state's spread) reproduces the uniform prior.
    """
    z = np.asarray(state, dtype=float).ravel()
    if z.shape[0] < 1:
        raise ValueError("need at least one observation")
    if bandwidth <= 0:
        raise ValueError("bandwidth must be positive")
    w = np.exp(-0.5 * ((z - target) / bandwidth) ** 2)
    return w / w.sum()


def combine_weights(*weight_sets: np.ndarray) -> np.ndarray:
    """Product of weight sets, renormalized - the FFR "both rules" case.

    E.g. combine_weights(time_decay, kernel) applies recency AND state
    conditioning; the joint weight of an observation is proportional to the
    product of its weights under each rule.
    """
    if not weight_sets:
        raise ValueError("nothing to combine")
    w = np.asarray(weight_sets[0], dtype=float).ravel().copy()
    for other in weight_sets[1:]:
        other = np.asarray(other, dtype=float).ravel()
        if other.shape != w.shape:
            raise ValueError("all weight sets must have the same length")
        w *= other
    total = w.sum()
    if total <= 0:
        raise ValueError("combined weights are all zero - conditioning too aggressive")
    return w / total


def effective_sample_size(weights: np.ndarray) -> float:
    """Kish effective sample size: 1 / sum w^2, in [1, T].

    Uniform weights give T (all of history counts); a one-hot weighting
    gives 1.  Report it next to every conditioned prior - it is the FFR
    analogue of EP's effective-number-of-scenarios diagnostic.
    """
    w = np.asarray(weights, dtype=float).ravel()
    if w.sum() <= 0:
        raise ValueError("weights must have positive mass")
    w = w / w.sum()
    return float(1.0 / (w @ w))


def weighted_moments(x: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Weighted mean and covariance of observation rows x under ``weights``.

    Reduces to the usual sample moments (ddof=1) under uniform weights.
    The covariance uses the reliability correction 1 / (1 - sum w^2), the
    weighted analogue of Bessel's correction.
    """
    x = np.atleast_2d(np.asarray(x, dtype=float))
    w = np.asarray(weights, dtype=float).ravel()
    if x.shape[0] != w.shape[0]:
        raise ValueError("one weight per observation row")
    w = w / w.sum()
    mean = w @ x
    xc = x - mean
    cov = (xc * w[:, None]).T @ xc
    cov /= max(1.0 - w @ w, 1e-12)  # Bessel-analogue reliability correction
    return mean, cov


@dataclass(frozen=True)
class FFRPrior:
    """A state-conditioned prior over the historical observations."""

    weights: np.ndarray  # (T,) probabilities over historical observations
    half_life: float
    bandwidth: float | None  # None when no state conditioning was applied
    state_name: str

    @property
    def ess(self) -> float:
        return effective_sample_size(self.weights)


def build_ffr_prior(
    n_obs: int,
    half_life: float,
    state: np.ndarray | None = None,
    target: float | None = None,
    bandwidth: float | None = None,
    state_name: str = "",
) -> FFRPrior:
    """Time-decay + optional kernel conditioning, combined into one prior."""
    w = time_decay_weights(n_obs, half_life)
    if state is not None:
        if target is None or bandwidth is None:
            raise ValueError("state conditioning needs target and bandwidth")
        w = combine_weights(w, kernel_weights(state, target, bandwidth))
    return FFRPrior(weights=w, half_life=half_life, bandwidth=bandwidth, state_name=state_name)


def bootstrap_horizon_invariants(
    weekly_invariants: np.ndarray,
    weights: np.ndarray,
    horizon_weeks: int,
    n_scenarios: int,
    seed: int,
) -> np.ndarray:
    """Resample history into horizon scenarios under flexible probabilities.

    Each scenario path sums ``horizon_weeks`` weekly invariant vectors drawn
    independently from the weighted empirical distribution.  Log returns and
    yield changes both aggregate by summation, so the horizon scenarios are
    exactly the invariants the market map expects.  The draws carry no
    parametric assumption - fat tails, skew and cross-dependence survive
    resampling untouched.
    """
    x = np.atleast_2d(np.asarray(weekly_invariants, dtype=float))
    w = np.asarray(weights, dtype=float).ravel()
    if x.shape[0] != w.shape[0]:
        raise ValueError("one weight per observation row")
    w = w / w.sum()
    rng = np.random.default_rng(seed)
    picks = rng.choice(x.shape[0], size=(n_scenarios, horizon_weeks), p=w)
    return x[picks].sum(axis=1)
