# Book review evidence,7 November2026

Read ../../BOOK_AUDIT.md for the page-referenced findings. The book PDF is not
included or committed. invariance.json records pinned data manifests, config,
clean implementation basis and descriptive raw/EWMA-residual checks. The source
basis is distinct from later documentation/evidence commits; it is not a new
historical-performance backtest. tests-summary.json records the test and
installed-wheel smoke checkpoint. No economic coverage is implied.

Reproduce the raw diagnostics: load the default config, call setup(config),
then inspect config['invariance_evidence']. For residual comparisons, call
filter_ewma(frame.to_numpy()) and diagnose(residuals, list(frame.columns)).
