
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
