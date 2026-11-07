# Wasserstein risk bounds in V2

This implementation adds distributionally robust risk constraints, not a robust
exponential-utility objective. Nominal expected CARA satisfaction remains the
objective. No GPL or third-party DRO implementation is used.

## Metric and scope

Each sample consists of normalized gross-price path coordinates r[t,j] and
normalized cumulative payout requirements b[i] = required[i] / initial wealth.
The L1 ground cost is the sum of absolute changes in all price coordinates plus
the sum of absolute changes in b divided by `wasserstein_liability_scale`.
A zero liability scale freezes payout-requirement coordinates. The scale is a
model choice, not a fitted confidence level. The price coordinates use scale 1.

The support is unrestricted real space. This admits negative hypothetical prices
and payout requirements and disregards the physical relationships among path
coordinates. That is conservative relative to a smaller economic support, but
must not be sold as a realistic scenario generator. The radius epsilon is in
these normalized-coordinate transport units. The example value 0.00002 is a
development illustration, not a data-driven guarantee of distribution coverage.

## Bound

For loss g(z,w) that is the maximum of finitely many affine pieces, the RU
hinge h(z,w,eta) = max(0,g(z,w)-eta) has a dual-norm Lipschitz bound L(w).
For a W1 ball around a discrete measure p, at each fixed eta:

    sup_Q E_Q[h] <= E_p[h] + epsilon * L(w)

For the unrestricted support and piecewise-affine hinges used here the fixed-eta
expectation dual gives this bound tightly. Minimizing the right-hand RU envelope
therefore provides a sufficient bound on sup_Q CVaR_Q(g):

    eta + E_p[max(0,g-eta)]/(1-alpha)
        + epsilon * L(w)/(1-alpha)

We do not rely on or assert an unproved interchange of sup_Q and min_eta.
The ordinary finite-sample CVaR plus that penalty is the minimized sufficient
bound. A shared eta for nominal/stressed measures remains a conservative
common-threshold envelope over both balls and mixtures. Evaluation reports
per-measure bounds separately; no claim that statistical coverage follows.

For market path loss max(0, max_t(1-r[t]·w)), L=||w||_infinity. For a funding gap
max(0,b[i]-r[t_i]·w), L=max(||w||_infinity, liability_scale). Both are convex in
weights. Terminal initial-loss risk uses the same market slope. Funding penalties
are converted back to dollars and included in calibration and held-out checks,
not hidden from the risk budgets. Utility is not made robust because exponential
loss under an unrestricted W1 support can have infinite worst-case expectation.

A positive radius cannot guarantee a zero funding gap budget under unrestricted
support. That combination is rejected rather than silently weakened.

## Tests

Independent tests include epsilon=0 equivalence, L1/L-infinity slope checks,
a finite-support adversarial transport LP approaching the theoretical hinge
bound, invalid-radius rejection, and a tiny funding optimizer whose active
constraint tightens with positive epsilon. The report exposes both empirical
intervals and the extra dollar buffer. Monte Carlo intervals remain conditional
batch estimates, not economic forecast guarantees.

## Sources

Mohajerin Esfahani and Kuhn, *Data-driven distributionally robust optimization
using the Wasserstein metric: performance guarantees and tractable
reformulations*, Corollary 5.1:
https://link.springer.com/article/10.1007/s10107-017-1172-1

Independent implementation documentation consulted for terminology only:
https://skfolio.org/generated/skfolio.optimization.DistributionallyRobustCVaR.html
No source code from it was copied or installed.
