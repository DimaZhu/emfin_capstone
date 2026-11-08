"""Standalone explained document: the Ballast funding-risk engine for a reader
new to the topic. Plain words, terms defined in line, main takeaways with the
sensitivity findings and their honest caveats. Chapter 7 of the final report
('Most worth telling the group') is deliberately left out (owner ask, 8 Nov).
All numbers come from the frozen results in studies/final5/results/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report6_data import assemble  # noqa: E402


def M(x):
    return f'${x / 1e6:,.1f}M'


def pct(x, dgt=0):
    return f'{x * 100:.{dgt}f}%'


def safe(cell):
    s = cell['search'].get('chosen_safe')
    return pct(s) if s is not None else 'none'


def build_content(d):
    h5, spay = d['h5'], d['spay']
    bench = d['charts']['benchmarks']

    SHORT = [
        "A wealthy family must pay out $250k every month from a $100M portfolio without ever missing a "
        "payment and without losing more than agreed limits along the way. The Ballast engine answers "
        "one question: how much of the money must sit in safe T-bills, and how much can stay in stocks, "
        "gold and property?",
        "The biggest lever is time. Money that must last 5 years needs about 10-25% in T-bills; money "
        "that must last 20-30 years needs about half to two-thirds. The loss limits, the payout size "
        "and the choice of mathematical objective all matter less.",
        "Every number in this document is the centre of a band roughly 10-15 percentage points wide, "
        "because simulated futures differ. The orderings are stable; the exact figures are not.",
    ]

    CONTENTS = ("Inside: 1. The problem in plain words - 2. The words used here - "
                "3. The main takeaways - 4. What this document does not claim")

    B = []
    # ---------- 1. The problem ----------
    B += [
        ('h1', '1. The problem in plain words'),
        ('p', "Imagine a single-family office: one wealthy family, one pool of money, and a standing "
              "obligation to spend it. The placeholder client in this study has $100M, must pay out "
              "$250k every month for 12 months, and holds 10% of wealth in a property that cannot be "
              "sold. The question is not how to get rich; it is how to be sure the payments are always "
              "met, how much can be lost on the way, and what is likely to be left over."),
        ('p', "The Ballast funding-risk engine answers that question by simulation. It proposes an "
              "investment mix - a split between safe US Treasury bills and a risky sleeve of US and "
              "emerging-market stocks, gold and the property - then tests that mix on thousands of "
              "simulated market futures. A mix only counts if it obeys every hard rule in every "
              "future: every payment met, no dip deeper than the agreed limit at any moment, and the "
              "end-of-plan loss inside its own limit. Among the mixes that pass, the engine keeps the "
              "one expected to leave the most behind."),
        ('fig', 'fig_x_flow.png',
         'How the engine works: the setup goes in, a mix is proposed, thousands of simulated futures '
         'test it, and only mixes that obey every rule count.'),
        ('p', "Everything in this document comes from that process, run on real market histories "
              "(Yahoo Finance data) and judged under two different models of how markets behave. "
              "Nothing here is investment advice, and the client is a placeholder - no real family's "
              "numbers have been fed in yet."),
    ]
    # ---------- 2. The words ----------
    B += [
        ('h1', '2. The words used here'),
        ('p', "Six terms carry the whole document. They are defined once here and then used without "
              "further ceremony."),
        ('table',
         ['Term', 'What it means here'],
         [['T-bills / the safe sleeve', 'US Treasury bills - short-term government loans that pay a known, '
           'modest yield. The safe part of the mix.'],
          ['The risky sleeve', 'US and emerging-market stocks and gold, plus the locked property. Higher '
           'expected return, real possibility of deep losses.'],
          ['The score', 'The certainty equivalent: the guaranteed dollar amount, after all payments, that '
           'would feel exactly as good as running the risky plan. Higher is better; it is not a forecast.'],
          ['The judge', 'The set of hard rules a mix must pass on every simulated future: fund every '
           'payment (with a 99% bar and a small per-payment allowance), never dip more than 40% at any '
           'moment, and end no more than 15% below the starting wealth. Passing is a statement about the '
           'model, never a guarantee.'],
          ['Market laws and seed families', 'The simulated futures are drawn under two different models of '
           'market behaviour, and each fresh draw of futures is called a seed family. Re-running on a new '
           'family shows which conclusions are real and which are luck of the draw.'],
          ['Two views of T-bill yield', '"Shrunk history" fits T-bill carry to long history (about 1.8% a '
           'year). "Today\'s yields" uses the current quote (4.17%). Both are shown side by side; the '
           'engine does not average them.'],
          ['Horizon', 'How long the money must last - the payouts continue and the loss limits apply until '
           'the horizon ends. The plan\'s default studies run at 5, 10, 15, 20 and 30 years.'],
          ['The two loss limits', 'The any-point cap (40% by default) limits how far underwater the plan '
           'may go at any moment. The terminal limit (15% by default) limits the loss measured only at '
           'the end of the horizon.']],
         [0.24, 0.76]),
    ]
    # ---------- 3. Main takeaways ----------
    B += [
        ('h1', '3. The main takeaways'),

        ('h2', '3.1 Time is the biggest lever: long money needs a big safe sleeve'),
        ('p', "The longer the money must last, the larger the share the judge demands in T-bills - from "
              "about 10-25% at 5 years to about half to two-thirds at 20-30 years. More time means more "
              "chances for a deep market fall before the last payment, and the 15% end-of-plan limit has "
              "to survive all of them."),
        ('fig', 'fig_x_horizon.png',
         'Minimum T-bill share the judge requires, by how long the money must last. The trend is steeply '
         'up under both yield views; the wiggle at 10 years is draw noise, not a real dip.'),
        ('bullets', [
            "A mix solved for 10 years cannot simply be held for 20 or 30: tested on fresh futures, the "
            "10-year answer passes the judge to about 15 years and fails the end-of-plan check at 20 and "
            "30. Longer mandates need their own solve.",
            "Scores across horizons are not comparable: 30 years pays out $90M of the $100M, 5 years pays "
            "$15M, so long-horizon scores mostly reflect more years of compounding on what is left.",
        ]),

        ('h2', '3.2 The two loss limits are one choice, not two'),
        ('p', "The any-point cap and the terminal limit turn out to be substitutes. Tighten the journey "
              "and the ending takes care of itself; tighten the ending and a loose journey limit costs "
              "almost nothing. Setting both tight is the most expensive portfolio in the study."),
        ('fig', 'fig_x_terminal.png',
         'The price of safety: T-bill share required by horizon and end-of-plan loss limit. Reading down '
         'a column, tighter limits demand more bills; reading across, longer horizons demand more bills.'),
        ('bullets', [
            "At the 40% default the any-point cap is slack: loosening it to 60% changes nothing, because "
            "the 15% terminal limit binds first. Tightening the cap to 25% costs about $1.3M of score "
            "(shrunk history), to 15% about $6.7M, and to 5% over $21M with 87.5% of the portfolio forced "
            "into bills.",
            "At a 5% any-point cap the terminal limit becomes decoration: the cap binds first and forces "
            "72-88% bills at every horizon.",
            "So the real question is which event is actually feared - a deep mid-journey dip on a client "
            "statement, or a bad ending - and to set that one limit tight and leave the other loose.",
        ]),

        ('h2', '3.3 Rebalance rarely, on a wide band, and let the safe target glide down'),
        ('p', "How the mix is run matters much less than the mix itself. At realistic trading fees, "
              "rebalancing once a year beats monthly by only $15-32k a year - hundredths of a percent. "
              "What does matter at long horizons is not standing still: never rebalancing roughly doubles "
              "the worst end-of-plan loss, and a glide path - letting the T-bill target fall each year as "
              "the end approaches - cuts it by about half versus a fixed target."),
        ('fig', 'fig_x_policy.png',
         'Five ways to run the same starting mix on the same simulated futures. Never rebalancing is the '
         'worst; yearly rebalancing or a wide drift band recover most of the safety; the glide path is '
         'best. No policy rescues a starting mix that is too risky.'),
        ('bullets', [
            "No execution policy passes a 25% terminal limit at 20-30 years from the 10-year starting mix "
            "- the starting safe share still has to be right. Policy decides how much of the theoretical "
            "safety the plan keeps; the mix decides how much there is.",
            "Clever has not beaten simple anywhere in the study: the learned policy that watches funding, "
            "prices and momentum loses to its own first-trade-only twin, and the mathematical objective "
            "(CARA, CRRA, HARA or the kinked-shortfall formula) moves the answer by less than 0.5% "
            "because the hard limits bind long before the objective gets a vote.",
        ]),

        ('pagebreak',),
        ('h2', '3.4 The payout size moves the score, not the safe share'),
        ('p', "Varying the monthly payout from $50k to $250k barely changes the safe share the judge "
              "requires - the loss limits, not the payments, set it. What the payout moves is what the "
              "plan is worth: at a 20-year horizon the score falls from about $166M at $50k a month to "
              "about $104M at $250k (shrunk-history view)."),
        ('table',
         ['Horizon', 'Payout', 'T-bills / score (shrunk history)', 'T-bills / score (today\'s yields)'],
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
            "For the family-office question 'what can we safely spend?': the binding lever is how much "
            "wealth the limits allow to be risked, not the monthly cheque - until the cheque itself "
            "breaks funding, which even $250k a month does not at these horizons.",
            "Only 12 months of payouts are owner-confirmed; the 20 and 30-year payout streams are a "
            "labeled sensitivity, not the agreed plan.",
        ]),

        ('h2', '3.5 Simple has not been beaten'),
        ('p', "The validated mix was benchmarked against the plain alternatives on identical futures "
              "under the same judge. Two simple mixes score higher than the validated mix - and both fail "
              "the safety checks that produced it. Scoring higher while failing the judge is not winning; "
              "the judge is the point."),
        ('table', ['Candidate', 'Score', 'Safety judge'],
         [[lab, M(bench[k]['common_cara_ledger_ce']),
           'passes' if (bench[k]['validation_pass'] and bench[k]['final_pass']) else
           ('FAILS validation' if not bench[k]['validation_pass'] else 'FAILS final')]
          for k, lab in [('clever (validated mix)', 'The validated mix'),
                         ('reserve payouts, rest risky', 'Reserve payouts, rest risky'),
                         ('equal weight (1/N)', 'Equal weight (1/N)'),
                         ('60/40-style (60% stocks, 30% bills)', '60/40-style'),
                         ('all T-bills + property', 'All T-bills + property')]],
         [0.42, 0.20, 0.30]),
        ('bullets', [
            "The historical record agrees: 19 frozen annual holdouts of real history, with the model "
            "re-fitted 152 times on data available at the time, show no objective formula, forecast model "
            "or trading rule beating the plain fixed mix once safety was enforced.",
            "There is no proof the validated mix is the best possible - a theoretical cheater who sees "
            "next week's returns scores $197-253M, far above everything tested. What the evidence shows "
            "is narrower and stronger: nothing implementable that was tested beat the simple mix.",
        ]),

        ('h2', '3.6 Every number is a band, not a point'),
        ('p', "Re-run the whole study on three independent sets of simulated futures and the required "
              "T-bill share at any given setting moves by up to about 20 percentage points (at 10 years "
              "with a 25% terminal limit: 10%, 45% and 40% by family). The orderings - horizon dominates, "
              "the glide path wins, drift is worst - are stable across all three. The exact figures are "
              "not."),
        ('fig', 'fig_x_seeds.png',
         'The honest uncertainty: minimum T-bill share by horizon on three independent seed families, '
         'with the min-max range labelled at each horizon. Read the slope and the band, never one cell.'),
        ('bullets', [
            "Treat every figure in this document as the centre of a band roughly 10-15 points wide, and "
            "every conclusion as a range: 'about half to two-thirds in T-bills at 20-30 years', never a "
            "single number.",
        ]),
    ]
    # ---------- 4. Caveats ----------
    B += [
        ('h1', '4. What this document does not claim'),
        ('bullets', [
            "The client is a placeholder: $100M, $250k a month for 12 months, 10% locked property. No "
            "real family-office inputs exist yet, so every dollar figure is illustrative.",
            "Simulated futures are not the future. The two market laws are two ways to be wrong, the "
            "seed bands are wide, and taxes, illiquidity and fee drag beyond the tested 5bp trading "
            "cost are outside the model. The numbers are a floor for prudence, not a promise.",
            "Scores are certainty equivalents - a yardstick for comparing plans on identical futures - "
            "not forecasts of what anyone will actually end up with.",
            "The market histories are Yahoo-sourced for private research. This document is fine to "
            "discuss; the underlying data bundle is not cleared for redistribution.",
            "Nothing here is investment advice.",
        ]),
        ('note', "Built from the frozen results of the final five-question report and its sensitivity "
                 "chapter (8 November 2026, seed families 20261109-20261111). Every results file is "
                 "SHA-256-stamped in the repository's run manifest: code commit, configs, data and "
                 "package versions. The full report, with the utility, rebalancing and horizon studies "
                 "behind these takeaways, is ballast-final-sensitivity-20261108.pdf."),
    ]
    return SHORT, CONTENTS, B
