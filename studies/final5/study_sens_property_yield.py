"""Sensitivity: Singapore property forward price-growth view (owner ask 8 Nov
16:25 SGT - 'bring evidence on whether 4% is fair, and how scores move at a
few alternative values'). The 4% forward_log_drift is an editable illustrative
view, not a data estimate (docs/SINGAPORE_REAL_ESTATE.md). This study scores
the frozen round-2 validated 10y mix at alternative views, both carry views,
dual-law judging, same seed family 20261109 and same shock sequences per cell
(deterministic in (config, seed); only the drift changes).

Checkpointed per cell in results/final5_sens_property.json. The owner has NOT
chosen a new value: the default stays 4%; this is decision input only.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common5
from common5 import save, load, f5_config, f5_fit, judge_frozen

R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'final5_sens_property.json'
DRIFTS = [0.00, 0.02, 0.03, 0.04, 0.05, 0.06]
SEED = 20261109


def main():
    r = load(RESULT)
    r.setdefault('meta', dict(
        label=('FINAL-5 property-yield sensitivity (owner ask 8 Nov 16:25 SGT): forward SG '
               'property price-log drift swept %s around the 4%% illustrative view; frozen '
               'round-2 validated 10y mix scored (not re-solved), both carry views, dual-law '
               'judging, seed family %d. Decision input only - default unchanged.' %
               (DRIFTS, SEED)),
        seed_family=SEED, drifts=DRIFTS))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        vent = r.setdefault(view, {})
        frozen = r2[view]['dual']['weights']
        for drift in DRIFTS:
            key = f're{drift:.2f}'
            if key in vent:
                continue
            t0 = time.time()
            c = f5_config(view)
            c['real_estate']['forward_log_drift'] = drift
            fit = f5_fit(c)
            tag = f'f5_h520_{view}_re{int(round(drift * 1000)):03d}'
            primary, fifth = common5.f5_draws(c, fit, tag)
            out = judge_frozen(c, primary, fifth, frozen,
                               label=f'{view} property forward drift {drift:.0%}')
            out['seconds'] = round(time.time() - t0, 1)
            vent[key] = out
            save(RESULT, r)
            print(view, key, 'CE', round(out['common_cara_ledger_ce'] / 1e6, 2),
                  'pass', out['final_pass'], f"({out['seconds']}s)", flush=True)
    save(RESULT, r)


if __name__ == '__main__':
    main()
