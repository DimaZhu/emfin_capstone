"""Assemble every number the 5th-edition report cites from the frozen result
files. Single source of truth: no number is typed into the report text that
is not pulled through here."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent / 'results'
FIX = Path('studies/fixes/results')
TBILL = Path('studies/tbill/results')


def load(p):
    return json.loads(Path(p).read_text())


def assemble():
    tips = load(TBILL / 'study_tips_charts.json')
    base = tips['base']
    fix1 = load(FIX / 'fix1_market_model.json')
    fix2 = load(FIX / 'fix2_radius.json')
    fix3 = load(FIX / 'fix3_real_terms.json')
    fix4 = load(FIX / 'fix4_longhorizon.json')
    fix5 = load(FIX / 'fix5_current_rates.json')
    fix6 = load(FIX / 'fix6_grid.json')
    dual = load(R / 'round2_dual_law.json')
    fresh = load(R / 'round2_longhorizon_fresh.json')
    mix10 = load(R / 'round2_longhorizon_mix.json') if (R / 'round2_longhorizon_mix.json').exists() else {}
    real = load(R / 'round2_real_repricing.json')
    return dict(base=base, sleeve_cara=tips['sleeve_cara'], fix1=fix1, fix2=fix2, fix3=fix3,
                fix4=fix4, fix5=fix5, fix6=fix6, dual=dual, fresh=fresh, mix10=mix10, real=real)


if __name__ == '__main__':
    d = assemble()
    for view in ('fitted', 'current_quotes'):
        v = d['dual'][view]
        print(view, 'sleeve', {k: round(x, 3) for k, x in v['sleeve']['proportions'].items()},
              'raw_safe=%.3f' % v['sleeve']['raw_safe_share'])
        for k in ('single', 'dual'):
            e = v[k]
            print(' ', k, 'safe=', e.get('chosen_safe'), 'CE=%.1fM' % (e.get('common_cara_ledger_ce', 0) / 1e6),
                  'q05=%.1fM' % (e.get('terminal_q05', 0) / 1e6), 'fifthCE=%.1fM' % (e.get('fifth_law_score', {}).get('common_cara_ledger_ce', 0) / 1e6 if isinstance(e.get('fifth_law_score'), dict) else 0))
