"""The judge: paired-seed out-of-sample comparison of allocation methods.

Massa's benchmark, as recorded on 22 Sep: constrained engine versus vanilla
mean-variance, repeated randomized runs, judged on out-of-sample certainty
equivalent.  Every allocation is graded by the same judge: fresh-seed
scenario sets that no optimizer saw, identical seeds across allocations
(paired comparison — the common draws cancel, so CE *differences* are far
more precise than their standard errors suggest).

Self-reported CEs (each optimizer under its own model) are mutually
incomparable and are not used anywhere here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from emfin_capstone.toolbox import liabilities as liab
from emfin_capstone.toolbox import scenario_market


@dataclass(frozen=True)
class JudgeResult:
    names: list[str]
    ce_by_seed: np.ndarray  # (n_seeds, n_methods) certainty equivalents
    shortfall_prob_by_seed: np.ndarray | None  # same shape, when a liability is set
    shortfall_cvar_by_seed: np.ndarray | None = None

    def summary(self) -> dict:
        mean_ce = self.ce_by_seed.mean(axis=0)
        se_ce = self.ce_by_seed.std(axis=0, ddof=1) / np.sqrt(len(self.ce_by_seed))
        out = {name: {"ce_mean": m, "ce_se": s} for name, m, s in zip(self.names, mean_ce, se_ce)}
        # paired differences against the first method (the baseline)
        base = self.ce_by_seed[:, [0]]
        diffs = self.ce_by_seed - base
        out["paired_diff_vs_" + self.names[0]] = {
            name: {"mean": float(d.mean()), "se": float(d.std(ddof=1) / np.sqrt(len(d)))}
            for name, d in zip(self.names, diffs.T)
        }
        return out


def mean_variance_allocation(
    mean_vector: np.ndarray,
    cov_matrix: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    long_only: bool = True,
) -> np.ndarray:
    """Vanilla mean-variance: max w'mu - w' Sigma w / (2 zeta_rel), sum w = 1.

    No risk-budget constraint — this is the unconstrained-by-design baseline
    the constrained engine is compared against.  Returns share allocations.
    """
    import cvxpy as cp

    mu = np.asarray(mean_vector, dtype=float).ravel()
    sigma = np.asarray(cov_matrix, dtype=float)
    p = np.asarray(prices_vector, dtype=float).ravel()
    n = len(mu)
    # weights formulation, returns space
    g = mu / p  # expected gross returns per dollar
    w_cov = sigma / np.outer(p, p)
    rel_tol = risk_tolerance / wealth
    # norm form (as the repo's normal_market): more solver-robust than quad_form
    eigvals, eigvecs = np.linalg.eigh(w_cov)
    sqrt_cov = eigvecs @ np.diag(np.sqrt(np.maximum(eigvals, 0.0))) @ eigvecs.T
    w = cp.Variable(n)
    objective = cp.Maximize(g @ w - cp.square(cp.norm(sqrt_cov @ w, 2)) / (2 * rel_tol))
    constraints = [cp.sum(w) == 1]
    if long_only:
        constraints.append(w >= 0)
    cp.Problem(objective, constraints).solve(solver="CLARABEL")
    if w.value is None:
        raise RuntimeError("mean-variance optimization failed")
    return w.value * wealth / p


def judge_allocations(
    allocations: dict[str, np.ndarray],
    sample_fn,
    n_judge_seeds: int,
    judge_seed_base: int,
    wealth: float,
    risk_tolerance: float,
    liability_due: float = 0.0,
    confidence_level: float = 0.95,
) -> JudgeResult:
    """Grade each allocation on fresh paired scenario sets.

    ``sample_fn(seed)`` must return a fresh (n_scenarios, n_assets) horizon
    price matrix for the given seed — the same seeds for every allocation,
    which is what makes the comparison paired.
    """
    names = list(allocations)
    ce_rows, sf_rows, sc_rows = [], [], []
    for seed in range(judge_seed_base, judge_seed_base + n_judge_seeds):
        samples = sample_fn(seed)
        ce_row, sf_row, sc_row = [], [], []
        for name in names:
            w_samples = samples @ np.asarray(allocations[name], dtype=float).ravel()
            ce = scenario_market.empirical_certainty_equivalent(w_samples, risk_tolerance)
            ce_row.append(ce)
            if liability_due > 0:
                m = liab.funding_gap_metrics(w_samples, liability_due, confidence_level)
                sf_row.append(m.shortfall_probability)
                sc_row.append(m.shortfall_cvar)
        ce_rows.append(ce_row)
        sf_rows.append(sf_row)
        sc_rows.append(sc_row)
    return JudgeResult(
        names=names,
        ce_by_seed=np.array(ce_rows),
        shortfall_prob_by_seed=np.array(sf_rows) if liability_due > 0 else None,
        shortfall_cvar_by_seed=np.array(sc_rows) if liability_due > 0 else None,
    )
