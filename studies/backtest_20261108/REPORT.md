# Walk-forward historical backtest (2007-2026)

First true chronological out-of-sample evaluation of the engine: 78 non-overlapping
13-week folds, decisions 2007-03-16 to 2026-05-22; every fold re-fit strictly on past
data and re-solved at full default scale; realized outcomes accounted through the
engine cash-first ledger with identical assets, haircuts, payouts (3 x $250k per fold)
and constraints. Property included via the URA quarterly index at the fixed 10%
placeholder holding (index granularity; not a tradable weekly property return).

Folds completed: 78 of 78.

## Headline table

| method | wealth relative | annualized | worst fold | folds with unpaid $ | total unpaid $ | mean turnover |
|---|---|---|---|---|---|---|
| proposed | 1.149 | 0.81% | -7.09% | 0 | $0 | 0.65 |
| cash | 0.556 | -2.97% | -0.75% | 0 | $0 | 0.00 |
| 1/N | 1.841 | 3.18% | -14.08% | 0 | $0 | 0.05 |
| min_var | 0.628 | -2.35% | -1.76% | 0 | $0 | 0.03 |
| shrunk_MV | 1.105 | 0.51% | -6.92% | 0 | $0 | 0.10 |

## Paired differences vs proposed (per-fold realized window return)

- proposed minus cash: +0.0098 per fold +/- 0.0031 (descriptive SE), n=69
- proposed minus 1/N: -0.0053 per fold +/- 0.0049 (descriptive SE), n=69
- proposed minus min_var: +0.0082 per fold +/- 0.0027 (descriptive SE), n=69
- proposed minus shrunk_MV: +0.0010 per fold +/- 0.0016 (descriptive SE), n=69

## Solver health: 105 solves, kinds {'optimized': 64, 'verified pointwise fixed-holdings fallback': 14, 'incompatible risk settings': 27}, median 878.13s, multipliers used [0.1, 0.25, 0.5, 1.0]
Folds where no proposed allocation passed: [7, 9, 41, 43, 49, 62, 63, 68, 69]
Proposed wealth relative counting abstention folds as cash: 1.073 (headline 1.149 skips those folds).

## Caveats

- Folds are solved at stationary reference wealth ($100M / $10M risk tolerance);
  wealth relatives compound offline. Chained-wealth re-solving is future work.
- 78 folds bound what can be said: paired differences are descriptive, no
  significance claims. Early folds have ~2 years of training data.
- Property marks: quarterly URA index, 45-day release lag; engine rent/sale
  conventions. No weekly property tails are observed or claimed.
- Cash account is the registry fixed-rate account in both model and realized
  paths (identical-investable-assets rule).

Figures: figs/wealth_relative.png, figs/funding_shortfalls.png, figs/window_returns.png
