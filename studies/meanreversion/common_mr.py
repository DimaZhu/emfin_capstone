"""Mean-reversion scenario study (owner ask 8 Nov 2026 ~16:32 SGT, "Yes!" to
the agent's offer of an optional mean-reverting market law scenario).

Compares the headline final-5 results under the research-only
`mixture_mean_reverting` law (shared transitory AR(1) equity fad, Poterba-
Summers style; see emfin_v2/mean_reversion.py) against the frozen iid
mixture base. Judging discipline identical to final-5: primary law (now the
MR law) plus the fhs_ewma fifth law, validation 4x200, final 4x400, same
seed families (20261109 headline, 20261111 seed band) so every MR cell has a
frozen iid comparison cell. The fifth-law draws reuse the exact final-5
cache tags, so the fhs judge draws are byte-identical with the base studies.

Nothing here changes any default or the iid base law.
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'studies' / 'tbill'))
sys.path.insert(0, str(ROOT / 'studies' / 'round2'))
sys.path.insert(0, str(ROOT / 'studies' / 'final5'))

import common5  # noqa: E402
from common5 import S, save, load, f5_fit, dual_mix_search, judge_frozen  # noqa: E402
from emfin_v2.mean_reversion import MODEL, DEFAULT as MR_DEFAULT  # noqa: E402
from emfin_v2.real_estate import ScenarioDraw  # noqa: E402

RESULTS = Path(__file__).resolve().parent / 'results'
RESULTS.mkdir(exist_ok=True)
DRAW_DIR = Path('/tmp/mr_draws')
DRAW_DIR.mkdir(exist_ok=True)

CALIBRATIONS = dict(
    weak=dict(half_life_years=3.0, variance_share=0.20),
    central=dict(MR_DEFAULT),                      # half-life 2.0y, share 0.40
    # 0.60 violates the permanent-covariance PSD guard on the fitted universe; 0.50 is the edge
    strong=dict(half_life_years=1.5, variance_share=0.50))

# seed family -> final-5 draw tag prefix (fifth-law draws shared with base studies)
FIFTH_TAG = {20261109: 'f5', 20261111: 'f5s11'}


def save_mr(name, data):
    (RESULTS / name).write_text(json.dumps(data, default=str, indent=1))


def load_mr(name):
    p = RESULTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def mr_config(view='fitted', seed=20261109, mr='central', **kw):
    c = S.nm_config(**kw)
    c['seed'] = seed
    c['carry_view'] = view
    c['scenario_model'] = MODEL
    c['mean_reversion'] = dict(CALIBRATIONS[mr]) if isinstance(mr, str) else dict(mr)
    c['label'] += (' MEAN-REVERSION SCENARIO (owner ask 8 Nov 16:32 SGT): research-only '
                   'shared equity fad law %s, calibration %s; carry view %s; seed %d; '
                   'dual-law judging (MR + %s). iid base and defaults unchanged.'
                   % (MODEL, c['mean_reversion'], view, seed, common5.FIFTH_LAW))
    from emfin_v2.default_run import validate_config
    return validate_config(c)


def mr_draws(c, fit, tag):
    """Primary (MR law) validation/final splits cached by tag; fifth law shared
    with the base final-5 studies through their original tags."""
    f = DRAW_DIR / f'{tag}.npz'
    val = fin = None
    if f.exists():
        try:
            z = np.load(f, allow_pickle=False)
            val, fin = common5._unpack(z, 'v', 4), common5._unpack(z, 'f', 4)
        except Exception:
            f.unlink()  # interrupted write; regenerate below
    if val is None:
        val = [S.draw_paths(c, fit, 200, c['seed'] + 1000 + j) for j in range(4)]
        fin = [S.draw_paths(c, fit, 400, c['seed'] + 10000 + j) for j in range(4)]
        blob = {}
        common5._pack(val, blob, 'v')
        common5._pack(fin, blob, 'f')
        np.savez(f, **blob)
    vp = [S.probabilities(c, v[0], v.re_price_logs) for v in val]
    fp = [S.probabilities(c, x[0], x.re_price_logs) for x in fin]
    # fifth law: reuse the base study's cache so the fhs judge draws are identical
    weeks = c['horizon_weeks']
    fifth_tag = f'{FIFTH_TAG[c["seed"]]}_h{weeks}_{c["carry_view"]}'
    ff = common5.DRAW_DIR / f'{fifth_tag}_{common5.FIFTH_LAW}.npz'
    if ff.exists():
        z = np.load(ff, allow_pickle=False)
        val2, fin2 = common5._unpack(z, 'v', 4), common5._unpack(z, 'f', 4)
    else:
        cc = copy.deepcopy(c)
        cc['scenario_model'] = common5.FIFTH_LAW
        cc.pop('mean_reversion', None)
        val2 = [S.draw_paths(cc, fit, 200, c['seed'] + 1000 + common5.LAW_OFFSET + j) for j in range(4)]
        fin2 = [S.draw_paths(cc, fit, 400, c['seed'] + 10000 + common5.LAW_OFFSET + j) for j in range(4)]
        blob = {}
        common5._pack(val2, blob, 'v')
        common5._pack(fin2, blob, 'f')
        np.savez(ff, **blob)
    vp2 = [S.probabilities(c, v[0], v.re_price_logs) for v in val2]
    fp2 = [S.probabilities(c, x[0], x.re_price_logs) for x in fin2]
    return (val, vp, fin, fp), (val2, vp2, fin2, fp2)
