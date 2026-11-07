# Coarse new-universe solver diagnosis

Exact100-path52-week baseline, fixed initial10% property, unchanged risk limits.
CLARABEL0.11.1 stopped with InsufficientProgress, not infeasibility or timeout.
SCS was rejected for a0.00443 constraint residual. The fallback was feasible,
not optimized, and is not the result to compare against optimized cases.

The CARA objective used a probability-weighted sum of exponentials. Replacing
it with log(sum(p*exp(-(net-reference)/tau))) changes neither the minimizer
nor any risk/holding constraint: log is strictly increasing. Log-sum-exp puts
the objective on a stable order-one scale. Zero-probability paths are excluded
only from this expectation, not from stress/constraint support. CE reporting
is changed consistently to reference-tau*objective rather than taking log again.

Ablation on identical data, paths and probabilities:

| Formulation | CLARABEL result | Solve time |
| --- | --- | --- |
| Original exponential sum | InsufficientProgress |0.149s |
| Certified funding presolve only | InsufficientProgress |0.041s |
| Log-sum-exp only, all original constraints | optimal |0.306s |
| Log-sum-exp plus certified presolve | optimal |0.123s |

The exact presolve may remove a funding constraint only when a pointwise
minimum portfolio value over the ENTIRE admissible long-only holdings domain,
plus the maximum possible holdings W1 penalty, is within that payment's
original budget. This holds for every scenario weighting, not just a candidate
or a posterior. A certificate records the bound and budget. Constraints that
cannot be certified remain. No candidate-specific guardrail is discarded.

Full coarse baseline after fix:1.03s, optimized, held-out funding passed.
This is timing/numerical evidence, not full-fidelity investment validation.
All economic constraints, probabilities, prices, scenario counts and external
residual acceptance threshold1e-5 remain unchanged. Regression checks compare
against a direct independent one-dimensional CARA optimum and re-evaluate the
original funding/CML/fixed-holding guardrails. An installed-wheel smoke also
solves optimized outside the checkout with independently installed dependencies.
