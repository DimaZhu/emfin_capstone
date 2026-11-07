# Book-based audit,7 November2026

## Scope and conclusion

Source: the user's attached Attilio Meucci, *Risk and Asset Allocation*, Springer,
2005, ISBN978-3-540-22213-2,547 PDF pages. This was a targeted mathematical and
implementation review, not a claim to have checked every line of the book or
every optional method in the repository. Printed-page and PDF-page numbers
are both given because they do not have one constant offset throughout this PDF.
The book PDF/pages are not committed or redistributed.

The current separation of estimation, scenario projection, investor objective,
optimization and independent evaluation is sensible. But finite moments and
numerically correct optimization are not enough: candidate invariants were
being assumed iid without showing the checks the book asks for. Actual data
show volatility clustering and asymmetric/heavier sample shapes that the
chosen symmetric iid mixture does not fit. The review adds evidence, fixes
concrete helper errors and corrects stale claims. It does not secretly replace
the scenario law, risk preferences or the final evaluation set.

## Errors fixed

1. **Empirical quantile interpolation.** The reusable VaR helper returned9.5
   for equal-mass losses0 and10 at95% confidence. That is an interpolated sample
   quantile, not the generalized inverse of that empirical loss CDF (10).
   It now explicitly uses the generalized inverse; invalid/empty/nonfinite
   samples and invalid confidence levels reject. The former CVaR helper could
   return0.75 for losses1 and2 with invalid confidence-1. Domain validation
   fixes that too. Book: printed p.7, equation1.17 (PDF31), and pp.277-278
   (PDF298-299). Discrete atoms need an explicit generalized-inverse convention.
   The delivered default studies use the separate weighted fractional-atom
   tail evaluator, so this helper repair does not revise those study numbers.
2. **One stochastic sleeve crashed covariance shrinkage.** NumPy returns a
   scalar covariance for one column. The code tried taking its trace as a
   matrix. It now preserves a1x1 matrix and the sample variance. The default
   has several risky sleeves and its existing results are unchanged. This is
   an implementation boundary bug, not a new shrinkage theorem. Book's general
   estimation discussion: section4.4, printed pp.201-205 (PDF222-226).
3. **Stale current documentation.** ENGINE_V2.md still mixed Student-t, old
   instruments, a$35M/$60M schedule,13-week outputs and older controls with
   the actual current default. It is replaced with one current model account;
   former text is preserved as explicitly archived notes. No original archive,
   history or attribution was deleted.
4. **Normal log returns versus normal prices.** A scenario-module explanation
   suggested normal-market analytical formulas validate lognormal prices
   exactly. Corrected: normal log invariants imply lognormal horizon prices;
   the normal-price CARA formula is exact only for normal wealth. Book:
   pp.275 (PDF296),336-338 (PDF357-359). New independent normal-wealth
   quadrature and skewed-wealth counterexamples pin the distinction.

## Missing scientific checks now exposed

### Invariance and volatility clustering

Book: pp.103-105 (PDF125-127) asks for chronological invariants, early/late
histograms and lagged scatter plots before iid projection. Equations3.60-3.77,
pp.123-125 (PDF145-147), project iid increments, not arbitrary dependent data.

The new diagnostic uses the pinned common1129-week listed/FX history. Cash is
identified as deterministic. It reports split empirical-CDF distance,
lag1/4/8 ordinary and squared-return correlations, sample skewness and sample
excess kurtosis. No rows are removed, no p-values or binary iid certification
are offered, and no parameter/portfolio is automatically changed. Diagnostics
are withheld for synthetic bootstrap row ordering because it is not observed
chronology. Quarterly property is not fabricated into weekly observations.

|Series|Lag1 returns|Lag1 squared returns|Sample skewness|Sample excess kurtosis|
|---|---:|---:|---:|---:|
|VTI|-0.071|0.329|-0.989|9.056|
|VWO|-0.032|0.344|-0.692|7.181|
|GLD|-0.000|0.119|-0.279|2.045|
|IEF|-0.060|0.112|-0.131|0.999|
|SGD/USD factor|0.018|0.138|-0.230|2.397|

Weak ordinary autocorrelation is not independence. The current iid prior has
independent weekly variance states, so it cannot represent this temporal
volatility dependence. Sample moments are noisy descriptive estimates, not
known population values or proof of future behavior. The before-EP mixture
has zero skewness and excess kurtosis1.6875 in every nondegenerate marginal;
its shape is a development choice, not a historical fit. EP may change a finite
path distribution but is not a fitted conditional-volatility model.

The existing EWMA-FHS filter reduces squared-return lag1 correlations in its
1077 residual rows to about0.124 for VTI and0.100 for VWO. This is not zero,
not an independent holdout, and not proof FHS is calibrated or superior. The
book discusses exponential smoothing/GARCH links on pp.233-234 (PDF254-255).
Decay0.94 remains a declared development setting, not book-validated calibration.

### Shrinkage terminology and parameter risk

The book's James-Stein construction uses a data-dependent weight and discusses
volatility-weighted targets, pp.201-204 (PDF222-225). Our fixed156-observation
strength and arithmetic cross-listed mean target are transparent shrinkage
heuristics, not those exact estimators or an inferred Bayesian posterior.
Covariance shrinkage is in standardized coordinates with an approximate
finite-sample intensity. A Bayesian or James-Stein optimality claim is not made.
No formula was silently swapped because that would create a new model and
invalidate comparison with the frozen studies.

### Means and covariance are not the whole law

Book: pp.336-340 (PDF357-361) explains MV approximation and monotonicity risks.
A new own-fixture test has wealth100 or300, never below cash100. Exact CARA
likes it, while a fixed-coefficient MV approximation can rank it below cash.
Thus close CARA/MV study averages are not a proof they are the same preference.
Dollar-scale and cash-translation CE identities, Jensen bounds and expected
shortfall translation/homogeneity/subadditivity now have independent tests.

The existing increment-summing projection is appropriate for whole weeks under
its stated iid law. It does not keep a weekly Student-t family unchanged over a
year. For iid mixture increments, excess kurtosis decreases with aggregation;
finite annual price moments do not establish realistic annual downside tails.
Property annual dispersion includes serial covariance of quarterly sums, but
weekly square-root disaggregation remains an assumption, not a recovered weekly
property process. Overlapping annual windows are not independent observations:
book p.234 (PDF255). These limits remain open.

## Existing parts that survive the review, with limits

- **CARA:** dollars of terminal net marked wealth and dollar risk tolerance,
  consistent with pp.261-262 (PDF282-283), not expected profit or consumption
  utility. A self-financing spending strategy and lifetime utility are different
  modeling tasks. The separate ledger still differs from provisioning.
- **ES/CVaR:** book pp.293-294 (PDF314-315), especially footnote7, limits the
  simple conditional-tail-expectation identity to smooth distributions. Our
  finite scenario tails correctly split the boundary atom. Do not replace them
  with a naive conditional average at VaR. For the loss sign convention used
  here, ES is convex/subadditive rather than the book's concave satisfaction
  sign. A new signed-loss/atom coherence test checks this.
- **Refit and average:** book pp.440-441 (PDF459-460) gives estimate, resample,
  refit, optimize, average. The implemented whole-fit bootstrap is a dependent
  block-bootstrap variant, not an exact parametric/Bayesian replica. Every
  required fit must succeed. Book p.445 (PDF464) warns averaging need not keep
  constraints; the average therefore still faces the same independent judge.
- **Robustness:** book pp.445-449 (PDF464-468) describes minimax opportunity
  cost/regret over a data-grounded parameter set. Our finite-posterior-hull/W1
  risk envelopes are a different, explicitly limited extension with nominal
  utility. They are not that exact book objective. A chosen radius is not a
  confidence set. The old radius remains uncalibrated.
- **Fixed income:** book pp.109-113 distinguishes yield changes from individual
  bond returns. IEF is a managed rolling ETF, not a specific bond converging to
  par. Its return model needs its own invariance checks; this review does not
  pretend the ETF's returns are automatically invariant because it is listed.

## What still needs a new scientific decision

Priority is model adequacy, not a better-looking allocation. Prespecify and
compare conditional-volatility or dependent finite-support models on past-only
fit/validation splits, including their standardized residual diagnostics and
unseen regimes. Keep the untouched final judge separate. Any new model must
retain a defensible moment domain, fitted dependence and finite-horizon cash
accounting. More data and independent holdouts, not a switch of labels, are
needed before calling an option more accurate.

Then address cash carry, joint quarterly property/ETF/FX estimation, true
property publication/vintages, actual settlement/costs, radius selection and
an explicit funded-policy objective. The earlier counterfactual remains:
a20% tail-gap allowance can pass while payments go unpaid. A99% joint-funding
requirement would be a different explicit policy, not this book audit silently
changing the user's preferences.

## Reproduction and evidence

`tests/test_book_foundations.py` and `tests/test_invariance.py` contain new own-
fixture checks. Current-history diagnostics are regenerated by normal registry
fitting. Saved review JSON identifies the config/data/implementation state;
this evidence is new, not a rewritten2007-2025 backtest. The previous science
report/evidence remains versioned and unchanged. No book source code or pages
were copied, no GPL was added, and nothing was publicly hosted or sent to
third parties.
