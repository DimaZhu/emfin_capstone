# Ranked model and pipeline review

7 November 2026. Code reviewed at 070d534; the coarse grid and new research are still in progress. This review is not a certification or client recommendation.

|Rank|Gap and recommended next step|Impact / effort|What would count as evidence|
|---|---|---|---|
|1|Run chronological historical evaluation on available liquid assets, with fitting and radius selection strictly before each decision date. Owner approved this next.|Very high / large|Saved fold cutoffs, realized paths, paired benchmark results, failures and sparse-tail counts, not only generator-held-out scores.|
|2|Calibrate and diagnose the W1 radius in the exact optimization metric. Owner approved this next.|Very high / large|Training-only empirical transport distances and blocked resamples, frozen held-out distance-inclusion frequency, sample-size/quantile instability and uncovered folds. No automatic coverage theorem.|
|3|Clarify the estimand of every performance number. The optimizer uses the EP posterior for utility; current evaluation CE is under uniform generated rows, while stressed funding uses a reweighted posterior. These are different measures.|High / medium|A deliberate base-versus-view evaluation table, clearly named weights, an independent test reproducing each figure and no silent relabelling of one as the other.|
|4|Expand held-out diagnostics beyond funding. Candidate selection and its pass flag test funding CVaR budgets; training optimization also imposes loss/CML limits, which are not the same as held-out confirmation of all constraints.|High / medium|Separate held-out funding, maximum-loss-CVaR/CML and utility panels with sample counts; never imply a funding pass certifies every risk constraint.|
|5|Quantify model uncertainty, not only simulation error. Two-seed prototype t intervals are noisy; zero losses give zero-width intervals without bounding unseen tails.|High / large|More independent batches, convergence curves and explicit bootstrap/parameter/dependence stress. Preserve the small-grid label.|
|6|Replace illustrative client and property assumptions with authorized, sourced inputs before use. Short property history, assumed dependence/rent and fixed sale/settlement omit closing/buyer, debt, tax and FX risk.|Very high for client use / large|A dated private input manifest with units, currency, owner and provenance; sensitivity to sale delays and joint stress; no source values in git.|
|7|Make the expensive solver path more predictable. Current subprocess timeout is honest but coarse and full research runs can be slow.|Medium / medium|Profile EP versus optimization versus rendering, cache repeated calibration, bound memory, keep timeout distinct from infeasibility. Do not trade residual checks for speed.|
|8|Strengthen release reproducibility and licensing checks. Preserve the original archive, expose its alerts, and settle inherited code/data rights before public release.|High / medium plus external rights decision|Clean-wheel smoke and CI, lock/audit supported runtime dependencies, documented rights. A private fork or synthetic RE does not cure inherited rights.|

## What I would not trust yet

- A portfolio funding-pass badge as proof of safety for a real family office.
- A development-selected or bootstrap-percentile W1 radius as a 95% economic coverage guarantee.
- A 729-point coarse lookup as a fresh solve, a universal optimum or a full-fidelity research grid.
- A short boom-period property series or the illustrative 4% forward price view as a reliable long-run expected return.
- Generator-based disjoint seeds as a substitute for real-history validation.
- The separate `--research` path as identical in validation scope to the default engine without its own results and checks.

## Already improved, versus still open

Implemented: cumulative payout accounting; marked versus spendable RE paths; sale settlement and rent; explicit forward RE view separated from boom sample mean; editable market views with achieved targets; solver residual checks and honest unavailable/fallback states; synthetic-only resumable experiments; small reference and sensitivity reports; local/prepared Apps Script lookup; reproducible test threads. These are useful engineering and mathematical checks, not economic validation.

Pending: the two approved research additions above, completion of the coarse grid, full-fidelity evidence, real client input review, public-release rights, live Apps Script deployment by the owner, and independent external review. No counterpart has been contacted and no access broadened.

Sources for this review are the repository's default_run.py (selection/evaluation), real_estate.py (valuation/funding assumptions), experiments/evidence.py and configs (comparators/sample sizes), prototype/ (lookup behavior), and the retained source and audit documents. The findings are code-scope observations; no unverified market claims are needed for them.
