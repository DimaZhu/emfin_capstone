"""Sequential entropy pooling (Meucci) — the view layer, upstream of the optimizer.

The scenario engine hands the optimizer a matrix of sampled scenarios with
(usually uniform) probabilities.  Entropy pooling changes only the
*probabilities*: given prior scenarios with probabilities ``p`` and a view
expressed as linear constraints on posterior expectations, it finds the
posterior probabilities ``q`` closest to ``p`` in Kullback-Leibler
(relative-entropy) distance that satisfy the view.  The optimizer downstream
is untouched — it consumes the same scenario matrix with weights ``q``.

This is the general form of the Black-Litterman views machinery: BL is the
special case where the prior is normal, views are on means only, and the
posterior is computed in closed form.  Entropy pooling imposes no
distributional assumption and accepts views on any feature of the scenarios
(here: expected returns and second moments, per the 15 Oct team decision).

Sequential pooling (Meucci, "Fully Flexible Views: Theory and Practice",
and the sequential refinement used for pooling possibly-conflicting views):
two modes are provided: *joint* pooling (one KL projection satisfying
all views simultaneously — the default for mutually consistent views) and
*sequential* pooling (views applied one at a time, each posterior becoming
the next prior; a later view can override an earlier, conflicting one, so
the order encodes priority).  Per-view achieved moments are always
reported, so an overridden view shows up as a violation, never silently.

References:
    Meucci (2010), "Fully Flexible Views: Theory and Practice",
        Risk 21(10), 97-102.
    Meucci (2008), "Fully Flexible Views: Theory and Practice" (working
        paper, ssrn.com/abstract=1213325) — the dual formulation used here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import optimize

# Numerical floor: probabilities below this are treated as zero in the
# tilt (they stay zero in the posterior — KL projection never revives a
# zero-probability scenario).
_P_FLOOR = 1e-300


@dataclass(frozen=True)
class View:
    """One equality view: ``q' @ features == target``.

    ``features`` is an (n_scenarios, d) matrix — each column a scenario
    feature (e.g. one asset's returns, or their squares); ``target`` the
    length-d vector of posterior expectations the view imposes.
    """

    features: np.ndarray
    target: np.ndarray
    name: str = ""

    def __post_init__(self) -> None:
        features = np.asarray(self.features, dtype=float)
        target = np.atleast_1d(np.asarray(self.target, dtype=float))
        if features.ndim == 1:
            features = features.reshape(-1, 1)
        if features.shape[1] != target.shape[0]:
            raise ValueError(
                f"features has {features.shape[1]} columns but target has "
                f"{target.shape[0]} entries"
            )
        object.__setattr__(self, "features", features)
        object.__setattr__(self, "target", target)


@dataclass(frozen=True)
class PoolingResult:
    posterior_probs: np.ndarray
    kl_divergence: float  # KL(q || p), nats
    effective_n_scenarios: float  # exp(-KL) * N for uniform prior
    per_view_achieved: list[np.ndarray]  # E_q[features] after each view
    view_names: list[str] = field(default_factory=list)


def mean_view(scenarios: np.ndarray, column: int, target_mean: float, name: str = "") -> View:
    """View on the posterior mean of one scenario column."""
    return View(features=scenarios[:, [column]], target=[target_mean], name=name or f"E[x_{column}] = {target_mean}")


def second_moment_view(scenarios: np.ndarray, column: int, target_second_moment: float, name: str = "") -> View:
    """View on E[x^2] of one scenario column (raw second moment, not variance)."""
    return View(features=scenarios[:, [column]] ** 2, target=[target_second_moment], name=name or f"E[x_{column}^2] = {target_second_moment}")


def volatility_view(
    scenarios: np.ndarray, column: int, target_vol: float, pin_mean: Optional[float] = None, name: str = ""
) -> View:
    """View on the volatility (std) of one scenario column.

    Volatility views are linear in the scenarios only through the raw second
    moment: Var = E[x^2] - E[x]^2.  With ``pin_mean=None`` the prior mean is
    kept as-is (add the matching :func:`mean_view` yourself if the view is
    "mean m AND vol s": E[x^2] = s^2 + m^2 requires the mean pinned too, or
    the variance target is not what you think it is).
    """
    mean = scenarios[:, column].mean() if pin_mean is None else pin_mean
    target_second = target_vol**2 + mean**2
    return second_moment_view(scenarios, column, target_second, name=name or f"std(x_{column}) = {target_vol}")


def _kl_project_single_view(prior_probs: np.ndarray, view: View) -> np.ndarray:
    """KL projection of ``prior_probs`` onto one view, via the convex dual.

    Posterior: q ∝ p ∘ exp(Z λ).  Dual objective (convex, smooth):
        D(λ) = log Σ_n p_n exp(z_n'λ) − λ'v,
    gradient E_{q(λ)}[Z] − v, solved with L-BFGS-B on standardized features
    for conditioning.  At the optimum E_q[Z] = v exactly (up to tolerance).
    """
    p = np.asarray(prior_probs, dtype=float).ravel()
    if not (p > 0).all():
        raise ValueError("prior probabilities must be strictly positive (KL support cannot grow)")
    p = p / p.sum()
    z = view.features
    v = view.target

    # Standardize features for conditioning; view transforms identically.
    loc = p @ z
    scale = np.sqrt(np.maximum(p @ (z**2) - loc**2, 1e-300))
    zs = (z - loc) / scale
    vs = (v - loc) / scale

    log_p = np.log(np.maximum(p, _P_FLOOR))

    def dual(lam: np.ndarray) -> tuple[float, np.ndarray]:
        tilt = zs @ lam
        tilt -= tilt.max()  # log-sum-exp stabilization
        w = np.exp(log_p + tilt)
        total = w.sum()
        q = w / total
        objective = np.log(total) + tilt.max() - lam @ vs
        gradient = q @ zs - vs
        return objective, gradient

    d = zs.shape[1]
    lam = _solve_dual_newton(zs, vs, log_p, d)
    tilt = zs @ lam
    tilt -= tilt.max()
    w = np.exp(log_p + tilt)
    q = w / w.sum()

    # The solver's exit is a claim; constraint satisfaction is the verdict.
    # Verify the view actually holds and refuse to return a silent miss
    # (this is also what flags mutually inconsistent joint views).
    achieved = q @ z
    violation = np.abs(achieved - v) / (np.abs(v) + scale)
    if violation.max() > 1e-6:
        raise RuntimeError(
            f"entropy pooling view not satisfied (max relative violation "
            f"{violation.max():.2e}); the views may be mutually inconsistent "
            f"— pool them sequentially instead"
        )
    return q



def _solve_dual_newton(zs: np.ndarray, vs: np.ndarray, log_p: np.ndarray, d: int) -> np.ndarray:
    """Newton solve of the KL dual: convex, smooth, with closed-form gradient
    and Hessian (the posterior covariance of the standardized features).
    Backtracking line search guards the rare ill-conditioned step.
    """
    lam = np.zeros(d)

    def posterior(lam: np.ndarray) -> np.ndarray:
        tilt = zs @ lam
        tilt -= tilt.max()
        w = np.exp(log_p + tilt)
        return w / w.sum()

    for _ in range(100):
        q = posterior(lam)
        gradient = q @ zs - vs
        if np.linalg.norm(gradient, ord=np.inf) < 1e-9:
            break
        zc = zs - q @ zs
        hessian = (zc * q[:, None]).T @ zc + 1e-12 * np.eye(d)
        step = np.linalg.solve(hessian, gradient)
        # Backtracking: the dual is convex, so the full Newton step
        # almost always reduces it; shrink only when it does not.
        f_now = _dual_value(lam, zs, vs, log_p)
        t = 1.0
        for _ in range(50):
            if _dual_value(lam - t * step, zs, vs, log_p) < f_now:
                break
            t *= 0.5
        lam = lam - t * step
    else:
        raise RuntimeError("entropy pooling dual Newton solve did not converge")
    return lam


def _dual_value(lam: np.ndarray, zs: np.ndarray, vs: np.ndarray, log_p: np.ndarray) -> float:
    tilt = zs @ lam
    m = tilt.max()
    return float(m + np.log(np.exp(log_p + tilt - m).sum()) - lam @ vs)

def joint_entropy_pooling(
    n_scenarios: int,
    views: list[View],
    prior_probs: Optional[np.ndarray] = None,
) -> PoolingResult:
    """One KL projection satisfying all views simultaneously.

    The right choice when the views are mutually consistent (the common
    case: views from one investment committee about one market).  Raises if
    the stacked dual fails to converge — a sign of mutually inconsistent
    views, which is exactly when to switch to sequential pooling (later
    views then take precedence) rather than silently averaging.
    """
    p = _normalized_prior(n_scenarios, prior_probs)
    if views:
        features = np.concatenate([v.features for v in views], axis=1)
        target = np.concatenate([v.target for v in views])
        q = _kl_project_single_view(p, View(features=features, target=target, name="joint"))
    else:
        q = p
    return _result(p, q, views)


def sequential_entropy_pooling(
    n_scenarios: int,
    views: list[View],
    prior_probs: Optional[np.ndarray] = None,
) -> PoolingResult:
    """Pool views one at a time; each posterior becomes the next prior.

    Sequential order encodes priority: each step satisfies its own view
    exactly, so a later view can override an earlier, conflicting one
    (Meucci's remedy for pooling views from different sources).  Consistent
    views should be pooled with :func:`joint_entropy_pooling` instead —
    a single sequential pass does not, in general, preserve earlier views.

    With no views, the posterior is the prior exactly (baseline reduction).
    Diagnostics report what each view achieved *after the full sequence*,
    so overridden earlier views show up as violations, never silently.
    """
    q = _normalized_prior(n_scenarios, prior_probs)
    p0 = q.copy()
    for view in views:
        q = _kl_project_single_view(q, view)
    return _result(p0, q, views)


def _normalized_prior(n_scenarios: int, prior_probs: Optional[np.ndarray]) -> np.ndarray:
    if prior_probs is None:
        return np.full(n_scenarios, 1.0 / n_scenarios)
    q = np.asarray(prior_probs, dtype=float).ravel()
    if q.shape[0] != n_scenarios:
        raise ValueError("prior_probs length must equal n_scenarios")
    return q / q.sum()


def _result(p0: np.ndarray, q: np.ndarray, views: list[View]) -> PoolingResult:
    kl = float(q @ (np.log(np.maximum(q, _P_FLOOR)) - np.log(np.maximum(p0, _P_FLOOR))))
    n = len(q)
    return PoolingResult(
        posterior_probs=q,
        kl_divergence=kl,
        effective_n_scenarios=float(np.exp(-kl) * n),
        per_view_achieved=[np.atleast_1d(q @ v.features) for v in views],
        view_names=[v.name for v in views],
    )


def apply_probs_to_expectations(probs: np.ndarray, scenarios: np.ndarray) -> np.ndarray:
    """Posterior expectations E_q[X] for a scenario matrix — the pooled mean."""
    q = np.asarray(probs, dtype=float).ravel()
    return q @ scenarios
