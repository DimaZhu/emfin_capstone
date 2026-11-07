# SGD/USD factor

The registry adapter has a non-investable USD-per-SGD factor. It does not
add an allocation sleeve. Its source is Board of Governors of the Federal
Reserve System (US), H.10, series RXI_N.B.SI, daily SGD per USD noon New York
buying rates. The bundled snapshot has 11,499 observations from1981-01-02
through2026-10-30, release prepared2026-11-02. The manifest records SHA256,
attribution and use terms. Source:
https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip
https://www.federalreserve.gov/releases/h10/hist/dat00_si.htm
https://www.federalreserve.gov/disclaimer.htm

The quotation is inverted before calculating log changes. Weekly anchors are
past-only Fridays matching the ETF sample; stale data fail, never forward-fill
across long gaps. The joint listed-ETF/FX covariance is shrunk, excluding
deterministic cash. The factor uses the same Student-t radial shock as ETFs.
Its prior log drift is explicitly zero, an assumption rather than historical
carry, a forward rate or a forecast. Entropy pooling on correlated assets may
change the posterior FX mean. Data and fitted vol/correlations are reported
separately. New York noon FX and closing ETF NAV are not synchronous.

Property local-price paths remain based on quarterly URA price statistics and
assumed equity dependence, not fabricated weekly observed property returns.
USD marks multiply local price by relative USD-per-SGD spot. Rent converts
at receipt. Pending sale proceeds remain in SGD with FX exposure until
settlement, then become USD cash earning the cash-account rate. No sale means
no property sale proceeds are available for liabilities. Rent defaults to0.

There is no hedge, FX spread/fee, leverage, currency carry or tenant model.
Property/FX correlation is induced through the equity factor; it is NOT
independently calibrated to quarterly property history. Latest-vintage source
data are not a point-in-time revision-safe historical backtest.

The legacy configuration still carries no-FX warnings. Enabling the registry
adapter does not pretend the legacy return models became new tickers.
