"""Multi-Period (Sequential) Entropy Pooling - Kristensen & Vorobets (2026).

Implemented from the public article "Multi-Period Entropy Pooling"
(antonvorobets.substack.com/p/multi-period-entropy-pooling, first version
Oct 5 2026).  No code from the GPL-3.0 fortitudo.tech package is used; the
EP/SeqEP primitives are this repo's own toolbox modules.

The article's construction: the market is Monte Carlo PATHS
R in R^{S x I x H} with a probability vector p over paths; views carry a
horizon subscript h, e.g. a mean view on instrument i at horizon h is
E_q[R_{.,i,h}] = mu.  Because every such view is linear in the path
probabilities, MPEP reduces to one-period SeqEP on the stacked
S x (I*H) matrix of per-horizon marginals, with fixed parameters (means,
vols) pinned ONLY at each view's own horizon (article Section 3).  Views
keep their one-period parameter classes (means/ranks/ML in C0, vols in
C1, ..., CML in V-bar).

Maximum Loss and Conditional Maximum Loss views (article Section 3.2):
L_s(i) = max_h max(0, -(R_{s,i,h} - R_{s,i,0})) is the worst drawdown of
instrument i along path s.  An alpha-ML view caps the probability mass on
paths whose L exceeds v_ML at 1 - alpha (a static indicator constraint,
class C0 like VaR).  An alpha-CML view adds (L . a)' q >= (1 - alpha) v_CML
with a the top-l loss indicator and a' q = 1 - alpha; the count l of tail
paths is not known in advance.  The article resolves l with a proprietary
algorithm; we substitute our OWN coarse-to-fine search over l that
minimizes the posterior relative entropy (documented here, not derived
from any licensed source).

The payoff for the engine: the posterior is a probability vector over
PATHS, so it feeds path-dependent optimization (our multi-period
liability-aware solver, whose per-date funding-gap constraints are
path-based tail constraints) directly - the "CML unified" pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from emfin_capstone.toolbox import entropy_pooling as ep
from emfin_capstone.toolbox import seqep

CML_LEVEL = 99  # V-bar: processed together with all views in the final pass


@dataclass(frozen=True)
class MPView:
    """One multi-period view.

    kind: "mean" | "rank" | "vol" | "ml" | "cml".
    instrument/horizon: 0-based asset and step indices (horizon is ignored
    for "ml"/"cml", which act on the whole path).
    value: view level (mean level, vol, ML loss cap, or CML level).
    sense: "eq" | "ge" | "le".  For "cml", "ge" stresses the tail to be at
    least as bad as value; "le" insists it be no worse.
    alpha: tail level for "ml"/"cml" (e.g. 0.95).
    scale/instrument2/horizon2: for "rank", E[R_i,h] >= scale * E[R_i2,h2].
    """

    kind: str
    instrument: int
    horizon: int = 0
    value: float = 0.0
    sense: str = "eq"
    alpha: float = 0.95
    scale: float = 1.0
    instrument2: int = 0
    horizon2: int = 0
    name: str = ""


@dataclass(frozen=True)
class MPEPResult:
    posterior_probs: np.ndarray
    relative_entropy: float
    ens_ratio: float
    view_names: tuple[str, ...]
    achieved: dict[str, float]  # realized value of each view under the posterior
    cml_tail_counts: dict[str, int] = field(default_factory=dict)  # l per CML view
    heuristic: str = "H1"


def stack_paths(paths: np.ndarray) -> np.ndarray:
    """(S, H, I) value paths -> (S, I*H) matrix; column i*H + h is asset i at step h."""
    p = np.asarray(paths, dtype=float)
    if p.ndim != 3:
        raise ValueError("paths must be (n_scenarios, n_steps, n_assets)")
    s, h, i = p.shape
    return np.ascontiguousarray(p.transpose(0, 2, 1)).reshape(s, i * h)


def max_path_loss(asset_paths: np.ndarray, initial_value: float) -> np.ndarray:
    """L_s = max_h max(0, -(V_{s,h} - V_0)) for one instrument's value paths."""
    v = np.asarray(asset_paths, dtype=float)
    return np.maximum(0.0, -(v - initial_value)).max(axis=1)


def cml_of_paths(losses: np.ndarray, probs: np.ndarray, alpha: float) -> float:
    """Probability-weighted mean of the worst (1 - alpha) path losses."""
    l = np.asarray(losses, dtype=float)
    q = np.asarray(probs, dtype=float)
    order = np.argsort(-l)
    l_sorted, q_sorted = l[order], q[order]
    budget = (1.0 - alpha) * q.sum()
    cum = np.cumsum(q_sorted)
    k = int(np.searchsorted(cum, budget, side="left"))
    if k >= len(l):
        return float((l_sorted * q_sorted).sum() / q_sorted.sum())
    full = float((l_sorted[:k] * q_sorted[:k]).sum())
    rem = budget - float(q_sorted[:k].sum())
    return float((full + rem * l_sorted[k]) / budget)


def _col(instrument: int, horizon: int, n_steps: int) -> int:
    return instrument * n_steps + horizon


def _moment_seq_views(x: np.ndarray, n_steps: int, views: list[MPView]) -> list[seqep.SeqView]:
    """Mean / rank / vol views as class-tagged SeqViews on the stacked matrix."""
    out: list[seqep.SeqView] = []
    for v in views:
        if v.kind == "mean":
            c = _col(v.instrument, v.horizon, n_steps)
            out.append(seqep.SeqView(
                level=0,
                build=lambda params, c=c, v=v: ep.View(
                    features=x[:, [c]], target=[v.value], sense=v.sense,
                    name=v.name or f"E[x_{v.instrument},h={v.horizon}] {v.sense} {v.value}"),
                name=v.name))
        elif v.kind == "rank":
            c1, c2 = _col(v.instrument, v.horizon, n_steps), _col(v.instrument2, v.horizon2, n_steps)
            out.append(seqep.SeqView(
                level=0,
                build=lambda params, c1=c1, c2=c2, v=v: ep.View(
                    features=x[:, [c1]] - v.scale * x[:, [c2]], target=[0.0], sense="ge",
                    name=v.name or "multi-period rank view"),
                name=v.name))
        elif v.kind == "vol":
            c = _col(v.instrument, v.horizon, n_steps)
            out.append(seqep.SeqView(
                level=1,
                build=lambda params, c=c, v=v: ep.volatility_view(
                    x, c, v.value, pin_mean=params[("mean", c)],
                    name=v.name or f"std(x_{v.instrument},h={v.horizon}) = {v.value}"),
                name=v.name))
    return out


def _tail_seq_views(paths: np.ndarray, views: list[MPView], initial_prices: np.ndarray,
                    cml_l: dict[int, int]) -> list[seqep.SeqView]:
    """ML / CML indicator constraints, one SeqView per linear constraint."""
    out: list[seqep.SeqView] = []
    for vi, v in enumerate(views):
        if v.kind not in ("ml", "cml"):
            continue
        losses = max_path_loss(paths[:, :, v.instrument], initial_prices[v.instrument])
        if v.kind == "ml":
            a = (losses >= v.value).astype(float)
            out.append(seqep.SeqView(
                level=0,
                build=lambda params, a=a, v=v: ep.View(
                    features=a.reshape(-1, 1), target=[1.0 - v.alpha], sense=v.sense,
                    name=v.name or f"ML_{v.alpha}(x_{v.instrument}) indicator"),
                name=v.name))
        else:
            if vi not in cml_l:
                raise ValueError("cml view requires a tail count l (run find_cml_tail_count)")
            a = np.zeros(len(losses))
            a[np.argsort(-losses)[: cml_l[vi]]] = 1.0
            out.append(seqep.SeqView(
                level=CML_LEVEL,
                build=lambda params, a=a, v=v: ep.View(
                    features=a.reshape(-1, 1), target=[1.0 - v.alpha], sense="eq",
                    name=v.name or f"CML_{v.alpha} tail mass"),
                name=v.name))
            out.append(seqep.SeqView(
                level=CML_LEVEL,
                build=lambda params, a=a, losses=losses, v=v: ep.View(
                    features=(losses * a).reshape(-1, 1),
                    target=[(1.0 - v.alpha) * v.value], sense=v.sense,
                    name=v.name or f"CML_{v.alpha}(x_{v.instrument}) {v.sense} {v.value}"),
                name=v.name))
    return out


def _solve(paths: np.ndarray, views: list[MPView], prior: np.ndarray, heuristic: str,
           initial_prices: np.ndarray, cml_l: dict[int, int]) -> seqep.SeqEPResult:
    x = stack_paths(paths)
    seq_views = _moment_seq_views(x, paths.shape[1], views)
    seq_views += _tail_seq_views(paths, views, initial_prices, cml_l)
    return seqep.sequential_entropy_pooling(x, seq_views, prior_probs=prior,
                                            heuristic=heuristic, sweeps=1)


def find_cml_tail_count(paths: np.ndarray, views: list[MPView], view_index: int,
                        prior: np.ndarray, initial_prices: np.ndarray,
                        heuristic: str = "H1", n_search: int = 2000) -> int:
    """Coarse-to-fine search for the entropy-minimizing CML tail count l.

    Our own substitute for the article's proprietary algorithm: score
    candidate l values by the posterior relative entropy on a coarse grid
    (computed on a subsample of paths for speed), then refine twice around
    the best grid point.  Returns l on the FULL path set, rescaled from the
    subsample ratio.
    """
    v = views[view_index]
    s = paths.shape[0]
    if s > n_search:
        idx = np.linspace(0, s - 1, n_search).astype(int)
        sub_paths, sub_prior = paths[idx], prior[idx] / prior[idx].sum()
    else:
        sub_paths, sub_prior = paths, prior
    sn = sub_paths.shape[0]
    lo, hi = 2, max(3, min(sn - 1, int(3 * (1 - v.alpha) * sn)))

    def score(l_count: int) -> float:
        return _solve(sub_paths, views, sub_prior, heuristic, initial_prices,
                      {view_index: l_count}).relative_entropy

    grid = np.unique(np.linspace(lo, hi, 7).astype(int))
    best_l = min(((int(l), score(int(l))) for l in grid), key=lambda t: t[1])[0]
    step = max(1, (hi - lo) // 6)
    for _ in range(2):
        cands = [l for l in (best_l - step, best_l + step) if lo <= l <= hi]
        for l in cands:
            if score(l) < score(best_l):
                best_l = l
        step = max(1, step // 3)
    return max(2, int(round(best_l * s / sn)))


def mpep(paths: np.ndarray, views: list[MPView], initial_prices: np.ndarray,
         prior_probs: Optional[np.ndarray] = None, heuristic: str = "H1",
         cml_search: bool = True) -> MPEPResult:
    """Multi-Period (Sequential) Entropy Pooling over scenario paths.

    paths: (S, H, I) value paths; initial_prices: the I current prices the
    paths start from.  Returns posterior path probabilities and the value
    each view actually achieves under them.
    """
    p_arr = np.asarray(paths, dtype=float)
    if p_arr.ndim != 3:
        raise ValueError("paths must be (n_scenarios, n_steps, n_assets)")
    init = np.asarray(initial_prices, dtype=float)
    if init.shape != (p_arr.shape[2],):
        raise ValueError("initial_prices must have one entry per asset")
    s = p_arr.shape[0]
    prior = np.full(s, 1.0 / s) if prior_probs is None else np.asarray(prior_probs, float)
    prior = prior / prior.sum()

    cml_l: dict[int, int] = {}
    if cml_search:
        for vi, v in enumerate(views):
            if v.kind == "cml":
                cml_l[vi] = find_cml_tail_count(p_arr, views, vi, prior, init, heuristic)
    res = _solve(p_arr, views, prior, heuristic, init, cml_l)

    q = res.posterior_probs
    x = stack_paths(p_arr)
    achieved: dict[str, float] = {}
    counts: dict[str, int] = {}
    for vi, v in enumerate(views):
        label = v.name or f"{v.kind}_{v.instrument}"
        if v.kind == "mean":
            achieved[label] = float(x[:, _col(v.instrument, v.horizon, p_arr.shape[1])] @ q)
        elif v.kind == "rank":
            c1 = _col(v.instrument, v.horizon, p_arr.shape[1])
            c2 = _col(v.instrument2, v.horizon2, p_arr.shape[1])
            achieved[label] = float(x[:, c1] @ q - v.scale * (x[:, c2] @ q))
        elif v.kind == "vol":
            col = x[:, _col(v.instrument, v.horizon, p_arr.shape[1])]
            achieved[label] = float(np.sqrt(((col - col @ q) ** 2) @ q))
        elif v.kind in ("ml", "cml"):
            losses = max_path_loss(p_arr[:, :, v.instrument], init[v.instrument])
            achieved[label] = cml_of_paths(losses, q, v.alpha)
            if v.kind == "cml":
                counts[label] = cml_l.get(vi, 0)
    return MPEPResult(posterior_probs=q, relative_entropy=res.relative_entropy,
                      ens_ratio=res.ens_ratio, view_names=tuple(v.name or v.kind for v in views),
                      achieved=achieved, cml_tail_counts=counts, heuristic=heuristic)
