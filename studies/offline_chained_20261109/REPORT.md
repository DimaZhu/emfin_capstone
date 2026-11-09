# Offline chained-wealth analysis (2007-2026), no new solves

Answers the chained-wealth question from the reference-wealth study's own fold
records, at zero solver cost: what happens when each method compounds its own
wealth from $100M against the ABSOLUTE payout schedule (3 x $250k per fold).
Commissioned after the 9 Nov 2026 design review of the full chained-wealth
re-solve study (studies/backtest_chained_20261109); owner approval "Ok. Go!"
(WhatsApp 9 Nov 2026 10:30 +08). Method and all numbers: analysis.py
(deterministic, seed 20261109). Figure: figs/offline_chained.png.

## Why this substitutes for the full chained re-solve (for now)

The full chained study re-solves every fold at the method's compounded wealth
(risk_tolerance = 10% of current wealth vs the fixed $10M of the reference
study). That state-dependence only changes decisions if wealth moves far from
$100M. Offline chaining of the realized path shows the proposed method's
wealth stays inside [99.0, 112.2]M: its risk tolerance would wander only
~$9.9-11.2M vs $10M, the same 9 folds would abstain at nearly the same
wealth, and decisions would barely move. The methods whose payout ratio does
rise (cash to 1.8%/fold, min_var to 1.5%/fold) never re-solve - only their
ledgers pay - so no decision changes there either. The full run is deferred;
it remains on branch paper-chained-20261109 as an end-to-end robustness
exhibit, with the review fixes applied.

## Headline: offline chained wealth, realized path 2007-2026

| method | terminal | min wealth | max payout ratio per fold |
|---|---|---|---|
| proposed | 1.122x ($112.2M) | $99.0M | 0.76% |
| cash | 0.415x ($41.5M) | $41.5M | 1.81% |
| 1/N | 2.154x ($215.4M) | $89.6M | 0.84% |
| min_var | 0.516x ($51.6M) | $51.6M | 1.45% |
| shrunk_MV | 1.217x ($121.7M) | $98.6M | 0.76% |

Decomposition: per-fold realized window return + 0.75% reference payout drag =
gross asset return; re-chained as W <- W*(1+g) - $750k. Payouts land in weeks
4/8/13; the add-back treats them as fold-end (error ~0.002%/fold). Abstention
folds earn the 0% registry cash account (conservative; the T-bill fallback is
implemented on the chained branch but not retrofitted here).

## Stationary bootstrap of chained terminal wealth

5,000 resampled 78-fold sequences (Politis & Romano 1994 stationary bootstrap,
geometric block lengths, mean 4 folds = 1 year; fold indices resampled
jointly across methods to keep cross-method dependence), each chained with
absolute payouts. Terminal wealth relative to $100M:

| method | q05 | q50 | q95 | P(min wealth < 0.75x) |
|---|---|---|---|---|
| proposed | 0.649 | 1.096 | 1.780 | 0.17 |
| cash | 0.415 | 0.415 | 0.415 | 1.00 |
| 1/N | 0.973 | 2.148 | 4.403 | 0.09 |
| min_var | 0.440 | 0.506 | 0.586 | 1.00 |
| shrunk_MV | 0.660 | 1.152 | 1.830 | 0.14 |

P(proposed terminal exceeds), over the 5,000 sequences: cash 99.8%, min_var
99.6%, shrunk_MV 41.7%, 1/N 3.6%.

Reading: "1/N compounds higher" is robust across resampled histories, not an
artifact of the 2022-2026 run-up; vs shrunk MV the compounding contest is a
coin flip; vs idle cash and naive variance-minimization the engine wins
near-certainly. The engine's edge is not terminal wealth; it is drawdown
control (worst fold -7.1% vs 1/N's -14.1%) and payout funding (0 unpaid in
all 78 folds for every method - the 0.75%/fold = 3%/yr payout rate never
stresses any method, chained or not).

## Paired per-fold differences vs proposed, BOTH abstention treatments

The reference report excludes the 9 abstention folds from paired stats (n=69).
That exclusion flatters the proposed method: in those quarters 1/N averaged
+1.71% while proposed-as-cash earns -0.75%. Both conditionings, descriptive
SEs only:

| comparison | excluding abstentions (n=69) | including as cash (n=78) |
|---|---|---|
| proposed - cash | +0.983% +/- 0.305 | +0.869% +/- 0.272 |
| proposed - 1/N | -0.528% +/- 0.488 | -0.751% +/- 0.449 |
| proposed - min_var | +0.816% +/- 0.274 | +0.712% +/- 0.245 |
| proposed - shrunk_MV | +0.096% +/- 0.162 | -0.035% +/- 0.182 |

Abstention folds (decision dates): 2008-12-12, 2009-06-12, 2017-06-02,
2017-12-01, 2019-05-31, 2022-08-26, 2022-11-25, 2024-02-23, 2024-05-24.

## Caveats

- Abstentions earn 0% here; with the T-bill fallback (chained branch) the
  abstention cost would be smaller, narrowing the abstention-inclusive gap
  vs 1/N somewhat (2022-24 bills paid ~5%). Direction: favors proposed.
- No state-dependent re-solving (shown above to be a small effect here).
- 78 quarters bound tail coverage; bootstrap sequences are resamples of ONE
  realized history (2007-2026, US-heavy), not new histories. Descriptive
  only; no significance claims.
- All reference-study caveats carry over (0% cash account, model-fitted
  covariance for min_var, full-notional haircut convention, property at
  quarterly URA index granularity, Yahoo-sourced histories private use).
