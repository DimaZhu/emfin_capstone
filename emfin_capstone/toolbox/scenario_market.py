"""Scenario-based (simulation) counterpart of ``normal_market``.

Here the market distribution is represented only by a matrix of sampled
horizon prices — the optimization and the satisfaction/risk evaluators work
for any distribution that can produce such samples (Sample Average
Approximation).  Under normal invariants the samples are exactly lognormal,
and the ``normal_market`` closed forms serve as validation anchors.

"Scenario" is used in the stochastic-programming sense: any row of a
discrete representation of the market distribution, with a probability
attached — whether 200,000 Monte Carlo draws, bootstrapped historical
weeks, quadrature nodes, or a handful of handcrafted stress cases.  The
stress-testing usage (few, named, deliberately extreme states of the
world) is the small-N special case, not a different concept: this module
deliberately does not know where its scenarios came from.

The probabilities are explicit (Fully Flexible Probabilities, Meucci 2010):
every consumer of a scenario set — both optimizers, the CE/CVaR yardsticks,
the evaluator — takes a ``probabilities`` vector p alongside the scenario
matrix X (uniform when None).  Views never touch the scenarios, only p:
``entropy_pooling`` maps (X, prior p0, view constraints) to a posterior p.

References:
    Rockafellar & Uryasev (2000), "Optimization of Conditional Value-at-Risk",
        Journal of Risk 2(3), 21-41 — the CVaR minimization formula, under
        continuous loss distributions.
    Rockafellar & Uryasev (2002), "Conditional Value-at-Risk for General Loss
        Distributions", Journal of Banking & Finance 26(7), 1443-1471,
        doi:10.1016/S0378-4266(02)00271-6 — extends it to discrete/empirical
        distributions (our case): fractional atom-splitting, argmin is an
        interval.
    Politis & Romano (1994), "The Stationary Bootstrap", Journal of the
        American Statistical Association 89(428), 1303-1313 — the resampling
        scheme of ``sample_block_bootstrap_scenarios``.
    Meucci (2008), "Fully Flexible Views: Theory and Practice", Risk 21(10),
        97-102 — entropy pooling: views as linear constraints on scenario
        probabilities, posterior = minimum relative entropy to the prior.
    Meucci (2010), "Historical Scenarios with Fully Flexible Probabilities",
        GARP Risk Professional, Dec 2010, 47-51 — scenarios + probabilities as
        the general representation of a distribution.
"""

import warnings
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import cvxpy as cp
import numpy as np
from scipy import special

# CLARABEL settings, tried in order until one certifies "optimal".  With default
# settings (max_step_fraction 0.99) the 1-year problem — CE exponents spread over
# ~10 units, so exp-cone slacks span ~1e-5..1 — with a binding CVaR budget stalls
# ("InsufficientProgress", dual residual stuck ~1e-4) on 49 of 70 bootstrap sets
# of 10k scenarios.  Shorter steps fix most; the sets that still fail at one rung
# are largely disjoint from those failing at another; rungs 0-3 certified all 70
# (rung 0 on 63), rung 4 one more history replica that failed rungs 0-3.  A rare
# set certifies on no rung and comes back "optimal_inaccurate" (or raises): the
# status is printed — check it.  Rescaling the objective or the CVaR row, centering the
# exponents, or minimizing E[exp(-psi/zeta)] instead did not help.  Where two
# rungs both certify, the weights agree to ~1e-7.  At one week rung 0 reproduces
# the default-settings optimum to solver tolerance.
_CLARABEL_SETTINGS_LADDER = (
    {"max_step_fraction": 0.9},
    {"max_step_fraction": 0.9, "equilibrate_enable": False},
    {"max_step_fraction": 0.8, "max_iter": 1000},
    {"max_step_fraction": 0.7, "max_iter": 1000},
    {"max_step_fraction": 0.6, "max_iter": 2000},
)


def _solve_with_clarabel(problem: cp.Problem) -> str:
    """Solve with CLARABEL, walking ``_CLARABEL_SETTINGS_LADDER`` until a rung certifies "optimal".

    If no rung does, falls back to the first rung that reached
    "optimal_inaccurate" (re-solved, so the variables hold its solution) and
    returns that status; raises if not even that.  Returns the final status.
    """
    first_inaccurate = None
    for rung, settings in enumerate(_CLARABEL_SETTINGS_LADDER):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # an inaccurate rung is retried, not reported
            try:
                problem.solve(solver="CLARABEL", **settings)
            except cp.error.SolverError:
                continue
        if problem.status == cp.OPTIMAL:
            return problem.status
        if problem.status == cp.OPTIMAL_INACCURATE and first_inaccurate is None:
            first_inaccurate = rung
    if first_inaccurate is None:
        raise RuntimeError(f"CLARABEL found no solution on any settings rung (last status {problem.status})")
    problem.solve(solver="CLARABEL", **_CLARABEL_SETTINGS_LADDER[first_inaccurate])  # warns: inaccurate
    return problem.status


def sample_market_scenarios(
    prices_vector: np.ndarray,
    projected_mean_vector: np.ndarray,
    projected_cov_matrix: np.ndarray,
    n_scenarios: int,
    seed: int,
) -> np.ndarray:
    """Sample horizon prices P = p * exp(X), X ~ N(mu, Sigma) — lognormal market.

    Correlation is induced in log space via the Cholesky factor of Sigma;
    an elementwise lognormal sampler cannot do this (no covariance argument).
    Returns an (n_scenarios, n_assets) array of prices.
    """
    rng = np.random.default_rng(seed)
    cholesky_factor = np.linalg.cholesky(projected_cov_matrix)  # Sigma = L L'
    invariant_scenarios = (
        projected_mean_vector.ravel()
        + rng.standard_normal((n_scenarios, len(prices_vector))) @ cholesky_factor.transpose()
    )
    return prices_vector.ravel() * np.exp(invariant_scenarios)


def _stationary_bootstrap_week_indices(
    n_weeks: int,
    path_length: int,
    n_paths: int,
    mean_block_length: float,
    rng: np.random.Generator,
    probabilities: np.ndarray | None,
) -> Iterator[np.ndarray]:
    """Yield, step by step, the historical week index of every path (shape (n_paths,)).

    The index chain of ``sample_block_bootstrap_scenarios`` (see there for the
    restart distribution and the no-wrap edge correction), factored out so that
    ``resample_history`` walks the very same chain.  Draw order from ``rng`` is
    part of the contract: changing it changes every seeded scenario set.
    """
    restart_probability = 1 / mean_block_length
    week_probabilities = (
        np.full(n_weeks, 1 / n_weeks) if probabilities is None else np.asarray(probabilities, dtype=float)
    )

    # stationarity of the no-wrap chain: pi_i = (1 - 1/L) pi_(i-1) + restart mass into i
    restart_probabilities = np.clip(
        week_probabilities - (1 - restart_probability) * np.concatenate([[0.0], week_probabilities[:-1]]), 0, None
    )
    restart_probabilities /= restart_probabilities.sum()

    # vectorized across paths, looped over the steps
    week_index = rng.choice(n_weeks, size=n_paths, p=week_probabilities)
    yield week_index
    for _ in range(path_length - 1):
        week_index = week_index + 1
        restart = (rng.random(n_paths) < restart_probability) | (week_index >= n_weeks)
        week_index[restart] = rng.choice(n_weeks, size=restart.sum(), p=restart_probabilities)
        yield week_index


def _check_bootstrap_inputs(weekly_log_returns: np.ndarray, mean_block_length: float, path_length: int) -> None:
    if np.isnan(weekly_log_returns).any():
        raise ValueError("weekly_log_returns contains NaN; drop incomplete weeks first")
    if mean_block_length < 1 or path_length < 1:
        raise ValueError(
            f"need mean_block_length >= 1 and horizon_weeks >= 1, got {mean_block_length}, {path_length}"
        )


def sample_block_bootstrap_scenarios(
    weekly_log_returns: np.ndarray,
    prices_vector: np.ndarray,
    horizon_weeks: int,
    n_scenarios: int,
    mean_block_length: float,
    seed: int,
    probabilities: np.ndarray | None = None,
) -> np.ndarray:
    """Sample horizon prices P = p * exp(sum of resampled weekly invariants).

    Stationary bootstrap (Politis & Romano 1994) of the historical weeks: a
    path's first week is drawn from ``probabilities`` (uniform if None); each
    next step moves on to the following historical week with probability
    1 - 1/mean_block_length, otherwise restarts at a freshly drawn week (see
    below for the restart distribution).  Block
    lengths are therefore geometric with mean ``mean_block_length``; at 1 every
    step restarts and this is the i.i.d. bootstrap.  Whole rows (dates) are
    resampled, so cross-asset dependence is kept as observed — no copula, no
    covariance model.

    No circular wrap: a block that runs past the last week restarts instead
    (wrapping would splice the newest week onto the oldest).  Left alone, that
    creates an edge effect: the first weeks can be entered only by a restart,
    never by continuation, so with restarts drawn from ``probabilities`` they
    are under-visited (at mean block length 6 on ~270 weeks, week 1 at ~18% of
    its weight, the first ~15 weeks visibly short).  Restarts are therefore
    drawn from q_i - (1 - 1/L) q_(i-1) (normalized; q = ``probabilities``,
    L = mean_block_length), which makes q the stationary distribution of the
    index chain: every step of every path, not only the first, then has
    marginal q exactly.  The extra restart mass lands on week 1 — the blocks a
    circular wrap would have fed in from the end start there instead.  If q
    falls faster than 1 - 1/L between consecutive weeks (e.g. zero-weight
    weeks under state conditioning), the formula goes negative, is clipped,
    and the marginal is only approximately q: continuation enters such weeks
    regardless of their probability.

    ``probabilities`` here weight historical *weeks* (state/time conditioning
    of the history), not the returned scenarios: the returned rows are equally
    likely draws.  Scenario probabilities come later (``uniform_prior``,
    ``entropy_pooling``).

    ``weekly_log_returns``: (n_weeks, n_assets) in chronological order, no NaN
    (drop the rows of an outer-joined calendar first).  Note that a calendar
    gap (a skipped holiday week) is continued across as if adjacent.
    Returns an (n_scenarios, n_assets) array of prices.
    """
    _check_bootstrap_inputs(weekly_log_returns, mean_block_length, horizon_weeks)
    rng = np.random.default_rng(seed)
    week_index_steps = _stationary_bootstrap_week_indices(
        len(weekly_log_returns), horizon_weeks, n_scenarios, mean_block_length, rng, probabilities
    )
    horizon_log_returns = weekly_log_returns[next(week_index_steps)]  # fancy indexing copies
    for week_index in week_index_steps:
        horizon_log_returns += weekly_log_returns[week_index]
    return prices_vector.ravel() * np.exp(horizon_log_returns)


def resample_history(
    weekly_log_returns: np.ndarray,
    mean_block_length: float,
    seed: int,
) -> np.ndarray:
    """One stationary-bootstrap replica of the history itself: same length, same block scheme.

    Feeding the replica through projection + optimization instead of the
    observed history, many times, measures estimation uncertainty — the
    spread of the allocation an equally plausible history would have produced.
    Fresh projection seeds on the *same* history measure only Monte Carlo
    noise.  Same chain as ``sample_block_bootstrap_scenarios`` (one path,
    ``len(weekly_log_returns)`` steps), so the replica keeps blocks of
    consecutive weeks — and their volatility clustering — intact.
    Returns an (n_weeks, n_assets) array of weekly log returns.
    """
    n_weeks = len(weekly_log_returns)
    _check_bootstrap_inputs(weekly_log_returns, mean_block_length, n_weeks)
    rng = np.random.default_rng(seed)
    week_index_steps = _stationary_bootstrap_week_indices(n_weeks, n_weeks, 1, mean_block_length, rng, None)
    return np.concatenate([weekly_log_returns[week_index] for week_index in week_index_steps])


def append_cash_column(market_samples: np.ndarray, cash_horizon_value: float) -> np.ndarray:
    """Add a riskless asset: the same horizon price in every scenario.

    Apply it to every scenario set an allocation is optimized on or graded on,
    so the samples always have as many columns as the allocation has assets.
    """
    return np.column_stack([market_samples, np.full(len(market_samples), cash_horizon_value)])


def uniform_prior(n_scenarios: int) -> np.ndarray:
    """Prior probabilities p0 = 1/J: every projected scenario equally likely (historical simulation)."""
    return np.full(n_scenarios, 1 / n_scenarios)


def _probabilities_or_uniform(probabilities: np.ndarray | None, n_scenarios: int) -> np.ndarray:
    """Validate a scenario probability vector (uniform if None): length J, nonnegative, sums to 1."""
    if probabilities is None:
        return uniform_prior(n_scenarios)
    probabilities = np.asarray(probabilities, dtype=float).ravel()
    if len(probabilities) != n_scenarios:
        raise ValueError(f"{len(probabilities)} probabilities for {n_scenarios} scenarios")
    if (probabilities < 0).any() or abs(probabilities.sum() - 1) > 1e-9:
        raise ValueError("probabilities must be nonnegative and sum to 1")
    return probabilities


@dataclass(frozen=True)
class ViewConstraints:
    """Views as linear constraints on the posterior scenario probabilities p.

    ``equality_matrix @ p == equality_target`` and
    ``inequality_matrix @ p <= inequality_target`` (Meucci 2008, eq. 9-10).
    A view on an expectation E[f(X)] = v is the row f(x_j) with target v; a
    view on a probability is an indicator row; ranking views are inequality
    rows.  The "converter" box of the architecture diagram turns views into
    this form; sum(p) == 1 is added by the solver, not stated here.

    These act on probabilities only — constraints on the portfolio weights
    (long-only, caps) are a separate kind and live in the optimizer.
    """

    equality_matrix: np.ndarray  # (n_equality_views, J)
    equality_target: np.ndarray  # (n_equality_views,)
    inequality_matrix: np.ndarray  # (n_inequality_views, J)
    inequality_target: np.ndarray  # (n_inequality_views,)


def entropy_pooling(
    market_samples: np.ndarray,
    prior_probabilities: np.ndarray,
    view_constraints: ViewConstraints | None = None,
) -> np.ndarray:
    """Posterior scenario probabilities: argmin_p KL(p || p0) s.t. the view constraints.

    Pass-through for now: with no views the minimum-relative-entropy posterior
    is the prior itself (KL = 0), which is what this returns.  The stage exists
    so that everything downstream already consumes (X, p) and a future solver
    (Meucci 2008: dual of the entropy problem, one unconstrained convex
    program in the number of views) slots in without touching any consumer.

    Views given but not yet solvable raise instead of being silently ignored.
    The scenarios are unchanged by construction — a constant column (cash)
    stays constant under any reweighting.
    """
    prior_probabilities = _probabilities_or_uniform(prior_probabilities, len(market_samples))
    if view_constraints is not None:
        raise NotImplementedError("entropy-pooling solver not implemented yet; pass view_constraints=None")
    return prior_probabilities


def empirical_certainty_equivalent(
    wealth_samples: np.ndarray,
    risk_tolerance: float,
    probabilities: np.ndarray | None = None,
) -> float:
    """CE of the scenario wealth distribution under CARA utility (dollars in, dollars out).

    CE = -zeta * log sum_j p_j exp(-psi_j / zeta); uniform p gives
    -zeta * (logsumexp(-psi / zeta) - log J).
    """
    wealth_samples = np.asarray(wealth_samples).ravel()
    probabilities = _probabilities_or_uniform(probabilities, len(wealth_samples))
    return -risk_tolerance * special.logsumexp(-wealth_samples / risk_tolerance, b=probabilities)


def empirical_cvar(
    loss_samples: np.ndarray,
    confidence_level: float,
    probabilities: np.ndarray | None = None,
) -> float:
    """Probability-weighted average of the worst (1-c) tail of losses (loss convention).

    Exact for any discrete distribution (Rockafellar & Uryasev 2002): the
    losses are sorted worst first and taken with their full probability until
    the tail mass 1-c is reached; the atom that straddles the boundary enters
    with the fraction of its probability that completes the tail.  Uniform p
    with (1-c)*J an integer is the plain mean of the worst (1-c)*J losses.
    """
    loss_samples = np.asarray(loss_samples).ravel()
    probabilities = _probabilities_or_uniform(probabilities, len(loss_samples))
    tail_probability = 1 - confidence_level

    worst_first = np.argsort(loss_samples)[::-1]
    sorted_losses = loss_samples[worst_first]
    sorted_probabilities = probabilities[worst_first]
    mass_before = np.cumsum(sorted_probabilities) - sorted_probabilities  # strictly worse atoms
    # full atoms, then the fractional boundary atom, then zeros
    tail_weights = np.clip(tail_probability - mass_before, 0, sorted_probabilities)
    return tail_weights @ sorted_losses / tail_probability


def _solver_scenarios(
    market_samples: np.ndarray,
    probabilities: np.ndarray | None,
    n_optimization_scenarios: int,
) -> tuple[np.ndarray, np.ndarray]:
    """The first ``n_optimization_scenarios`` rows with their probabilities, renormalized to sum to 1.

    Zero-probability rows are dropped: they carry no information and log(0)
    is not admissible in the CE objective.
    """
    probabilities = _probabilities_or_uniform(probabilities, len(market_samples))[:n_optimization_scenarios]
    solver_samples = market_samples[:n_optimization_scenarios]
    positive = probabilities > 0
    return solver_samples[positive], probabilities[positive] / probabilities[positive].sum()


def optimization_with_cvar_constrain(
    market_samples: np.ndarray,
    prices_vector: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma: float = 0.041,
    n_optimization_scenarios: int = 10_000,
    probabilities: np.ndarray | None = None,
) -> np.ndarray:
    """Maximize the probability-weighted CARA CE subject to a weighted CVaR budget (SAA).

    Only the first ``n_optimization_scenarios`` rows enter the solver (their
    probabilities renormalized):
    CLARABEL certifies "optimal" cleanly at ~10k scenarios and strains above
    (at a 1-year horizon it needs ``_CLARABEL_SETTINGS_LADDER``);
    the SAA optimum error is O(1/sqrt(N)) anyway.  Evaluate the returned
    allocation on the full sample set and a fresh seed (``evaluate_allocation``).

    Portfolio constraints (on weights, unlike view constraints, which act on
    probabilities): full investment and long-only.
    ``probabilities``: scenario probabilities p (uniform if None — Meucci's
    "historical simulation" special case, which reproduces the unweighted SAA).
    """
    solver_samples, solver_probabilities = _solver_scenarios(market_samples, probabilities, n_optimization_scenarios)
    n_scenarios, n_assets = solver_samples.shape

    # weights formulation: weight_i = price_i * alpha_i / wealth, unit budget
    gross_return_scenarios = solver_samples / prices_vector.ravel()
    relative_risk_tolerance = risk_tolerance / wealth

    weights = cp.Variable((n_assets, 1))
    relative_wealth_goal = gross_return_scenarios @ weights  # psi_s / w, symbolic
    relative_loss = 1 - relative_wealth_goal  # L_s / w, loss convention

    # CE = -zeta log sum_s p_s exp(-psi_s / zeta): log p_s rides inside the log-sum-exp
    ce_rel = -relative_risk_tolerance * cp.log_sum_exp(
        -relative_wealth_goal / relative_risk_tolerance + np.log(solver_probabilities).reshape((-1, 1))
    )

    # CVaR via Rockafellar-Uryasev: min over t of  t + sum_s p_s (L_s - t)+ / (1 - c),
    # written symbol-for-symbol with cp.pos; the free variable performs the min
    # implicitly (a feasibility witness — see module docstring references)
    var_proxy = cp.Variable()
    cvar_rel = var_proxy + solver_probabilities @ cp.pos(relative_loss[:, 0] - var_proxy) / (1 - confidence_level)

    constraints = [
        cp.sum(weights) == 1,  # budget
        cvar_rel <= gamma,  # risk budget
        weights >= 0,  # portfolio constraint: long-only
    ]
    problem = cp.Problem(cp.Maximize(ce_rel), constraints)
    _solve_with_clarabel(problem)
    if weights.value is None:
        raise RuntimeError(f"no solution: solver status {problem.status}")

    alpha_scenario = weights.value * wealth / prices_vector.reshape((-1, 1))  # back to shares
    print(f"status: {problem.status}")
    print(f"Allocations: {alpha_scenario.ravel().round()}")
    print(f"CE (in-solver, optimistically biased): {problem.value * wealth:,.0f}")
    print(f"VaR proxy t*: {var_proxy.value * wealth:,.0f}")  # argmin is an interval on discrete data
    return alpha_scenario


@dataclass(frozen=True)
class AllocationScores:
    """Probability-weighted yardsticks of one allocation on one scenario set (horizon dollars)."""

    certainty_equivalent: float
    cvar: float  # loss convention: positive = loss, relative to initial wealth
    expected_value: float


@dataclass(frozen=True)
class AllocationEvaluation:
    in_solver: AllocationScores | None  # the rows the optimizer saw (None if not requested)
    full_set: AllocationScores
    unseen: AllocationScores


def score_allocation(
    allocations: np.ndarray,
    market_samples: np.ndarray,
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    probabilities: np.ndarray | None = None,
) -> AllocationScores:
    """CE, CVaR and expected value of a fixed allocation under (X, p)."""
    wealth_samples = (market_samples @ allocations).ravel()
    probabilities = _probabilities_or_uniform(probabilities, len(wealth_samples))
    return AllocationScores(
        certainty_equivalent=empirical_certainty_equivalent(wealth_samples, risk_tolerance, probabilities),
        cvar=empirical_cvar(wealth - wealth_samples, confidence_level, probabilities),
        expected_value=probabilities @ wealth_samples,
    )


def evaluate_allocation(
    allocations: np.ndarray,
    market_samples: np.ndarray,
    sample_scenarios: Callable[[int], tuple[np.ndarray, np.ndarray]],
    wealth: float,
    risk_tolerance: float,
    confidence_level: float,
    gamma: float,
    out_of_sample_seed: int,
    probabilities: np.ndarray | None = None,
    n_optimization_scenarios: int | None = None,
) -> AllocationEvaluation:
    """Probability-weighted CE/CVaR/value of a fixed allocation: solver rows, full sample set, fresh seed.

    The yardsticks are computed outside the solver — a solver status is a
    claim; these numbers are the verdict.  The fresh-seed line is the honest
    risk report: the in-sample one is the quantity the optimizer was allowed
    to flatter.

    ``sample_scenarios``: seed -> (scenario set, probabilities), built exactly
    like ``market_samples`` (same generator, same size, same cash column, same
    entropy-pooling stage), so the fresh draw differs from the in-sample one
    only by its seed.  Passing the generator keeps this module ignorant of
    where scenarios come from.
    ``n_optimization_scenarios``: if given, also score the first rows — the
    set the optimizer actually saw — with renormalized probabilities, which
    reproduces the in-solver CE.
    """

    def report(label: str, scores: AllocationScores) -> None:
        print(
            f"{label:13s}: CE {scores.certainty_equivalent:,.0f}   CVaR {scores.cvar:,.0f}   "
            f"E[value] {scores.expected_value:,.0f}   (budget {gamma * wealth:,.0f})"
        )

    in_solver = None
    if n_optimization_scenarios is not None:
        solver_samples, solver_probabilities = _solver_scenarios(
            market_samples, probabilities, n_optimization_scenarios
        )
        in_solver = score_allocation(
            allocations, solver_samples, wealth, risk_tolerance, confidence_level, solver_probabilities
        )
        report("in-solver", in_solver)

    full_set = score_allocation(allocations, market_samples, wealth, risk_tolerance, confidence_level, probabilities)
    report("full set", full_set)

    unseen_samples, unseen_probabilities = sample_scenarios(out_of_sample_seed)
    unseen = score_allocation(
        allocations, unseen_samples, wealth, risk_tolerance, confidence_level, unseen_probabilities
    )
    report("out-of-sample", unseen)
    return AllocationEvaluation(in_solver=in_solver, full_set=full_set, unseen=unseen)
