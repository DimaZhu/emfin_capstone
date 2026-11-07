# Finite-moment default scenario law

The current default is an iid weekly Gaussian variance mixture. Each week has
probability0.9 of innovation variance scale0.75 and probability0.1 of scale3.25.
Their weighted mean variance is exactly1, preserving the shrunk joint log
covariance. One shared variance state multiplies listed ETF, FX and property
Gaussian innovations each week. It preserves the specified cross-asset log
correlations and induces joint volatility clustering within a week, but NOT
serially persistent regimes. It is not fitted FHS, a t distribution or a
claim about observed regime probabilities. The parameters are labelled
explicit development choices pending sensitivity testing.

For innovation vector X with mean mu and covariance Sigma, conditional on
state k it is N(mu, v_k Sigma). For any finite exposure b,

    log E exp(b'X) = b'mu + log sum_k p_k exp(v_k b'Sigma b / 2).

For h independent weeks this log moment multiplies by h. Thus every finite
positive or negative exponential moment of each linear log exposure exists.
Finite sums/products of these gross prices (including the specified fixed
property mark/rent/sale policy with deterministic obligations) have the needed
price first/second moments. Log drift is NOT a simple-return expectation;
we retain the shrinkage log-mean assumption and its Jensen effect explicitly.
The moment helper and independent Monte Carlo tests check first, second and
cross-price moments, covariance preservation and repeatability.

The former default exponentiated unbounded Student-t innovations. Its log
variance exists at nu8 but nonzero price exponential moments do not. A finite
simulation mean/covariance does not estimate finite population moments there.
The old law remains named legacy_student_t for archived reproducibility, with
explicit warnings. Existing outputs are not relabelled as mixture results.
The default UI's fat-tail switch now means the finite Gaussian variance
mixture (off selects Gaussian). It no longer offers Student-t under a new name.

No finite-moment claim is made for legacy yield-repricing equations or a
stochastic-liability option until those specific mappings are checked. The
new universe uses direct total-return ETF log prices and deterministic cash.
FX's prior log drift stays zero, which does not imply flat expected spot.

Changing the innovation law changes the exact path fixture. On the100-path
new-universe regression, CLARABEL at step fraction0.95 failed,0.90 failed,
0.99 failed and0.85 returned optimal with maximum residual1.65e-9 in0.13s.
The new serial-aware property calibration and max-path metric changed the fixture again;0.80 returned optimal on100/200 paths; a400-path diagnostic needed0.75, now used, with risk constraints normalized by their budgets (an exact positive scaling). Objective, budgets, residual
acceptance and tolerances are unchanged. This is a numerical line-search
setting, not a risk relaxation. Full tests and matched sample sensitivity
must remain green; solver success on one fixture is not statistical validation.


A second exact centered exponential CARA representation is attempted only
when the logarithmic-cone representation fails validation. Both have the same
minimizer and constraints; a successful retry names its formulation and retains
the first failure. A failed fit is still reported and never averaged silently.
The seeded sensitivity matrix is a numerical regression, not a universal solver
success guarantee. Risk constraints divided by positive budgets are algebraically
equivalent, with zero budgets handled separately.
