# Asset registry migration (in progress)

`emfin_v2/resources/configs/assets.json` is the target six-asset universe, not
an assertion that the legacy numerical runtime has already been replaced.
`assets.py` validates metadata and generates stable-ID layouts and memberships.
`asset_history.py` validates private actual-instrument total-return histories,
then aligns common Friday observations using only prior data. Missing/stale
weeks fail, rather than treating a three-week return as one week.

Add an ETF by copying a registry row, assigning a unique stable ID and actual
ticker, setting its factors, views, currency, liquidity and haircut, and
providing its private data manifest. Remove it with enabled=false. Never reuse
an old ID to disguise a new instrument. New unsupported return models fail.
The add/remove dummy tests currently cover metadata/layout and data alignment;
end-to-end solve/UI add/remove tests remain to be written as migration proceeds.

Each private history manifest names asset_id, ticker, currency, source_url,
use_terms, adjustment_method, return_type=total_return, file and sha256. CSV
columns are date,total_return_index. Raw NAVs without verified distributions
are not total returns. Keep restricted data and manifests in .private/, never git.

Cash remains a cash-account model, not a silently substituted SHV ETF. Its
zero annual rate is an explicit uncalibrated placeholder in the target registry.
IEF is the candidate actual7-10y Treasury ETF and differs from the old synthetic
fixed10y bond. Its history is still pending. Property remains quarterly price
history, not a fabricated observed weekly tradable series. The approved SGD/USD
risk-factor extension is queued after the registry adapter.

Source rights: URA data are attributed under the Singapore Open Data Licence.
GLD's issuer offers a full XLSX archive but restricts reproduction/redistribution;
its raw private archive is excluded from git. Yahoo is not used as an unofficial
automated download route. Vanguard and BlackRock download/use terms need to be
honored independently; available downloads do not grant publication clearance.
