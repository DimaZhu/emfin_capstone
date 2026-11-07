"""Shared capped-cone-solver policy for the optimizer stack.

Three optimizers (asset-only SAA, liability-aware, multi-period) all solve
the same shape: an exponential (CARA CE) objective with CVaR epigraphs.
They used to carry three copies of the same solver policy; this is the one
place it lives now:

  * CLARABEL first, with a generous iteration budget and a HARD time cap -
    the weighted CE with epigraphs is the pipeline's dominant solve and
    CLARABEL intermittently stalls on it (observed 0.6s-46s on identical
    inputs).
  * SCS as the sturdier fallback for this cone shape, also capped: an
    uncapped SCS run is minutes-slow and reads as a hang.
  * "optimal_inaccurate" is accepted but reported in the diagnostics - the
    caller sees the solver and status, never a silent approximate answer.
"""

from __future__ import annotations

import cvxpy as cp

CLARABEL_TIME_LIMIT_SECS = 60.0
CLARABEL_MAX_ITER = 400
SCS_TIME_LIMIT_SECS = 60.0
SCS_MAX_ITERS = 10_000


def solve_capped(problem: cp.Problem, name: str = "optimization") -> str:
    """Solve with CLARABEL-then-SCS under time caps; return the solver used.

    Raises RuntimeError if neither solver produces a solution.
    """
    used_solver = "CLARABEL"
    try:
        problem.solve(solver="CLARABEL", max_iter=CLARABEL_MAX_ITER,
                      time_limit=CLARABEL_TIME_LIMIT_SECS)
    except cp.SolverError:
        used_solver = "SCS"
        problem.solve(solver="SCS", eps_abs=1e-6, eps_rel=1e-6,
                      max_iters=SCS_MAX_ITERS, time_limit_secs=SCS_TIME_LIMIT_SECS)
    if problem.value is None or problem.value == float("inf"):
        raise RuntimeError(f"{name} failed: {problem.status}")
    return used_solver
