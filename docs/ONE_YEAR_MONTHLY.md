# One year and recurring monthly funding

The active default is52 weeks, not13. The old two lump payments have been replaced by an editable placeholder of$250,000 per month for12 months ($3M,3% of the illustrative$100M). This is not client evidence. The monthly schedule and additional one-off batches are separate inputs and add together.

The default first due week is4 and spacing is52/12 weeks. Rounded weeks are4,8,13,17,21,26,30,34,39,43,47,52. These are a weekly approximation, not actual calendar-month dates. First due week, count, amount and spacing are editable. Payments outside the horizon fail explicitly; the model never silently truncates or moves them when the horizon changes. Each payment has a separate CVaR funding constraint. Cumulative earlier payments reduce what is available later, including money-market opportunity cost. Equal-week payments are handled in stable order without reusing cash.

The user chose to keep the W1 radius0.00002 and raise the per-payment shortfall-tail budget to20%. At$250k this means a$50k modeled tail-gap tolerance per payment, not a fee or planned spending. It is a risk assumption, not a recommendation about tolerable real missed payments. The W1 buffer is included inside that budget. A necessary lower-buffer test detects plainly incompatible combinations, without loosening tolerances or changing inputs. The setting remains visible and editable.

## Compute tiers

- Interactive dashboard:100 training /200 validation /300 evaluation scenarios, two independent validation/evaluation seeds, multipliers1/.25 and cash blends1/.5/0. It is labelled INTERACTIVE COARSE. This is for exploring inputs, not full-fidelity scientific evidence.
- Full CLI/config tier:1000/4000/8000 scenarios with the default3/8 seed batches and full calibration grids. An initial one-year run with the old lump payments took73.56 seconds and returned an honest cash fallback. The full new monthly run exceeded a two-minute local execution window before writing results. It is not reported complete.
- A reduced monthly one-year pilot with the approved20% budget and W1 on took8.80 seconds and returned a CLARABEL allocation whose residual checks passed. An optimizer warning on a separate candidate is not suppressed. This single liquid pilot does not estimate worst-case RE-grid runtime.

No52-week grid has been launched. The729-cell plan now varies monthly payout$k (125/250/500), first due week(1/2/4), profile, RE minimum, radius and dependence. Twelve payments and52/12 spacing are fixed. The old payout-ratio/two-batch timing axes are retired. A smaller27-cell option would fix timing/profile/dependence and vary three monthly amounts, three RE minima and three radii. At the single liquid pilot's8.8s, naive serial arithmetic is4min for27 and107min for729, before benchmarks, RE complexity, timeouts or retries. This is not a measured grid ETA. Do not launch either without approval and representative RE timing evidence.

## Views and old evidence

Liquid mean targets and +/-2pp presets remain simple returns over the selected horizon. At52 weeks they refer to one year, not an annualization of a13-week target. The relative equity spread remains0.5pp at the horizon. The RE forward view remains annual price-log drift (illustrative4%); net rent is separate. No preset is an analyst forecast.

The13-week coarse ledger stopped at575/729 computed cells and154 pending, with no recorded errors. It is retained, not mixed with one-year IDs. The earlier9-cell and32-study reference, stored HTML and private lookup Sheet are13-week archives, not current one-year evidence. Current configs define52-week experiments; they have not been run. Previous model code hashes remain in their manifests. Build a new directory when a one-year grid is approved.
