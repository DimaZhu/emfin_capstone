"""SeqEP (Vorobets heuristics H1/H2) against the paper's claims."""

import numpy as np

from emfin_v2.toolbox import entropy_pooling as ep
from emfin_v2.toolbox import seqep


def _scenarios(n=4000, seed=11):
    rng = np.random.default_rng(seed)
    return rng.multivariate_normal([0.05, 0.10], [[0.04, 0.01], [0.01, 0.09]], size=n)


def _mean_view(x, j, target):
    return ep.View(features=x[:, j], target=[target], sense="eq", name=f"mean[{j}]")


def _vol_builder(x, j, target_var):
    # variance view linearized by pinning the mean: E[x^2] - mu^2 = target
    def build(params):
        mu = params[("mean", j)]
        return ep.View(features=x[:, j] ** 2, target=[target_var + mu ** 2],
                       sense="eq", name=f"var[{j}]")
    return build


def test_h1_coincides_with_original_when_fully_specified():
    x = _scenarios()
    m0, v0 = 0.06, 0.05
    # original EP with the view-consistent pin (mean fixed at the view value)
    original = ep.joint_entropy_pooling(
        len(x),
        [_mean_view(x, 0, m0),
         ep.View(features=x[:, 0] ** 2, target=[v0 + m0 ** 2], sense="eq", name="var[0]")],
    )
    result = seqep.sequential_entropy_pooling(
        x,
        [seqep.SeqView(level=0, build=lambda p: _mean_view(x, 0, m0), name="mean0"),
         seqep.SeqView(level=1, build=_vol_builder(x, 0, v0), name="var0")],
        heuristic="H1",
    )
    np.testing.assert_allclose(result.posterior_probs, original.posterior_probs, atol=1e-6)


def test_h1_centers_variance_correctly_where_prior_pinning_misses():
    x = _scenarios()
    prior_mean = float(x[:, 0].mean())
    m_view = prior_mean + 0.05  # mean view moves the mean a lot
    v_target = 0.03
    # original heuristic: pin the mean at its PRIOR value
    original = ep.joint_entropy_pooling(
        len(x),
        [_mean_view(x, 0, m_view),
         ep.View(features=x[:, 0] ** 2, target=[v_target + prior_mean ** 2], sense="eq")],
    )
    q_orig = original.posterior_probs
    var_orig = float((x[:, 0] ** 2) @ q_orig - (x[:, 0] @ q_orig) ** 2)
    result = seqep.sequential_entropy_pooling(
        x,
        [seqep.SeqView(level=0, build=lambda p: _mean_view(x, 0, m_view), name="mean0"),
         seqep.SeqView(level=1, build=_vol_builder(x, 0, v_target), name="var0")],
        heuristic="H1",
    )
    q = result.posterior_probs
    var_h1 = float((x[:, 0] ** 2) @ q - (x[:, 0] @ q) ** 2)
    # the paper's point: prior pinning mis-centers the variance view, H1 does not
    assert abs(var_orig - v_target) > 10 * abs(var_h1 - v_target)
    assert abs(var_h1 - v_target) < 1e-6
    assert abs(float(x[:, 0] @ q) - m_view) < 1e-8


def test_rank_and_vol_views_consistent_under_h1():
    # the paper's example the ORIGINAL cannot handle cleanly: rank view on
    # means (asset 0 above asset 1, against the prior ranking) + vol views
    x = _scenarios()  # prior means 5% and 10%
    rank = ep.View(features=x[:, 0] - x[:, 1], target=[0.0], sense="ge", name="rank")
    result = seqep.sequential_entropy_pooling(
        x,
        [seqep.SeqView(level=0, build=lambda p: rank, name="rank"),
         seqep.SeqView(level=1, build=_vol_builder(x, 0, 0.02), name="var0"),
         seqep.SeqView(level=1, build=_vol_builder(x, 1, 0.05), name="var1")],
        heuristic="H1", sweeps=8,  # fixed-point refinement: interacting classes converge
    )
    q = result.posterior_probs
    assert float(x[:, 0] @ q) >= float(x[:, 1] @ q) - 1e-8  # rank holds
    for j, vt in ((0, 0.02), (1, 0.05)):
        var_j = float((x[:, j] ** 2) @ q - (x[:, j] @ q) ** 2)
        assert abs(var_j - vt) < 1e-6  # vols hold around the UPDATED means
    # one sweep (the paper's exact algorithm) leaves a small fixed-point
    # residual here; three sweeps close it
    one = seqep.sequential_entropy_pooling(
        x,
        [seqep.SeqView(level=0, build=lambda p: rank, name="rank"),
         seqep.SeqView(level=1, build=_vol_builder(x, 0, 0.02), name="var0"),
         seqep.SeqView(level=1, build=_vol_builder(x, 1, 0.05), name="var1")],
        heuristic="H1", sweeps=1,
    )
    var1_one = float((x[:, 1] ** 2) @ one.posterior_probs - (x[:, 1] @ one.posterior_probs) ** 2)
    var1_conv = float((x[:, 1] ** 2) @ q - (x[:, 1] @ q) ** 2)
    assert abs(var1_conv - 0.05) < abs(var1_one - 0.05)


def test_h2_close_to_h1_and_diagnostics_consistent():
    x = _scenarios()
    views = [
        seqep.SeqView(level=0, build=lambda p: _mean_view(x, 1, 0.08), name="mean1"),
        seqep.SeqView(level=1, build=_vol_builder(x, 0, 0.05), name="var0"),
    ]
    h1 = seqep.sequential_entropy_pooling(x, views, heuristic="H1")
    h2 = seqep.sequential_entropy_pooling(x, views, heuristic="H2")
    assert abs(h1.relative_entropy - h2.relative_entropy) < 0.05  # paper: minor differences
    np.testing.assert_allclose(h1.ens_ratio, np.exp(-h1.relative_entropy), rtol=1e-12)
    # both satisfy the views
    for res in (h1, h2):
        assert abs(float(x[:, 1] @ res.posterior_probs) - 0.08) < 1e-8
    # per-stage diagnostics recorded (one class pass for C0, one for C1, plus final)
    assert len(h1.stage_relative_entropy) == 3
