# Default funding-risk comparison

Private research: actual VTI/VWO/GLD/IEF histories, cash account, SGD property with USD FX. Not client-calibrated.

Snapshot 2026-10-30; status: no calibration candidate passed

|Method|Net CE mean ($)|Per-date nominal/stressed gap CVaR upper CI ($)|W1 buffer ($)|Upper bounds incl. W1 ($)|Pass all risk budgets?|

|---|---:|---|---:|---|---|

|1/N|100,126,527|0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0|813,488,226|813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226|False|

|shrunk MV|101,810,240|0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0, 0/0|813,488,226|813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226, 813,488,226|False|

## Independent final all-risk verdicts

1/N: funding=False; overall=False; breaches=Held-out funding: week 4, Held-out funding: week 8, Held-out funding: week 13, Held-out funding: week 17, Held-out funding: week 21, Held-out funding: week 26, Held-out funding: week 30, Held-out funding: week 34, Held-out funding: week 39, Held-out funding: week 43, Held-out funding: week 47, Held-out funding: week 52, Held-out path-loss tail, Held-out terminal-loss tail. Conditional diagnostics only, not economic coverage.

shrunk MV: funding=False; overall=False; breaches=Held-out funding: week 4, Held-out funding: week 8, Held-out funding: week 13, Held-out funding: week 17, Held-out funding: week 21, Held-out funding: week 26, Held-out funding: week 30, Held-out funding: week 34, Held-out funding: week 39, Held-out funding: week 43, Held-out funding: week 47, Held-out funding: week 52, Held-out path-loss tail, Held-out terminal-loss tail. Conditional diagnostics only, not economic coverage.

## Qualifications

- Wasserstein risk bounds use an explicit max_path transport metric on normalized path prices and cumulative payout requirements, unrestricted support and a development-selected radius, not a confidence-calibrated ambiguity set. Utility remains nominal.

- Final all-risk verdict uses separate Bonferroni-adjusted one-sided conditional batch bounds for every payment, path/terminal loss and holdings. Reference, nominal and stress measures plus their common-threshold convex-hull envelope are checked. These are Monte Carlo diagnostics, not economic forecast coverage. Zero observed losses do not bound unseen tails.

- Funding-selected candidates remain frozen when final all-risk evaluation fails. Final results never tune or repair them. Passing a coarse model check is not an investment recommendation.

- Archive split independence is the input provider responsibility; generated mode uses disjoint calibration/evaluation seeds. Final failures are never recalibrated away.

- Stressed posterior and nominal share funding/CML thresholds, covering their finite convex hull only.

- Liabilities, views and innovation-law parameters are illustrative/development-selected, not client evidence. Scenario law: gaussian_scale_mixture

- Weekly log shocks aggregate by summation. Read innovation_evidence for the selected iid, conditional or legacy model domain. Legacy t cannot support population price means/variances; iid exact formulas do not apply to recursive conditional variance.

- Cumulative payouts use money-market opportunity costs, not dynamic rebalancing. RE uses an explicit fixed planned sale/settlement schedule; marked value is not available cash.

- Cash mixing is an explicit validation-selected portfolio calibration grid, not a claim of globally optimal robust weights.

- 1/N allocates the free budget equally subject to floors and fixed initial holdings; all allocation comparators and the displayed frontier honor those holdings.
