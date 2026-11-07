# Independent final all-risk judge

`evaluation.evaluate` receives frozen holdings and independent final scenario
batches. It neither solves nor repairs a portfolio. The runner retains its
funding-validation selection rule for now and reports a final failure without
searching the test set for a replacement. Final results must not become a
selection grid or silently feed another calibration attempt.

The judge checks every scheduled payment (including same-week ordering),
terminal initial-capital loss, maximum initial-capital loss over the full path,
full investment, no shorting, minimum holdings and fixed holdings. Market loss
is before payouts, matching the stated optimization constraints. Funding uses
separate spendable prices; marked property is not spendable cash. Accounting
still uses the documented money-market provisioning convention, not an
executable selling ledger. A later ledger must replace both the producer and
the judge's accounting with a tested common economic specification.

Reference (uniform), nominal-view and stressed probabilities are evaluated.
For each risk, an exact one-dimensional common-RU-threshold upper envelope
covers their finite convex hull. The calculation is separate from the CVXPY
optimizer. It sorts atoms and tests knots and pairwise affine intersections.
A separate scipy linear-program oracle and hand examples test this calculation.
Maximum endpoint CVaR alone does not cover mixtures: with losses 0,1,2,
probabilities (.8,0,.2) and (0,1,0), and confidence .5, the largest endpoint
CVaR is1 while the common-threshold hull envelope is1.25.

Risk estimates across independent batches have one-sided 95% conditional
Student-t diagnostics, Bonferroni-adjusted over all reported risk/measure
comparisons. The larger of the endpoint and common-hull upper diagnostics is
checked, then the existing W1 sufficient buffer is added. This is conditional
Monte Carlo uncertainty, not exact frequentist coverage for an estimated
CVaR, parameter uncertainty, historical/economic coverage, or a calibrated W1
radius. With only two batches these diagnostics can be extremely wide, even
above 100% loss. That is imprecision, not a forecast of such losses. Zero sample
variance is not a bound on unseen tails. The UI calls this out.

`funding_pass` checks the independent funding bounds only. `overall_pass`
requires all risks and holdings. The old `evaluation_pass` field now aliases
`overall_pass`, deliberately breaking the misleading funding-only meaning.
Each breach is named. Numerical risk-budget tolerance is zero. Holdings use
an explicit absolute weight residual tolerance of1e-7. Passing is a conditional
research result, never an investment recommendation. Coarse results retain
explicit scenario counts and a research-only label.

The benchmark UI shows each method's worst payment date by upper/budget ratio,
not merely the final payment. A missing candidate never automatically displays
a comparator fan: the user must choose Compare baselines. Old archived results
without this judge are marked unchecked, not retroactively passed.

The local HTTP server allows one active solve with no waiting queue. Concurrent
requests get429. Full research-tier controls and legacy single-date companion
requests are rejected by this UI. Raw-config requests have an explicit100,000
scenario-week work cap. The CLI remains available for measured research jobs.
Closing the browser does not cancel a solver already running; its slot remains
occupied until completion. Process-based cancellation is not yet implemented.
