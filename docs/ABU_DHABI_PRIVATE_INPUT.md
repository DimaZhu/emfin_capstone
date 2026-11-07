# Abu Dhabi local private input

Tijs selected the AD_Apt_Monthly tab (gid=8) of his spreadsheet as the provisional
Abu Dhabi input. It contains 46 consecutive observed apartment-index levels from
Aug 2022 through May 2026. Earlier backcasts/proxies/interpolation are excluded
from calibration. No workbook values are committed to this public fork.

Export that tab as CSV (including its first six explanation/header rows), then:

```
python scripts/import_abu_dhabi.py --input /private/path/AD_Apt_Monthly.csv
```

The validated file goes to ~/.config/emfin-v2/abu_dhabi_sheet.json with owner-only
file permissions. A JSON tab-grid snapshot is also supported. Set
EMFIN_V2_RE_IMPORT to choose another local file. .private/ is ignored by git.
The wheel includes only a small explicitly synthetic test fixture, not the
licensed sheet. Choosing the private source without an import reports unavailable.

The RE scenario sleeve uses annualized observed monthly log-return drift and
volatility as provisional marginal price-index estimates. It does not add gross
yield as though it were net rent. Unsmoothing, equity dependence, vacancy, rent,
expenses, debt, valuation error and time-to-cash remain assumptions/gaps. A short
rising index sample is not a reliable estimate of long-run expected return.

Other tabs: Sheet2 is an unlabeled reconstructed index, Summary is formula
comparisons, REIDIN_Sales and REIDIN_Rent hold sparse multi-emirate price/rent
levels, REIDIN_Yield holds reported/implied yields and price-to-rent,
BIS_UAE holds national quarterly nominal/real levels through 2024Q1,
ValuStrat_AD contains two incompatible base-year groups, ADREC_Volume has
transaction/lease headlines with scope warnings, and Sources_and_Gaps records
extraction/source limitations. None are silently merged into one return history.

## Access does not mean redistribution permission

The workbook says REIDIN reports reserve reproduction rights and request written
permission. ValuStrat's public reviews use an email form, not an open-data licence.
ADREC reports/tools are publicly accessible but the workbook establishes no bulk
API or redistribution grant. BIS/FRED national series are downloadable subject
to national source/BIS attribution terms. Do not bundle REIDIN/ValuStrat sheet
contents just because the PDFs can be downloaded. No one has been contacted.
