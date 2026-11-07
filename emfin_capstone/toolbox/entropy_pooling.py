"""Sequential entropy pooling (Meucci) — the view layer, upstream of the optimizer.

The scenario engine hands the optimizer a matrix of sampled scenarios with
(usually uniform) probabilities.  Entropy pooling changes only the
*probabilities*: given prior scenarios with probabilities ``p`` and views
expressed as linear constraints on posterior expectations, it finds the
posterior probabilities ``q`` closest to ``p`` in Kullback-Leibler
(relative-entropy) distance that satisfy the views.  The optimizer downstream
is untouched — it consumes the same scenario matrix with weights ``q``.

This is the general form of the Black-Litterman views machinery: BL is the
special case where the prior is normal, views are on means only, and the
posterior is computed in closed form.  Entropy pooling imposes no
distributional assumption and accepts views on any feature of the scenarios.

Supported view types (all linear in the posterior probabilities):

* equality views: means, second moments/volatilities, skewness, kurtosis,
  correlations — any scenario feature whose posterior expectation is pinned;
* inequality views: volatility caps, mean floors, relative (ranking) views,
  skewness/kurtosis bounds — the ``G q <= h`` block of the classic
  ``A q = b, G q <= h`` formulation (Vorobets 2021 notation);
* confidence blending (Meucci's "confidence in views"): the posterior is
  ``(1 - c) * prior + c * EP posterior``, so partial confidence shrinks the
  posterior toward the prior instead of imposing the view exactly.

Sequential pooling (Meucci, "Fully Flexible Views: Theory and Practice",
and the sequential refinement of Vorobets 2021): two modes are provided —
*joint* pooling (one KL projection satisfying all views simultaneously —
the default for mutually consistent views) and *sequential* pooling (views
applied one at a time, each posterior becoming the next prior; a later view
can override an earlier, conflicting one, so the order encodes priority).
Per-view achieved moments are always reported, so an overridden view shows
up as a violation, never silently.

Numerics: the KL dual is minimized with an exact Newton solver (closed-form
gradient and Hessian) when all views are equalities, and with bound-
constrained L-BFGS-B (equality multipliers free, inequality multipliers
one-sided per the KKT sign) when inequalities are present.  Both solve the
same convex dual to the same tolerance; constraint satisfaction is verified
after every solve and a violation raises instead of returning a silent miss.

Diagnostics: relative entropy (KL divergence) and the effective number of
scenarios ``ENS = exp(-KL) * N`` (equivalently the ENS ratio ``exp(-KL)``)
quantify how much information the views add — the standard EP stress-test
summary (Meucci 2008; Vorobets 2021).

References:
    Meucci (2008), "Fully Flexible Views: Theory and Practice"
        (ssrn.com/abstract=1213325) — the dual formulation and ENS.
    Meucci (2010), "Fully Flexible Views: Theory and Practice",
        Risk 21(10), 97-102 — confidence in views.
    Vorobets (2021), "Sequential Entropy Pooling" — inequality constraints
        in the ``A q = b, G q <= h`` form and the sequential refinement.
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

_SENSES = ("eq", "le", "ge")


@dataclass(frozen=True)
class View:
    """One view: ``q' @ features <sense> target``.

    ``features`` is an (n_scenarios, d) matrix — each column a scenario
    feature (e.g. one asset's returns, or their squares); ``target`` the
    length-d vector the view imposes on posterior expectations; ``sense``
    one of ``"eq"`` (E_q[feature] == target), ``"le"`` (<= target) or
    ``"ge"`` (>= target).  Inequality views bind only when the prior
    violates them; a non-binding inequality leaves the posterior at the
    prior along that feature.
    """

    features: np.ndarray
    target: np.ndarray
    sense: str = "eq"
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
        if self.sense not in _SENSES:
            raise ValueError(f"sense must be one of {_SENSES}, got {self.sense!r}")
        object.__setattr__(self, "features", features)
        object.__setattr__(self, "target", target)

    @property
    def is_equality(self) -> bool:
        return self.sense == "eq"


@dataclass(frozen=True)
class PoolingResult:
    posterior_probs: np.ndarray
    kl_divergence: float  # KL(q || p), nats
    effective_n_scenarios: float  # exp(-KL) * N for uniform prior
    per_view_achieved: list[np.ndarray]  # E_q[features] after the full pool
    view_names: list[str] = field(default_factory=list)
    confidence: float = 1.0  # blend weight applied between prior and full posterior

    @property
    def effective_n_scenarios_ratio(self) -> float:
        """ENS as a fraction of the scenario count: exp(-KL), in (0, 1].

        1.0 means the views added no information (posterior == prior);
        0.5 means the posterior concentrates on half the scenarios' worth
        of probability mass.  The standard EP stress-test diagnostic.
        """
        return float(np.exp(-self.kl_divergence))


# ---------------------------------------------------------------------------
# View constructors
# ---------------------------------------------------------------------------

def mean_view(scenarios: np.ndarray, column: int, target_mean: float, name: str = "") -> View:
    """View on the posterior mean of one scenario column."""
    return View(features=scenarios[:, [column]], target=[target_mean], name=name or f"E[x_{column}] = {target_mean}")


def mean_floor(scenarios: np.ndarray, column: int, min_mean: float, name: str = "") -> View:
    """Inequality view: posterior mean of one column at least ``min_mean``."""
    return View(features=scenarios[:, [column]], target=[min_mean], sense="ge", name=name or f"E[x_{column}] >= {min_mean}")


def mean_cap(scenarios: np.ndarray, column: int, max_mean: float, name: str = "") -> View:
    """Inequality view: posterior mean of one column at most ``max_mean``."""
    return View(features=scenarios[:, [column]], target=[max_mean], sense="le", name=name or f"E[x_{column}] <= {max_mean}")


def relative_mean_view(
    scenarios: np.ndarray, column_a: int, column_b: int, min_spread: float = 0.0, name: str = ""
) -> View:
    """Ranking view: E[x_a] - E[x_b] >= ``min_spread`` (column a outperforms b)."""
    return View(
        features=scenarios[:, [column_a]] - scenarios[:, [column_b]],
        target=[min_spread],
        sense="ge",
        name=name or f"E[x_{column_a}] - E[x_{column_b}] >= {min_spread}",
    )


def second_moment_view(scenarios: np.ndarray, column: int, target_second_moment: float, name: str = "") -> View:
    """View on E[x^2] of one scenario column (raw second moment, not variance)."""
    return View(features=scenarios[:, [column]] ** 2, target=[target_second_moment], name=name or f"E[x_{column}^2] = {target_second_moment}")


def volatility_view(
    scenarios: np.ndarray, column: int, target_vol: float, pin_mean: Optional[float] = None, name: str = ""
) -> View:
    """View on the volatility (std) of one scenario column.

    Formulated on the centered squared feature E[(x - m)^2] = s^2 with a
    pinned location m (the prior mean by default — the standard EP
    formulation): the constraint is linear in the probabilities only with
    the location pinned.  Add the matching :func:`mean_view` if the view is
    "mean m AND vol s", or the realized std around the posterior mean
    differs from the target by the mean drift.
    """
    x = scenarios[:, column]
    mean = x.mean() if pin_mean is None else pin_mean
    return View(
        features=((x - mean) ** 2).reshape(-1, 1),
        target=[target_vol**2],
        sense="eq",
        name=name or f"std(x_{column}) = {target_vol}",
    )


def volatility_cap(
    scenarios: np.ndarray, column: int, max_vol: float, pin_mean: Optional[float] = None, name: str = ""
) -> View:
    """Inequality view: volatility of one column at most ``max_vol``.

    Centered formulation E[(x - m)^2] <= max_vol^2 with a pinned location m
    (the prior mean by default).  Because Var(x) = E[(x - m)^2] - (E[x] - m)^2
    <= E[(x - m)^2], the realized std around the posterior mean is always
    within the cap, whatever the posterior mean does — the cap only bites
    when the view demands less volatility than the prior has.
    """
    x = scenarios[:, column]
    mean = x.mean() if pin_mean is None else pin_mean
    return View(
        features=((x - mean) ** 2).reshape(-1, 1),
        target=[max_vol**2],
        sense="le",
        name=name or f"std(x_{column}) <= {max_vol}",
    )


def skewness_view(
    scenarios: np.ndarray,
    column: int,
    target_skew: float,
    pin_mean: Optional[float] = None,
    pin_vol: Optional[float] = None,
    sense: str = "eq",
    name: str = "",
) -> View:
    """View on the skewness of one column: E[((x - m) / s)^3] <sense> target.

    Skewness is linear in the probabilities only with a pinned location and
    scale (prior mean/vol by default, per the standard EP formulation —
    pin them with explicit views if they are part of the view).
    """
    x = scenarios[:, column]
    m = x.mean() if pin_mean is None else pin_mean
    s = x.std() if pin_vol is None else pin_vol
    return View(
        features=(((x - m) / s) ** 3).reshape(-1, 1),
        target=[target_skew],
        sense=sense,
        name=name or f"skew(x_{column}) {sense} {target_skew}",
    )


def kurtosis_view(
    scenarios: np.ndarray,
    column: int,
    target_kurt: float,
    pin_mean: Optional[float] = None,
    pin_vol: Optional[float] = None,
    sense: str = "eq",
    name: str = "",
) -> View:
    """View on the kurtosis of one column: E[((x - m) / s)^4] <sense> target.

    Same pinning caveat as :func:`skewness_view`.  Note kurtosis here is the
    raw fourth standardized moment (3.0 for a normal distribution), not
    excess kurtosis.
    """
    x = scenarios[:, column]
    m = x.mean() if pin_mean is None else pin_mean
    s = x.std() if pin_vol is None else pin_vol
    return View(
        features=(((x - m) / s) ** 4).reshape(-1, 1),
        target=[target_kurt],
        sense=sense,
        name=name or f"kurt(x_{column}) {sense} {target_kurt}",
    )


def correlation_view(
    scenarios: np.ndarray,
    column_x: int,
    column_y: int,
    target_corr: float,
    name: str = "",
) -> View:
    """View on the correlation between two columns.

    Linearized as a view on the cross-moment E[(x - m_x)(y - m_y)] with
    prior-pinned means and vols: target covariance = rho * s_x * s_y.  Pin
    the means and vols with explicit views if they are part of the view.
    """
    x, y = scenarios[:, column_x], scenarios[:, column_y]
    cross = (x - x.mean()) * (y - y.mean())
    target_cov = target_corr * x.std() * y.std()
    return View(
        features=cross.reshape(-1, 1),
        target=[target_cov],
        sense="eq",
        name=name or f"corr(x_{column_x}, x_{column_y}) = {target_corr}",
    )


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

def _kl_project_mixed(
    prior_probs: np.ndarray,
    eq_features: Optional[np.ndarray],
    eq_target: Optional[np.ndarray],
    le_features: Optional[np.ndarray],
    le_target: Optional[np.ndarray],
) -> np.ndarray:
    """KL projection of ``prior_probs`` onto equality + "<=" views, one dual.

    Posterior: q proportional to p * exp(Z lambda).  Dual objective (convex,
    smooth), minimized over lambda:
        D(lambda) = log sum_n p_n exp(z_n' lambda) - lambda' v,
    gradient E_{q(lambda)}[Z] - v.  Equality multipliers are free; a "<="
    constraint E_q[g] <= h carries multiplier lambda <= 0 in this sign
    convention (KKT), zero when the constraint is slack.  Both blocks are
    stacked and solved jointly — pooling an inequality after the equalities
    would let it disturb them.  Pure-equality problems use the exact Newton
    solver; anything with an inequality uses bound-constrained L-BFGS-B on
    the same dual.  Features are standardized for conditioning; targets
    transform identically.
    """
    p = np.asarray(prior_probs, dtype=float).ravel()
    if not (p > 0).all():
        raise ValueError("prior probabilities must be strictly positive (KL support cannot grow)")
    p = p / p.sum()

    blocks = [b for b in ((eq_features, eq_target, True), (le_features, le_target, False)) if b[0] is not None]
    z = np.concatenate([b[0] for b in blocks], axis=1)
    v = np.concatenate([b[1] for b in blocks])
    d_eq = 0 if eq_features is None else eq_features.shape[1]

    # Standardize features for conditioning; targets transform identically.
    loc = p @ z
    scale = np.sqrt(np.maximum(p @ (z**2) - loc**2, 1e-300))
    zs = (z - loc) / scale
    vs = (v - loc) / scale

    log_p = np.log(p)
    if d_eq == zs.shape[1]:
        lam = _solve_dual_newton(zs, vs, log_p, zs.shape[1])
    else:
        lam = _solve_dual_bounded(zs, vs, log_p, d_eq)
    tilt = zs @ lam
    tilt -= tilt.max()
    w = np.exp(log_p + tilt)
    q = w / w.sum()

    # The solver's exit is a claim; constraint satisfaction is the verdict.
    # Verify the views actually hold and refuse to return a silent miss
    # (this is also what flags mutually inconsistent joint views).
    achieved = q @ z
    denom = np.abs(v) + scale
    violation = np.abs(achieved - v) / denom
    if d_eq < zs.shape[1]:
        violation = np.concatenate([violation[:d_eq], np.maximum(achieved - v, 0.0)[d_eq:] / denom[d_eq:]])
    if violation.max() > 1e-6:
        raise RuntimeError(
            f"entropy pooling views not satisfied (max relative violation "
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


def _solve_dual_bounded(zs: np.ndarray, vs: np.ndarray, log_p: np.ndarray, d_eq: int) -> np.ndarray:
    """Bound-constrained solve of the KL dual with mixed multipliers.

    The first ``d_eq`` multipliers are free (equality views); the rest are
    bounded above by zero ("<=" views — KKT sign, zero when slack).
    L-BFGS-B handles the one-sided bounds on the same convex dual objective
    the Newton solver uses for pure-equality problems.
    """
    d = zs.shape[1]

    def objective(lam: np.ndarray):
        tilt = zs @ lam
        m = tilt.max()
        w = np.exp(log_p + tilt - m)
        s = w.sum()
        q = w / s
        value = m + np.log(s) - lam @ vs
        gradient = q @ zs - vs
        return value, gradient

    res = optimize.minimize(
        objective,
        np.zeros(d),
        jac=True,
        method="L-BFGS-B",
        bounds=[(None, None)] * d_eq + [(None, 0.0)] * (d - d_eq),
        options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-9},
    )
    # The post-solve constraint verification is the verdict: a solver exit
    # short of its convergence flags still gets checked, and a genuine
    # failure (e.g. inconsistent views) raises there, not here.
    return res.x


def _dual_value(lam: np.ndarray, zs: np.ndarray, vs: np.ndarray, log_p: np.ndarray) -> float:
    tilt = zs @ lam
    m = tilt.max()
    return float(m + np.log(np.exp(log_p + tilt - m).sum()) - lam @ vs)


def _as_le(view: View) -> tuple[np.ndarray, np.ndarray]:
    """A view as (features, target) of a "<=" constraint (signs flipped for "ge")."""
    if view.sense == "ge":
        return -view.features, -view.target
    return view.features, view.target


def _project_view(p: np.ndarray, view: View) -> np.ndarray:
    if view.is_equality:
        return _kl_project_mixed(p, view.features, view.target, None, None)
    f, t = _as_le(view)
    return _kl_project_mixed(p, None, None, f, t)


# ---------------------------------------------------------------------------
# Pooling entry points
# ---------------------------------------------------------------------------

def joint_entropy_pooling(
    n_scenarios: int,
    views: list[View],
    prior_probs: Optional[np.ndarray] = None,
    confidence: float = 1.0,
) -> PoolingResult:
    """One KL projection satisfying all views simultaneously.

    The right choice when the views are mutually consistent (the common
    case: views from one investment committee about one market).  Raises if
    the stacked dual fails to converge or the constraints cannot be met —
    a sign of mutually inconsistent views, which is exactly when to switch
    to sequential pooling (later views then take precedence) rather than
    silently averaging.

    ``confidence`` in [0, 1] blends the result with the prior (Meucci's
    confidence in views): q = (1 - c) p + c q_EP.  At 1.0 the views hold
    exactly; below 1.0 they shrink toward the prior and the reported
    per-view achieved moments show the actual, blended values.
    """
    _check_confidence(confidence)
    p = _normalized_prior(n_scenarios, prior_probs)
    if views:
        eq = [v for v in views if v.is_equality]
        ineq = [v for v in views if not v.is_equality]
        eq_f = np.concatenate([v.features for v in eq], axis=1) if eq else None
        eq_t = np.concatenate([v.target for v in eq]) if eq else None
        le_f = np.concatenate([_as_le(v)[0] for v in ineq], axis=1) if ineq else None
        le_t = np.concatenate([_as_le(v)[1] for v in ineq]) if ineq else None
        q = _kl_project_mixed(p, eq_f, eq_t, le_f, le_t)
    else:
        q = p
    return _result(p, q, views, confidence)


def sequential_entropy_pooling(
    n_scenarios: int,
    views: list[View],
    prior_probs: Optional[np.ndarray] = None,
    confidence: float = 1.0,
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
    ``confidence`` blends the final posterior with the prior, as in
    :func:`joint_entropy_pooling`.
    """
    _check_confidence(confidence)
    q = _normalized_prior(n_scenarios, prior_probs)
    p0 = q.copy()
    for view in views:
        q = _project_view(q, view)
    return _result(p0, q, views, confidence)


def _check_confidence(confidence: float) -> None:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")


def _normalized_prior(n_scenarios: int, prior_probs: Optional[np.ndarray]) -> np.ndarray:
    if prior_probs is None:
        return np.full(n_scenarios, 1.0 / n_scenarios)
    q = np.asarray(prior_probs, dtype=float).ravel()
    if q.shape[0] != n_scenarios:
        raise ValueError("prior_probs length must equal n_scenarios")
    return q / q.sum()


def _result(p0: np.ndarray, q: np.ndarray, views: list[View], confidence: float) -> PoolingResult:
    if confidence < 1.0:
        q = (1.0 - confidence) * p0 + confidence * q
        q = q / q.sum()
    kl = float(q @ (np.log(np.maximum(q, _P_FLOOR)) - np.log(np.maximum(p0, _P_FLOOR))))
    n = len(q)
    return PoolingResult(
        posterior_probs=q,
        kl_divergence=kl,
        effective_n_scenarios=float(np.exp(-kl) * n),
        per_view_achieved=[np.atleast_1d(q @ v.features) for v in views],
        view_names=[v.name for v in views],
        confidence=confidence,
    )


def apply_probs_to_expectations(probs: np.ndarray, scenarios: np.ndarray) -> np.ndarray:
    """Posterior expectations E_q[X] for a scenario matrix — the pooled mean."""
    q = np.asarray(probs, dtype=float).ravel()
    return q @ scenarios
