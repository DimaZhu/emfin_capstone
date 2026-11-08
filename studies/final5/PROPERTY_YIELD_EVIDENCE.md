# Is 4% a fair forward view for Singapore property price growth?

Owner ask 8 Nov 2026 16:25 SGT: evidence on whether the 4% forward view is fair,
plus how scores move at alternative values. Decision input only - the default
stays 4% until the owner chooses otherwise.

## What the 4% is in the model

`forward_log_drift = 0.04` in the real-estate block: the expected annual
log-price growth of the Singapore home. The docs already call it "an
illustrative long-run price-log-return view, not a data estimate"
(emfin_v2/real_estate.py forward_note). Rent is zero (owner choice), the home
is a fixed 10% holding that is never sold, so the drift only moves the terminal
marked wealth, not the payout funding.

## Market evidence (fetched 8 Nov 2026)

Current facts:
- URA official flash estimate, Q3 2026 (1 Oct 2026): private residential price
  index +1.4% q/q, the fastest quarterly gain since Q4 2024; first three
  quarters of 2026 averaged +0.9% per quarter (about +3.6% annualized).
  https://www.ura.gov.sg/news/media/pr26-69/
- Knight Frank on the same release: +2.8% for the nine months of 2026; keeps
  its full-year 2026 forecast at 3-5%, expecting the middle of that range;
  flags rising retrenchments (3,830 in Q1 to 4,620 in Q2 2026) as the main
  downside watch.
  https://www.knightfrank.com.sg/perspectives/article/2026/10/knight-frank-commentary--ura-q3-2026-flash-estimates

Forward views for 2027 (the horizon the 4% claims to cover):
- List Sotheby's International Realty (2 Nov 2026): 2026 full year lands at
  3.3-4%; 2027 base case +2% to +4% (60% probability); upside +4% to +6% (20%);
  downside -2% to +1% (20%). Probability-weighted mean is about +2.7%.
  https://sbr.com.sg/residential-property/in-focus/home-prices-may-rise-2-4-in-2027-report

Supply and policy pressure (reasons the next decade could run below the long
average):
- URA: Government Land Sales Confirmed List for 2026 is 9,320 units, more than
  50% above the 10-year annual average; total pipeline about 60,600 private
  units. URA itself advises prudence given interest-rate uncertainty.
  (same URA release)

Historical anchor inside the model:
- The engine's own URA calibration over 1975-2026Q3 gives 6.25% annual log
  drift at 9.82% vol. That sample includes the high-inflation 1970s-80s and
  repeated en-bloc booms; analyst views for the coming years cluster well
  below it.

## How the scores move (10y validated mix, frozen)

Study: studies/final5/study_sens_property_yield.py, results
results/final5_sens_property.json. The round-2 validated 10y mix (safe share
32.5% fitted view / 10% current-quotes view) is re-scored at each drift under
both judging laws, same seed family 20261109, same shock sequences per cell.

| forward drift | fitted-view CE | current-quotes CE | verdicts |
|---|---|---|---|
| 0% | 106.6M | 118.3M | pass, both laws |
| 2% | 108.2M | 119.7M | pass, both laws |
| 3% | 109.0M | 120.5M | pass, both laws |
| **4% (current)** | **110.0M** | **121.4M** | **pass, both laws** |
| 5% | 111.0M | 122.4M | pass, both laws |
| 6% | 112.1M | 123.4M | pass, both laws |

About +0.9M certainty equivalent per +1 percentage point of drift in either
carry view. No pass/fail verdict, quantile shape, or P(end below start = 0%)
changes anywhere in the 0-6% range, because the home is only 10% of wealth,
never sold, and never funds a payment.

## Reading

4% is defensible but on the optimistic side of the current evidence: it sits at
the top of the 2027 analyst base range (2-4%), above the probability-weighted
view (about 3%), and below the model's own 1975-2026 historical sample (6.25%).
The decision stakes are small: the whole 0-6% sweep moves the score by about
5.5M of certainty equivalent (under 5%) and changes no verdict. If the owner
wants a number nearer the current analyst consensus, 3% is the defensible pick;
4% stays within every published range.
