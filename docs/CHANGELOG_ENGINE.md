# Historical development log

Superseded results and earlier claims are preserved below as history, not current
method documentation. Use ENGINE_V2.md and regenerated artifacts for current status.
In particular: the old CRRA/DCP claim is incorrect, old probability alignment and
TSDR transitions were fixed, and raw-unit covariance shrinkage was replaced.


## CRRA-on-surplus objective (review point 2)

CARA's absolute risk tolerance is wealth-independent; a family's risk capacity
should scale with its surplus.  `--no-crra` skips this block (default on).  The
Kallberg-Ziemba surrogate keeps the convex CARA solve and rescales the
tolerance by the surplus ratio at the optimum relative to its pre-solve
reference (`crra_scaled_tolerance`), one rescale iteration.  Exact power
utility over unbounded scenario sets is not DCP-robust.  On the reference
problem the optimum sits above the reference funding ratio (7.3% vs 5.0%), so
the rescale lifts tolerance 47% and the allocation barely moves (34.9% vs
34.1% US equity): the correction binds only when a portfolio would push the
funding ratio below reference.

## Multi-Period Entropy Pooling + CML views (Kristensen & Vorobets 2026)

Implemented from the public article
(antonvorobets.substack.com/p/multi-period-entropy-pooling, Oct 5 2026); no
GPL code.  `toolbox/mpep.py` exploits the article's key linearity: every
per-horizon view is linear in the PATH probabilities, so MPEP is one-period
SeqEP on the stacked S x (I*H) path matrix, with pinned parameters fixed
only at each view's own horizon.  View classes carry over (means/ranks/ML
in C0, vols in C1, CML in V-bar).  ML views are static indicator
constraints; CML views add the weighted-tail constraint with a tail count l
found by our OWN coarse-to-fine relative-entropy search - the article's
search algorithm is proprietary, ours is a documented substitute, not a
copy.

The runner demo is a STRESS TEST, not a forecast: 95%-CML of US equity max
path drawdown forced at least 20% deeper than the FFR prior.  The posterior
path probabilities (RE 0.011, ENS 98.9%, l=255 of 10,000 paths) feed the
multi-period liability-aware solver directly - the article's "CML unified"
pipeline.  Under the stress the allocation de-risks from 18.7% to 1.0% US
equity into money market: the tail view flows through to the allocation,
which is the point of the machinery.  Validated on synthetic geometric
paths (tests/test_mpep.py): per-horizon views bind at their own horizon,
the cross-horizon ripple the article predicts is present, and ML/CML
constraints achieve their targets within the discrete-path approximation.

## Time- and State-Dependent Resampling (Kristensen & Vorobets 2025)

`toolbox/tsdr.py`, behind `--tsdr`.  Implemented from the PUBLIC
descriptions (Substack summary, SSRN 5117589 abstract, and the MPEP case
study's parameters) - the definitions PDF is access-gated and the
accompanying code is GPL-3.0; neither was consulted.  Construction:
per-state probability vectors (exponential time decay x crisp 25%/90%
quantile classification of the trailing-vol state, half-life tau = T/2 as
in the article), and Markov-chain path resampling where the next weekly
invariant is drawn conditional on the current state and the chain
transitions to the empirical successor state.  Where ffr.py produces ONE
state-conditioned prior, TSDR keeps regime persistence inside the
simulated paths; tests verify the article's headline stationarity property
(initial-state dependence fades with horizon) and that simulated
transitions match the empirical transition matrix.

Reference-run finding (real data): the current state is LOW vol, yet the
resampled paths carry a fatter DFUS tail than the i.i.d. Gaussian (95%
CVaR 11.7% vs 8.9% of terminal return) - history's tails are fatter than
the parametric fit - and the multi-period allocation shifts accordingly
(29.2% vs 18.7% US equity).

## Validation expansion: empirical judge and SAA study

The new empirical judge resamples joint weekly history via the state transition
chain without decay. Its evaluation overlaps the fitted history, so it is
explicitly **not historical out-of-sample evidence**. A high-vol/calm split
is a conditional diagnostic, not a claim that high volatility predicts losses.
1/N is included alongside the common shrunk-moment MV benchmark.

The SAA study solves 12 independent 2,000-scenario problems and evaluates all
allocations on one shared 50,000-scenario Monte Carlo holdout. Training and
holdout use the same Gaussian or variance-matched Student-t DGP and liquidity
map. It is a prior/no-views diagnostic, not a repeated EP-view experiment.
The t intervals condition on the shared holdout and fitted DGP; they exclude
holdout error, parameter uncertainty, and economic out-of-sample uncertainty.
The first run's absolute CE-gap intervals cover zero. Paired excess gaps over
a fixed 1/N control are $39k [-$5k,$84k] for MV and $44k [$1k,$87k] for SAA.
These are small-sample Monte Carlo findings, not a general optimism bound.
Calibration and final parametric evaluation now use disjoint seed streams.

For numerical stability, the liability solvers minimize centered expected
exponential disutility, an exactly monotone transform of CARA CE, instead of
nesting an extra log cone. Diagnostics transform back to dollar CE. A regression
test verifies the value against logsumexp. The default reference pipeline
completes in about 40 seconds here; timing remains machine-dependent.

## Chronological calibration and data-driven nu

`python scripts/validate_chronological.py` builds expanding development folds,
selects nu by validation weekly multivariate log likelihood, and picks the largest
budget multiplier meeting the worst development-fold empirical gap budget.
The last 26 observations (2026-05-13 through 2026-11-04 on this snapshot) are
reserved and **not evaluated** by this script. This restriction applies to this
protocol, not to the existing full-history current-allocation runner.

The three development folds select nu=5 from {5,8,30,200} and multiplier=1 from
{0.25,0.5,1}. This is exploratory, not a validated 95% tail guarantee: each fold
contains only 1-2 nonoverlapping 13-week outcomes; rolling outcomes overlap.
The JSON records every fold's score, dates and effective nonoverlap count.
No liquidity costs are assumed in this diagnostic; exact repricing uses synthetic
10-year 4%-coupon instruments and training-date yield/spread anchors.

`--student-t=auto` in the main runner fits conditional nu MLE on the development
prefix, constrained to [4.1,200] to keep the existing moment views finite. It is
not a joint location/covariance/nu MLE. Unconstrained development fits are near
2.8 in this small sample; therefore the finite-fourth-moment restriction matters
and must not be hidden. Weekly t tails and the elliptical horizon approximation
are different models: aggregation does not preserve Student-t degrees of freedom.

A transition-order regression test also caught and fixed an in-place grouped
TSDR update: a path entering a later state could previously be advanced twice
within a single week. Transitions are now simultaneous. Earlier TSDR performance
numbers should be rerun, not reused. Stationarity requires invariant initialization;
convergence from a chosen initial state is not the same as strict stationarity.

## CML budgets and finite-posterior robustness

`optimization_multiperiod(..., cml_budget=..., stress_probabilities=[...])`
constrains the tail mean of maximum loss from **initial wealth** across a path,
not peak-to-trough drawdown. The nominal and stressed EP measures share one
Rockafellar-Uryasev threshold and excess vector. Thus the same upper bound holds
for every convex mixture of these measures, not only their listed endpoints.
This is a finite-measure robust CML constraint, not an unrestricted KL ball or
Wasserstein DRO model, and the objective remains nominal CARA utility.

The reference comparison uses a 6% placeholder CML budget and 500 path scenarios.
The 2,000/10,000-scenario formulations failed solver residual checks here, so no
claim of large-N readiness is made. The 500-path row is explicitly an SAA example,
not a funding guarantee: its fresh parametric funding-gap CVaR is ~$644k against
the separate $190k funding target. A CML constraint cannot replace funding-budget
calibration. The baseline multi-period row likewise has no OOS-calibrated budget.

MPEP now supports multiple CML views with an approximate coordinate search over
tail counts on the full path set. It skips infeasible candidates and makes no
global-optimality claim. Unknown views/invalid weights fail loudly. Rank/vol
view senses are honored; ML diagnostics now report ML, not CML by mistake.

A probability-alignment correction: multi-period allocations previously reused
probabilities from an independently generated one-period scenario set by row
number. They now pool views on their actual path scenarios. TSDR's liabilities
and money-market provisioning now also follow its own resampled paths. These
fixes change earlier multi-period and TSDR headline numbers; rerun, do not reuse.

Solver policy checks status, finite variables/objective and maximum constraint
residual <=1e-5 in normalized units. Failed or materially infeasible approximate
solutions are rejected, never presented as allocations. A shorter interior-point
step and centered disutility improve stability; they do not solve every case.
