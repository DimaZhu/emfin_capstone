"""4th-edition content: the new sections 21-23."""

SECTIONS_21_23 = [
    ('h1', '21. The T-bill asset: what was built, and what it earns you'),
    ('p', "The 3rd edition's most valuable open fix was a real short-term government asset, so the safe "
          "pile earns a real yield instead of a placeholder 0%. This section documents exactly what was "
          "built, how it was checked, and what it changes. Nothing here is an invented number: every rate "
          "comes from a dated public series, and every result reruns the frozen engine with only the "
          "labeled changes described below."),

    ('h2', 'What the asset is'),
    ('p', "A rolling three-month US Treasury bill position, rebuilt weekly from the Fed's 3-month "
          "constant-maturity yield series (FRED DGS3MO, public data, 1981 through 6 November 2026, 2,355 "
          "weeks). Each week the position earns the week's carry (the annual yield divided by 52) minus a "
          "small price term: if yields rose during the week, a 3-month bill loses a quarter-year's worth "
          "of that rise in price. That is the engine's own documented money-market convention, reused "
          "rather than invented. The result: an average yield of 3.88% a year over the full history, "
          "weekly volatility of 0.54%, and a worst single week of -0.16%. For comparison, the fitted "
          "7-10 year Treasury fund carries 6.4% yearly risk and lost 15-18% in its worst year."),
    ('fig', 'fig_tbill_history.png',
     "The constructed bill roll since 2005: $1 grows steadily, goes nowhere during the zero-rate decade, "
     "and compounds again at 4-5% since 2022. Built from FRED DGS3MO (1981-2026); construction "
     "documented in the repo manifest."),

    ('h2', 'How it was checked against the real world'),
    ('p', "A constructed series is not a traded fund, so it was cross-checked against one: BIL, the "
          "SPDR 1-3 month T-bill ETF, over 1,013 shared weeks (2007-2026). The constructed roll earns "
          "16bp a year more than BIL, which is almost exactly BIL's management fee - the gap you would "
          "expect between an idealized roll and a real fund. Weekly volatilities are 0.31% vs 0.36% "
          "and the two series move together (correlation 0.75 on weekly returns, which for bills are "
          "tiny numbers dominated by the rate path). Honest reading: the asset is realistic, and a "
          "real-world version costs about 0.16% a year in fees."),

    ('h2', 'How the engine treats it (two labeled changes)'),
    ('bullets', [
        "Its carry is structural, not a statistical view. The engine shrinks every asset's fitted "
        "expected return toward safe values because raw estimates are noise. A bill's carry is "
        "different: the yield you lock for the next 13 weeks is known today, not estimated. So the "
        "bill's carry is exempted from shrinkage (a labeled code change with its own test), while its "
        "small rate-risk term stays fully stochastic in every scenario and every law.",
        "It becomes the anchor asset. The engine's safety anchor - the mix it blends toward until "
        "every check passes - was 90% idle cash. The anchor is now 90% bills (a labeled configuration "
        "option; the old cash anchor remains available, and the bundled baseline registry is "
        "untouched, enforced by a test).",
    ]),

    ('h2', 'What it changes'),
    ('table',
     ['Run (all at the confirmed $250k/month)', 'Safe asset', 'Score', 'Difference'],
     [['Baseline, frozen 3rd-edition pipeline', '76.4% cash at 0%', '$98.25M', '-'],
      ['Add the bill asset, keep the cash anchor', '45% cash + 30% bills', '$99.22M', '+$0.97M'],
      ['Also anchor in bills (the validated 4th-edition answer)',
       '75.3% bills, 0% idle cash', '$99.98M', '+$1.73M'],
      ['Same, at current bill rates (4.17% instead of the fitted 1.81%)',
       '77.5% bills, Treasuries drop to 0%', '$101.86M', '+$3.60M']],
     [0.42, 0.24, 0.14, 0.20]),
    ('note', "Same engine, frozen data and seeds; only the labeled changes differ. Every row passes "
             "every check: strict 99% funding, all four laws, the loss limits and the execution audit. "
             "The last row is a labeled sensitivity, not the default: the fitted carry averages the "
             "2005-2026 window, which includes the zero-rate decade, so it understates today's yield. "
             "The +$3.60M matches the 3rd edition's cash-at-4% estimate to the decimal - the paper "
             "promise and the built asset agree."),
    ('fig', 'fig_alloc.png',
     "The validated portfolio before and after: the 76% idle cash becomes 75% three-month bills, the "
     "Treasury fund halves, everything else barely moves. Same safety, +$1.73M a year of carry on the "
     "fitted data."),

    ('h2', 'Honest caveats'),
    ('bullets', [
        "The series is constructed from a constant-maturity yield, not a fund's tick-for-tick NAV; "
        "the BIL cross-check quantifies the difference at about 16bp a year plus tracking noise.",
        "The fitted carry (1.81% a year) looks backward across a zero-rate decade; the current-rate "
        "sensitivity (4.17%, Fed H.15 release of 6 Nov 2026) shows the same run at today's rates. "
        "Both are stated; neither is a promise about next year.",
        "The bill's tiny price term means it can lose a little in a week when rates jump; the worst "
        "week in 45 years of data is -0.16%, and the held-out checks include it.",
        "Bills answer \"the safe pile was idle\". They do not fix the open model risks (crisis tails, "
        "the uncalibrated model-wrongness margin, volatility clustering), which are unchanged and "
        "listed in section 19.",
    ]),

    ('h1', '22. The loss limits, plainly: who set them, and what actually binds'),
    ('p', "You asked where the current drawdown limit comes from - who sets it, and with which "
          "parameter. Here is the exact answer, including the uncomfortable part."),

    ('h2', 'The two loss limits and where they live'),
    ('table',
     ['Parameter', 'Value', 'What it caps', 'Set by'],
     [['loss_budget', '0.15', 'worst allowed loss at the very end of the year, in the bad tail of fresh '
       'held-out paths', 'development default'],
      ['cml_budget', '0.06', 'worst allowed loss at ANY point along the path (the deepest drawdown), '
       'in the bad tail', 'development default']],
     [0.16, 0.10, 0.50, 0.24]),
    ('p', "Both were introduced as development defaults when the engine was packaged on 7 November "
          "(commit 6606df4). They were not in Dmitry's original engine, and there is no record that "
          "you chose them. What you did choose: the 20% per-payment tail allowance, the $250k monthly "
          "amount, and the one-year horizon. The 6% and 15% caps are, in other words, a careful "
          "engineer's placeholder that became load-bearing - this report now treats them as your "
          "decision to make, with the menu below."),

    ('h2', 'Which limit actually drives the cash share'),
    ('p', "Only the 6% any-point cap binds. The raw optimizer's pick (35.5% cash, score $100.1M) "
          "fails exactly one check: the held-out path-loss tail, which is the cml_budget. The 15% "
          "final-loss cap is slack: sweeping it from 10% to 30% changes nothing - the selected mix "
          "is bit-for-bit identical at every point of the sweep. (An interim answer during the day "
          "said both caps bind; that was wrong, and this is the correction.)"),
    ('p', "And the payments do not drive it either. The twelve per-payment tests pass at every tested "
          "mix - even the raw optimizer's 35.5%-cash mix funds every payment on every fresh path. At "
          "$50k a month the year's $0.6M is covered by the safe pile for over a century; at $250k it "
          "is covered for decades. The reason the portfolio sits at 75% bills is not the payout "
          "schedule. It is the 6% any-point loss cap, applied to the whole $100M balance sheet: the "
          "engine will not accept a mix whose bad-tail drawdown exceeds about $6M at any point in the "
          "year, and only a bill-heavy mix survives that test."),

    ('h2', 'The menu: what moving the any-point cap does'),
    ('fig', 'fig_caps.png',
     "The any-point loss cap, moved one dial at a time (labeled sensitivity, same frozen engine). At "
     "3% nothing is acceptable; at 10% riskier mixes pass validation, but the T-bill mix selected "
     "there fails the final held-out judge - reported, not certified."),
    ('table',
     ['Any-point cap', 'Outcome'],
     [['3%', 'engine refuses: no mix passes validation at all'],
      ['6% (current)', 'the validated answers in this report (75% bills, $99.98M)'],
      ['10%', 'validation selects a riskier mix (about 48% safe, score ~$101M), but the final '
       'independent judge rejects it: the optimum is flat near the boundary and the winner does not '
       'hold up on fresh paths. Reported, not certified'],
      ['15% final-loss cap moved 10-30% instead', 'nothing changes: that cap is not binding anywhere '
       'in the sweep']],
     [0.24, 0.76]),
    ('p', "The honest reading: the 6% number is doing enormous work - it is worth several percent of "
          "safe share either way - and it was never consciously chosen. That is a decision worth "
          "making with your eyes open. The engine's job is to show you the trade (the table above), "
          "not to make it for you."),

    ('h1', '23. Longer horizons: 10, 20 and 30 years'),
    ('p', "Your question: over a longer horizon - 10 to 30 years - there will be an increase, so how "
          "should the engine account for that properly? First the plain answer, then the numbers."),

    ('h2', 'The plain answer'),
    ('p', "You are right that the balance grows over longer horizons - at $250k a month you are "
          "paying out 3% a year of a pile whose safe core alone yields about that at current rates, "
          "so almost any mix keeps up. The catch is the path, not the destination: over 30 years, a "
          "mix with meaningful equity will at some point be down far more than 6% - that is near "
          "certain, not bad luck. A one-year loss limit of 6% at any point, carried unchanged to 30 "
          "years, forbids exactly the asset classes that make the long run pay. So accounting for "
          "the long run properly does NOT mean keeping today's limits and hoping; it means giving "
          "the loss budget a horizon: tight for money needed soon, looser for money not needed for "
          "decades. And a warning from the literature against the naive version of your intuition: "
          "Bodie (1995) proved that the cost of insuring a stock portfolio against underperforming "
          "bills RISES with the horizon - time diversifies average returns, but it does not make "
          "stocks safe, and it must not be used as a license to ignore drawdowns."),

    ('h2', 'The numbers (labeled screen, fixed mixes, fresh-path judge)'),
    ('p', "Four fixed mixes from 90% safe to 30% safe, run at the confirmed $250k/month over 10, 20 "
          "and 30 years, judged on fresh simulated futures. Because the cvxpy optimizer does not "
          "scale past one year, this is a labeled screen over fixed candidate mixes rather than a "
          "re-optimized selection - the honest way to look before building the real multi-year "
          "validator. Payments: $30M total over 10 years, $60M over 20, $90M over 30."),
    ('table',
     ['Mix', '10y median end', '20y median end', '30y median end', 'Every payment made?', 'Passes the '
      'current loss limits?'],
     [['90% bills', '$90M', '$79M', '$68M', 'yes, at every horizon', 'yes (10y, 20y); yes at 30y on '
       'fresh paths after a validation-boundary wobble'],
      ['70% safe', '$108M', '$132M', '$196M', 'yes', 'passes the final judge at 10y and 20y; fails '
       'at 30y'],
      ['50% safe', '$123M', '$187M', '$334M', 'yes', 'fails at every horizon'],
      ['30% safe', '$139M', '$243M', '$483M', 'yes', 'fails at every horizon']],
     [0.13, 0.15, 0.15, 0.15, 0.16, 0.26]),
    ('fig', 'fig_horizon.png',
     "Median wealth at the end of each horizon, by mix. Every mix makes every payment at every "
     "horizon. The x marks the mixes the current one-year loss limits reject - which over 30 years "
     "is almost everything with equity in it."),
    ('p', "Read the first row slowly: the \"safest\" mix makes every payment and STILL shrinks the "
          "fortune to a median $68M over 30 years, because it pays out $90M while earning little "
          "above the payout. The growth mixes pay the same $90M and end two to five times richer. "
          "That is your intuition confirmed with numbers. And the right-hand column is the problem "
          "stated precisely: the current limits cannot tell these mixes apart in the way a 30-year "
          "plan needs, because a 6% any-point cap is a one-year idea."),
    ('bullets', [
        "What \"properly\" looks like: a loss budget per horizon (for example, tight caps on money "
        "needed within 1-3 years, a much wider drawdown allowance for the long-run sleeve), then "
        "re-run the validated selection under those budgets. That is a designed next step, not yet "
        "built into the validator - section 19 lists it as open work.",
        "Caveats that come with every number above: the model is nominal (no inflation, so $483M in "
        "30 years is not $483M of today's purchasing power); the weekly law cannot manufacture "
        "multi-year storms (section 17), so long-run tails are understated for the riskier mixes; "
        "property is never sold; and all of it is model-driven simulation, not historical proof.",
    ]),
]
