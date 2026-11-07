# W1 metric and representation sensitivity

New default `max_path`: the ground cost between two normalized scenarios includes marked and separate spendable price paths as primitive coordinates and is

    max_(time,asset) |price perturbation|
        + max_payment |cumulative requirement perturbation| / liability_scale.

For a dated funding hinge the dual Lipschitz slope is
`max(sum(abs(weights)), liability_scale)`. For path/terminal market loss it
is `sum(abs(weights))`. These are the norms of the actual affine slopes;
maximum over time does not multiply the constant by the number of time
steps. Duplicate identical sleeves split into positive subweights preserve
the sum exposure. Repeating identical time coordinates preserves the ground
cost. Both have hand/LP/CVXPY tests.

For fully invested long-only holdings the market slope is exactly1. Thus at
radius0.00002 and confidence0.95 the sufficient market/funding buffer is
0.0004 of initial wealth, or$40,000 on$100M (liability_scale0.01 is smaller).
The old L1 price metric's dual max-weight norm gave$32,000 for [.8,.2] but
$16,000 for [.4,.4,.2]. It remains named `legacy_l1` for archived replication,
not as an unlabeled new choice. The new metric changes economic assumptions;
keeping the same numerical radius does not preserve the old ambiguity set.

The radius remains a development placeholder. This metric bounds a common
per-unit relative price shock across the path plus scaled obligations; it
neither makes a price shock likely nor supplies a calibrated confidence set.
Unrestricted support still admits impossible negative prices. Same-path
radius sensitivity and rolling past-only discrepancy calibration must be
reported as empirical diagnostics, not a finite-sample confidence guarantee.
When a risk budget is too small for the unavoidable long-only buffer, fail
with the dollar conflict rather than loosen solver acceptance.

This metric is deliberately conservative: it does not reward diversification
through a smaller W1 slope, since sum positive weights is1. The scenario
risk model can still reflect diversification. A future factor-weighted metric
may distinguish economic shocks, but needs explicit units and invariant alias
handling rather than another unexplained radius adjustment.


The primitive-coordinate ambiguity set can perturb marked and spendable paths
independently, including the nominally deterministic cash sleeve. That is a
conservative modeling relaxation, not a claim that every perturbed scenario is
an economically executable path. The bound does not transfer automatically to
the nonlinear cash-first sales ledger.

Optional `past_empirical` policy and its large budget conflicts are documented
in STRICT_FUNDING_PROTOCOL.md and STRICT_FUNDING_RESULTS.md. Half-split
historical discrepancies are a shift-stress policy, not future-law coverage.
