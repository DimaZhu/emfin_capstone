# Phase 4 exit note: the remaining provisioning-vs-execution gap

8 November 2026, refactor-shared-accounting-20261108 (37e28e1).

After Phase 4 parts 1-3, both accountings value the same LiabilitySchedule
through one primitive (contracts.money_market_provision /
accumulated_requirement). The residual difference is exactly one named
thing: trading vs no-trading. This note quantifies it.

Method: the frozen dynamic-bundle config and laws (iid_nominal,
bounded_nominal, iid_drift_minus2pp, iid_drift_minus2pp_cov1.2), 4x200
validation paths on the frozen validation seeds (offset 310000), stressed
measures; each candidate scored by metrics() (provisioning) and
metrics_executable() (shared event engine, cash-first ledger). Terminal CE
(CARA, config tolerance) averaged across batches; worst per-payment gap
tail shown alongside.

Findings:

- Recommended mix (the frozen selection: about 76% T-bills, 10% property):
  the gap is EXACTLY ZERO on every law. The ledger never liquidates a risky
  sleeve, so paid-from-cash at the money-market ratio and provisioning at
  the money-market ratio are the same algebra. Same for a bold 10%-cash
  mix (CE +100.0M to +100.7M depending on law, identical under both).
- Forced thin-cash mix (2% T-bills), where the ledger does trade on some
  paths: the CE differs by a few thousand dollars on a $100M portfolio,
  both signs (iid_nominal -$1,001, bounded_nominal -$2,860,
  iid_drift_minus2pp +$1,339, iid_drift_minus2pp_cov1.2 +$3,061; at most
  about 0.003%). Driven by trade timing inside the settlement week and
  haircut costs, which the provisioning convention does not model.
  Per-payment funding gaps stay zero in all these cases (every payment
  funded under both accountings).

Conclusion: for any candidate whose cash sleeve covers the schedule on
nearly every path - which is every candidate the calibration loop has ever
selected - the producer/judge gap vanishes numerically. It appears only
for thin-cash candidates, and even there it is thousandths of a percent of
wealth. The executable-ledger scorer (candidate_scoring=
'executable_ledger') remains EXPERIMENTAL: untimed at production scale and
not a default; no default change without owner sign-off.
