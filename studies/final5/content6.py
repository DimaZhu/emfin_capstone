"""Final report content: the owner's five questions, answered (8 Nov 2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report6_data import assemble  # noqa: E402
from content_sens import build_sens  # noqa: E402

YEARS = [5, 10, 15, 20, 30]
KEYS = [f'{y}y' for y in YEARS]


def M(x):
    return f'${x / 1e6:,.1f}M'


def pct(x, dgt=0):
    return f'{x * 100:.{dgt}f}%'


def build_content(d):
    h5, q4, charts, r2, fix6 = d['h5'], d['q4'], d['charts'], d['r2'], d['fix6']
    util = charts['utilities']
    bench = charts['benchmarks']
    rec = r2['current_quotes']['dual']
    alt = r2['fitted']['dual']

    SHORT = [
        "All five answers in one line each: (1) the utility formula barely matters - CARA, CRRA, HARA and "
        "the kinked objective pick the same mix within ~0.5% of score; (2) rebalance rarely - annual wins "
        "once trading costs are charged, by a small margin; (3) horizon is the biggest lever here - longer "
        "horizons need much larger T-bill shares, and just holding the 10-year mix fails the regime law at "
        "20+ years; (4) the in-period cap is cheap until it bites - at your 40% it costs nothing, at 5-10% "
        "it dominates everything; (5) clever has still not beaten simple.",
        "Everything new in this report was run on a fresh seed family (20261109), disjoint from all earlier "
        "studies, and judged under both market laws and both carry views. Where an older seed family says "
        "something different, both are shown.",
    ]

    CONTENTS = ("Inside: 1. Utility models - 2. Rebalancing frequency - 3. Investment horizon - "
                "4. The in-period limit - 5. Clever vs simple - 6. Sensitivity and trade-offs - "
                "7. What is most worth telling the group - "
                "Appendix: evidence and provenance")

    B = []
    # ---------- Q1 ----------
    B += [
        ('h1', '1. Utility models: CARA, HARA and the others barely move the answer'),
        ('p', "You asked how the choice of utility model - CARA, CRRA, HARA, or the kinked-shortfall "
              "objective - changes the outcome. Short answer: at your $250k/month it does not, to any "
              "degree that matters."),
        ('table',
         ['Objective', 'What it rewards', 'Bills + anchor', 'Score (10y, new model)'],
         [['CARA (surplus)', 'steady dollar aversion to missing the surplus target',
           pct(util['cara']['chosen_safe']), M(util['cara']['common_cara_ledger_ce'])],
          ['CRRA (gross wealth)', 'relative aversion on total wealth',
           pct(util['crra_gross']['chosen_safe']), M(util['crra_gross']['common_cara_ledger_ce'])],
          ['HARA (payment floor)', 'aversion that explodes near the payment floor',
           pct(util['hara_payment_floor']['chosen_safe']), M(util['hara_payment_floor']['common_cara_ledger_ce'])],
          ['Kinked shortfall', '5:1 extra penalty on falling short',
           pct(util['kinked_shortfall']['chosen_safe']), M(util['kinked_shortfall']['common_cara_ledger_ce'])]],
         [0.26, 0.36, 0.16, 0.22]),
        ('bullets', [
            "All scores are re-expressed on one common scale (the CARA cash-first ledger), so the table "
            "compares like with like. The spread between the four is about $0.5M on a $110M score.",
            "In the one-year study (identical paths, all four objectives, all-risk judge) the four picked "
            "the exact same portfolio. The reason is structural: your hard limits - fund every payment, "
            "40% worst-path cap, 15% terminal cap - bind long before the utility's appetite for risk gets "
            "a vote. The constraints, not the utility, set the safe share.",
            "The flavor only starts to matter in the stress fixtures where the plan is close to infeasible "
            "(e.g. $95M due at horizon: nobody has a valid candidate, and HARA's score is mathematically "
            "undefined below the floor). That is where a utility choice becomes a real decision - not at "
            "$250k/month.",
            "Payout size moves the safe share far more than the utility does: at $50k/$100k/$250k per "
            "month the validated mix is nearly unchanged because the loss caps, not the payments, bind.",
        ]),
        ('fig', 'fig_utility_freq.png',
         'Left: four objectives, same universe and limits, 10y - the scores sit within ~0.5% and the safe '
         'shares within 2.5 points. Right: rebalancing at 1y with fees, per market law; annual leads by a '
         'few tens of thousands of dollars.'),
    ]
    # ---------- Q2 ----------
    B += [
        ('h1', '2. Rebalancing frequency: rarely wins, and the prize is small'),
        ('p', "Monthly, quarterly, semiannual and annual rebalancing were compared on identical paths, "
              "same starting mix, same payments, with 5bp trading fees and one-week settlement - the "
              "realistic friction case."),
        ('table',
         ['Market law', 'Monthly', 'Quarterly', 'Semiannual', 'Annual / hold'],
         [['IID nominal', '98.217', '98.224', '98.230', '98.246'],
          ['Bounded nominal', '98.209', '98.216', '98.224', '98.241'],
          ['Equity drift -2pp/yr', '97.946', '97.950', '97.953', '97.962'],
          ['Drift -2pp, vol x1.2', '97.949', '97.953', '97.956', '97.964']],
         [0.34, 0.165, 0.165, 0.165, 0.165]),
        ('bullets', [
            "Scores are certainty equivalents in $M over the one-year test window; all 16 rows pass every "
            "risk and funding check. Annual wins in all four laws - by $15-32k, i.e. hundredths of a "
            "percent. Fees explain the ordering: monthly trading costs ~$1.7k/yr here, annual ~$0.",
            "At 3 and 5 years, no frequency passes all four laws under the unchanged budgets - reported, "
            "not hidden. Annual still ranks first by score ($54-174k over monthly), but that is a ranking "
            "of tested schedules, not a certified optimum.",
            "A fee-free 10y twin study (no buy-side cost, labeled) flips the sign: monthly scores "
            "marginally higher ($111.38M vs $110.84M buy-and-hold). So the honest rule is: at real fee "
            "levels, rebalance about annually; the decision matters less than every other choice in this "
            "report.",
            "Cleverer does not help: the learned feedback policy that watches funding, prices and momentum "
            "loses to its own first-trade-only twin in attribution, and the robust four-law search found "
            "no acceptable candidate at all.",
        ]),
    ]
    # ---------- Q3 ----------
    hrows = []
    for y, k in zip(YEARS, KEYS):
        f5 = h5['fitted'][k]['search']
        cq = h5['current_quotes'][k]['search']
        old = charts['horizon'][k]
        hrows.append([f'{y}y',
                      pct(old['chosen_safe']),
                      pct(f5['chosen_safe']) if f5.get('chosen_safe') is not None else 'none',
                      pct(cq['chosen_safe']) if cq.get('chosen_safe') is not None else 'none',
                      M(cq['common_cara_ledger_ce']) if cq.get('chosen_safe') is not None else '-',
                      'yes' if h5['current_quotes'][k]['hold_10y_mix']['final_pass'] else 'NO'])
    B += [
        ('h1', '3. Investment horizon: the biggest lever of the five'),
        ('p', "Same $250k/month, same limits (the 15% terminal cap sits at the end of each horizon, as you "
              "specified), horizons of 5, 10, 15, 20 and 30 years. New this report: the whole sweep re-run "
              "on a fresh seed family under both carry views and both judging laws."),
        ('table',
         ['Horizon', 'Earlier sweep\n(single law)', 'Fresh: fitted\nview', 'Fresh: current\nquotes',
          'Fresh: current\nquotes score', 'Holding the 10y\nmix works?'],
         hrows,
         [0.11, 0.20, 0.16, 0.17, 0.19, 0.17]),
        ('fig', 'fig_horizon.png',
         'Left: minimum validated T-bill share by horizon - the trend is steeply up, the wiggles are seed '
         'noise at a flat frontier. Right: the frozen 10-year mix simply held to other horizons - fine to '
         'about 15 years, rejected by the regime law at 20+.'),
        ('bullets', [
            "The trend is the answer: the longer the money must last, the larger the safe share the judge "
            "demands - from ~10-25% bills at 5 years to ~45-68% at 20-30 years. More time is more chances "
            "for a deep drawdown before the last payment, and the 15% terminal cap has to survive all of "
            "them.",
            "The wiggles are honest noise: at 10y the fresh fitted run validates at 12.5% bills where the "
            "round-2 seed family needed 32.5%. The score difference between those cells is small; the "
            "frontier is flat, so the exact minimum is seed-sensitive. Do not read precision into any one "
            "cell - read the slope.",
            "CE levels across horizons are NOT comparable: 30 years pays out $90M of the $100M, 5 years "
            "pays $15M. The rising scores at long horizons mostly reflect more years of compounding on "
            "what is left, not a better deal.",
            "Practical: the current 10y answer is robust for horizons up to about 15 years. If the real "
            "mandate is 20+ years, the mix must be re-solved for that horizon - holding the 10y mix fails "
            "the regime law's terminal-loss check at 20 and 30 years on fresh paths.",
        ]),
    ]
    # ---------- Q4 ----------
    qrows = []
    loose_f = max(v['common_cara_ledger_ce'] for v in q4['fitted'].values())
    loose_c = max(v['common_cara_ledger_ce'] for v in q4['current_quotes'].values())
    for c in [0.05, 0.10, 0.15, 0.25, 0.40, 0.60]:
        f5c = q4['fitted'][f'{c:.2f}']
        cqc = q4['current_quotes'][f'{c:.2f}']
        qrows.append([pct(c),
                      pct(f5c['chosen_safe']) + ' / ' + M(f5c['common_cara_ledger_ce']),
                      M(loose_f - f5c['common_cara_ledger_ce']),
                      pct(cqc['chosen_safe']) + ' / ' + M(cqc['common_cara_ledger_ce']),
                      M(loose_c - cqc['common_cara_ledger_ce'])])
    B += [
        ('h1', '4. The in-period limit: free until it bites, then it owns the portfolio'),
        ('p', "The in-period (any-point) cap limits how far underwater the plan may go at any moment, not "
              "just at the end. Your default is 40% with a 15% terminal limit. Fresh 10y sweep, both "
              "views, terminal limit fixed at 15%:"),
        ('table',
         ['Any-point cap', 'Fitted: bills / score', 'Fitted: below\nbest cell', 'Quotes: bills / score', 'Quotes: below\nbest cell'],
         qrows,
         [0.14, 0.24, 0.14, 0.26, 0.14]),
        ('fig', 'fig_inperiod.png',
         'Left: score vs the any-point cap at a fixed 15% terminal limit (fresh seeds). Right: the full '
         'two-limit grid from the earlier seed family - the box marks your 40% / 15% defaults.'),
        ('bullets', [
            "At your 40% the cap is slack: loosening it to 60% changes nothing, because the 15% terminal "
            "limit binds first. Tightening to 25% costs the fitted view about $1.3M; to 15%, about "
            "$6.7M; to 5%, over $21M and 87.5% of the portfolio in bills.",
            "Under current quotes the same pattern with smaller costs (bill carry does more of the work): "
            "the 15% in-period cap even scores slightly above the 40% cell - a flat-frontier wiggle, not "
            "a free lunch; the 5-10% caps still cost $3-5M.",
            "So the choice is genuinely yours: the cap is cheap insurance at 25-40% and very expensive "
            "below ~15%. If the point of the cap is 'never show the client a scary number', 15% costs "
            "roughly $4-7M of score; 40% costs nothing but allows deep interim drawdowns.",
        ]),
    ]
    # ---------- Q5 ----------
    brows = []
    for k, lab in [('clever (validated mix)', 'Clever: the validated mix'),
                   ('reserve payouts, rest risky', 'Reserve payouts, rest risky'),
                   ('equal weight (1/N)', 'Equal weight (1/N)'),
                   ('60/40-style (60% stocks, 30% bills)', '60/40-style'),
                   ('all T-bills + property', 'All T-bills + property')]:
        e = bench[k]
        verdict = 'passes' if (e['validation_pass'] and e['final_pass']) else \
            ('FAILS validation' if not e['validation_pass'] else 'FAILS final')
        brows.append([lab, M(e['common_cara_ledger_ce']), verdict])
    B += [
        ('h1', '5. Clever vs simple: simple has not been beaten'),
        ('p', "Benchmarking the validated mix against the plain alternatives on identical paths, under the "
              "same safety judge (10y new model):"),
        ('table', ['Candidate', 'Score', 'Safety judge'], brows, [0.42, 0.20, 0.30]),
        ('fig', 'fig_benchmarks.png',
         'Green passes the full judge, red fails it. Two simple mixes score above the validated mix - and '
         'neither survives the safety checks that produced it.'),
        ('bullets', [
            "The honest nuance: 'reserve payouts, rest risky' scores $1.4M MORE than the validated mix - "
            "on paths it was then rejected by. Scoring higher while failing the judge is not winning; the "
            "judge is the point.",
            "The historical record agrees: 19 frozen annual holdouts of real history, matched objectives, "
            "152 outer refits - no objective formula, forecast model or trading rule beat the plain fixed "
            "mix once safety was enforced.",
            "The frozen policy-by-model matrix (5th edition): the two 1y-sleeve mixes and the two 10y-"
            "sleeve mixes sit within a few $M of each other under every law, including the regime law and "
            "real terms. No policy wins everywhere; complexity never wins anywhere.",
            "The clairvoyant relaxation (a cheater who sees next week's returns) bounds any policy at "
            "$197-253M - far above everything tested. There is no near-optimality certificate; what we can "
            "say is narrower and stronger: nothing implementable that we tested beat the simple mix.",
        ]),
    ]
    # ---------- sensitivity chapter ----------
    B += build_sens(d)
    # ---------- extras ----------
    real = d['real']['real_repricing']
    B += [
        ('h1', '7. Most worth telling the group'),
        ('bullets', [
            f"The inflation illusion: the recommended mix scores {M(rec['common_cara_ledger_ce'])} nominal "
            f"but {M(real['current_quotes']['common_cara_ledger_ce'])} in today's dollars. No fixed mix "
            "passes a 15% real final-loss limit; the tightest real limits are about 45% worst-path / 40% "
            "final. Nominal safety is partly inflation.",
            f"Two honest answers beat one fake one: fitted history says hold {pct(alt['chosen_safe'])} "
            f"bills ({M(alt['common_cara_ledger_ce'])}), today's quotes say {pct(rec['chosen_safe'])} "
            f"({M(rec['common_cara_ledger_ce'])}), because bills pay 4.17% now vs ~1.8% in the shrunk "
            "history. The engine shows both and does not average them.",
            "Flat optima are treacherous: the true 10y solve reallocates most of the risky sleeve between "
            "seeds while the score moves ~$1M. An optimizer that swings wildly is telling you the objective "
            "is flat, not that the data changed.",
            "The model-wrongness margin is a budget, not a calibration: a statistically real Wasserstein "
            "radius is ~100,000x the placeholder and unaffordable under the payment budgets. Choose the "
            "budget, then the margin - not the reverse.",
            "Hard limits dominate preferences: with a 99% funding rule and loss caps, the utility function "
            "is nearly irrelevant. Groups often spend weeks on the objective and minutes on the "
            "constraints; here the constraints did all the work.",
            "Data rights note for sharing: the histories are Yahoo-sourced for private research; the "
            "report is fine to discuss, the data bundle is not cleared for redistribution.",
        ]),
        ('pagebreak',),
        ('h1', 'Appendix. Evidence and provenance'),
        ('bullets', [
            "New in this report (seed family 20261109, disjoint from all earlier studies): horizon sweep "
            "5/10/15/20/30y and the in-period cap slice, both carry views, dual-law judging "
            "(studies/final5/results/).",
            "Carried in unchanged: utility comparison (7 Nov, 1y + 10y new-model), rebalancing frequency "
            "(1y/3y/5y with fees; 10y fee-free twin), benchmarks and the new-model cml sweep (seed "
            "20261107), round-2 dual-law mixes, true-10y solves, real-terms repricing (seed 20261108).",
            "Score definition: certainty equivalent - the guaranteed dollar amount after all payments "
            "worth exactly as much as the risky plan, expressed on the common CARA cash-first ledger.",
            "Judge: frozen mixes on independent paths under the mixture law and the EWMA regime/bootstrap "
            "law; funding (99% all-payments), per-payment tails within the 20% allowance, 40% any-point "
            "and 15% terminal loss caps. Passing is a statement about the model, never a guarantee.",
            "Every results file is SHA-256-stamped in studies/RUN_MANIFEST.json (code commit, configs, "
            "data, scripts, package versions). The refactor plan for the shared accounting engine is "
            "docs/REFACTOR_PLAN_SHARED_ACCOUNTING.md - not started, as agreed.",
            "Private research for Tijs de Boer. Placeholder client ($100M, $250k/month); not investment "
            "advice; only 12 months of payments are owner-confirmed.",
        ]),
    ]
    return SHORT, CONTENTS, B


if __name__ == '__main__':
    d = assemble()
    s, c, b = build_content(d)
    print(len(b), 'blocks')
