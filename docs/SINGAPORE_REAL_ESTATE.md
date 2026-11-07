# Singapore private-residential price history

The active RE calibration source is now Singapore URA, All Residential. Landed and Non-Landed are separately selectable. The bundled CSV has621 rows:207 quarters per property type,1975-Q1 to2026-Q3. It is a private-residential transaction price index, base2009-Q1=100, not HDB, a tradable fund, rental yield, net income, property-specific valuation or total return.

Source: https://data.gov.sg/datasets/d_97f8a2e995022d311c6c68cfda6d034c/view

Contains information from Private Residential Property Price Index (Base Quarter2009-Q1=100), Quarterly, accessed on7 November2026 from data.gov.sg / Urban Redevelopment Authority, made available under the Singapore Open Data Licence version1.0: https://data.gov.sg/open-data-licence . No official endorsement.

The licence allows download, copying, distribution and adaptation for commercial or noncommercial use, subject to its limitations and attribution. The repository includes a source manifest and SHA256 integrity check. This grant covers the URA dataset, not inherited code or other market data.

## Calibration and limits

Quarterly log-price changes are annualized with4 periods per year and square-root-of4 for sample volatility. The central sample-implied annual price-log drift is6.250% and sample annualized volatility9.821% at alpha0 for All Residential. These are long-window historical estimates, not a forecast. Four-quarter circular block bootstrap resamples2000 times with a fixed seed. Optional Geltner inversion uses an assumed source-frequency alpha; it is not estimated from the data. Bootstrap endpoints are marginal sensitivity values, not a joint confidence region.

The forward annual price-log view stays an editable, explicitly illustrative4%, separate from the6.250% historical sample mean. It is not newly claimed to be calibrated from the index. Sample mode is optional. Net rental yield defaults to0 and remains an assumption if entered. Weekly property paths are simulated under the stated parametric model and square-root-of-time scaling; there are no observed weekly property returns in this CSV. Dependence, sale timing, haircut and settlement remain separate assumptions.

URA describes stratified hedonic estimation using caveat, stamp-duty and developer information, with transaction weighting. An aggregate price index need not reflect one property's sale price or time to sell. This is a current data vintage; earlier quarters may be revised, so a historical strategy backtest must not claim it had today's revised index values at past decisions. No SGD/USD FX adjustment has been added: price-index returns are local-currency economics while the existing funding model's reporting currency is USD. Cross-currency wealth requires an explicit FX model or a consistently SGD balance sheet before client use.

The Abu Dhabi loader remains optional and private for legacy reproduction, behind the explicit legacy-source selection. It is no longer the active default. Its original import is not committed or included in public data. The RE sleeve is still off unless enabled; changing the data source does not silently add a property holding.
