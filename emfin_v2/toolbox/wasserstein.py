"""Sufficient W1 robust CVaR bounds, not a distributional-coverage claim.

Ground cost is L1 on normalized gross-price paths and normalized cumulative
payout requirements (liability coordinate scale given explicitly). Support is
unrestricted Euclidean space, including economically impossible negative prices.
For each fixed RU threshold, the convex piecewise-affine hinge has Lipschitz
constant equal to the largest dual-norm slope. Its worst expectation equals
empirical expectation + epsilon*L. Minimizing the robust RU upper envelope is
a sufficient bound on worst-case CVaR; no unsupported minimax-equality claim.

Reference: Mohajerin Esfahani & Kuhn, Corollary 5.1 (2018),
https://link.springer.com/article/10.1007/s10107-017-1172-1
No third-party implementation is used.
"""
import numpy as np
import cvxpy as cp


def validate(radius,liability_scale):
    if not np.isfinite(radius) or radius<0 or not np.isfinite(liability_scale) or liability_scale<0:
        raise ValueError('Wasserstein radius and liability coordinate scale must be finite and nonnegative')


def cvx_penalty(weights,radius,confidence,liability_scale=0.,metric='legacy_l1'):
    if metric not in ('legacy_l1','max_path'):raise ValueError('unknown Wasserstein metric')
    validate(radius,liability_scale)
    if not 0<confidence<1:raise ValueError('confidence must be in (0,1)')
    if radius==0:return 0.
    return radius*cp.maximum(cp.norm1(weights) if metric=='max_path' else cp.norm_inf(weights),liability_scale)/(1-confidence)


def penalty(weights,radius,confidence,liability_scale=0.,metric='legacy_l1'):
    if metric not in ('legacy_l1','max_path'):raise ValueError('unknown Wasserstein metric')
    validate(radius,liability_scale)
    if not 0<confidence<1:raise ValueError('confidence must be in (0,1)')
    w=np.asarray(weights,float)
    if not np.isfinite(w).all():raise ValueError('finite weights required')
    return float(radius*max(np.abs(w).sum() if metric=='max_path' else np.abs(w).max(),liability_scale)/(1-confidence))


def ground_distance(price_delta,liability_delta=None,liability_scale=.01,metric='max_path'):
    """Normalized path perturbation cost, no dependence on time-grid count.

    New metric: max absolute price perturbation across sleeves/time PLUS
    max absolute cumulative-requirement perturbation divided by its scale.
    Dual for a single dated funding hinge: max(sum |weights|, scale).
    Duplicate identical sleeves and repeated times do not change this cost.
    """
    p=np.asarray(price_delta,float)
    if not p.size or not np.isfinite(p).all():raise ValueError('finite nonempty price perturbation required')
    if metric!='max_path':raise ValueError('ground_distance implements explicit max_path metric only')
    value=float(np.max(np.abs(p)))
    if liability_delta is not None:
        l=np.asarray(liability_delta,float)
        if not np.isfinite(l).all() or liability_scale<=0:raise ValueError('positive scale and finite liability perturbations required')
        value+=float(np.max(np.abs(l)))/liability_scale
    return value
