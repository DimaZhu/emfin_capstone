# Why a better one-week GARCH score is not an annual price model

Original mathematical domain check for this project,7 November2026. This is
not a claim that all models called GARCH fail or that one-week forecasts are
undefined. It concerns unbounded Gaussian log innovations with positive ARCH
variance feedback, including the experimental Gaussian-mixture candidate.

Let a zero-mean log-return shock have the recursion

    epsilon_t = sqrt(h_t) z_t, z_t iid N(0,1)
    h_(t+1) = omega + alpha epsilon_t^2 + beta h_t,

with h_1>0,omega>0,alpha>0,beta>=0. Finite starting h_1 implies every fixed
one-step conditional return is Gaussian and has all exponential moments.
The usual alpha+beta<1 condition concerns unconditional second moments of
returns; it does not imply finite moments of exponentiated accumulated returns.

For the three-step price ratio exp(epsilon_1+epsilon_2+epsilon_3), first
condition on epsilon_1 and epsilon_2 and integrate over z_3:

    E[exp(epsilon_3) | epsilon_1,epsilon_2] = exp(h_3/2).

Thus the remaining integrand contains exp(epsilon_2 + alpha epsilon_2^2/2).
Conditional on epsilon_1, epsilon_2 has law N(0,h_2). The integral over
epsilon_2 has a quadratic exponent whose leading coefficient is

    alpha/2 - 1/(2 h_2).

It diverges whenever alpha h_2 >=1. Because alpha>0 and epsilon_1 has
unbounded Gaussian support, h_2 = omega + alpha epsilon_1^2 + beta h_1 is
unbounded. Therefore {alpha h_2 >=1} has positive probability, however small.
The nonnegative expectation of the three-step price ratio is infinite.
Finite log-return drift adds finite deterministic factors and does not cure it.

A finite Gaussian variance mixture still has a positive-probability sequence
of Gaussian components with positive variance scales. Conditioning on that
sequence gives the same argument, with a rescaled positive threshold. A
stationary variance constraint, stable optimizer output or a million finite
simulated paths cannot make this exponential moment finite.

Example: h_1=1,omega=1,alpha=0.1,beta=0.8. At epsilon_1=10,
h_2=11.8 and alpha*h_2=1.18. An open neighborhood of that event is enough
for divergence. These are own mathematical values, not fitted market estimates.

Consequences:
- The new experiments compare only one-week marginal forecasts. No recursive
  GARCH/parametric-EWMA path generator is added to the installed engine.
- Better one-week CRPS/QLIKE and residual diagnostics do not authorize annual
  expected-price, mean-variance or finite-moment utility claims for that model.
- A bounded empirical innovation support at a finite horizon has a different
  moment domain; the existing EWMA-FHS variant is not this unbounded-Gaussian
  counterexample. Neither bounded support nor the iid mixture proves economic
  adequacy, tail coverage or annual funding safety.
- A future conditional annual model needs an explicit defensible domain, such
  as a declared bounded-state/support design, and new joint/horizon validation.
  Do not add a silent cap or truncation and call it the same GARCH model.

Method context: Bollerslev(1986), the GARCH variance recursion and stationarity
conditions, https://public.econ.duke.edu/%7Eboller/Published_Papers/joe_86.pdf .
The exponential-price calculation above is an independent derivation; it is
not attributed as a theorem copied from that paper.
