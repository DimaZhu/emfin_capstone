# Next research: historical evaluation and empirical W1 radius

Owner requested these two additions on 7 November 2026. This is the plan, not completed evidence. No private RE/client data will enter git.

## Historical test

Use the pinned public-source liquid-market snapshot and FRED rate/spread series already bundled. First inspect date coverage, adjustment conventions and source metadata. Fit each fold using only dates preceding its decision date. Build non-overlapping 13-week realized paths after that date, carry the same cumulative payout accounting and fixed synthetic bond-pricing convention, and compare proposed, cash, 1/N, minimum variance and shrunk mean-variance under identical investable assets, costs, payout schedule and constraints where applicable. Save every skipped/error fold, training cutoff, test dates, solver status and allocation.

No historical RE result will be invented: omit RE in the main historical experiment because there is no suitable long public property total-return/executable-liquidity series in the bundle. Label bond returns as repriced synthetic exposures driven by observed yield/spread changes, not ETF total returns. A short ETF inception window limits the number of independent folds and crisis coverage. Use earlier public proxies only in a separately labelled robustness exercise after checking current source rights and definitions.

Report realized funding deficits, tail loss with sample counts, terminal surplus/CE, turnover convention and paired differences against benchmarks. Avoid confidence or significance claims unsupported by the number of non-overlapping folds. Keep radius selection and model fitting inside training/validation; never tune after seeing final folds.

## Empirical radius diagnostic

Use exactly the existing L1 ground metric and its path/liability scaling. Estimate train-to-heldout empirical W1 distances on matching normalized feature representations, with linear-transport computation on bounded samples. Select a radius from training-only, dependence-aware block resamples or chronological calibration folds. Freeze it before final testing. Then measure held-out distance inclusion frequency and sensitivity across quantiles, sample sizes and seeds. Store distances, radii, uncovered folds and Monte Carlo error rather than only a chosen number.

This is an empirical finite-sample diagnostic conditional on data and resampling choices. It is not a theorem-backed out-of-sample guarantee, not a familywise guarantee, and not evidence that a simulated scenario model covers unknown real-estate or client risks. Do not advertise 95% coverage merely because the 95th bootstrap percentile was used. Check representation dimension and historical path counts before claiming a stable radius; show instability honestly.

## Integration and gates

Implement on a separate feature branch after the current grid's model fingerprint is frozen. Keep scientific scripts outside the runtime path. Add tests for strict chronological separation, no private imports, same metric in calibration and optimization, deterministic seeds, zero-distance identity, known tiny transport example and explicit insufficient-history failure. Deliver raw tables, provenance, a readable report and inspected figures. Do not replace the dashboard's illustrative default radius until evidence justifies it and its meaning is explained.
