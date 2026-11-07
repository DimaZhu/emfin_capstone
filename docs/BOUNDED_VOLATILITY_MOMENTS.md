# Finite-horizon moment domain of the capped variance model
Own derivation,7 November 2026. Not a theorem attributed to RiskMetrics.

At a frozen forecast origin, baseline variances s_j^2 and finite log mean mu
are known. h_j,t lies in[.05 s_j^2,9 s_j^2], predictably. Given history and the
weekly mixture state V_t in{.75,3.25}, shocks are centered Gaussian with
covariance D_t R D_t. For any finite real exposure b,

    b' D_t R D_t b <= (sum_j |b_j| sqrt(9 s_j^2))^2 = K(b)<infinity.

This follows from |R_ij|<=1 and does not assume factor independence. Thus

    E[exp(b' r_t)|history] <= exp(b'mu+3.25 K(b)/2)=C(b)<infinity.

Apply the tower property to the NONNEGATIVE exponential product. By induction,
E exp(b' sum_(t=1)^H r_t)<=C(b)^H for every finite H, including52. Same proof
for time-varying deterministic exposures using product C(b_t). Conditional
means are finite/frozen, innovations independent of the current predictable
variance. No independence of accumulated returns is claimed. Exact iid mixture
MGF formulas do not apply and are explicitly rejected for this scenario model.

The property log shock is a fixed finite Gaussian linear loading on the same
static equity Gaussian factor and an independent Gaussian residual, multiplied
by sqrt(V_t). It keeps a bounded conditional variance too. Include it with its
own bound, and include the capped FX factor, in the same Cauchy-Schwarz bound.
Adding local property and FX log returns gives USD property and preserves the
bound. Deterministic cash, finite log drifts, haircuts and no-sale property
receipts do not destroy finite positive moments. This does not turn the
provisioning account into an executable selling policy or bound tail risk.

Return support is UNBOUNDED. The cap is on predictable variance state, not
price/return truncation. Extreme Gaussian-mixture shocks can still occur; the
cap limits their effect on later conditional volatility. That is a deliberate
model change with a possible underestimation of crisis persistence. Existence
of all finite moments is a weak domain requirement, NOT economic calibration.

The bound can be very loose. Floating-point overflow remains possible for
extreme user inputs, despite finite mathematical moments. The generator
rejects nonfinite paths rather than returning a plausible partial result.
CARA of long-only wealth with finite deterministic payouts remains bounded
below by finite liabilities under the modeled positive prices; no claim of
robust exponential utility over an unrestricted W1 ball is introduced.
