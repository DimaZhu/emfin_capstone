# Asset registry migration (in progress)

`emfin_v2/resources/configs/assets.json` is the target six-asset universe, not
an assertion that the legacy default data have already been replaced.
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
The add/remove dummy tests currently cover metadata/layout and data alignment;
end-to-end path, solve, fixed-property, factor and view membership add/remove tests now cover a dummy liquid instrument. Fixtures are synthetic TEST DATA, never market evidence. Visual rendering is checked on a test fixture separately.

Each private history manifest names asset_id, ticker, currency, source_url,
use_terms, adjustment_method, return_type=total_return, file and sha256. CSV
columns are date,total_return_index. Raw NAVs without verified distributions
are not total returns. Keep restricted data and manifests in .private/, never git.

Cash remains a cash-account model, not a silently substituted SHV ETF. Its
zero annual rate is an explicit uncalibrated placeholder in the target registry.
IEF is the candidate actual7-10y Treasury ETF and differs from the old synthetic
fixed10y bond. Its issuer NAV history and matched distributions have been privately verified. Property remains quarterly price
history, not a fabricated observed weekly tradable series. The SGD/USD factor now converts local property marks, rent and sale cash flows.
See FX_MODEL.md for its scope and limits.

Source rights: URA data are attributed under the Singapore Open Data Licence.
GLD's issuer offers a full XLSX archive but restricts reproduction/redistribution;
its raw private archive is excluded from git. Yahoo is not used as an unofficial
automated download route. Vanguard and BlackRock download/use terms need to be
honored independently; available downloads do not grant publication clearance.

The adapter uses actual ETF total-return log invariants for all listed legs,
not yield/spread repricing, with shrinkage over stochastic legs only. An
explicit cash-account rate stays deterministic and does not receive artificial
covariance shrinkage. Gold is not an equity factor member. The former
International-minus-US relative view is disabled. Absolute mean views use
registry membership. Property fixed/minimum holdings and cash index follow the
registry. Simple old-universe shock cards are unavailable until new instrument
shocks are specified. The allocation frontier also respects fixed holdings.

Current data gap: full verified VTI/VWO weekly total-return histories are not
yet available by a permitted route. The defaults therefore still use the old
liquid dataset rather than mislabeling its return models as new tickers.
