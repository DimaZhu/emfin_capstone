"""Fix 6 (kept as sensitivity, owner 11:05): upside given up for stricter or
looser loss limits around the owner defaults (40% any-point cap, 15% terminal
loss limit at horizon end), 10y horizon, $250k/month.

Grid over cml_budget x loss_budget. Same frozen draws for every cell: budgets
do not enter fit, draw generation or scenario probabilities, so the cached
h520 validation/final sets are reused exactly. CARA sleeve proportions frozen
from the base study. The far-loose cell (cap 100%, terminal 60%) is the
approximate unconstrained reference - the walk-back still caps the safe share
at 90% and the funding budgets stay intact, so it is 'loosest tested', not
unconstrained.

Answer per cell: chosen safe share, common CARA CE, funding pass. Upside
given up = CE(loosest tested) - CE(cell).
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import S, save, load, sleeve_proportions_with_fit

CMLS = [0.15, 0.25, 0.40, 0.60, 1.00]
LOSSES = [0.05, 0.10, 0.15, 0.25, 0.40, 0.60]


def main():
    r = load('fix6_grid.json')
    r.setdefault('meta', dict(
        label='LABELED SENSITIVITY (owner ask 8 Nov 11:05): constraint tightness. '
              'Not a client risk statement - the client is a placeholder.',
        cmls=CMLS, losses=LOSSES, horizon='10y', payout='$250k/month x120'))
    prop, raw_safe, kind = sleeve_proportions_with_fit('cara')
    r['meta']['sleeve'] = dict(proportions=prop, safe_share_1y=raw_safe, status=kind)
    cells = r.setdefault('cells', {})
    for loss in LOSSES:
        for cml in CMLS:
            key = f'cml{cml:.2f}_loss{loss:.2f}'
            if key in cells:
                print('skip', key, flush=True)
                continue
            c = S.nm_config(cml=cml, loss=loss)
            fit = S.setup(c)
            val, vp, fin, fp = S.get_draws(c, fit, 'h520')
            t0 = time.perf_counter()
            res = S.mix_search(c, val, vp, fin, fp, prop,
                               label=f'grid cell: any-point cap {cml:.0%}, terminal loss limit {loss:.0%}')
            res['seconds'] = time.perf_counter() - t0
            cells[key] = res
            save('fix6_grid.json', r)
            print(key, 'safe=', res.get('chosen_safe'),
                  'CE=%.1fM' % (res.get('common_cara_ledger_ce', 0) / 1e6),
                  'pass=', res.get('final_pass'), flush=True)
    # upside given up vs loosest tested cell that produced a portfolio
    ref_key = f'cml{max(CMLS):.2f}_loss{max(LOSSES):.2f}'
    ref_ce = cells[ref_key]['common_cara_ledger_ce']
    for key, cell in cells.items():
        if cell.get('common_cara_ledger_ce') is not None:
            cell['upside_given_up_vs_loosest'] = ref_ce - cell['common_cara_ledger_ce']
    r['reference_cell'] = ref_key
    save('fix6_grid.json', r)
    print('grid done', flush=True)


if __name__ == '__main__':
    main()
