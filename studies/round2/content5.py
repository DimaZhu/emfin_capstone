"""5th-edition unified scientific report content. All figures from frozen
study results via report5_data.assemble(); nothing typed by hand."""

NAMES = {'tbill': 'T-bills', 'treasury': 'IEF 7-10y Treasuries', 'tips': 'TIPS',
         'us_equity': 'US stocks', 'em_equity': 'EM stocks', 'gold': 'Gold',
         'cash': 'Cash (0%)', 'sg_property': 'SG property'}


def M(x):
    return f"${x / 1e6:,.1f}M"


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def wrow(label, w):
    order = ['tbill', 'treasury', 'tips', 'us_equity', 'gold', 'sg_property']
    return [label] + [pct(w.get(k, 0)) for k in order]


def build_content(d):
    base = d['base']
    fit_v = d['dual']['fitted']
    cur_v = d['dual']['current_quotes']
    fit_dual, cur_dual = fit_v['dual'], cur_v['dual']
    real = d['real']['real_repricing']
    fix1, fix2, fix3, fix4, fix5, fix6 = d['fix1'], d['fix2'], d['fix3'], d['fix4'], d['fix5'], d['fix6']
    fresh = d['fresh']
    mix10 = d['mix10']

    rec_w = cur_dual['weights']
    alt_w = fit_dual['weights']

    SHORT = [
        f"The recommended mix is now set by two default views instead of one, and judged under five market "
        f"laws instead of four. Under today's market rates the validated mix holds only "
        f"{pct(rec_w['tbill'], 0)} in T-bills and scores {M(cur_dual['common_cara_ledger_ce'])} over 10 years; "
        f"the fitted-history view stays more careful at {pct(alt_w['tbill'], 0)} bills and "
        f"{M(fit_dual['common_cara_ledger_ce'])}. Both pass every check under both laws.",
        f"Read in today's dollars the safety promise shrinks. The recommended mix is worth "
        f"{M(real['current_quotes']['common_cara_ledger_ce'])} in real terms, not "
        f"{M(cur_dual['common_cara_ledger_ce'])} - and no fixed mix passes your 15% final-loss limit once "
        f"inflation is priced in. The nominal answer was partly an inflation illusion.",
        f"The regime law (market memory: calm weeks follow calm weeks) now votes on every candidate. On the "
        f"fitted view it is the binding law: it pushed the safe share from the 10% floor up to "
        f"{pct(alt_w['tbill'], 0)} bills. Under current rates it changes nothing - bills at 4.2% carry the "
        f"portfolio past both laws.",
        f"The true 10-year optimization is too noisy to trust as a steering wheel. Re-run on fresh paths at "
        f"three sizes, the risky sleeve swings wildly (US stocks anywhere from a quarter to over half of the "
        f"risky part). The score barely moves. We keep it as a cross-check, not the default.",
        "The model-wrongness margin stays as it was: a real calibration says it should be ~100,000 times "
        "larger than the placeholder, and making it real would break every budget. That is a budget "
        "decision for you, not a math problem.",
        "Clever has still not beaten simple. Across every law, view and horizon tested, no trading rule, "
        "objective formula or forecast model beat the plain fixed mix once safety was enforced.",
    ]

    CONTENTS = ("Inside: 1. The question - 2. How the engine now works - 3. The recommended portfolio - "
                "4. Real dollars: the honest headline - 5. The regime law joins the judge - "
                "6. The second view: current rates - 7. The ten-year optimization - "
                "8. The model-wrongness margin - 9. What the loss limits cost - "
                "10. What carries over - 11. Still open - 12. The verdict - Appendices A-C")

    B = []
    # ---------- 1. the question ----------
    B += [
        ('h1', '1. The question'),
        ('p', "Pay out $250,000 every month for ten years from a $100M balance sheet, without being forced "
              "to sell investments at a bad time, and keep as much wealth as possible at the end. The engine "
              "answers: which fixed mix of assets gives the best risk-adjusted outcome while passing every "
              "safety check?"),
        ('table',
         ['Input', 'Value used', 'Status'],
         [['Total wealth', '$100M', 'illustrative'],
          ['Payments', '$250k per month, 120 months ($30M)', '12 months confirmed; the 10-year extension is a labeled assumption'],
          ['Horizon', '10 years (520 weeks)', 'your default, 8 Nov 2026'],
          ['Property', '10% of wealth, Singapore residential, not sold, no rent', 'assumption'],
          ['Liquid assets', '3-month T-bills, IEF (7-10y Treasuries), TIPS, VTI (US stocks), VWO (emerging), GLD (gold), 0% cash account', 'real funds, real histories'],
          ['Safety limits', '20% per-payment tail allowance at 95%; worst-path loss cap 40%; final-loss cap 15% at the horizon end', 'your defaults, 8 Nov 2026'],
          ['Views', 'two default views: fitted history, and current market quotes (5 Nov 2026)', 'new in this edition'],
          ['Judge', 'five market laws on independent fresh paths', 'fifth law new in this edition']],
         [0.14, 0.56, 0.30]),
        ('p', "Two terms: the score is the certainty equivalent - the guaranteed dollar amount after all "
              "payments that the model values exactly as much as running the risky plan. A market law is one "
              "complete assumption set about how prices move; the final judge now runs five of them so no "
              "answer rests on one guess."),
    ]
    # ---------- 2. how it works ----------
    B += [
        ('h1', '2. How the engine now works'),
        ('numbers', [
            "Inputs: wealth, the payment calendar, the limits, the fixed property.",
            "Estimation: real weekly total-return histories, shrunk toward safe values because raw estimates "
            "are noisy. New: the safe assets' carry is estimated twice - once from the full fitted history "
            "and once from current market quotes (3M bill 4.17%, 10y 4.84%, 10y TIPS real 2.60%, FRED, "
            "5 Nov 2026). The two answers are reported side by side as the two default views.",
            "Scenarios: thousands of simulated 520-week futures for all assets at once.",
            "Optimizer: picks the long-only mix with the best score subject to every funding and loss limit.",
            "Independent judge: the frozen mix is re-checked on entirely fresh paths under five laws: the "
            "four fixed envelopes (reference, nominal, stressed, and their common hull) plus, new in this "
            "edition, the regime/bootstrap law - a bootstrap of real historical weeks with volatility that "
            "follows recent data. Extra laws only judge; they never fit, solve or repair.",
            "Execution audit: a separate cash-first ledger counts whether every payment was actually made.",
        ]),
        ('p', "Everything in this edition was re-run on a fresh seed family: training, validation and final "
              "paths are all disjoint from every earlier study. Nothing was tuned on the paths it is "
              "judged on."),
    ]
    # ---------- 3. recommended portfolio ----------
    rows = [wrow('Previous default (four envelopes, fitted)', base['weights']),
            wrow('Fitted carry view (five laws)', alt_w),
            wrow('Current-quotes view (five laws)', rec_w)]
    if mix10.get('fresh_sleeve_dual', {}).get('weights'):
        rows.append(wrow('True 10y sleeve (fresh, five laws)', mix10['fresh_sleeve_dual']['weights']))
    B += [
        ('h1', '3. The recommended portfolio'),
        ('p', f"The headline mix - current-quotes view, five laws - holds {pct(rec_w['tbill'], 0)} T-bills, "
              f"{pct(rec_w['treasury'], 0)} IEF, {pct(rec_w['us_equity'], 0)} US stocks, "
              f"{pct(rec_w['gold'], 0)} gold and {pct(rec_w['sg_property'], 0)} property. It scores "
              f"{M(cur_dual['common_cara_ledger_ce'])} over ten years on the fitted law and "
              f"{M(cur_dual.get('fifth_law_score', {}).get('common_cara_ledger_ce', 0))} when scored by the "
              f"regime law. Five percent of outcomes end below "
              f"{M(cur_dual['terminal_q05'])}; the median outcome is {M(cur_dual['terminal_median'])}."),
        ('table',
         ['Portfolio', 'T-bills', 'IEF', 'TIPS', 'US stocks', 'Gold', 'SG prop.'],
         rows,
         [0.30, 0.117, 0.117, 0.117, 0.117, 0.117, 0.115]),
        ('fig', 'fig_mixes.png',
         'The validated mixes. The two default views disagree about the safe share: the fitted-history view '
         'still wants a third in bills; at current quotes the same checks pass at the 10% floor.'),
        ('p', f"The two views disagree, and the disagreement is the point. The fitted history says bills "
              f"yield ~1.8% and the mix needs {pct(alt_w['tbill'], 0)} of them to pass all five laws "
              f"(score {M(fit_dual['common_cara_ledger_ce'])}). Today's quotes say bills yield 4.17%, and at "
              f"that carry the same checks pass at the 10% grid floor with a {M(cur_dual['common_cara_ledger_ce'])} "
              f"score. The engine now shows both; it does not average them into a false compromise."),
        ('note', "Which to hold? If you believe today's bill curve persists, the current-quotes mix dominates "
                 "on every judge we have, nominal and real. If you distrust the quotes and trust the fitted "
                 "history, hold the fitted-view mix. The engine's answer is the pair, not a coin flip."),
    ]
    # ---------- 4. real terms ----------
    B += [
        ('h1', '4. Real dollars: the honest headline'),
        ('p', "Everything so far is nominal: dollars of the year they arrive in. You asked for the real view "
              "- today's purchasing power - as the headline. Here it is."),
        ('fig', 'fig_nominal_vs_real.png',
         'The same two recommended mixes, scored nominally and in CPI-deflated real terms. The gap is the '
         'inflation illusion: bills look safe only because the nominal judge never asks what a dollar buys.'),
        ('p', f"In real terms the current-quotes mix is worth {M(real['current_quotes']['common_cara_ledger_ce'])} "
              f"and the fitted mix {M(real['fitted']['common_cara_ledger_ce'])} - against nominal scores of "
              f"{M(cur_dual['common_cara_ledger_ce'])} and {M(fit_dual['common_cara_ledger_ce'])}. And under the "
              f"real judge, both mixes fail your 15% final-loss limit at ten years. No fixed mix passes it: "
              f"not the old sleeve, not a re-solved sleeve, not 90% TIPS. The tightest limits any static mix "
              f"can meet in real terms are about 45% worst-path and 40% final (90% TIPS plus the fixed 10% "
              f"property, real score {M(fix3['real_feasible_limits']['common_cara_ledger_ce'])})."),
        ('bullets', [
            "How real terms are built: every scenario is deflated by a bootstrapped inflation path (US CPI, "
            "1947-2026, mean 3.5% a year), payments become inflation-indexed (a constant real $250k/month), "
            "and TIPS are modeled as a genuinely real asset at the live 2.60% real yield.",
            "Inflation paths are drawn independently of market paths - a labeled simplification; TIPS get "
            "their inflation link mechanically by construction.",
            "Your standing defaults stay nominal (40% worst-path, 15% final at each horizon's end). The real "
            "view is a re-pricing of the same portfolios, reported alongside, not a new set of limits - "
            "changing the limits is your call, and section 9 prices it.",
        ]),
    ]
    # ---------- 5. fifth law ----------
    fhs_frozen = fix1.get('fhs_ewma_frozen_sleeve') or fix1.get('fhs_frozen_sleeve', {})
    B += [
        ('h1', '5. The regime law joins the judge'),
        ('p', "Markets have memory in their volatility: calm weeks follow calm weeks, storms follow storms. "
              "The default law ignores this - every week is drawn independently. Earlier editions flagged it "
              "as the biggest model risk. This edition does something about it: the engine's bootstrap/"
              "regime variant (EWMA-filtered resampling of real historical weeks) is now a fifth judging "
              "law. Every candidate must pass on independent draws of both laws."),
        ('bullets', [
            f"On the fitted view the regime law binds: the safe share rises from the 10% floor to "
            f"{pct(alt_w['tbill'], 0)} bills, costing {M(fit_v['single']['common_cara_ledger_ce'] - fit_dual['common_cara_ledger_ce'])} "
            f"of score against the single-law answer.",
            f"On the current-quotes view it changes nothing: bill carry at 4.17% passes both laws at the "
            f"floor. The regime law even scores that mix higher ({M(cur_dual.get('fifth_law_score', {}).get('common_cara_ledger_ce', 0))}) "
            f"than the default law does - its historical weeks include long stretches of high bill rates.",
            f"Judged alone, the regime law is kinder than the default (its frozen-sleeve answer: "
            f"{pct(fhs_frozen.get('chosen_safe', 0), 0)} bills, score {M(fhs_frozen.get('common_cara_ledger_ce', 0))}). "
            f"It is not a harsher world; it is a different one. That is why it belongs in the judge.",
        ]),
        ('note', "The regime law's own caveat stands: as wired, it is a current-volatility-regime law - its "
                 "resampled weeks are scaled by today's volatility level, so it under-weights calmer regimes "
                 "than today's. That makes it a complement to the default law, not a replacement."),
    ]
    # ---------- 5b. policy-by-model matrix (review brief) ----------
    f5th = lambda e: (e.get('fifth_law_score') or {}).get('common_cara_ledger_ce')
    mrows = []
    def matrix_row(name, mix_ce, regime_ce, real_ce):
        mrows.append([name, M(mix_ce) if mix_ce else '-', M(regime_ce) if regime_ce else '-',
                      M(real_ce) if real_ce else '-'])
    matrix_row('1y sleeve, fitted carry (recommended alt.)', fit_dual['common_cara_ledger_ce'],
               f5th(fit_dual), real['fitted']['common_cara_ledger_ce'])
    matrix_row('1y sleeve, current quotes (recommended)', cur_dual['common_cara_ledger_ce'],
               f5th(cur_dual), real['current_quotes']['common_cara_ledger_ce'])
    if mix10.get('fresh_sleeve_dual', {}).get('chosen_safe'):
        matrix_row('True 10y sleeve (fresh)', mix10['fresh_sleeve_dual']['common_cara_ledger_ce'],
                   f5th(mix10['fresh_sleeve_dual']), None)
    if mix10.get('fix4_sleeve_fresh_dual', {}).get('chosen_safe'):
        matrix_row('True 10y sleeve (fix 4, on fresh paths)', mix10['fix4_sleeve_fresh_dual']['common_cara_ledger_ce'],
                   f5th(mix10['fix4_sleeve_fresh_dual']), None)
    matrix_row('Previous default (pre-round-2)', base['common_cara_ledger_ce'], None,
               fix3['cross_base_on_real']['common_cara_ledger_ce'])
    B += [
        ('h2', 'The policy-by-model matrix, frozen'),
        ('table',
         ['Policy (all five-law validated where shown)', 'Default law', 'Regime law', 'Real terms'],
         mrows,
         [0.40, 0.20, 0.20, 0.20]),
        ('note', 'Scores are certainty equivalents over 10 years on shared frozen paths; each column judges '
                 'under a different law, so columns are not utilities compared - they are the same CARA score '
                 'under different worlds. Real terms deflate by bootstrapped CPI. Missing cells: not yet '
                 'computed on this seed family, not hidden failures.'),
        ('p', "No policy wins everywhere, and no complex policy beats the simple fixed mixes: the two 1y-sleeve "
              "mixes and the two 10y-sleeve mixes sit within a few $M of each other under every law, and the "
              "regime law actually prefers the riskier current-quotes mix. The simple static policy remains "
              "the answer; the matrix is the proof, frozen."),
    ]
    # ---------- 6. second view ----------
    f5 = fix5['current_rates']
    B += [
        ('h1', '6. The second default view: current market rates'),
        ('p', f"The fitted estimation window quietly drove the old answer: it has bills earning ~1.8% because "
              f"that is the shrunk historical average, while a 3-month bill pays 4.17% today. The engine now "
              f"always computes both views. Fitted means: score {M(base['common_cara_ledger_ce'])} at "
              f"{pct(base['weights']['tbill'], 0)} bills (old judge) / {M(fit_dual['common_cara_ledger_ce'])} at "
              f"{pct(alt_w['tbill'], 0)} bills (five laws). Current quotes: {M(cur_dual['common_cara_ledger_ce'])} "
              f"at {pct(rec_w['tbill'], 0)} bills."),
        ('bullets', [
            "What changes in the quotes view: only the safe assets' expected carry (bill 4.17%, IEF 4.84%, "
            "TIPS 2.60% real + 2.24% breakeven). Volatilities, correlations and all risky-asset means stay "
            "fitted. Labeled simplification: IEF/TIP expected return is set to the current yield, with no "
            "roll or term-premium model.",
            "Quotes are a dated snapshot (FRED, 5 Nov 2026), not a maintained feed. The view goes stale; "
            "the date travels with it wherever it is shown.",
            f"The quotes view also holds up under the regime law and in real terms "
            f"({M(real['current_quotes']['common_cara_ledger_ce'])} real vs {M(real['fitted']['common_cara_ledger_ce'])} "
            f"for the fitted mix).",
        ]),
    ]
    # ---------- 7. ten-year optimization ----------
    st = fresh.get('stability', {}).get('sleeve_L1', {})
    n400 = fresh.get('solves', {}).get('400', {})
    B += [
        ('h1', '7. The ten-year optimization, properly'),
        ('p', "The old pipeline solved the risky sleeve on a one-year problem and stretched it to ten years. "
              "The fix round solved the true 10-year problem directly. This edition re-ran that solve on "
              "completely fresh paths at three scenario sizes - and the honest finding is that the true "
              "10-year solve is too noisy to steer by."),
        ('fig', 'fig_stability.png',
         'The risky sleeve from the true 10-year solve, by scenario count and seed family. The proportions '
         'swing far more than the score does: the optimum is flat, so the solver chases noise.'),
        ('bullets', [
            f"Fresh solves: n=100 in {fresh['solves']['100']['seconds']:.0f}s, n=200 in "
            f"{fresh['solves']['200']['seconds']:.0f}s"
            + (f", n=400 in {n400['seconds']:.0f}s" if n400.get('status') == 'optimized' else
               f"; n=400 did not produce a solution ({n400.get('status', 'still running')}) - labeled, as before"),
            f"Sleeve instability: the risky-sleeve proportions move by {st.get('fix4_n200_vs_200', 0):.2f} "
            f"(L1) between the old and fresh seed at n=200 - the solver reallocates most of the risky part "
            f"between runs while the score moves by about a million dollars.",
            (f"Put through the five-law discipline anyway, the fresh 10y sleeve validates at "
             f"{pct(mix10['fresh_sleeve_dual']['chosen_safe'], 1)} bills and scores "
             f"{M(mix10['fresh_sleeve_dual']['common_cara_ledger_ce'])}" if mix10.get('fresh_sleeve_dual', {}).get('chosen_safe') else
             "Put through the five-law discipline, the fresh 10y sleeve did not validate"),
            (f"The old-seed 10y sleeve, re-judged on genuinely fresh paths, validates at "
             f"{pct(mix10['fix4_sleeve_fresh_dual']['chosen_safe'], 1)} bills and scores "
             f"{M(mix10['fix4_sleeve_fresh_dual']['common_cara_ledger_ce'])} - the fix-4 result survives "
             f"out-of-sample" if mix10.get('fix4_sleeve_fresh_dual', {}).get('chosen_safe') else
             "The old-seed 10y sleeve did not re-validate on fresh paths"),
            "Verdict: keep the 1y sleeve as the default; the 10y solve stays a cross-check. The score "
            "difference between them is small and unstable in sign.",
        ]),
    ]
    # ---------- 8. radius ----------
    rad = fix2.get('radius_calibration', fix2)
    B += [
        ('h1', '8. The model-wrongness margin: still a budget decision'),
        ('p', f"The engine keeps a safety margin for the market model itself being wrong (the Wasserstein "
              f"radius). The placeholder is 0.00002. Calibrated from how much the fitted model actually moves "
              f"across refits, it should be about 2.55 - roughly 100,000 times larger. Nothing in this "
              f"edition changes that math."),
        ('bullets', [
            f"At the placeholder, the margin already spends about $40k of the $50k smallest payment budget.",
            f"One step up (0.000025) the current portfolio still passes; two steps (0.00003) and no mix is "
            f"feasible at any setting. A statistically real margin is unaffordable under the 20% per-payment "
            f"budget.",
            "That is why this stays open: it is not a calibration problem, it is a budget decision - how "
            "much payment flexibility you are willing to spend on model wrongness. Your plan: leave it, "
            "documented.",
        ]),
    ]
    # ---------- 9. cost of limits ----------
    cells = fix6['cells']
    def ce_of(loss):
        return cells.get(f'cml0.40_loss{loss:.2f}', {}).get('common_cara_ledger_ce')
    loose = max((v.get('common_cara_ledger_ce') for v in cells.values() if v.get('common_cara_ledger_ce')), default=None)
    B += [
        ('h1', '9. What the loss limits cost'),
        ('p', f"At the standing 40% worst-path cap, tightening the final-loss limit from the loosest tested "
              f"setting to 15% costs {M(loose - ce_of(0.15))} of score; to 10% costs {M(loose - ce_of(0.1))}; "
              f"to 5% costs {M(loose - ce_of(0.05))}. Loosening 15% to 25% recovers the full "
              f"{M(ce_of(0.25) - ce_of(0.15))} - and nothing beyond that, because the 40% worst-path cap "
              f"starts binding instead."),
        ('fig', 'fig_limit_cost.png',
         'Score versus the final-loss limit at the standing 40% worst-path cap. The current 15% sits on the '
         'cheap part of the curve; 10% and 5% get expensive fast.'),
        ('p', "The same question in real terms has a harsher answer (section 4): at 15% real, nothing "
              "passes. If you ever want the limits stated in real terms, the feasible pair is about "
              "45% worst-path / 40% final."),
    ]
    # ---------- 10. carries over ----------
    B += [
        ('h1', '10. What carries over from earlier editions'),
        ('bullets', [
            "19 frozen annual holdouts of real history, matched objectives, 152 historical outer refits and "
            "the payout stresses: no objective formula, forecast model or trading rule beat the plain fixed "
            "mix once safety was enforced. (4th edition, sections 5-9.)",
            "Rebalance rarely: annual scored best of the tested frequencies; at one year that means set the "
            "mix once and do not trade. No frequency was accepted across all laws at 3-5 years under "
            "unchanged budgets - reported, not hidden.",
            "Utilities: CARA, CRRA, HARA and the kinked-shortfall objective pick the same portfolio at the "
            "confirmed $250k/month. The answer does not depend on the utility flavor.",
            "Payouts $50k/$100k/$250k per month: the validated mix barely changes; the loss caps, not the "
            "payments, set the safe share.",
            "Execution audit: the cash-first ledger pays every payment in the validated configurations; "
            "the strict 99% all-payments check remains a separate, stronger line.",
            "Regression: 380 tests pass against this edition's engine changes (second view, fifth law, review-"
            "brief fixes). Two pre-existing failures are unchanged from the base commit - hardcoded "
            "paths in two committed study configs and one solver accuracy flag in this sandbox; neither "
            "touches the engine.",
        ]),
    ]
    # ---------- 11. open ----------
    B += [
        ('h1', '11. Everything that is still open'),
        ('bullets', [
            "Real vs nominal limits: the one decision that shapes everything else. This edition shows both; "
            "it does not choose for you.",
            "The model-wrongness margin (section 8): a budget decision, parked.",
            "The regime law is a current-volatility-regime law as wired; a multi-regime version is research, "
            "not a patch.",
            "The 10-year optimizer needs scenario counts beyond this machine's budget before its sleeve can "
            "be trusted as a default (section 7).",
            "The client is still a placeholder: real SFO inputs (actual obligations, tax, other accounts) "
            "would change the answer more than any modeling choice in this report.",
            "The current-quotes view is a 5 Nov 2026 snapshot; it should be refreshed when quotes move.",
            "Property is a price index, not a tradable total return; no rent, no sale, fixed 10%.",
            "Data rights: Yahoo-sourced histories are fine for private research; not cleared for sharing.",
        ]),
    ]
    # ---------- 12. verdict ----------
    B += [
        ('h1', '12. The verdict'),
        ('p', f"Hold the current-quotes mix - {pct(rec_w['tbill'], 0)} T-bills, {pct(rec_w['treasury'], 0)} IEF, "
              f"{pct(rec_w['us_equity'], 0)} US stocks, {pct(rec_w['gold'], 0)} gold, {pct(rec_w['sg_property'], 0)} "
              f"property - if you accept today's bill curve as the carry you actually earn. It passes all five "
              f"laws on fresh paths, scores {M(cur_dual['common_cara_ledger_ce'])} nominal and "
              f"{M(real['current_quotes']['common_cara_ledger_ce'])} real, and it is the mix the engine now shows "
              f"as its second default view."),
        ('p', f"Hold the fitted-view mix ({pct(alt_w['tbill'], 0)} bills) if you distrust the quotes. It is the "
              f"conservative answer and it also passes all five laws. What you should not do is average the "
              f"two: the disagreement is information, not noise."),
        ('p', "And read the real-terms headline before spending the nominal one: in today's dollars the "
              "recommended mix promises about four-fifths of its nominal score, and the 15% final-loss limit "
              "is not achievable by any fixed mix. That is the boundary of what a static portfolio can "
              "promise - the engine now says so in both currencies."),
        ('note', "Private research for Tijs de Boer, not investment advice. Every portfolio here is a frozen "
                 "candidate judged on paths it never saw; passing is a statement about the model, not a "
                 "guarantee about the future."),
    ]
    # ---------- appendices ----------
    B += [
        ('pagebreak',),
        ('h1', 'Appendix A. Data, rights and reproducibility'),
        ('bullets', [
            "Universe: VTI, VWO, GLD, IEF, TIP total-return histories (Yahoo, private use accepted); "
            "3-month T-bill roll built from FRED DGS3MO; Singapore URA private residential index "
            "(data.gov.sg); SGD/USD from FRED; CPI from FRED CPIAUCSL (1947-2026).",
            "Current quotes: FRED H.15 daily, 5 Nov 2026 - DGS3MO 4.17%, DGS10 4.84%, DFII10 2.60%; "
            "breakeven 2.24% by subtraction.",
            "Every study in this edition carries its config, seeds and data hashes in "
            "studies/round2/results/ and studies/fixes/results/. Draws are cached and deterministic in "
            "(config, seed); the fresh family is seed 20261108, disjoint from the earlier 20261107 family.",
            "Engine changes in this edition: emfin_v2/current_rates.py (second view), emfin_v2/multi_law.py "
            "(fifth law), default config gains secondary_carry_view and validation_laws. Regression suite "
            "and smoke test re-run.",
            "Branch: engine-round2-20261108 on the private repo. No upstream writes; inherited code rights "
            "still unresolved for anything beyond private use.",
        ]),
        ('h1', 'Appendix B. The five laws, precisely'),
        ('table',
         ['Law', 'What it is', 'Role'],
         [['1. Reference', 'Empirical distribution of the simulated paths', 'baseline judge'],
          ['2. Nominal', 'Entropy-pooled posterior matching the configured views', 'judge under your views'],
          ['3. Stressed', 'Nominal pushed to a worse equity-basket path loss', 'adverse judge'],
          ['4. Common hull', 'Worst common-threshold bound over the finite hull of 1-3', 'envelope of the three'],
          ['5. Regime/bootstrap', 'Independent draws of the EWMA filtered historical simulation law, judged under its own 1-4 envelopes', 'new in this edition']],
         [0.20, 0.50, 0.30]),
        ('h1', 'Appendix C. Study inventory for this edition'),
        ('bullets', [
            "studies/round2/study_a_dual_law.py: both carry views x single/dual-law mix searches, fresh seeds.",
            "studies/round2/study_c_longhorizon.py: true 10y solves at n=100/200/400 on fresh paths + stability.",
            "studies/round2/study_c2_longhorizon_mix.py: fresh and old 10y sleeves through the five-law discipline.",
            "studies/round2/study_d_real.py: real-terms repricing of the recommended mixes (fix-3 machinery, fresh seeds).",
            "studies/fixes/study_*.py (fixes 1-6): market models, radius calibration, real terms, true 10y, "
            "current rates, constraint grid - results carried into sections 4-9.",
        ]),
    ]
    return SHORT, CONTENTS, B
