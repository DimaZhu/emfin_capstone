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

Both abstention treatments (numbers verified by
studies/offline_chained_20261109/analysis.py). Excluding the 9 abstention
folds (n=69) flatters the proposed method: in those quarters 1/N averaged
+1.71% while proposed-as-cash earns -0.75%.

| comparison | excluding abstentions (n=69) | including abstentions as cash (n=78) |
|---|---|---|
| proposed - cash | +0.0098 +/- 0.0031 | +0.0087 +/- 0.0027 |
| proposed - 1/N | -0.0053 +/- 0.0049 | -0.0075 +/- 0.0045 |
| proposed - min_var | +0.0082 +/- 0.0027 | +0.0071 +/- 0.0024 |
| proposed - shrunk_MV | +0.0010 +/- 0.0016 | -0.0003 +/- 0.0018 |

## Solver health: 105 solves, kinds {'optimized': 64, 'verified pointwise fixed-holdings fallback': 14, 'incompatible risk settings': 27}, median 878.13s, multipliers used [0.1, 0.25, 0.5, 1.0]
Folds where no proposed allocation passed: [7, 9, 41, 43, 49, 62, 63, 68, 69]
Proposed wealth relative counting abstention folds as cash: 1.073 (headline 1.149 skips those folds).

## Caveats

- Folds are solved at stationary reference wealth ($100M / $10M risk tolerance);
  wealth relatives compound offline. The chained-wealth question is answered
  offline from these fold records in studies/offline_chained_20261109
  (chaining + stationary bootstrap; the full chained re-solve exists on branch
  paper-chained-20261109 but is deferred: proposed wealth stays within
  [99.0, 112.2]M offline, so its wealth-scaled risk tolerance barely moves
  and decisions would barely change).
- The registry cash account is a 0%-yield uncalibrated placeholder
  (configs/assets.json). "Beats cash" is therefore near-trivial (real T-bills
  paid 0-5% over the sample; a committed DGS3MO-based bill roll exists at
  resources/data/actual_etfs/tbill-total-return.csv), and min_var loads on
  that same 0% cash (terminal 0.628x vs cash 0.556x), so the cash and min_var
  comparisons are nearly the same comparison, not two independent wins.
- min_var and shrunk_MV are computed on the proposed model's fitted scenario
  moments (same past-only information set), not on sample moments of past
  returns; min_var is not the classic sample-covariance benchmark.
- Realized marks apply liquidity haircuts to the full notional every fold
  (gross*(1-haircut)), not per unit traded: a uniform cost convention equal
  across methods, but harsher on low-turnover baselines (1/N turnover 0.05)
  relative to a turnover-based cost model than on the proposed method (0.65).
- 78 folds bound what can be said: paired differences are descriptive, no
  significance claims. Early folds have ~2 years of training data; the first
  abstention (2008-12-12) is plausibly an artifact of that.
- Property marks: quarterly URA index, 45-day release lag; engine rent/sale
  conventions. No weekly property tails are observed or claimed.
- Cash account is the registry fixed-rate account in both model and realized
  paths (identical-investable-assets rule).

Figures: figs/wealth_relative.png, figs/funding_shortfalls.png, figs/window_returns.png
