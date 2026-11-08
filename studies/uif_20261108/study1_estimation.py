"""UIF item 1 (owner ask 8 Nov 2026 17:09 SGT): estimation uncertainty.

The point estimates behind the model (weekly log drifts and covariance,
Ledoit-Wolf + 156-observation cross-listed-mean shrinkage) are FITTED on one
history. This study re-fits them on circular block-bootstrap resamples of
the weekly return frame (26-week blocks, declared; respects short-horizon
vol clustering better than iid row resampling) and re-runs the full 10y
dual-law safe-share search per refit, same seed family and same RNG streams
(matched streams: differences across refits are parameter uncertainty, not
draw noise). Also re-judges the FROZEN round-2 mix under each refit law.

Outputs per (view, seed family): distribution of the validation-selected and
final-safe share, CE of the searched mix, frozen-mix final-pass fraction,
and per-asset annualized drift/vol ranges. Seed band: families 20261109 and
20261111. 10y owner defaults only (horizon dial unchanged).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_uif as U
from common_uif import S, common5

R2 = Path('studies/round2/results/round2_dual_law.json')
RESULT = 'uif1_estimation.json'
B = 16          # refits per base seed family (1-CPU sandbox budget)
B_BAND = 8      # refits per band seed family (seed-noise check on the band itself)
BLOCK = 26
FROZEN_ON_BAND = False  # frozen-mix re-judge on base families only (compute budget)


def run_cell(c0, fit0, prop, frozen, bidx, tag):
    """One refit: refit law on resampled rows, fresh matched-stream draws,
    dual-law search + frozen-mix judge."""
    c_b, fit_b = U.refit_on_rows(c0, fit0[0], bidx)
    primary, fifth = U.fresh_draws(c_b, fit_b)
    search = U.dual_mix_search_fast(c_b, primary, fifth, prop,
                                label=f'UIF1 refit {tag}, dual-law')
    hold = None
    if frozen is not None:
        hold = common5.judge_frozen(c_b, primary, fifth, frozen,
                                    label=f'UIF1 frozen round-2 mix, refit {tag}')
    mom = U.annual_moments(fit_b)
    return dict(chosen_safe=search.get('chosen_safe'),
                validation_selected_safe=search.get('validation_selected_safe'),
                search_note=search.get('note'),
                ce=search.get('common_cara_ledger_ce'),
                fifth_ce=(search.get('fifth_law_score') or {}).get('common_cara_ledger_ce'),
                frozen_final_pass=None if hold is None else hold['final_pass'],
                frozen_ce=None if hold is None else hold.get('common_cara_ledger_ce'),
                drift=mom['drift'], vol=mom['vol'])


def main():
    r = U.load(RESULT)
    r.setdefault('meta', dict(
        label=('UIF item 1 (owner ask 8 Nov 17:09 SGT): estimation uncertainty on fitted '
               'drift/vol. %d circular block-bootstrap refits (block %d weeks) of the weekly '
               'return frame per (view, seed family); full 10y dual-law safe-share search per '
               'refit on matched RNG streams; frozen round-2 mix re-judged per refit. '
               'Declared: block length 26w; shrinkage re-applied per refit; current_quotes '
               'view re-anchors tbill/treasury/tips means to the same quotes per refit by '
               'design, so its band excludes safe-carry uncertainty.' % (B, BLOCK)),
        B=B, block_weeks=BLOCK, seeds=[U.SEED_BASE, U.SEED_BAND]))
    r2 = json.loads(R2.read_text())
    for view in ('fitted', 'current_quotes'):
        prop = r2[view]['sleeve']['proportions']
        frozen = r2[view]['dual']['weights']
        for seed in (U.SEED_BASE, U.SEED_BAND):
            n_target = B if seed == U.SEED_BASE else B_BAND
            skey = f'seed{seed}'
            vent = r.setdefault(view, {}).setdefault(skey, {})
            if vent.get('cells') and len(vent['cells']) >= n_target:
                continue
            t0 = time.perf_counter()
            c0 = U.uif_config(view=view, seed=seed, weeks=520, months=120)
            fit0 = U.uif_fit(c0)
            T = len(fit0[0])
            boots = U.block_bootstrap_indices(T, B, BLOCK, seed + 4242)
            base = dict(base_moments=U.annual_moments(fit0), T_weeks=T)
            cells = vent.get('cells', [])
            froz = frozen if (seed == U.SEED_BASE or FROZEN_ON_BAND) else None
            for b in range(len(cells), n_target):
                cells.append(run_cell(c0, fit0, prop, froz, boots[b], f'{view}/{seed}/b{b}'))
                if b % 2 == 1:
                    vent['cells'] = cells
                    vent.update(base)
                    r[view][skey] = vent
                    U.save(RESULT, r)
                    print(view, seed, 'refit', b + 1, '/', B, flush=True)
            vent['cells'] = cells
            vent.update(base)
            vent['seconds'] = time.perf_counter() - t0
            r[view][skey] = vent
            U.save(RESULT, r)
            safes = [x['chosen_safe'] for x in cells if x['chosen_safe'] is not None]
            fps = [x['frozen_final_pass'] for x in cells if x['frozen_final_pass'] is not None]
            passes = float(np.mean(fps)) if fps else float('nan')
            print(view, seed, 'safe median %.3f [%.3f, %.3f] n=%d/%d frozen-pass %.2f (%.0fs)'
                  % (np.median(safes), np.min(safes), np.max(safes), len(safes), n_target,
                     passes, vent['seconds']), flush=True)
    U.save(RESULT, r)


if __name__ == '__main__':
    main()
