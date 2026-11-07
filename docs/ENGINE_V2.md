
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
