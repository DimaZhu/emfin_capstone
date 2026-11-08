# UIF studies - 8 Nov 2026 (owner ask 17:09 SGT: items 1, 3, 4)

Branch `research-uncertainty-inflation-fees-20261108` off `engine-sensitivity-20261108`.
Fully additive: no engine-core edits, so this rebases cleanly onto the
refactored accounting engine (refactor-shared-accounting-20261108). What
needs porting after the refactor lands:

- `common_uif.simulate_fees` duplicates the study-level cash-first twin and
  adds the fee layer; the refactored shared engine should instead accept
  `fee_trade` / `fee_aum_annual` parameters in its sale rules, and the fee
  studies re-pointed at it.
- `common_uif.dual_mix_search_fast` is a two-phase scan that returns the
  IDENTICAL first-pass safe share as `common5.dual_mix_search` (verified
  cell-by-cell); port only if search time matters.
- Item 1 uses `registry_runtime.fit_frame` as the refit entry point
  (designed for past-only refits); unchanged by the refactor.
- Item 3 replaces per-path payment amounts inside `ScenarioDraw`; the
  refactor's draw/ledger split should expose this as indexed-liability
  support instead of a study-side wrapper.

Studies (dual-law judging, owner defaults 10y/40%/15%, $250k/month; seeds
20261109 main, 20261111 band):

1. `study1_estimation.py` -> `results/uif1_estimation.json`: 16+8 circular
   block-bootstrap refits (26w blocks) per carry view; full safe-share
   search + frozen-mix judge per refit, matched RNG streams.
3. `study3_inflation.py` -> `results/uif3_inflation.json`: CPI-indexed vs
   nominal payouts; BLS CPI-U model (see data/CPI_SOURCE.md); independent
   RNG stream; tail budgets scale with the expected index.
4. `study4_fees.py` -> `results/uif4_fees.json`: trading-fee tiers
   0/10/25bp + holding fees 0.25/0.50%/yr on the policy dial
   (never/annual/threshold/glide), 10/20/30y; plus holding-fee mean-drag
   searches at 10y. No tax, per the owner instruction.

Report: `ballast-uncertainty-inflation-fees-20261108.pdf` (3 pages) via
`build_uif_pdf.py`. Private research; labeled sensitivities; no default
changes.
