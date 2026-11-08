"""Sensitivity-and-trade-offs chapter (owner ask 8 Nov 13:12 SGT, joint views
13:51 SGT). Blocks appended to the final report by content6.build_content.
Every dial varied one at a time around the round-2 validated point; same seed
family 20261109 throughout so only the dial changes; both carry views,
dual-law judging; noise band on a third family (20261111)."""
YEARS = [5, 10, 15, 20, 30]
KEYS = [f'{y}y' for y in YEARS]


def M(x):
    return f'${x / 1e6:,.1f}M'


def pct(x, dgt=0):
    return f'{x * 100:.{dgt}f}%'


def safe(cell):
    s = cell['search'].get('chosen_safe')
    return pct(s) if s is not None else 'none'


def build_sens(d):
    h5, sl, sl25, sp, spay, ss, t25 = (d['h5'], d['sl'], d['sl25'], d['sp'],
                                       d['spay'], d['ss'], d['t25'])
    B = []
    B += [
        ('h1', '6. Sensitivity and trade-offs: every dial open'),
        ('p', "This chapter treats every choice as a dial, not a default: horizon, the two loss limits, "
              "the execution policy and the payout size. Each dial is moved on its own around the "
              "validated answer, on the SAME simulated paths, so every difference inside a table is the "
              "dial alone. Both carry views (shrunk history and today's quotes) and both judging laws "
              "throughout. A third seed family repeats the key cells so you can see which differences "
              "are real and which are draw noise."),

        ('h2', '6.1 Horizon x terminal loss limit: the price of safety over time'),
        ('p', "The terminal limit caps how far below the starting wealth the plan may end, measured at "
              "the horizon end. Your default is 15%; here it runs 5-50% at every horizon."),
        ('fig', 'fig_sens_terminal.png',
         'Minimum validated T-bill share by horizon (x) and terminal loss limit (y). Left: fitted '
         'carry. Right: today\'s quotes. Same paths within each panel; 15% and 25% rows re-use the '
         'fresh sweeps, so every step in a column is the limit alone.'),
        ('bullets', [
            "Reading down a column: at 5y the limit barely matters (10-65% bills from loosest to "
            "tightest); at 30y even a 50% limit wants ~35-58% bills. The longer the horizon, the more "
            "any loss limit costs.",
            "Reading across a row: at the 5% limit the required bill share is extreme everywhere "
            "(45-88%) - a near-cash portfolio. At 15-25% the 5-15y answers cluster at 10-40%.",
            "The frozen 10y mix still fails the judge at 20-30y under EVERY tested limit up to 50% "
            "(fitted) - loosening the limit cannot rescue it there, because its problem is the terminal "
            "tail, not the limit level. Only re-solving the mix fixes it.",
        ]),

        ('h2', '6.2 The two loss limits together: which one binds'),
        ('p', "The any-point cap limits the worst dip at any moment; the terminal limit only the end. "
              "Swept together at 10/20/30y (any-point 5/15/25/40% x terminal 15/25%):"),
        ('fig', 'fig_sens_caps.png',
         'Minimum validated T-bill share by horizon (x) and any-point cap (y), terminal limit 15%. '
         'Left: fitted. Right: quotes. The 40% row is the base run; the cap bites below ~25%.'),
        ('bullets', [
            "At a 5% any-point cap the terminal limit is irrelevant: the cap binds first and forces "
            "72-88% bills at every horizon, at both 15% and 25% terminal. If you want a tight floor "
            "under the journey, the terminal limit becomes decoration.",
            "At 25-40% any-point, the terminal limit does the work at long horizons - the cap is slack "
            "and loosening it further buys nothing.",
            "So the two limits are substitutes, not complements: pick which event you actually fear "
            "(a deep mid-journey dip vs a bad ending) and set that one; the other can stay loose.",
        ]),

        ('h2', '6.3 Execution policy: rebalancing helps, a glide path helps more - neither replaces the mix'),
        ('p', "Five ways to run the same starting mix at 20y and 30y, same paths: mark-to-market "
              "(what the judge measures), cash-first with no rebalancing (drift), annual rebalancing, "
              "rebalancing only when the mix drifts 10 points, and a glide path whose bill target "
              "declines each year from the validated static share toward the 10y share."),
        ('fig', 'fig_sens_policy.png',
         'Upper bound on the terminal loss tail (lower is safer; the 25% and 15% limit lines marked) '
         'by policy, 20y and 30y, fitted view. The frozen-mix bar is the judged metric; every policy '
         'bar is the executed twin on the same paths.'),
        ('bullets', [
            "Drift is the enemy at long horizons: never rebalancing roughly doubles the tail loss vs "
            "the marked mix (20y fitted: 1.12 vs 0.68). Annual rebalancing claws most of that back; "
            "trading only on a 10-point drift does at least as well with less turnover.",
            "The glide path is the real answer to 'should rebalancing not handle the horizon?': "
            "rebalancing only ever returns to the SAME target; the glide moves the target as the "
            "remaining horizon shortens. At 30y it cuts the tail roughly in half vs a fixed target "
            "(quotes: 1.46 -> 0.49).",
            "But no policy passes a 25% terminal limit at 20-30y from the 10y starting mix - the "
            "starting bill share still has to be right. Policy decides how much of the theoretical "
            "safety you actually keep; the mix decides how much there is.",
            "Seed noise warning: on a third seed family the same policies rank the same but the "
            "levels move a lot (the frozen 20y mark-to-market tail reads 0.08-0.68 across families). "
            "Trust the ordering, not the second decimal.",
        ]),

        ('h2', '6.4 Payout size: it moves the score, not the safe share'),
        ('p', "$50k, $100k and $250k per month at 10/20/30y (only 12 months are owner-confirmed; "
              "longer payout streams are a labeled sensitivity):"),
        ('table',
         ['Horizon', 'Payout', 'Fitted: bills / score', 'Quotes: bills / score'],
         [[f'{y}y', f'${p}k',
           safe(spay['fitted'][f'{y}y_p{p}k']) + ' / ' + M(spay['fitted'][f'{y}y_p{p}k']['search']['common_cara_ledger_ce']),
           safe(spay['current_quotes'][f'{y}y_p{p}k']) + ' / ' + M(spay['current_quotes'][f'{y}y_p{p}k']['search']['common_cara_ledger_ce'])]
          for y in (10, 20, 30) for p in (50, 100)] +
         [[f'{y}y', '$250k',
           safe(h5['fitted'][f'{y}y']) + ' / ' + M(h5['fitted'][f'{y}y']['search']['common_cara_ledger_ce']),
           safe(h5['current_quotes'][f'{y}y']) + ' / ' + M(h5['current_quotes'][f'{y}y']['search']['common_cara_ledger_ce'])]
          for y in (10, 20, 30)],
         [0.12, 0.12, 0.38, 0.38]),
        ('bullets', [
            "The safe share barely moves with the payout (20y fitted: 60% bills at $50k, $100k and "
            "$250k alike) - the loss limits, not the payments, set it. What the payout moves is the "
            "score: 20y fitted certainty equivalent falls from ~$166M at $50k/month to ~$104M at "
            "$250k/month.",
            "For the family-office question 'what can we safely spend?': the binding lever is how "
            "much wealth the limits let you risk, not the monthly cheque - until the cheque itself "
            "breaks funding, which even $250k/month does not at these horizons.",
        ]),

        ('h2', '6.5 How much of this is real: the seed-noise band'),
        ('fig', 'fig_sens_seeds.png',
         'Minimum validated T-bill share at the 15% and 25% terminal limits, fitted view, on three '
         'independent seed families. The band between families is the honest uncertainty on any '
         'single run.'),
        ('bullets', [
            "Across three seed families the required bill share at a given cell moves by up to "
            "~20 points (fitted 10y at 25%: 10% / 45% / 40% by family). The ORDER of dials is stable; "
            "the exact share is not.",
            "Treat every number in this chapter as the centre of a band roughly +/-10-15 points "
            "wide, and every recommendation as a range - 'about half to two-thirds bills at 20-30y' "
            "- never a single figure.",
        ]),

        ('h2', '6.6 What this means for the family office'),
        ('bullets', [
            "A spending policy, not a portfolio: pick the horizon and the payout, and the model "
            "hands back the safe sleeve and the cost of it in expected wealth.",
            "One rule of thumb survives every dial: horizon dominates. Long money needs a big bill "
            "sleeve no matter how you rebalance or what you spend.",
            "The two safety limits are one choice, not two. Tight floor on the journey OR tight "
            "limit on the ending; setting both tight is the most expensive portfolio in this study.",
            "Review annually, rebalance on a wide band (~10 points), and let the target bill share "
            "glide down as the horizon shortens - that combination captured most of the available "
            "safety in every test.",
            "Honest edge of the model: seed bands are wide, the regime law is one way to be wrong, "
            "and taxes, illiquidity and fee drag are outside it. The numbers are a floor for "
            "prudence, not a promise.",
        ]),
    ]
    return B
