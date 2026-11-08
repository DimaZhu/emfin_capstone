# Final config boundary and disabled stochastic calls

`validate_config` deep copies and validates the fully edited config. It is
used by file loading and by `run` immediately before fitting/drawing/solving,
so UI mutations, CLI and archive/direct calls meet the same boundary. Repeated
recurring-payment expansion is idempotent. Bad final inputs fail before fit.
The registry re-derives FX enablement from the current property/source state;
turning property off or switching away from Singapore clears stale FX evidence.

The formerly optional stochastic-liability option is disabled: a positive
liability_vol fails with an explicit message. Deterministic dated schedules
still work. The previous model tied early calls to terminal equity stress
and used a Gaussian drift correction on a non-Gaussian mixture. It is not
retained as a latent selectable feature under a new label. Any replacement
needs an explicit adapted information process, amount versus timing semantics,
finite moments and user evidence/calibration. This is narrower and safer than
pretending the option was validated because today's default set vol to zero.

Typed frozen config records landed as emfin_v2/contracts.py (Phase 2), and the
unified optimizer/ledger accounting model landed on
refactor-shared-accounting-20261108: one event engine with declared specs
(Phases 1-3) and one provisioning primitive shared by optimizer and judge
(Phase 4). The candidate_scoring='executable_ledger' config key opts into the
EXPERIMENTAL executable-ledger scorer; anything else keeps the provisioning
scoring unchanged. This boundary file otherwise reads as before.
