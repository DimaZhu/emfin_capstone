# Declarative assets and actual-history adapter

`emfin_v2/resources/configs/assets.json` is the default six-asset universe. The former
liquid dataset is retained only by the explicit legacy.json configuration.
The shared runner supports this registry through `asset_registry` and
`history_manifests` config fields. Missing histories fail explicitly.
`emfin-explore --config path/to/config.json` uses that config for recomputations.
`assets.py` validates metadata and generates stable-ID layouts and memberships.
`asset_history.py` validates private actual-instrument total-return histories,
then aligns common Friday observations using only prior data. Missing/stale
weeks fail, rather than treating a three-week return as one week.

Add an ETF by copying a registry row, assigning a unique stable ID and actual
ticker, setting its factors, views, currency, liquidity and haircut, and
providing its private data manifest. Remove it with enabled=false. Never reuse
an old ID to disguise a new instrument. New unsupported return models fail.
Add/remove tests cover metadata, alignment, paths, solve, fixed-property,
factor and view membership. Fixtures are labelled synthetic TEST DATA.

Each private history manifest names asset_id, ticker, currency, source_url,
use_terms, adjustment_method, return_type=total_return, file and sha256. CSV
columns are date,total_return_index. Raw NAVs without verified distributions
are not total returns. The owner approved private-fork storage of market
histories on2026-11-07. No client data, credentials or auth caches are bundled.

Cash remains a cash-account model, not a silently substituted SHV ETF. Its
zero annual rate is an explicit uncalibrated placeholder in the target registry.
IEF is the candidate actual7-10y Treasury ETF and differs from the old synthetic
fixed10y bond. Its issuer NAV history and matched distributions have been privately verified. Property remains quarterly price
history, not a fabricated observed weekly tradable series. The SGD/USD factor now converts local property marks, rent and sale cash flows.
See FX_MODEL.md for its scope and limits.

Source rights: URA data are attributed under the Singapore Open Data Licence.
The owner accepted Yahoo automated-access terms risk for private research
and private-fork storage. This does not claim Yahoo permission or public
redistribution rights. yfinance is Apache-2.0, an optional import-only
dependency. Normal default runs are offline and make no market-data requests.
Source attribution, SHA and notices remain in each manifest.

The adapter uses actual ETF total-return log invariants for all listed legs,
not yield/spread repricing, with shrinkage over stochastic legs only. An
explicit cash-account rate stays deterministic and does not receive artificial
covariance shrinkage. Gold is not an equity factor member. The former
International-minus-US relative view is disabled. Absolute mean views use
registry membership. Property fixed/minimum holdings and cash index follow the
registry. Simple old-universe shock cards are unavailable until new instrument
shocks are specified. The allocation frontier also respects fixed holdings.

Bundled inputs: Yahoo adjusted closes for VTI/VWO/GLD and issuer NAV plus
matched ex-date distributions for IEF. GLD issuer/Yahoo early closing-price
differences were found; one consistent Yahoo series is used, not a splice.
IEF NAV and Yahoo market-close return differences are disclosed rather than
mislabelled as exact matches. Common weekly sample:2005-03-18 to2026-10-30,
limited by the latest FedFX release. Actual data calibrate parametric paths;
this is NOT itself an actual-history backtest. No public data sharing approved.

To refresh explicitly (not automatic):
`pip install .[market-data]` then
`python -m emfin_v2.yahoo_import --symbols VTI VWO GLD IEF --folder .private/yahoo-history --ack-yahoo-terms-risk`.
Existing raw CSVs are reused, with no network request. This importer never
silently extends or merges an older cache; remove/replace it intentionally
when an updated snapshot is wanted. Do not mistake a cache hit for fresh data.
