# Reproduce the preserved study

The protocol was committed at f1b6fd6; original score implementation basis is
4be65c0. Use a separate worktree at that commit, with existing pinned data and
dependencies. Run python -m experiments.model_adequacy pilot, then validation,
then final. Do not use the final outcome to alter selection. The later failure-
retention amendment changes source hashes and intentionally fails the old
selection lock; do not overwrite preserved validation/final files to evade it.

The frozen-study-runner.py is a byte-for-byte copy of that runner for inspection.
When checking source_sha256 use its original experiments/model_adequacy.py path,
not this renamed copy. The hash includes source paths and the emfin_v2 Python
files. Data-manifest hashes and fit/forecast boundary dates are in each stage.
The full experiment inputs remain in the repository at their committed paths.

Development2007 failed the104-row minimum. Its saved original abort and later
unavailable-year record remain visible. No outputs for2007 were invented.
Tail transitions and FHS support audit were added after final results only as
descriptive checks, not selection inputs. The FHS residual support is centered
and normalized: over2014-2025 the absolute mean was below2e-16, variance within
2.3e-15 of1. Thus EWMA-FHS uses the same mean/variance forecasts, different shape.

The renderer regenerates the four-page PDF using the summary file. Source book
PDF/pages are intentionally absent. No data is uploaded by running the study.
