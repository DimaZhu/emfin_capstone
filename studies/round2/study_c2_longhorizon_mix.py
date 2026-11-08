"""Round 2, item C follow-through: the fresh 10y sleeve through the dual-law
mix search, and the fix-4 sleeve re-judged on genuinely fresh paths.

Owner plan (8 Nov 11:37): re-validate the true 10y sleeve on fresh paths.
Two readings, both answered here:
  fresh_sleeve_dual   sleeve from the fresh n-best 10y solve (study C), put
                      through the round-2 dual-law discipline
  fix4_sleeve_fresh   fix 4's 10y sleeve (old seed family) judged on the fresh
                      validation/final draws - a true out-of-sample re-check
"""
import sys, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common2 import S, save, load, fresh_config, fresh_fit, dual_draws, dual_mix_search


def main():
    r = load('round2_longhorizon_mix.json')
    r.setdefault('meta', dict(label='ROUND 2 STUDY (owner plan 8 Nov 11:37): 10y sleeve mix '
                                    'searches and fresh-path re-validation.'))
    c = fresh_config('fitted')
    fit = fresh_fit(c)
    primary, fifth = dual_draws(c, fit, 'r2_h520')
    fresh = json.loads((Path(__file__).resolve().parent / 'results' / 'round2_longhorizon_fresh.json').read_text())
    fix4 = json.loads(Path('studies/fixes/results/fix4_longhorizon.json').read_text())
    if 'fresh_sleeve_dual' not in r:
        prop = fresh['sleeve_10y_fresh']['proportions']
        t0 = time.perf_counter()
        res = dual_mix_search(c, primary, fifth, prop,
                              label='fresh 10y sleeve (n=%s), dual-law (round 2)' % fresh['sleeve_10y_fresh']['source_n'])
        res['seconds'] = time.perf_counter() - t0
        if 'fifth_law_final' in res:
            res['fifth_law_score'] = res.pop('fifth_law_final')['ce']
        res['sleeve_proportions'] = prop
        r['fresh_sleeve_dual'] = res
        save('round2_longhorizon_mix.json', r)
        print('fresh sleeve dual: safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'fresh_sleeve_single' not in r:
        prop = fresh['sleeve_10y_fresh']['proportions']
        val, vp, fin, fp = primary
        res = S.mix_search(c, val, vp, fin, fp, prop, label='fresh 10y sleeve, single-law reference')
        r['fresh_sleeve_single'] = res
        save('round2_longhorizon_mix.json', r)
        print('fresh sleeve single: safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    if 'fix4_sleeve_fresh_dual' not in r:
        prop = fix4['sleeve_10y']['proportions']
        res = dual_mix_search(c, primary, fifth, prop,
                              label='fix-4 10y sleeve (old seed) on fresh paths, dual-law (round 2)')
        if 'fifth_law_final' in res:
            res['fifth_law_score'] = res.pop('fifth_law_final')['ce']
        res['sleeve_proportions'] = prop
        r['fix4_sleeve_fresh_dual'] = res
        save('round2_longhorizon_mix.json', r)
        print('fix4 sleeve on fresh paths, dual: safe=', res.get('chosen_safe'),
              'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6), flush=True)


if __name__ == '__main__':
    main()
