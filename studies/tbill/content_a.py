"""4th-edition content: cover + sections 1-10 (carried from the 3rd edition,
with 4th-edition edits marked in-line where they change a fact)."""

SHORT_VERSION = [
    "The engine is careful and honest. Every candidate is checked on fresh simulated futures it never saw "
    "during selection, under four different market laws, and a separate cash-first ledger counts whether "
    "every payment was actually made.",
    "At your confirmed $250k/month, the safe answer is still boring, but no longer idle. The validated mix "
    "now holds about 75% three-month Treasury bills earning a real yield instead of cash at a placeholder "
    "0%. Same safety, better score: +$1.73M a year on the fitted data, +$3.60M at current bill rates.",
    "Clever has not beaten simple. Across 19 years of real history and thousands of simulated futures, no "
    "objective formula, forecast model, trading rule or rebalancing schedule beat the plain fixed mix once "
    "safety was enforced.",
    "Rebalance rarely. Annual rebalancing scores best of the four frequencies tested at 1, 3 and 5 years. "
    "At one year that literally means: set the mix once, then do not trade.",
    "\"Passed\" never meant \"every payment guaranteed\". The setup knowingly tolerates a small shortfall "
    "allowance per payment; the strict 99% all-payments check and the execution audit are the lines to "
    "read for the guarantee question.",
    "The real open risks are the market model, not the objectives. Markets cluster calm and stormy weeks "
    "and the default law does not; the model-risk margin is uncalibrated and honestly reported as such.",
    "The loss limits are development defaults, not your choices. The 6% any-point loss cap and the 15% "
    "final-loss cap were set when the engine was packaged on 7 November; there is no record you chose "
    "them. Only the 6% cap actually binds. What you chose is the 20% per-payment allowance, the monthly "
    "amount and the horizon.",
    "Payments are not the reason the portfolio is safe-heavy. At every tested mix the payment checks "
    "pass; the whole-portfolio loss caps set the safe share. Section 22 shows the dial-by-dial proof.",
    "Over 10-30 years every tested mix pays every bill, and growth-heavier mixes end 2-5 times richer - "
    "but they fail the one-year loss caps, which forbid the drawdowns equities inevitably take over "
    "decades. Accounting for the long run properly means horizon-scaled loss budgets, not a bigger cash "
    "pile (section 23).",
    "The model survived an inside-out audit. Every module was re-read, eleven independent numerical "
    "tests pass, and the one soft spot - a flat optimum where any cash share between 62% and 90% is "
    "about equally good - is reported openly rather than tuned away.",
]

CONTENTS = ("Inside: 1. The question - 2. How it works - 3-4. Does the market model fit - 5. Benchmarking - "
            "6. Backtest - 7. Utility comparison - 8. Model-wrongness margin - 9. Dynamic trading - "
            "10. Rebalancing frequency - 11. Why so much cash (now answered with a real T-bill asset) - "
            "12. Payout sensitivities - 13. Portfolios at $50k/$100k/$250k - 14. View sensitivities - "
            "15. \"Passed\" vs \"paid\" - 16. Inside-out checks - 17. Every dial - 18. Outside literature - "
            "19. Open items - 20. Verdict - 21. The T-bill asset (new) - 22. The loss limits, plainly (new) - "
            "23. Longer horizons (new) - Appendices A-C")

SECTIONS_1_10 = [
    ('h1', '1. The question'),
    ('p', "You want to pay out $250,000 every month from a large investment balance sheet, without being "
          "forced to sell investments at a bad time. The engine answers one question: which mix of assets "
          "gives the best risk-adjusted outcome while keeping the chance of missing a payment small?"),
    ('p', "Everything was tested on one working example. Only the monthly amount is confirmed by you; "
          "the rest is a clearly labelled research assumption, not your real balance sheet."),
    ('table',
     ['Input', 'Value used', 'Status'],
     [['Total wealth', '$100M', 'illustrative'],
      ['Payments', '$250k per month, 12 months ($3M, 3% of wealth)', 'confirmed by you'],
      ['Property', '10% of wealth, Singapore residential (URA index), not sold, no rent assumed', 'assumption'],
      ['Liquid assets', 'VTI (US stocks), VWO (emerging markets), GLD (gold), IEF (7-10y US Treasuries), '
       'plus a 3-month Treasury bill roll added in this 4th edition; 0% cash account retained',
       'real funds, real histories'],
      ['Reporting', 'US dollars, with SGD/USD currency risk modeled', 'assumption'],
      ['Safety limits', 'per-payment tail shortfall at most 20% of the payment at 95% confidence; limits on '
       'final loss and worst-path loss; no borrowing; long only', 'chosen limits, editable']],
     [0.16, 0.60, 0.24]),
    ('note', "The one-year working example. Three- and five-year versions ($9M and $15M of payments) were "
             "tested as sensitivities, not because longer obligations are confirmed; the new section 23 looks "
             "at 10-30 years."),
    ('p', "Two terms used throughout: the score of a plan is its certainty equivalent: the guaranteed dollar "
          "amount, after making all planned payments, that the model considers exactly as good as running "
          "the risky plan. Higher is better. A market law is one complete set of assumptions about how "
          "prices move; final checks run under four different laws so that no answer depends on a single "
          "guess about the future."),

    ('h1', '2. How the engine works, in plain words'),
    ('note', "The six parts. Data in, verdict out. The optimizer never sees the paths it is judged on."),
    ('bullets', [
        "Inputs. Wealth, the payment calendar, risk limits and current holdings, including the property "
        "that stays unsold.",
        "Estimation. Real weekly total-return histories for the four funds (2005-2026), the quarterly URA "
        "property index and the Fed's SGD/USD series, plus the FRED 3-month Treasury bill rate series "
        "(1981-2026) added in this edition. Averages and correlations are shrunk toward safe values "
        "because raw estimates are noisy.",
        "Scenarios. Thousands of simulated 52-week futures for all assets at once, including occasional "
        "bad weeks (a two-state Gaussian mixture, 90/10 probability, variance 0.75x/3.25x).",
        "Optimizer. Picks the long-only mix with the best score subject to every funding and loss limit, "
        "using cumulative provisioning for the payments.",
        "Independent judge. The frozen mix is re-checked on entirely fresh paths, under four market laws, "
        "against every limit: each payment, final loss, worst-path loss, holdings. A fail is reported, "
        "never repaired by retuning.",
        "Execution audit. A separate cash-first ledger simulates actually paying: cash first, then "
        "proportional sales, with arrears tracked. It answers the only question that matters in practice: "
        "was every payment actually made?",
    ]),
    ('table',
     ['Law', 'What it assumes', 'Plain meaning'],
     [['A. Baseline', 'Gaussian weekly mixture fitted to history; weeks independent', 'the model as designed'],
      ['B. Capped-vol', 'Like A, but volatility follows recent data, capped at 3x normal', 'calm and stormy regimes exist'],
      ['C. Lower returns', 'Like A, with expected returns 2 percentage points lower per year', 'the future is worse than the fit'],
      ['D. Lower + jumpier', 'Law C plus 20% larger covariance', 'worse and wilder']],
     [0.18, 0.52, 0.30]),
    ('p', "A candidate that only passes the law it was designed on is not accepted. These four are fixed "
          "diagnostics, not a complete map of everything that could happen."),
    ('p', "368 automated tests pass, including independent re-implementations of the math. The dashboard "
          "is a coarse preview (100-300 paths); every number in this report comes from the larger frozen "
          "studies."),

    ('h1', '3. Does the market model match reality?'),
    ('p', "Your copy of Meucci's Risk and Asset Allocation (2005) was used as the audit standard. The "
          "audit fixed four concrete errors in the engine (an interpolated-quantile bug, a crash with a "
          "single stochastic asset, stale documentation, and an overclaimed formula). More importantly, it "
          "exposed that the basic checks the book demands before assuming independent weeks had never "
          "been run. This section is those checks."),
    ('p', "Weekly returns have no memory of direction, but volatility has memory. Last week's return tells "
          "you almost nothing about this week's direction (correlations between -0.07 and +0.02). But last "
          "week's squared return does predict this week's squared return (correlations up to 0.34): calm "
          "weeks follow calm weeks, storms follow storms. The default law treats every week as "
          "independent, so it cannot produce clusters of bad weeks."),
    ('note', "3rd-edition chart, summarized in text: correlation of each series with its own previous week, "
             "2005-2026 (1,129 weeks). Return correlations are near zero; squared-return correlations are "
             "tall (up to 0.34) - that is volatility clustering, which the default model omits."),
    ('bullets', [
        "Equities are also left-skewed and fat-tailed in the data (VTI sample skewness -0.99, excess "
        "kurtosis 9.1). The default mixture is symmetric with excess kurtosis 1.69: milder tails than "
        "history.",
        "A history-bootstrap variant (EWMA-FHS) reduces the clustering in its residuals to about "
        "0.10-0.12, but that is not zero and not proof it is better.",
        "These are descriptive facts about 21 years, not guarantees about the next one.",
    ]),

    ('h1', '4. The forecast-model contest'),
    ('p', "If the default law misses volatility clustering, would a conditional-volatility model do better? "
          "Four models were committed in advance, fit on the past only, and scored on one-week-ahead "
          "distribution forecasts for 2019-2025. The selection was locked on 2014-2018 data before the "
          "final scoring. This is a forecasting contest, not a portfolio result."),
    ('note', "Result from the frozen study: the default mixture and the history bootstrap are "
             "statistically tied for best; no candidate handled a real crisis as advertised (2008-style "
             "crash weeks: default mixture 21.5% worse than expected, GARCH 13.9%, history bootstrap "
             "8.9% better - no model is a shield)."),

    ('h1', '5. Benchmarking: clever vs simple'),
    ('p', "Three portfolio recipes were compared on identical inputs: equal weights (1/N, the simplest "
          "possible), shrunk mean-variance (the classic textbook optimizer with noise control) and the "
          "funding-aware optimizer (the engine's own, maximizing the after-payments score under every "
          "risk limit). A fourth row is the cash-heavy blend that validation actually selected. All were "
          "frozen, then judged on 1,600 fresh final paths."),
    ('table',
     ['Recipe', 'Score ($M)', 'Every payment funded?', 'Passes ALL risk checks?'],
     [['Equal weights (1/N)', '100.13', 'Yes (1,600/1,600 paths)', 'No - worst-path loss'],
      ['Shrunk mean-variance', '101.81', 'Yes', 'No - worst-path loss'],
      ['Funding-aware optimizer (raw)', '100.11', 'Yes', 'No - worst-path loss'],
      ['Validated cash-heavy blend', '97.46', 'Yes', 'Yes']],
     [0.34, 0.12, 0.28, 0.26]),
    ('note', "Strict-funding study, baseline law, 1,600 fresh final paths. The highest score belongs to a "
             "portfolio that fails the declared safety checks. The blend that passes gives up about "
             "$2.6-4.4M of score: that gap is the price of the safety limits."),
    ('p', "The confirmed plan's validated blend (25% of the optimizer's mix, 75% of the cash/property "
          "anchor) looked like this in the 3rd edition: 76% cash at a placeholder 0%, 9% Treasuries, 5% US "
          "stocks, 10% property. In this 4th edition the same machinery, given a real Treasury bill asset, "
          "selects 75% bills instead (section 21): the blend is 50% of the optimizer's mix, 50% of the new "
          "bill-heavy anchor."),
    ('bullets', [
        "The funding-aware optimizer does not beat shrunk mean-variance on raw score. Its value is that "
        "it optimizes under the funding constraints directly, not that it found a higher-return mix.",
        "Every raw (fully invested) candidate fails the final worst-path-loss check. Only blends with a "
        "large safe anchor pass. Safety, not score, is the binding constraint at these limits.",
        "Mean-variance and CARA scores are close on average, but a constructed test case proves they "
        "can rank plans differently; closeness on these studies is not a proof they are the same "
        "preference.",
    ]),

    ('h1', '6. The historical backtest: 19 real years'),
    ('p', "The only historical evidence in the project: 19 non-overlapping one-year episodes, 2007-2025, "
          "on the real fund, currency and property histories, including 2008, 2020 and 2022. Parameters "
          "were refit 152 times using only data available at each refit date; all 152 refits succeeded. "
          "Everything else in this report uses simulated futures, which are model-driven and are not "
          "historical out-of-sample proof."),
    ('table',
     ['Comparison over the 19 episodes', 'Avg difference in final wealth', 'Honest reading'],
     [['Matched mean-variance vs the CARA engine', '+0.20 percentage points per year',
       'uncertainty interval touches zero: not significant'],
      ['History bootstrap (FHS) vs the default mixture', '-0.02 pp', 'nothing there'],
      ['Refit-and-average (bagging)', '-0.12 pp', 'but a milder worst episode'],
      ['Capped-vol model vs default (same episodes)', 'mixed: 52-week score 0.20% better, 26-week worse',
       'no demonstrated benefit']],
     [0.40, 0.30, 0.30]),
    ('note', "All final-wealth changes include the 3% scheduled withdrawals. No method beats another in a "
             "way that survives scrutiny."),
    ('bullets', [
        "19 episodes is thin evidence; estimation windows overlap; property uses the latest published "
        "index, not point-in-time vintages; and the calendar was known when the protocol was designed, "
        "so this is past-only, not a blind preregistered test.",
        "The bundled older history is only 151 weeks because of a credit-spread series, one reason the "
        "ETF-based 2005-2026 rebuild happened.",
        "What the backtest does establish: the pipeline runs end-to-end on real data, refits are "
        "numerically stable, and no hidden failure was rerun away.",
    ]),

    ('h1', '7. Four ways to define "a good outcome"'),
    ('p', "\"Risk-adjusted outcome\" needs a precise meaning. Four standard definitions were compared "
          "fairly: same simulated paths, same constraints, same judge, parameters fixed before any "
          "results. The study is frozen; the dashboard shows it side by side without recomputing."),
    ('table',
     ['Objective', 'What it cares about', 'Quirk'],
     [['CARA surplus (current)', 'dollars left after all payments; equally nervous about every dollar',
       'none special'],
      ['CRRA gross', 'percentage growth of total wealth; payments enter only through constraints',
       'ignores the floor shape'],
      ['HARA payment floor', 'wealth above the payment floor, in percentage terms',
       'mathematically undefined below the floor'],
      ['Kinked shortfall', 'dollars, but falling below target hurts 5x more than gains please',
       'kinked, not smooth']],
     [0.22, 0.48, 0.30]),
    ('note', "HARA-with-a-floor is the same family as CRRA-on-surplus; they were not double-counted. "
             "Scores are compared on one common dollar scale."),
    ('p', "Result: the choice of objective barely matters here. All four select the same validated blend, "
          "all pass every final check, and all fund 1,600/1,600 fresh paths (99.81% lower bound). The hard "
          "risk limits and the fixed validation grid decide; the utility formula gets almost no vote."),
    ('note', "3rd-edition chart, summarized in text: the four objectives pick statistically identical plans "
             "for the confirmed $250k/month schedule (score spread under $6k on $98M); the score falls by "
             "roughly the payments themselves as the monthly amount grows to 2x/4x/10x the confirmed "
             "level. Every tested size still passes all checks and funds every path."),
    ('bullets', [
        "Stress fixtures (deliberately extreme, not your plan): with $90M of calls every objective "
        "collapses to the 90% cash anchor; with a $95M final call, nothing is acceptable at all and even "
        "90% cash misses $5M on every path.",
        "HARA's floor is a real limitation: in the stress fixtures, 2-30 of 1,600 paths end below the "
        "floor, where the objective is undefined. Those failures are recorded, not clipped away.",
        "No \"best utility\" is established. The current CARA objective stays, by your earlier choice, not "
        "by a result of this study.",
    ]),

    ('h1', '8. How wrong could the model itself be?'),
    ('p', "On top of simulating market risk, the engine can charge each portfolio a safety margin for "
          "model risk: pretend the fitted law could be off by some radius, and price the worst case inside "
          "it (a Wasserstein, or W1, margin). This is where the most uncomfortable finding of the whole "
          "project sits."),
    ('note', "The assumed model-wrongness margin implies a $40k buffer. The margin actually measured "
             "from 21 years of history implies $813M: more than eight times the balance sheet, against a "
             "per-payment budget of $50k."),
    ('bullets', [
        "The working radius (0.00002) was always a placeholder. Measured from 21 complete years of "
        "history, year-to-year model drift implies a radius of about 0.41 (range 0.39-0.63 across "
        "2013-2024).",
        "At that honest radius, the unavoidable safety buffer is about $813M on a $100M balance sheet: "
        "no long-only portfolio can be certified against a $50k per-payment budget. The calibration "
        "therefore returns no candidate at all.",
        "Nothing was tuned to hide this: the placeholder stays, labelled uncalibrated, and the conflict "
        "is shown in the dashboard. Shrinking the radius until something passes would be exactly the "
        "kind of quiet repair this project refuses to do.",
        "Part of the gap is a crude metric: the current measure gives no credit for diversification and "
        "allows economically impossible perturbed scenarios. Redesigning it is an open research item, "
        "not a number to quietly adjust.",
    ]),

    ('h1', '9. Can month-by-month trading beat a fixed plan?'),
    ('p', "You asked for a mathematical optimization, not a bucket playbook. So a feedback rule was "
          "trained: eight learned parameters that map only what is knowable at the time (current wealth, "
          "remaining payments, drawdown, recent returns) into target weights, with realistic frictions "
          "(0.05% per trade, one-week settlement). Selection was frozen before final judging; simple "
          "fixed mixes were compared on identical paths and costs."),
    ('note', "3rd-edition chart, summarized in text: after costs, the learned feedback rule beats the "
             "original static mix, but a rule that makes the same first trade and then does nothing beats "
             "the feedback rule. Both learned variants fail when expected returns are 2pp lower; the "
             "simple static mixes pass all four laws."),
    ('bullets', [
        "On the two laws it was designed for, the feedback rule beats the static start by about "
        "$0.56-0.59M on a ~$98M score, after roughly $9k of fees.",
        "Attribution shows all of that gain is the first trade (a better starting mix). The "
        "month-to-month reactions themselves subtract about $20-28k relative to doing nothing after day "
        "one.",
        "The feedback rule and its first-trade-only variant both fail the two lower-return laws. Three "
        "simple fixed-mix baselines pass all four laws.",
        "A robust redesign (trained to do well under the worst of all four laws) found no acceptable "
        "rule: 360 candidates evaluated, none of the top 12 passed validation everywhere.",
        "How far from optimal is anything? A cheating bound (a clairvoyant with no costs reaches a "
        "$197-241M score vs the ~$98M achieved) is far too loose to say. There is no near-optimality "
        "certificate, and no proven better sell rule. The search failing does not prove a good rule "
        "cannot exist.",
    ]),

    ('h1', '10. How often should you rebalance?'),
    ('p', "Monthly, quarterly, semiannual and annual rebalancing of the same fixed target mix were "
          "compared on shared paths, with the same 0.05% costs, one-week settlement and monthly "
          "payments. Frequencies were judged on fresh paths under all four laws; ties under $100k count "
          "as ties."),
    ('note', "3rd-edition chart, summarized in text: annual wins at every horizon, but the gaps are "
             "0.03-0.18%. At 3 and 5 years no frequency passes all safety checks, so the ranking is a "
             "score ranking, not an accepted answer."),
    ('table',
     ['Horizon', 'Best score', 'Annual minus monthly', 'Safety checks'],
     [['1 year ($3M)', 'annual, $98.246M', '+$29k (bounded law +$32k; lower-return laws +$15-16k)',
       'all four frequencies pass all four laws'],
      ['3 years ($9M)', 'annual, $94.552M', '+$95k',
       'none passes all four laws (all pass only under the capped-vol law)'],
      ['5 years ($15M)', 'annual, $90.866M', '+$161k', 'none passes under any law']],
     [0.15, 0.22, 0.35, 0.28]),
    ('note', "Scores are the baseline-law certainty equivalents; payments were fully funded on every "
             "final path in every row. Some pairwise differences are within simulation noise after "
             "multiple-comparison adjustment; the ordering is stable, the exact gaps are not precise."),
    ('bullets', [
        "Why annual wins here: the starting mix is 76% cash (now: 75% bills), so there is little to "
        "rebalance, and every rebalance costs 0.05%. \"Less trading is slightly cheaper\" is the honest "
        "summary.",
        "At one year, \"annual\" literally means \"never trade after day one\". The 3- and 5-year runs "
        "(where annual does trade between years) still score best but fail the loss checks: drift "
        "between rebalances eventually hurts.",
        "Not tested: tolerance bands (trade only when weights drift far from target), which the "
        "practitioner literature prefers over any calendar schedule. That is a fair next experiment.",
    ]),
]
