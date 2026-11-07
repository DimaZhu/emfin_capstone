"""Sequential Entropy Pooling (SeqEP) - Vorobets (2021/2026) heuristics H1 and H2.

Implemented from the published article "Sequential Entropy Pooling
Heuristics" (Anton Vorobets, first version Oct 2021, latest 9 Apr 2026,
public article).  No code from the GPL-3.0 fortitudo.tech package is used
or copied; the EP primitive is this repo's own toolbox/entropy_pooling.py.

Problem: views on variances, skewness, kurtosis and correlations are
NONLINEAR in the posterior probabilities, so EP linearizes them by fixing
other parameters - conventionally at prior values.  That injects implicit
views (the posterior variance gets measured around the wrong center when a
mean view moves the mean) and can make view sets logically inconsistent.
SeqEP orders views by parameter class and carries the UPDATED parameters
forward as the fixed values:

  C0: means (no fixed parameters)
  C1: variances (mean fixed)
  C2: skewness, kurtosis (mean and variance fixed)
  C4: correlations (two means and two variances fixed)

Algorithm 1 (H1): for each nonempty class in order, re-solve EP on the
cumulative view set with the latest parameters, always against the
ORIGINAL prior p; finish with one full pass over all views.  Algorithm 2
(H2) is identical but solves against the running posterior - slightly
faster, slightly worse relative entropy.  The paper recommends H1 unless
computation time binds; both coincide with the original EP when the views
are fully specified or single-class.

Diagnostics follow the paper: relative entropy (RE) and the effective
number of scenarios ratio ENS = exp(-RE), per stage and overall.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from emfin_v2.toolbox import entropy_pooling as ep

# Parameter keys are ("mean", j) and ("var", j) for scenario column j.
ParamDict = dict[tuple[str, int], float]


@dataclass(frozen=True)
class SeqView:
    """A view plus its parameter class and a builder for its linearization.

    ``build(params)`` must return the toolbox ``View`` with every fixed
    parameter taken from ``params`` (e.g. a variance view pins its mean to
    ``params[("mean", j)]``).  ``level`` is the parameter class: 0 means,
    1 variances, 2 skew/kurtosis, 4 correlations (paper notation).
    """

    level: int
    build: Callable[[ParamDict], ep.View]
    name: str = ""


@dataclass(frozen=True)
class SeqEPResult:
    posterior_probs: np.ndarray
    heuristic: str
    stage_relative_entropy: tuple[float, ...]  # RE of each class pass + final pass
    stage_ens_ratio: tuple[float, ...]
    relative_entropy: float  # KL(q || p) of the final posterior
    ens_ratio: float
    per_view_achieved: tuple[np.ndarray, ...]
    view_names: tuple[str, ...]


def _extract_params(scenarios: np.ndarray, q: np.ndarray) -> ParamDict:
    """Posterior means and variances of every scenario column."""
    means = scenarios.T @ q
    second = (scenarios ** 2).T @ q
    params: ParamDict = {}
    for j in range(scenarios.shape[1]):
        params[("mean", j)] = float(means[j])
        params[("var", j)] = float(second[j] - means[j] ** 2)
    return params


def sequential_entropy_pooling(
    scenarios: np.ndarray,
    views: list[SeqView],
    prior_probs: Optional[np.ndarray] = None,
    heuristic: str = "H1",
    sweeps: int = 1,
) -> SeqEPResult:
    """Run the paper's H1 or H2 heuristic over class-ordered views.

    ``sweeps=1`` is exactly the paper's algorithm.  Larger values repeat the
    final full pass with refreshed pins - a fixed-point iteration that
    closes the residual the single pass leaves when views interact across
    classes (e.g. a rank view moves a mean after the variance views were
    pinned).  Diagnostics record every pass.
    """
    if heuristic not in ("H1", "H2"):
        raise ValueError(f"heuristic must be 'H1' or 'H2', got {heuristic!r}")
    if sweeps < 1:
        raise ValueError("sweeps must be >= 1")
    x = np.asarray(scenarios, dtype=float)
    n = x.shape[0]
    p = np.full(n, 1.0 / n) if prior_probs is None else np.asarray(prior_probs, dtype=float)
    p = p / p.sum()

    theta = _extract_params(x, p)
    levels = sorted({v.level for v in views})
    q_run = p
    stage_re: list[float] = []
    stage_ens: list[float] = []
    for level in levels:
        built = [v.build(theta) for v in views if v.level <= level]
        base = p if heuristic == "H1" else q_run
        res = ep.joint_entropy_pooling(n, built, prior_probs=base)
        q_run = res.posterior_probs
        theta = _extract_params(x, q_run)
        stage_re.append(res.kl_divergence)
        stage_ens.append(res.effective_n_scenarios_ratio)

    # final full pass: all views, latest parameters (paper: the EP(V, theta, .) step).
    # sweeps > 1 repeats THIS pass with refreshed pins: a fixed-point
    # iteration on the pin values.  (Repeating the whole class sequence
    # would not contract - the first-class pass re-solves against p and
    # forgets the later-class parameter updates.)
    q = q_run
    for _ in range(sweeps):
        built_all = [v.build(theta) for v in views]
        base = p if heuristic == "H1" else q_run
        final = ep.joint_entropy_pooling(n, built_all, prior_probs=base)
        q = final.posterior_probs
        theta = _extract_params(x, q)
        if heuristic == "H2":
            q_run = q
        stage_re.append(final.kl_divergence)
        stage_ens.append(final.effective_n_scenarios_ratio)

    kl = float(np.sum(q * (np.log(q) - np.log(p))))  # RE of final vs ORIGINAL prior
    return SeqEPResult(
        posterior_probs=q,
        heuristic=heuristic,
        stage_relative_entropy=tuple(stage_re),
        stage_ens_ratio=tuple(stage_ens),
        relative_entropy=kl,
        ens_ratio=float(np.exp(-kl)),
        per_view_achieved=tuple(v.features.T @ q for v in built_all),
        view_names=tuple(v.name or bv.name for v, bv in zip(views, built_all)),
    )
