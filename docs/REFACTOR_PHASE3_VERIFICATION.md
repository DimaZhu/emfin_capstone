# Phase 3 verification: dynamic evidence re-derived through the shared engine

8 November 2026, on refactor-shared-accounting-20261108 (c626a6b).

After all seven `dynamic_policy.execute` modes were migrated onto the shared
event engine and the inline twin loop was deleted, the two dynamic studies
were re-run on their frozen seeds:

- `python -m experiments.dynamic_execution` (bounded feedback policy search
  plus independent final evaluation)
- `python -m experiments.dynamic_frequency` (1/3/6/12-month rebalancing
  comparison, validation and final batches)

Method: frozen results restored with `python -m experiments.restore_dynamic_evidence`,
archived aside, studies re-run into the same ignored `artifacts/` tree, JSONs
compared field by field, then the frozen archive restored. A symlink
`/home/sandbox/repo -> /home/sandbox/emfin_capstone` resolved the absolute
data paths recorded in the frozen configs; the bundled market data files are
unchanged.

Result: every published number is bit-identical. `summary.json` from the
frequency study matches the frozen file exactly. The only differences in the
execution outputs are provenance metadata: `code_commit` (the refactor
itself), `source_sha256` (same), `lock_sha256` (cascades from those),
`search_seconds` (wall clock), `history_manifests` paths (the symlinked
checkout location; manifest contents identical), and `protocol_sha256`
(docs/DYNAMIC_POLICY_PROTOCOL.md evolved after the studies were frozen:
fa333da at the execution freeze, 1423f88 at the frequency-freeze commit
e11da19, 7609320 at HEAD after 8dcbda6; no protocol content affecting the
studies changed hands here). Selected policy parameters, validation scores,
final CEs, verdicts, costs and paired comparisons all reproduce exactly,
including the differential-evolution search trajectory.

This complements the golden fixtures (tests/golden/dynamic_*_{calm,stress}.json),
which pin every mode bit-for-bit (rtol 1e-9, atol 1e-12) as captured from the
retired twin loop.
