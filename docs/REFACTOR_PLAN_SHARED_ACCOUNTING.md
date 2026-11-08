# Phased plan: one shared accounting engine (review brief P0 items 1-2, P1 item 5)

Owner: Tijs de Boer. Status (8 Nov 2026): plan approved for writing, execution deferred as its own piece.
This is the sequenced plan promised in the round-2 closeout. No code changes are made by this document.

## Why

Four separate accountings currently answer the same economic question, and a
fix to one does not reach the others:

1. **Optimizer accounting (money-market provisioning).** Inside `default_run`
   and `engine`: each future payment is grown at the cash/money-market rate
   and netted against terminal wealth (`provision(...)` one-liners, e.g.
   `default_run.py:488`, mirrored by `study_tbill.provision`). Declared
   convention: "cumulative payouts use money-market opportunity costs, not
   dynamic rebalancing".
2. **Judge accounting** (`emfin_v2/evaluation.py`): funding bounds use
   separate spendable prices; marked property is not spendable cash;
   "current provisioning convention, not a trading ledger".
3. **Executable audit ledger** (`emfin_v2/ledger.py:cash_first`): cash first,
   then pro-rata liquidation at haircut-netted values, immediate within-week
   settlement, arrears at the cash rate. Used by the default run's execution
   audit and by every `studies/*` score (`score_final`).
4. **Policy experiment engine** (`emfin_v2/dynamic_policy.py:execute`): fees,
   one-week settlement queue, softmax feedback / rebalance modes. Plus
   purpose-built twins in studies (`study_tips_charts.simulate`,
   `dynamic_frequency`) because `execute` requires exactly 4 risky sleeves.

Consequences already observed: the optimizer and the judge can disagree about
the same portfolio by convention, not by economics; every new study re-asks
"which ledger am I on"; twins drift (the rebalancing twin has no buy-side
cost); the review brief (P0-1, P0-2) is valid and already labeled in docs.

## Non-goals

- No change to any risk budget, limit, default view, or validated portfolio.
- No change to published numbers: phases preserve or explicitly re-stamp
  frozen evidence; nothing is silently recomputed.
- No global dynamic-programming solver; this is accounting consolidation,
  not a new optimization method.

## Phase 0 - Pin current behavior (about 2-3 hours, zero refactors)

- Golden-path fixtures: for each of the four accountings, freeze 2 small
  deterministic scenarios (one calm, one with a drawn-down equity path and a
  missed payment) with exact expected ledgers as JSON. Tests assert current
  outputs bit-for-bit (tolerance 1e-9).
- Write the canonical **event order** as a doc (`docs/LEDGER_EVENT_ORDER.md`):
  within one week: grow cash/arrears -> credit property receipts -> execute
  declared trades (settle per lag) -> pay due payments (arrears persist) ->
  mark wealth. Every existing accounting is mapped onto this order with its
  deviations named (e.g. judge uses spendable prices; provisioning skips
  trading entirely).
- Exit: golden tests green on the unmodified code; event-order doc reviewed
  against each call site.

## Phase 1 - The shared event engine (about 4-6 hours)

- New module `emfin_v2/event_ledger.py`: one vectorized event engine
  parameterized by a `LedgerSpec` (liquidation rule, fee bps, settlement lag
  weeks, rebalance calendar, property receipts convention, arrears rate).
  `cash_first` becomes `EventLedger(LedgerSpec.cash_first())`;
  `dynamic_policy.execute` modes become other specs.
- Migrate `emfin_v2/ledger.py:cash_first` to a thin wrapper over the engine;
  golden tests from Phase 0 must pass unchanged.
- Property receipts, min/fixed holdings clipping, and the negative-roundoff
  tolerance move into the engine exactly once.
- Exit: cash_first wrapper green; engine unit tests cover ordering,
  arrears, property double-count guard, fee burn, settlement queue.

## Phase 2 - Typed contracts at the boundaries (P1 item 5, about 3-4 hours)

- Introduce immutable dataclasses: `ModelSpec` (law, view, budgets, radius),
  `ScenarioBatch` (prices, amounts, steps, bases, growth + provenance: seed,
  law, draw tag), `LiabilitySchedule`, `PolicySpec`, `Allocation`,
  `LedgerEvent`/`LedgerResult`, `Verdict`.
- Adapters at current call sites so old dicts keep working; new code takes
  contracts only. `ScenarioBatch` carries the provenance fields the run
  manifest hashes (below), so a batch can no longer silently cross seed
  families or laws.
- Validation at construction: shapes, monotonic weeks, nonnegativity,
  sum-to-one allocations, fixed-holding equality.
- Exit: engine + judge + one study run end-to-end on contracts; mypy or
  runtime checks in CI; no behavior change (golden tests still green).

## Phase 3 - Retire the twins (about 3-4 hours)

- `dynamic_policy.execute` re-expressed as `EventLedger` with
  `PolicySpec(feedback softmax | rebalance | cash-first)`; the 4-risky-sleeve
  restriction disappears (the engine is dimension-agnostic).
- `study_tips_charts.simulate` and the frequency study's custom ledger are
  deleted; their published results are re-derived through the engine once,
  on the same seeds, and any numeric deltas are reported, not hidden.
- The judge (`evaluation.evaluate`) keeps its own tail math but sources all
  cash/wealth paths from the engine.
- Exit: studies run without a local simulator; dynamic evidence bundle
  regenerates with stated deltas or bit-equality.

## Phase 4 - Align optimizer and execution accounting (about 4-6 hours)

- Express money-market provisioning as a declared *valuation* of the same
  `LiabilitySchedule` inside the shared module (one function, used by both
  the optimizer's objective and the judge's provisioning convention), so the
  residual difference is exactly one named thing: trading vs no-trading.
- Add an optimizer-facing option to score candidates under the executable
  ledger on training paths (cheap inner approximation), closing the
  producer/judge gap the review brief flagged. Labeled experimental until
  timed; no default change without owner sign-off.
- Exit: one liability module; docs updated; a short note quantifies the
  remaining provisioning-vs-execution gap on the recommended mix.

## Phase 5 - Governance and CI gates (about 2 hours)

- Regression: full suite + golden ledgers + contract validation in CI.
- Every results JSON gains a `manifest` block from `scripts/run_manifest.py`
  (code SHA, config SHA-256, data manifest SHAs, seed family, package
  versions) written automatically by the study harness, not by hand.
- `ENGINE_V2.md` and `CONFIG_BOUNDARY.md` updated to say there is one
  accounting engine with declared specs.

## Sequencing and risk

Phases 0-2 are pure safety and can land in any order; Phase 1 is the keystone
and blocks 3-4. The riskiest step is Phase 3's re-derivation of published
dynamic numbers: it is done once, on frozen seeds, with deltas reported in
the commit message and the evidence bundle README. Total effort estimate
18-25 hours of focused work, best split into sessions of one phase each.
Each phase is independently revertible and leaves the repo greener.

## Relation to the run manifest

The run manifest (`scripts/run_manifest.py`, this branch) is the only item
from the review brief's governance point delivered ahead of this refactor:
it stamps existing evidence bundles with code/config/data hashes now, and
Phase 2's `ScenarioBatch` will carry the same fields so future bundles are
stamped automatically.
