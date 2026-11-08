"""Multi-law validation: extra scenario laws in the judge (fifth law).

Owner plan (8 Nov 2026): the regime/bootstrap variant (fhs_ewma, the engine's
declared EWMA filtered historical simulation) joins the judge. Before, every
candidate was judged on independent draws of the one configured scenario law
under reference, nominal, stressed and common-threshold finite posterior-hull
envelopes (four measures). With validation_laws set, independent validation
and final splits are drawn per listed law and a candidate passes only when
every law's judge passes. Extra laws only judge frozen holdings: fitting,
views, solving and selection budgets are unchanged.

The first law is always the config's own scenario_model. Extra laws reuse
the same fit, budgets, seeds family and split sizes; only the scenario law
changes. Per-law seed offsets keep the draws distinct across laws.
"""
import copy

from emfin_v2.default_run import draw_paths, probabilities
from emfin_v2.evaluation import evaluate


def all_laws(c):
    laws = [c['scenario_model']]
    for law in c.get('validation_laws') or []:
        if law not in laws:
            laws.append(law)
    return laws


def validate_laws(c):
    from emfin_v2.innovations import MODELS
    laws = c.get('validation_laws')
    if laws is None:
        return
    if not isinstance(laws, list) or any(not isinstance(law, str) for law in laws):
        raise ValueError('validation_laws must be a list of scenario model names')
    for law in laws:
        if law not in MODELS:
            raise ValueError('validation_laws names an unsupported scenario law: ' + law)
        if law in ('fhs_ewma', 'bounded_ewma_mixture') and not c.get('asset_registry'):
            raise ValueError('conditional-volatility validation laws require the actual-instrument registry adapter')
    if laws and c.get('scenario_archives'):
        raise ValueError('multi-law judging needs generated paths; imported archives carry one law only')


def law_config(c, law):
    cc = copy.deepcopy(c)
    cc['scenario_model'] = law
    return cc


def draw_extra_splits(c, fit, laws, kind, law_offset=500000):
    """Draw validation or evaluation splits for every extra law.

    Returns {law: draws} for laws beyond the primary. Seed offsets mirror
    run()'s scheme (validation +1000+j, evaluation +10000+j) plus a per-law
    offset so no two laws share a seed.
    """
    out = {}
    if kind == 'validation':
        count, seeds, base = c['validation_scenarios'], c['validation_seeds'], 1000
    elif kind == 'evaluation':
        count, seeds, base = c['evaluation_scenarios'], c['evaluation_seeds'], 10000
    else:
        raise ValueError('unknown split kind')
    for k, law in enumerate(laws[1:]):
        cc = law_config(c, law)
        out[law] = [draw_paths(cc, fit, count, c['seed'] + base + law_offset * (k + 1) + j)
                    for j in range(seeds)]
    return out


def measures(c, draws):
    probs = [probabilities(c, d[0], getattr(d, 're_price_logs', None)) for d in draws]
    return [p[0] for p in probs], [p[1] for p in probs]


def evaluate_extra_laws(c, extra_draws, allocation):
    """Judge frozen holdings on every extra law. Pass requires every law."""
    per_law = {}
    for law, draws in extra_draws.items():
        nominal, stress = measures(c, draws)
        per_law[law] = evaluate(c, draws, allocation, nominal, stress)
    return dict(per_law=per_law,
                overall_pass=bool(all(v['overall_pass'] for v in per_law.values())),
                scope='Frozen holdings judged on independent draws of each extra scenario law; '
                      'pass requires every law. Extra laws never fit, solve or repair.')
