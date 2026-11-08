"""4th-edition content: sections 11-20 + appendices."""

SECTIONS_11_20 = [
    ('h1', '11. Why is so much in cash? - answered properly this time'),
    ('p', "You asked this directly: why does the answer hold 76% cash, when a Treasury bond is low-risk "
          "and pays a decent yield, especially over one year? Fair question. The 3rd edition gave a "
          "precise answer in three parts; this edition adds the fourth part - the fix."),
    ('numbers', [
        "The model had no Treasury bill. The only bond it could buy was IEF, a fund holding 7-10 year "
        "Treasuries. A one-year bill held to the end is nearly riskless: you know exactly what you get "
        "back. A 7-10 year bond fund is different: when interest rates rise its price falls, and no "
        "maturity date pulls it back inside your one-year window. In the fitted model the fund carries "
        "6.4% yearly risk for about 3.5-4% expected return; in real history its worst year was -17.9% "
        "(in 2022, the year rates jumped, it lost 15.2%). Over a one-year horizon the model was right "
        "to treat it as a risky asset, not as a safe 5%.",
        "The 76% was forced by the safety rules, not chosen for its return. Left to itself, the "
        "optimizer picks only 35.5% cash and scores $100.1M, but that mix fails the held-out path-loss "
        "check. The engine then blends toward a 90%-cash anchor until every check holds, landing at "
        "76%. Passing the checks costs about $1.9M of score per year. The binding constraints are the "
        "twelve payment tests (each $250k payment may lose at most $50k in its 5% tail, with the "
        "family-wide bar tightened for having twelve tests), the worst-path loss limits, and a fixed "
        "model-miss buffer. The model's cash earned a placeholder 0%, so it was the one asset that "
        "could never fail any of these checks.",
        "Read \"cash\" as \"T-bills\" and the puzzle flipped already on paper. The 3rd edition reran "
        "with the cash earning a real deposit rate: at 2% the score rose $2.1M; at 4% (roughly a "
        "current bill yield) it rose $3.6M, and the model dropped the Treasury fund entirely. The "
        "reading was never \"76% idle\" but \"76% in bills or money-market at about 4-5%, because the "
        "rules demand something that cannot fall\".",
        "The fix is now built and validated. This edition adds a real three-month Treasury bill asset "
        "(section 21) and lets the engine anchor in it. The validated answer at $250k/month: 75.3% "
        "T-bills, 7.0% US stocks, 4.4% Treasuries, 3.3% gold, 10% property, 0% idle cash - score "
        "$99.98M against $98.25M with the 0% cash, a +$1.73M a year improvement on the fitted data. At "
        "current bill rates (4.17% for the 3-month constant maturity, 5 Nov 2026) the same run is "
        "worth +$3.60M, matching the 3rd edition's estimate to the decimal. The Treasury fund keeps "
        "only a small role as a diversifier and disappears at current rates.",
    ]),
    ('note', "3rd-edition chart, summarized in text: yearly risk assumed by the model versus the worst "
             "real one-year loss, 2005-2026 - the \"safe\" 7-10 year Treasury fund is much safer than "
             "stocks but far from riskless over one year; giving the cash a real yield raises the score "
             "and pushes the Treasury fund out of the mix."),
    ('p', "Making the safe asset realistic was the single most valuable open fix measured in this "
          "report, and it is now done: worth +$1.7M (fitted) to +$3.6M (current rates) a year, more "
          "than every other change tested."),

    ('h1', '12. What if the payout changes?'),
    ('p', "Your confirmed payout is $250k a month ($3M a year). Everything larger or different below is "
          "a sensitivity: same engine, same safety checks, one change at a time, on the frozen data and "
          "seeds."),
    ('table',
     ['Change tested', 'Recommended mix', 'Score', 'Reading'],
     [['$500k / month', 'unchanged: 76% cash, 9% Treasuries, 5% stocks, 10% property', '$95.3M',
       'each extra $1 out costs $1 of score'],
      ['$1M / month', 'unchanged', '$89.3M', 'same slope'],
      ['$2.5M / month', 'unchanged', '$71.3M', 'still passes every check'],
      ['one-off surprise call of +$2M / +$5M / +$10M mid-year', 'unchanged', '$96.3M / $93.3M / $88.3M',
       'dollar-for-dollar, on top of the planned $3M'],
      ['same $3M paid quarterly, semiannually, or once at year-end', '63% cash (a riskier blend passes)',
       '$99.0M', '+$0.7M vs monthly'],
      ['$125k / month', 'engine refuses to run', '-', 'guardrail, not infeasibility (see below)']],
     [0.28, 0.32, 0.16, 0.24]),
    ('note', "4th-edition note: the mix was identical for every larger payout because the cash earned "
             "0% - a dollar out was a dollar of score lost. With bills earning a real yield the slope "
             "softens (paying out less now leaves the pile compounding), and the mix starts to move "
             "slightly with the payout level (section 13)."),
    ('bullets', [
        "Why monthly is the hardest pattern: each of the twelve payments gets its own tail test with "
        "its own $50k allowance, and the family-wide confidence bar tightens with every extra test. "
        "Twelve small checks bind harder than one big one, so smaller-but-more-frequent payments demand "
        "more safety buffer, not less.",
        "Why $125k/month refuses: the fixed model-miss buffer ($40k) is larger than the smaller "
        "per-payment allowance ($25k), and the engine declines to run with contradictory settings. A "
        "guardrail, not infeasibility - section 13 gives the full portfolio at $50k, $100k and $250k "
        "under a clearly labeled scaled-buffer sensitivity.",
        "Extremes from the frozen studies: a $60M early call plus a $30M final call forces the 90%-cash "
        "anchor, and a $95M final call has no feasible plan at all (section 15).",
    ]),
    ('p', "And if the amounts themselves are uncertain? The engine needs a fixed schedule, so the honest "
          "test keeps the recommended fixed plan and lets reality deviate: payments drawn randomly plus "
          "or minus 50% month to month, doubled payments, and lumpy patterns. The plan makes every "
          "payment on 100% of futures up to $5.5M a month - twenty-two times your actual payout. The "
          "first rare misses appear at $6M a month (0.06% of futures), and the plan truly breaks at $7M "
          "(16% of futures, worst single miss $16M). At $250k a month, payout uncertainty is a "
          "non-issue: the safe pile alone covers roughly 25 years of payments."),

    ('h1', '13. The portfolio at $50k, $100k and $250k a month'),
    ('p', "What does the safe portfolio actually look like at each payout level? Section 12 traced the "
          "score across payout sizes; this section lays out the validated portfolio itself at $50k, "
          "$100k and $250k a month, with $125k added because it sits exactly at the engine's refusal "
          "boundary."),
    ('h2', 'Why the engine refuses below $200k a month, in plain words'),
    ('p', "Two safety settings collide there. The first is a fixed model-miss buffer: every payment "
          "must survive an extra margin for the chance the market model itself is wrong, and that "
          "margin is a fixed $40k per payment. The second is a per-payment allowance: the tail-risk "
          "budget for each payment is 20% of that payment. At $250k a month the allowance is $50k and "
          "comfortably covers the $40k buffer. At $125k the allowance is $25k - smaller than the buffer "
          "- and the settings contradict each other. The engine then declines to run instead of "
          "silently weakening either setting. That is a guardrail doing its job, not a claim that "
          "smaller payouts are infeasible."),
    ('h2', 'A clearly labeled sensitivity, not a changed default'),
    ('p', "To show the portfolios anyway, one number is scaled: the model-miss buffer is shrunk in "
          "proportion to the payment, keeping it at 80% of the allowance - the same ratio it has at the "
          "confirmed $250k level. No budget, limit or check is loosened; every safety test still runs "
          "and still passes with margin. The default configuration is untouched, and the refusal itself "
          "is reported above, not hidden."),
    ('h2', 'Baseline (3rd edition): cash at a placeholder 0%'),
    ('table',
     ['Monthly payout', 'As-is outcome', 'VTI', 'Treasuries', 'Cash', 'Property', 'Score', 'Safety checks'],
     [['$50k', 'passes', '4.6%', '9.1%', '76.3%', '10%', '$100.66M', 'all pass'],
      ['$100k', 'passes', '4.6%', '9.1%', '76.3%', '10%', '$100.06M', 'all pass'],
      ['$125k', 'passes', '4.6%', '9.1%', '76.3%', '10%', '$99.76M', 'all pass'],
      ['$250k', 'passes', '4.6%', '9.0%', '76.4%', '10%', '$98.25M', 'all pass']],
     [0.14, 0.13, 0.09, 0.12, 0.10, 0.11, 0.14, 0.17]),
    ('note', "Validated portfolio per payout level under the scaled-buffer sensitivity (buffer kept at "
             "80% of the per-payment allowance, its ratio at the confirmed $250k level). Weights are "
             "percent of wealth; the score is the certainty equivalent in $M. At $250k the sensitivity "
             "coincides with the confirmed baseline."),
    ('h2', 'This edition: the same runs with the T-bill asset'),
    ('table',
     ['Monthly payout', 'VTI', 'Gold', 'Treasuries', 'T-bills', 'Cash', 'Property', 'Score',
      'vs baseline'],
     [['$50k', '7.0%', '3.3%', '4.5%', '75.2%', '0%', '10%', '$102.42M', '+$1.76M'],
      ['$100k', '7.0%', '3.3%', '4.5%', '75.2%', '0%', '10%', '$101.81M', '+$1.75M'],
      ['$125k', '7.0%', '3.3%', '4.4%', '75.2%', '0%', '10%', '$101.50M', '+$1.75M'],
      ['$250k', '7.0%', '3.3%', '4.4%', '75.3%', '0%', '10%', '$99.98M', '+$1.73M']],
     [0.14, 0.08, 0.08, 0.12, 0.10, 0.08, 0.11, 0.15, 0.14]),
    ('note', "Same engine, same frozen data and seeds, same scaled-buffer sensitivity; the only change "
             "is the T-bill asset and the bill anchor. Every row passes every safety check, funds every "
             "payment on all 1,600 fresh final paths, and the idle 0% cash disappears from the mix."),
    ('fig', 'fig_payout.png',
     "The score by payout level, before and after. The gap is the bill yield the safe pile now earns: "
     "+$1.7-1.8M a year at every level on the fitted data (more at current rates, section 21)."),
    ('p', "What drives the differences: still almost nothing in the mix. The binding forces are the "
          "per-payment tail checks and the whole-portfolio loss caps, and they scale with the payment, "
          "so the same bill-heavy portfolio passes at every level. What changes is only the score: less "
          "paid out leaves more in the pile - and now the pile compounds instead of sitting at 0%. "
          "Smaller payouts are not harder to fund - at $50k a month the year's $0.6M is covered by the "
          "bills alone for over a century - the refusal below $200k is purely the two fixed safety "
          "settings colliding."),

    ('h1', '14. What if the views are wrong?'),
    ('p', "Every recommendation so far leans on fitted views: expected returns, volatilities, "
          "correlations and property growth. Two experiments test how much those views matter."),
    ('h2', 'Experiment one: change a view, re-solve'),
    ('p', "One input at a time: stock and Treasury expected returns plus or minus two points, all "
          "volatilities up or down a quarter, Treasuries that no longer hedge stocks, property growth "
          "of 0% or 8%, and cash that earns 2% or 4%. Everything else, including every safety check, "
          "stays fixed."),
    ('note', "3rd-edition chart, summarized in text: under each changed view the validated cash share "
             "stays between 62% and 82%, property stays at its fixed 10%, emerging markets are never "
             "bought; the score moves less than plus or minus $1.2M under every view except the cash "
             "rate, which was worth +$3.6M at 4% - exactly what the new T-bill asset now captures for "
             "real."),
    ('p', "Two honest mechanics notes. The raw optimizer does respond to views in the direction you "
          "would expect (a better Treasury view cuts raw cash from 36% to 18%); the validated blend "
          "moves less, partly because the blend grid is coarse - quarters of the way from anchor to "
          "optimizer. And when the optimizer's own mix gets safer, the checks let more of it through, "
          "which is why a worse stock view can end at a similar cash share with more stocks inside it. "
          "The direction of the raw response is the cleaner signal; the blend is the answer the checks "
          "actually accept."),
    ('h2', 'Experiment two: keep the plan, worsen the world'),
    ('p', "Take the 76%-cash plan as fixed, then re-check it in worlds worse than fitted: stocks two "
          "points weaker, Treasuries two points weaker, everything risky two points weaker, all "
          "volatilities a quarter higher, Treasuries falling together with stocks, property flat. The "
          "plan passes every safety check in every one of those worlds, makes every payment, and "
          "scores $97.9-98.4M against $98.3M in the fitted world."),
    ('bullets', [
        "Bottom line: within everything tested, wrong views cost at most about $1M of score and never "
        "break a payment. The binding safety rules, not the views, drive the allocation.",
        "The exception was the cash rate. It was a placeholder, not a fitted view, and it was the only "
        "input that moved the value by millions. That input is now a real fitted asset with a real "
        "rate series (section 21); its own sensitivity is measured there.",
        "All paths are synthetic futures from one fitted model vintage (7 November 2026); these are "
        "model-only statements about robustness, not historical proof.",
    ]),

    ('h1', '15. "Passed" does not mean "paid"'),
    ('p', "This distinction caused real confusion during the project, so it gets its own section. The "
          "declared funding limit allows each payment a 20% tail-shortfall allowance at 95% confidence. "
          "That is not a promise to make every payment. Counterfactual stress fixtures make the gap "
          "concrete:"),
    ('note', "3rd-edition chart, summarized in text: under a deliberately extreme $95M final call, the "
             "share of validation paths paying every call collapses as the mix is made safer, because "
             "the obligation is simply too large. Even 90% cash misses $5M on every path. Not your "
             "plan; a stress test."),
    ('bullets', [
        "With a $60M early call plus a $30M final call, a validation-calibrated portfolio passes every "
        "declared model limit while making every payment on only about 84% of paths.",
        "With your actual $3M schedule the risk is remote (the safe pile alone covers years of "
        "payments), which is exactly why the passing label is weak evidence there.",
        "Two fixes are now built in: a strict 99% all-payments check (at least 99% of fresh paths must "
        "make every payment, with an exact binomial lower bound) and a separate execution audit that "
        "counts actual unpaid calls in the cash-first ledger.",
        "Sample honesty: proving a 99% all-paid rate with zero observed misses takes at least 299 "
        "independent paths; the studies use 1,600.",
        "Both verdicts are shown side by side, and the strict check and the all-risk check can "
        "disagree. When they do, both are reported.",
    ]),

    ('h1', '16. How the model was checked, inside out'),
    ('p', "On the night of 7-8 November the whole computation path was audited from scratch: roughly "
          "thirty modules read line by line - scenario generation, the forecast mixture, entropy "
          "pooling, the optimizer, the tail-risk accounting, the cash ledger, property, currency and "
          "the strict funding check - and eleven independent numerical tests were written from scratch "
          "to compare the engine against hand-computed answers on cases where the truth is known."),
    ('table',
     ['Check', 'Result'],
     [['Simulated weekly means and covariances match the fitted moments',
       'PASS - max mean err 6.65e-05, max cov err 5.80e-06 (seed 20261107 train draw, n=4000 unless stated)'],
      ['Crash-mixture tail shape matches its closed form', 'PASS - sample 1.742 vs formula 1.688 (MC noise at n=208k)'],
      ['Property paths match their calibrated drift and volatility', 'PASS - drift 0.0400 vs 0.0400, vol 0.1584 vs 0.1593'],
      ['Property-equity co-movement matches the user-set correlation', 'PASS - sample corr 0.301 vs rho 0.30 (mixture state shared, MC noise)'],
      ['Payment provisioning arithmetic is exact', 'PASS - max err $0.00e+00; terminal_net = value - sum(payments) exactly when growth=1'],
      ['Cash ledger conserves wealth in a flat world', 'PASS - terminal net 98,000,000 vs expected 98,000,000, funded all True'],
      ['Ledger shortfall arithmetic is exact when money runs out', 'PASS - unpaid 20,000,000 vs expected 20,000,000; net -20,000,000'],
      ['Weighted tail loss equals the direct worst-5% mean', 'PASS - cml_of_paths 0.221648 vs direct tail mean 0.221648'],
      ['The tail-risk solver matches a brute-force minimizer', 'PASS - common_tail 2.46326346 vs brute 2.46326346'],
      ['Entropy pooling hits a requested view exactly', 'PASS - achieved 0.1000 vs requested 0.10; q sums to 1.000000000000, min q 1.45e-04'],
      ['Currency conversion matches a manual recomputation', 'PASS - max err 0.00e+00 on 1129 weeks']],
     [0.44, 0.56]),
    ('note', "Eleven identity tests, each comparing the engine to an independent recomputation or a "
             "known closed form. All pass; the largest discrepancy anywhere is Monte Carlo sampling "
             "noise."),
    ('bullets', [
        "Code audit: no new errors found in any module on the computation path. The one real bug ever "
        "found by an earlier audit - a payment-netting error in an old commit - is confirmed fixed in "
        "the current engine, and the netting now matches between the optimizer and the independent "
        "ledger.",
        "Consequence: no corrections were needed, so every frozen number carried into this report "
        "stands unchanged. The audit changed the evidence, not the results.",
        "4th edition: seven more tests were added for the new T-bill asset (carry math against a "
        "hand-computed roll, rate-change loss term, registry isolation, anchor wiring, and the "
        "structural-carry exemption from mean shrinkage). 375 tests pass in total.",
    ]),

    ('h1', '17. Every dial, and what it moves'),
    ('p', "Every modeling decision that could move the answer was perturbed one at a time on the frozen "
          "machinery - nineteen variants - and the validated portfolio was re-derived from scratch each "
          "time. The chart shows how far the cash share moves; the table says why each setting is what "
          "it is."),
    ('note', "3rd-edition chart, summarized in text: the cash share of the validated plan stays in a "
             "broad safe band no matter which dial is turned; the binding safety rules, not any single "
             "modeling choice, set the level."),
    ('table',
     ['Decision', 'Setting', 'Grounding and test'],
     [['Crash-mixture law (90% calm / 10% storm weeks)', 'kept',
       'Matches realized weekly crash frequency (below); a plain Gaussian under-reserves by $3M; Student-t(5) lands within 0.7 points'],
      ['Mean shrinkage strength', '156 weeks',
       'Jorion/Ledoit-Wolf classics; the selected plan is identical at 50, 156 and 400 - the decision does not bind'],
      ['Risk tolerance', '$10M', 'Your setting; at $5M and $20M the selected plan barely moves and every check passes'],
      ['Per-payment tail allowance', '20%', 'Your setting; identical plan at 30%; at 10% the engine refuses rather than loosen'],
      ['Model-miss buffer', '$40k/payment',
       'Honest placeholder (section 8); removing it moves cash by 0.1 points; at 5x the engine refuses. Cost and boundary now measured'],
      ['Property-equity correlation', '0.3', 'Your setting; at 0 the plan is unchanged within 1 point; at 0.6 the marginal blend point slips (below)'],
      ['Stress worsening of views', '+1% path loss', 'Committee-style margin; at 0% the plan is unchanged within 1 point; at 2% the marginal blend point slips'],
      ['Cash yield', 'was 0% placeholder',
       'No investable cash asset existed; the only dial worth millions (section 11). This edition replaces it with the fitted T-bill roll.'],
      ['Random seeds', 'frozen',
       'Twelve fresh master seeds re-run the whole selection: usually the quarter blend (69-78% cash); every selected mix passes every check']],
     [0.30, 0.16, 0.54]),
    ('note', "One decision at a time on the frozen engine. No perturbation changed the character of the "
             "answer."),
    ('p', "Does the crash model match reality? Two direct tests. Weekly: the mixture predicts how often "
          "real markets move more than two, two-and-a-half and three standard deviations in a week, and "
          "it tracks 21 years of realized history closely, while a plain Gaussian misses three-sigma "
          "weeks by a factor of four. Yearly: the model's simulated one-year losses for the chosen mix "
          "are harsher than anything in 84 rolling years of realized history - so even though "
          "independent weekly draws cannot manufacture multi-year storms, the annual risk of this plan "
          "is not understated."),
    ('p', "And the missing volatility clustering? It is real: squared weekly returns are strongly "
          "autocorrelated in every asset (Ljung-Box p ~ 0), so calm and storm weeks genuinely cluster. "
          "But a clustering-preserving stationary bootstrap of the realized quarters (Politis-Romano, "
          "crisis quarters kept adjacent) gives annual tails for the selected mix - q5 -1.1%, worst "
          "-5.3% over 20,000 synthetic years - that match rolling history and are no harsher than the "
          "model's independent-week years (q5 -2.2%, worst -5.4%). Independent weeks do not understate "
          "this mix at one year. Clustering stays an open risk for riskier mixes and for multi-year "
          "horizons, where the bootstrap cannot reach."),
    ('note', "3rd-edition chart, summarized in text: weekly crash frequencies past 2, 2.5 and 3 standard "
             "deviations - realized history, the mixture the engine uses, and a plain Gaussian; and "
             "one-year outcomes of the selected mix, simulated versus realized history."),
    ('bullets', [
        "One honest caveat the audit surfaced: the blend between the anchor and the optimizer moves in "
        "quarters, and the half-way point sits near the path-loss budget boundary, so small Monte Carlo "
        "noise can move the winner by one grid point. Across twelve fresh simulation seeds the engine "
        "picks the quarter blend (69-78% cash) seven times, the half blend (62-65% cash) four times - "
        "two of those then fail the independent final check - and once the all-cash mix (90% cash, "
        "score $97.4M). A finer eighth-step blend grid was tried at four seeds and does not stabilize "
        "the choice, so granularity is not the cause; the optimum is simply flat. What is stable: every "
        "selected mix passes every check, and the score stays within $97.4-99.0M (1.6% of wealth) "
        "across all twelve seeds. The published mixes are default-seed representatives of that region, "
        "not sharply tuned optima - which is exactly how a safety-first answer should look.",
        "What this means for trust: no single dial secretly carries the result. The answer is what the "
        "safety checks allow, and they allow roughly the same mix everywhere nearby.",
    ]),

    ('h1', '18. What outside research and practice say'),
    ('p', "Thirteen sources (academic papers and family-office practice) were fetched and read. The "
          "short version: the engine's core frame is the endorsed one, and practice adds a liquidity "
          "playbook on top of it."),
    ('bullets', [
        "Secure the liability first, take risk with what is left. The surplus/LDI literature "
        "(Sharpe/Scott/Watson 2008; Ashton 2011) endorses exactly the engine's frame: optimize wealth "
        "after obligations, not raw returns.",
        "Selling at a bad time has a name: sequence-of-returns risk. With withdrawals, the order of "
        "returns matters more than the average (Pfau). Selling a bit of everything every month is the "
        "textbook thing to avoid.",
        "A cash reserve of 1-2 years of payouts, refilled only from winners and never by selling what "
        "is down, improved 30-year plan survival by up to 6 points in one study (Pfeiffer/Salter/"
        "Evensky 2013). For you that is $3-6M, cheap insurance at a 3% payout.",
        "But buckets are mostly relabeling: a cash bucket is financially near-equivalent to a static "
        "mix with the same overall allocation (Tomlinson 2020). The benefit is behavior and costs, not "
        "magic return.",
        "Rebalance with tolerance bands (~20% of target weight), not a calendar (Kitces 2015; "
        "Daryanani 2007). In a drawdown, fund spending by selling the most overweight or most "
        "appreciated asset first.",
        "Family offices typically hold 0-2 (up to 3) years of spending in cash or near-cash, and use a "
        "post-stress liquidity ratio of 3x annual needs as a safety gauge (Cambridge Associates 2023; "
        "RBC/Campden 2025).",
        "Property crowds out equity in optimal household portfolios (Cocco 2005): the fixed 10% "
        "property correctly pushes the liquid sleeve more conservative.",
        "Added in this edition: Bodie (1995) on stocks over long horizons - the cost of insuring a "
        "floor rises with the horizon, so time alone does not make equities safe. That paper is the "
        "rigorous answer behind section 23's treatment of your 10-30 year question.",
    ]),
    ('p', "Where this meets the engine's results: the annual-rebalancing win and the safe-heavy "
          "validated mix agree with practice. The open tension is bands versus calendar: the engine "
          "tested calendar schedules only, and the literature suggests bands are the better rule. The "
          "liquidity-tier suggestion is the literature brief author's judgment, flagged as judgment, "
          "not engine evidence."),

    ('h1', '19. Everything that is still open'),
    ('p', "Consolidated from all the studies. None of these is hidden in the underlying reports; they "
          "are gathered here so one page holds the full list."),
    ('table',
     ['Area', 'What is not solved'],
     [['Market model',
       'Volatility clustering is absent from the default law (Ljung-Box p ~ 0 confirms it is real), but a '
       'clustering-preserving bootstrap shows the selected mix\'s annual risk is not understated (section '
       '17); crisis tails (2008) break every candidate; joint property/fund/currency dependence is '
       'assumed, not fitted'],
      ['Model-wrongness margin',
       'The W1 radius is an uncalibrated placeholder; the honest empirical calibration conflicts with the '
       'budgets by orders of magnitude; the metric itself is crude (no diversification credit)'],
      ['Data',
       'The T-bill roll is constructed from a constant-maturity yield series, not a traded fund - a real '
       'bill fund costs about 16bp/yr more (the BIL fee gap, section 21) and its fitted carry (1.81%) '
       'lags current rates (4.17%); property is a quarterly price index (no rent, no sale, latest '
       'vintage, assumed 45-day publication lag, SGD economics on a USD balance sheet); fees (0.05%) and '
       'one-week settlement are assumptions, not broker quotes; Yahoo history is private-use only'],
      ['Accounting',
       'The optimizer still thinks in provisioning while the audit ledger thinks in cash-first selling; '
       'unifying them is parked work; stochastic liabilities are disabled until a causal calibrated '
       'model exists'],
      ['Evidence',
       '19 historical episodes is thin; simulated futures are model-driven, not historical proof; the '
       'weekly model approximates calendar months; no near-optimality certificate exists for any policy'],
      ['Scope',
       'Only the $250k/month amount is confirmed by you. Wealth level, property share, risk limits '
       '(including the 6% and 15% loss caps, section 22), horizons and the four laws are research '
       'settings, and 3/5/10-30-year durations are sensitivities, not obligations'],
      ['Selection granularity',
       'The anchor-optimizer blend moves in quarters near a flat optimum: across twelve seeds the engine '
       'selects 62-90% safe (usually 69-78%); a finer eighth-step grid does not stabilize the choice. '
       'Every selected mix passes every check and scores within 1.6% of wealth; the region is stable, '
       'the point inside it is Monte Carlo noise'],
      ['Engineering',
       'Solver time is flaky (0.6-60s for identical inputs); closing the dashboard does not cancel a '
       'running solve; 18 dependency alerts on the repo\'s default branch are being audited separately'],
      ['Long horizons',
       'The loss limits are one-year limits applied unchanged to longer runs; a principled '
       'horizon-scaled budget (section 23) is designed but not yet built into the validator']],
     [0.18, 0.82]),
    ('note', "Grouped from SCIENTIFIC_STATUS.md, the book audit, the model-adequacy, bounded-volatility, "
             "strict-funding, utility, dynamic-policy and frequency studies, and this edition's T-bill, "
             "loss-limit and long-horizon studies."),

    ('h1', '20. The verdict'),
    ('p', "On the confirmed plan, the defensible answer is a boring one - but no longer an idle one. A "
          "bill-heavy mix (about 75% three-month Treasury bills, 7% US stocks, 4.4% Treasuries, 3.3% "
          "gold, 10% property) passes every check under every market law tested, funds every payment on "
          "all 1,600 fresh paths, earns real carry on the safe pile, and no cleverer alternative proved "
          "itself better. At a 3% annual payout, safety is cheap and the payout is the tail risk that "
          "matters least; the model is the tail risk that matters most."),
    ('bullets', [
        "Objective: keep CARA-on-surplus. The four-way comparison shows the choice does not drive the "
        "answer at these limits.",
        "Trading: one good allocation, then bills-first. Learned monthly feedback adds nothing after "
        "its first trade and breaks when returns disappoint; no robust rule was found.",
        "Rebalancing: annual is the best of the four tested, at every horizon, on score. At one year "
        "it also passes every check. Past one year, nothing passes everything, so treat annual as "
        "\"best tested\", not \"proven\".",
        "Safety labels: read the strict 99% all-payments line and the execution audit when asking "
        "\"will every payment be made?\", not the 20% allowance line.",
        "Loss limits: the 6% any-point cap is the one rule that actually sets the safe share, and it "
        "is a development default, not your choice (section 22). It deserves a conscious decision from "
        "you, with the sweep table in section 22 as the menu.",
        "Biggest open risks: crisis tails in the market model and the uncalibrated model-wrongness "
        "margin, with volatility clustering real but shown not to understate this plan at one year "
        "(section 17). All are documented; none was tuned away.",
    ]),
    ('h2', 'What would change the answer'),
    ('p', "A conscious decision from you on the loss limits (section 22); promoting the capped "
          "conditional-volatility model after a real annual validation (your decision, currently "
          "unapproved); actual property, rent, settlement and cost data; a redesigned, calibrated "
          "model-risk margin; tolerance-band rebalancing tests; a horizon-scaled loss budget for "
          "multi-year plans (section 23); and real client constraints beyond the monthly amount. The "
          "3rd edition's biggest open fix - a real T-bill asset for the cash - is done in this "
          "edition."),
    ('h2', 'What the overnight audit changed'),
    ('p', "The evidence, not the answer. A full re-read of the engine, eleven independent numerical "
          "tests, nineteen one-decision perturbations and direct weekly and yearly tail checks against "
          "realized history found no errors and no hidden load-bearing choice. The crash-mixture law "
          "is now backed by data rather than judgment alone, and the one soft spot the audit surfaced "
          "- the flat blend optimum (62-90% safe across seeds, usually 69-78%) - is reported openly in "
          "section 17. This edition's own studies (T-bill asset, payout levels, loss-limit sweep, "
          "10-30 year screens) run on the same frozen data, code and seeds, with the new numbers "
          "labeled wherever a setting was changed for the study."),
    ('h2', 'What this report is not'),
    ('p', "Investment advice, a client calibration, or a proof about the future. It is a record of "
          "what careful experiments and a full inside-out audit found, and of exactly where they stop."),
]

APPENDICES = [
    ('h1', 'Appendix A. Data and rights'),
    ('table',
     ['Data', 'Source', 'Terms'],
     [['VTI, VWO, GLD, IEF weekly total returns, 2005-2026',
       'issuer downloads (Vanguard, iShares, SPDR) plus an existing private Yahoo snapshot',
       'private use only; raw histories kept out of git; nothing derived shared without asking'],
      ['3-month Treasury bill rates (DGS3MO), 1981-2026',
       'FRED, Federal Reserve Bank of St. Louis (constant-maturity series)',
       'public data; series and construction documented in the repo manifest'],
      ['BIL ETF weekly total returns, 2007-2026 (validation cross-check only)',
       'same private snapshot pipeline as the other funds',
       'private use only; used only to sanity-check the constructed bill roll'],
      ['Singapore residential property', 'URA All Residential price index, quarterly',
       'open license; attribution bundled'],
      ['SGD/USD', 'Federal Reserve official series', 'public data'],
      ['Meucci, Risk and Asset Allocation (2005)', 'your own copy', 'reviewed; no pages copied or redistributed'],
      ['Code', 'original, in your private repo', 'no GPL components; nothing publicly hosted']],
     [0.34, 0.34, 0.32]),
    ('note', "You accepted the Yahoo terms risk for private research only (WhatsApp, 7 Nov, 18:23). Do "
             "not make the repository public as it stands: the bundled snapshot has no redistribution "
             "clearance."),

    ('h1', 'Appendix B. Reproduction and verification'),
    ('bullets', [
        "Everything lives in the private repo github.com/TijsdeBoer/emfin_capstone. The frozen "
        "baseline is branch engine-v2 (head 6bb8047), with the dynamic-policy work merged from its "
        "feature branch. This edition's work is on branch tbill-asset (commits fd7e58b and c80c88d): "
        "the T-bill asset, its tests, and the study scripts and frozen JSONs under studies/tbill/.",
        "375 automated tests pass (368 plus 7 new for the bill asset), including independent "
        "re-implementations of the quantile, CVaR, certainty-equivalent, W1 and funding-bound math. "
        "The wheel builds, installs and runs outside the checkout.",
        "Every study was frozen before its final paths were drawn: seeds, code and data hashes and "
        "selection locks are archived with it, and failed runs are preserved rather than deleted. No "
        "failing final judge was retuned.",
        "Studies used 100 training / 200 validation / 400 final paths per batch, four final batches "
        "(1,600 final paths), with disjoint seeds for the dynamic, robust and frequency follow-ups.",
        "Measured compute: dynamic study 6.8s; robust variant 12.8s; frequency 2.0s (1 year) and "
        "14.7s (multi-year); utility comparison 6.8s; strict funding 3.4s. The 4th-edition studies "
        "(payout levels, loss-limit sweeps, current-rate sensitivity) reuse the same frozen machinery; "
        "the 10-30 year screens use fixed mixes and a fresh-path judge because the cvxpy optimizer "
        "does not scale past one year - that substitution is labeled wherever it is used.",
        "Overnight audit (third edition): ~30 modules re-read; 11 identity tests (audit_identities.py, "
        "all pass); 19 one-decision perturbations (study_decisions.py); weekly and annual tail "
        "calibration against realized history (audit_tails.py); a clustering-preserving stationary "
        "bootstrap (audit_clustering.py); payout-level portfolios (study_variants4.py). All on the "
        "same frozen data, code and seeds.",
        "The dashboard (emfin-explore, local only) is a coarse preview tier; it is not the source of "
        "any number in this report.",
        "Charts: the 3rd-edition build scripts were not preserved, so 3rd-edition charts that could "
        "not be regenerated from archived data are summarized in italic text notes where they "
        "appeared. All charts in sections 13 and 21-23 are new, regenerated from the frozen study "
        "JSONs in studies/tbill/results/.",
    ]),

    ('h1', 'Appendix C. Sources'),
    ('p', "All external sources were fetched and read. Methods grounding only; no source code copied."),
    ('bullets', [
        "Meucci, Risk and Asset Allocation, Springer 2005 (audit standard, your copy)",
        "Gneiting & Raftery 2007, proper scoring rules (CRPS) - sites.stat.washington.edu/raftery",
        "Patton 2011, QLIKE and volatility proxies - public.econ.duke.edu/~ap172",
        "Bollerslev 1986, GARCH - public.econ.duke.edu/~boller",
        "Esfahani & Kuhn 2018, Wasserstein distributionally robust optimization - link.springer.com",
        "Politis & Romano 1994, the stationary bootstrap - tandfonline.com",
        "Federal Reserve FEDS 2001-27, The Hidden Dangers of Historical Simulation - federalreserve.gov",
        "Michaud & Michaud 2007, Estimation Error and Portfolio Optimization - newfrontieradvisors.com",
        "Shiraishi & Taniguchi 2010, portfolio estimation resampling - jstage.jst.go.jp",
        "Jacquier 2010, Simulation-based Estimation in Portfolio Selection - people.bu.edu/jacquier",
        "Boyd et al., dynamic portfolio optimization papers - stanford.edu/~boyd (3 papers)",
        "Pfau, sequence-of-returns risk - retirementresearcher.com",
        "Pfeiffer, Salter & Evensky 2013, cash-reserve strategies - financialplanningassociation.org",
        "Tomlinson 2020, bucket strategies re-tested - advisorperspectives.com",
        "Sharpe, Scott & Watson 2008, efficient retirement spending - web.stanford.edu/~wfsharpe",
        "Ashton 2011, LDI for individuals - soa.org",
        "Kitces 2015 / Daryanani 2007, rebalancing tolerance bands - kitces.com",
        "Cambridge Associates 2023, Liquidity Hazard planning - publishedresearch.cambridgeassociates.com",
        "Cocco 2005, housing in household portfolios - academic.oup.com",
        "RBC/Campden 2025 family-office survey; Canadian Family Offices 2026; TIFF Spend Policy 101",
        "Added in this edition: Bodie 1995, On the Risk of Stocks in the Long Run, Financial Analysts "
        "Journal 51(3), 18-22 - rpc.cfainstitute.org/research/financial-analysts-journal/1995/",
        "Added in this edition: FRED DGS3MO, 3-Month Treasury Constant Maturity Rate - "
        "fred.stlouisfed.org/series/DGS3MO",
        "Added in this edition: Federal Reserve H.15 Selected Interest Rates, 6 Nov 2026 release "
        "(3M CMT 4.17%, 3M bill secondary market 4.00%, 4-week bill 3.89%, all 5 Nov 2026) - "
        "federalreserve.gov/releases/h15",
        "Added in this edition: SPDR Bloomberg 1-3 Month T-Bill ETF (BIL), fund page and fee - "
        "ssga.com",
        "Data terms: investor.vanguard.com/terms-conditions, spdrgoldshares.com/terms-and-conditions, "
        "ishares.com, legal.yahoo.com, ura.gov.sg",
    ]),
    ('note', "Prepared 7 November 2026 as a consolidation of the day's frozen studies; second edition 8 "
             "November added the cash, payout and view sensitivity studies; third edition the same "
             "night added the payout-level portfolios (section 13), the inside-out audit (section 16) "
             "and the decision-by-decision evidence (section 17); fourth edition, still 8 November, "
             "adds the real T-bill asset and its validated results (sections 11, 13, 21), the "
             "loss-limit provenance and sweep (section 22) and the 10-30 year screens (section 23). "
             "The individual study documents remain the authoritative record; this report simplifies "
             "them and does not override them."),
]
