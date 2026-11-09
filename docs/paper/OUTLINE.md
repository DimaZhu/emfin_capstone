# Paper skeleton: method paper + labeled synthetic case study

Status: skeleton, 8 Nov 2026. Framing approved by owner (WhatsApp, "Yes, a and
b", 8 Nov 2026 19:06 +08): **method paper with a clearly labeled synthetic
case study, not client advice.** Aligned with docs/PAPER_STRUCTURE.md (one
30-page argument) and the review doc's recommendation.

One-sentence thesis (candidate, to be sharpened after P0 results):

> For an illiquid family balance sheet with hard payout and loss limits, the
> limits — not the utility, the alpha model, or the trading rule — determine
> the portfolio; once estimation uncertainty is priced in, the answer is a
> wide band with a flat cost frontier, so simple static mixes are all the
> data can support.

## Main text (target ~30 pages)

1. **Problem and setting.** Payout obligations, illiquid property, loss
   limits. What is known and what is placeholder (client = placeholder:
   $100M, $250k/month confirmed 12 months, 10y extension a labeled
   assumption; 10% fixed SG property). No real SFO inputs; say so.
2. **Model.** One scenario interface; liability-aware allocation with funding
   and loss constraints; two carry views (fitted / current quotes); five
   judging laws; Wasserstein margin as an explicit budget, not a hidden
   default.
3. **Fair comparison.** 1/N, shrunk MV, reserve rule, dynamic policies,
   clairvoyant bound, on identical inputs under one safety judge; simple
   baselines prominent (supervisor steer).
4. **Results.** Claims 1–4 (see CLAIMS_EVIDENCE_MAP.md), each with its figure
   and its uncertainty band. The synthetic case study is labeled as such in
   every exhibit.
5. **Uncertainty.** Estimation band (claim 5), radius economics (claim 6),
   seed noise and flat frontiers; walk-forward historical results (P0-1) and
   the radius diagnostic (P0-2) land here.
6. **Limits and what real client data would change.** Data-rights statement
   (Yahoo-sourced histories, private use; derived tables/figures only).

## Appendices

Solver details and conditioning; EP/BL/SeqEP variants; sensitivity grids;
regime-law construction; MPEP/CML/DRO variants; data provenance and rights;
the Sobol/antithetic experiments. Anything not supporting claims 1–6.

## Figures (from review doc §4.4; owners and status to be assigned)

1. Two-view mix comparison with scores (+ refit band) — exists, extend.
2. Real vs nominal headline chart — exists.
3. Horizon vs validated safe share, both views, seed-noise band — exists as points.
4. Cost of loss limits: score vs terminal/any-point cap curve — exists.
5. Policy-by-model matrix heatmap — exists as table.
6. Estimation-uncertainty band chart (promote from UIF study to main text).
7. NEW: walk-forward realized funding deficits and paired terminal-wealth
   differences vs benchmarks — from studies/backtest_20261108 (done 9 Nov);
   plus offline chained wealth paths + stationary-bootstrap panel from
   studies/offline_chained_20261109/figs/offline_chained.png.
8. NEW: empirical radius vs placeholder with heldout coverage — from
   studies/radius_20261108 (first results in).

## Writing notes

- Plain words, honest caveats, every featured number with its band; no bare
  point estimates (P0-3 presentation rule).
- Distinguish code validation from client evidence in every section
  (PAPER_STRUCTURE.md rule).
- Property exhibits: marks at quarterly URA index granularity; the backtest's
  property path is index-level, not a tradable weekly property return.
