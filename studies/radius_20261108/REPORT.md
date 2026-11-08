# Empirical W1 radius diagnostic — results

Owner-approved run (WhatsApp "Yes, a and b", 8 Nov 2026 19:06 +08), item 2 of
docs/NEXT_RESEARCH_PLAN.md. Method: engine's own max_path ground metric and
block construction (emfin_v2.radius_calibration), 21 non-overlapping 52-week
blocks over the committed universe (VTI/VWO/GLD/IEF + cash + SG URA property
marks + SGD/USD), 2005-03 to 2026-02. Chronological split: 14 training blocks
(2005-2018), 7 heldout blocks (2019-2026, includes the 2020 crash).

Raw output: results/radius_diagnostic.json. Script: radius_diagnostic.py.

## Findings

1. **The placeholder radius is decorative.** The config's `wasserstein_radius`
   = 2e-05. The empirical training radii on the engine's own metric are 0.41
   (q50), 0.44 (q75), 0.46 (q90), 0.47 (q95) — roughly **23,000x the
   placeholder**. The default carries no statistical margin; the review's
   "robustness is a budget" claim stands with a concrete price tag.

2. **The empirical radius is materially unstable.** Block-bootstrap (200
   resamples, 3-block runs) of the q90 radius: median 0.42, 5-95% range
   [0.25, 0.57]. Sample-size sensitivity: 0.61 with 8 training blocks, 0.55
   with 11, 0.46 with 14. Half-split seed noise is small (0.451-0.470). So the
   radius is known to about ±25%, not ±2%.

3. **Frozen-radius heldout coverage is encouraging but thin.** All 7 heldout
   blocks lie within even the q50 training radius (nearest-train distances
   0.18-0.36 vs radius 0.41; train→heldout assignment distance 0.25). With a
   denominator of 7, this is suggestive, not a coverage guarantee; no 95%
   coverage claim follows from using the 95th percentile.

## What this means for the paper (judgment, flagged as such)

- Claim 6 ("robustness is a budget") survives with numbers attached: a
  statistically real margin costs ~0.41-0.47 on the max_path scale; the
  unavoidable funding buffer at that radius is far above the per-payment
  budget, so the engine's answer is "unaffordable robustness", not a hidden
  free lunch. That is a result, not an embarrassment.
- The dashboard's illustrative default radius must stay labeled as a
  placeholder; the plan's gate ("do not replace the default until evidence
  justifies it") is not yet met on stability grounds alone.
- Recommended exhibit: radii vs quantile with the bootstrap band, plus the
  heldout nearest-distance scatter against the frozen radius.

## Scope (verbatim from the diagnostic)

Empirical finite-sample diagnostic conditional on data and resampling
choices. Not a theorem-backed out-of-sample or familywise guarantee. Property
marks at quarterly URA index granularity. 21 blocks total; every heldout
frequency has denominator 7.
