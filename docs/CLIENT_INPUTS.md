# Real SFO inputs needed before client conclusions

Do not email sensitive client material or commit it to a public repository.
Use a private local input file and keep source documents in the client's approved
storage. The supplied default config is illustrative, not a request to fill gaps
with guesses.

|Input|Required fields|Why|
|---|---|---|
|Balance sheet|Valuation date, base currency, liquid assets, debt, net wealth|Avoid double counting wealth and obligations|
|Liability schedule|Name, amount, currency, due week/date, must-pay or optional, uncertainty/correlation assumptions, evidence source|Funding timing and cumulative payouts|
|Current holdings|Instrument, units/value, valuation date, sale limits, lockups, minimum holdings|Account for what cannot be sold|
|Committee views|Instrument(s), horizon, mean/rank/vol/tail value, confidence, source/owner|Separate beliefs from fitted history|
|Family company|Equity value/range, distributions, capital calls, sale/pledge restrictions, currency, market-factor links, source|Nontraded exposure and correlated funding needs|
|Real estate|Property/location/type, holding value, mortgage/debt, rent/costs, valuation dates, transaction evidence, correlation uncertainty|Do not substitute stale UAE data for client assets|
|Liquidity|Executable spread/fees, time-to-sale distribution, volume/position sizes, stressed haircut, financing terms|Distinguish investment value from available cash|
|Preferences and rules|Risk tolerance/objective, loss and funding budgets, horizon, allowed assets, shorting/credit rules|No inferred client risk permission|

## Config format

Copy `emfin_v2/resources/configs/default.json` to a PRIVATE file and pass `--config /private/path.json`.
Amounts are base-currency units, wealth is gross investable initial wealth, weeks
are one-based. Each `liabilities` row has `name`, `week`, `amount`. Current default
supports deterministic payouts or one stated lognormal uncertainty parameter;
complex client uncertainty belongs in the scenario archive interface below.

`real_estate.enabled` adds a synthetic scenario sleeve. All its drift, volatility,
correlation, haircut and minimum holding must be explicitly supplied and sourced;
a default value is not client evidence. No family-company model is inferred.

`client_evidence` holds metadata (`status`, `sources`, `holdings`, `family_company`).
It is an inventory only, not proof that those holdings have been modeled. Do not
put personally identifying or proprietary source content into an exported report.

## General scenario interchange (no new optimizer code)

For richer client cases, use `optimization_multiperiod` directly with arrays:
`market_paths[S,H,I]`, `prices_vector[I]`, `wealth`,
`liability_scenarios[S,J]`, `payout_steps[J]`, `liability_base[J]`,
`mm_growth_paths[S,H]`, `scenario_probs[S]`, `minimum_weights[I]`.
A private NPZ can store these exact keys; load with `numpy.load(..., allow_pickle=False)`.
Prices and values use the same currency. Every scenario row must describe the SAME
market path, liability realization, cash growth and probability. Family-company
or real property scenarios can be extra instrument columns without changing the
optimizer. Stressed posterior vectors must align to those exact rows.

The CLI accepts `scenario_archives` in the JSON config:

```
"scenario_archives": {
  "training": "/private/train.npz",
  "validation": ["/private/val1.npz", "/private/val2.npz"],
  "evaluation": ["/private/test1.npz", "/private/test2.npz"]
},
"asset_names": ["equity A", "equity B", "bonds", "property", "company", "cash"],
"cash_index": 5,
"view_instruments": [1, 0],
"minimum_weights": [0, 0, 0, 0.2, 0.1, 0]
```

Archives use the six exact array keys above (probabilities are computed from
these paths); asset values are normalized by `prices_vector`. Every split must
use matching asset/payout semantics. Duplicate archive bytes are rejected; this
does not prove statistical independence. The provider must create genuinely
independent or chronological splits. Forecast dates, currency conversion and
valuation assumptions remain the provider's responsibility.

No new optimizer code is required for additional property/company columns.
Calendar mapping, FX, taxes, mortgages and asset-specific sale scheduling still
need explicit model choices before a real client file is economically meaningful.

## Dashboard path

Section 06, SFO client inputs, shows the current placeholder capital/payout
schedule and missing evidence. Download its checklist/template for collection;
that small template is not a complete runnable config. Copy the bundled full
default config for actual model settings, replace inputs using the format above,
and select that JSON under "My private full model config" in the local app.
The local server accepts it at Recompute/Run, not GitHub or a public service.
Paths in scenario_archives must exist on the same computer as the local server.
Static exports disable that input runner. Private files must not be committed.

Market series do not prove family holdings. Unknown company value is displayed
as not provided/excluded, not a factual zero. No family-company or property
valuation has been invented to fill the default.
