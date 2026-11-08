"""MR scenario: payout dial under mean reversion. Mirrors
studies/final5/study_sens_payouts.py ($50k/$100k per month at 10/20/30y,
both views, seed 20261109, radius scaled with payout) with the MR law as
primary; MR price draws shared with mr_horizon.json. Checkpointed per cell."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_mr
from common_mr import S, f5_fit, dual_mix_search, judge_frozen, mr_config, mr_draws, save_mr, load_mr
from emfin_v2.real_estate import ScenarioDraw

YEARS = [10, 20, 30]
PAYOUTS = [50000.0, 100000.0]
R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'mr_sens_payouts.json'


def scaled(splits, scale):
    val, vp, fin, fp = splits
    def sc(ds):
        return [ScenarioDraw((d[0], d[1] * scale, d[2], d[3] * scale, d[4]),
                             d.funding_paths, d.re_price_logs) for d in ds]
    return sc(val), vp, sc(fin), fp


def main():
    r = load_mr(RESULT)
    r.setdefault('meta', dict(
        label=('MR scenario: $50k/$100k per month at 10/20/30y under the MR law (central), '
               'both views, seed 20261109, radius scaled with payout (sec_payout precedent). '
               'Comparison base: final5_sens_payouts.json.'),
        years=YEARS, payouts=PAYOUTS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        prop = r2[view]['sleeve']['proportions']
        frozen = r2[view]['dual']['weights']
        for years in YEARS:
            for monthly in PAYOUTS:
                key = f'{years}y_p{int(monthly / 1000)}k'
                if key in vent:
                    continue
                t0 = time.perf_counter()
                scale = monthly / 250000.0
                # draw with the base 250k config so the shared cache always holds
                # unscaled amounts; judge with the payout config (radius scaled)
                c_draw = mr_config(view=view, seed=20261109, weeks=52 * years,
                                   months=12 * years)
                c = mr_config(view=view, seed=20261109, weeks=52 * years, months=12 * years,
                              payout=monthly, radius_scale=scale)
                fit = f5_fit(c)
                tag = f'mr09_h{52 * years}_{view}'
                primary, fifth = mr_draws(c_draw, fit, tag)
                primary, fifth = scaled(primary, scale), scaled(fifth, scale)
                search = dual_mix_search(c, primary, fifth, prop,
                                         label=f'MR central {view}, {years}y, ${monthly / 1000:.0f}k/month')
                hold = judge_frozen(c, primary, fifth, frozen,
                                    label=f'frozen round-2 {view} mix at {years}y under MR, ${monthly / 1000:.0f}k')
                vent[key] = dict(years=years, monthly=monthly,
                                 total_paid=12 * years * monthly,
                                 search=search, hold_10y_mix=hold,
                                 seconds=time.perf_counter() - t0)
                save_mr(RESULT, r)
                print(view, key, 'safe=', search.get('chosen_safe'),
                      'CE=%.1fM' % (search.get('common_cara_ledger_ce', 0) / 1e6), flush=True)
    save_mr(RESULT, r)


if __name__ == '__main__':
    main()
