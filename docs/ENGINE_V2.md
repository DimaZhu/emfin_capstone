
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
