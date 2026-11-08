"""Shared helpers for the open-points fix studies (8 Nov 2026).

Owner ask (WhatsApp 8 Nov 11:05, relayed by main): implement fixes for open
points 1-5 of the model review; keep 6 (client inputs) as a sensitivity.

All studies reuse the frozen validation discipline of studies/tbill
(study_tips_charts.py): same seeds, same draw batching (validation 4x200,
final 4x400), same mix search (lowest safe share passing validation, then
one-step-safer walk-back on the independent final judge). Every variant is a
labeled sensitivity; no engine default is changed here.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies' / 'tbill'))

import study_tips_charts as S  # noqa: E402

RESULTS = Path(__file__).resolve().parent / 'results'


def save(name, data):
    import json
    (RESULTS / name).write_text(json.dumps(data, default=str, indent=1))


def load(name):
    import json
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def sleeve_proportions_with_fit(objective, fit_override=None):
    """study_tips_charts.sleeve_proportions with an optional fit transform.

    fit_override(config, fit) -> fit lets a study change the fitted law (e.g.
    current-rate carry) before the 1-year sleeve solve, so the sleeve and the
    10y study see the same market view.
    """
    c = S.nm_config(one_year_sleeve=True, objective=objective)
    fit = S.setup(c)
    if fit_override:
        fit = fit_override(c, fit)
    dr = S.draw_paths(c, fit, 100, c['seed'])
    p, ps = S.probabilities(c, dr[0], dr.re_price_logs)
    raw, status = S.solve(c, dr, p, ps, 1.)
    ids = c['asset_layout']['ids']
    mins, fixed = S.holding_bounds(c, len(ids))
    fixed = {int(k): v for k, v in fixed.items()}
    safe_idx = ids.index('tbill')
    risky = {}
    for i, a in enumerate(ids):
        if i == safe_idx or i in fixed or mins[i] > 0 or a == 'cash':
            continue
        w = float(raw[i] / c['wealth'])
        if w > 1e-6:
            risky[a] = w
    tot = sum(risky.values())
    return ({k: v / tot for k, v in risky.items()}, float(raw[safe_idx] / c['wealth']),
            status.get('kind'))


def full_pipeline(tag, label, fit_override=None, config_kwargs=None, prop=None):
    """fit -> draws -> (optional fresh sleeve) -> mix_search. Returns result dict."""
    c = S.nm_config(**(config_kwargs or {}))
    fit = S.setup(c)
    if fit_override:
        fit = fit_override(c, fit)
    val, vp, fin, fp = S.get_draws(c, fit, tag)
    if prop is None:
        prop, raw_safe, kind = sleeve_proportions_with_fit('cara', fit_override)
    else:
        raw_safe, kind = None, 'frozen sleeve proportions'
    res = S.mix_search(c, val, vp, fin, fp, prop, label=label)
    res['sleeve_proportions'] = prop
    res['sleeve_safe_share_1y'] = raw_safe
    res['sleeve_status'] = kind
    return c, fit, (val, vp, fin, fp), res
