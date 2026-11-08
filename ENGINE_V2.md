# Current engine documentation

See [docs/ENGINE_V2.md](docs/ENGINE_V2.md) for the current default, corrections and limits.
Older multi-period figures are withdrawn following the cumulative payout-accounting correction.

### Dynamic execution and rebalancing research (7 November 2026)
The companion now contains a frozen 1/3/5-year frequency comparison, not a live
policy optimizer. See `docs/research/dynamic-policy-20261107/report.md` and the
five-page PDF under `docs/evidence/dynamic-policy-20261107/`.
Annual leads the tested CE rankings, but no frequency is accepted across all
four validation laws over 3/5years under unchanged loss budgets. Bounded dynamic
feedback search has no global certificate and the exploratory robust extension
found no validation candidate. No defaults change. Selection locks, failures,
source notes, 368-test regression and installed-wheel smoke are preserved.

### Unified accounting (8 November 2026, refactor branch)
There is one accounting engine: `emfin_v2.event_ledger.run_event_ledger`, driven
by declared `LedgerSpec`s (liquidation, fees, settlement lag, arrears, property
receipts, decision calendar, target rules). `ledger.cash_first` and every
`dynamic_policy.execute` mode are thin wrappers over it; the inline twin loops
are deleted. Money-market provisioning is one primitive in `emfin_v2.contracts`
used by the optimizer, the judge and the toolbox; the residual
provisioning-vs-execution difference is exactly trading vs no-trading,
quantified in `docs/REFACTOR_PHASE4_GAP.md` (zero for cash-covering mixes).
Golden fixtures pin every accounting bit-for-bit; the executable-ledger
candidate scorer exists but is EXPERIMENTAL and off by default.
