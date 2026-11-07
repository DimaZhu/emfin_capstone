# Engine validation appendix

Snapshot: 2026-11-06.

|Method|Parametric CE ($)|Overlapping empirical CE ($)|Fresh MC gap CVaR ($)|
|---|---:|---:|---:|
|vanilla MV|101,900,900|100,382,192|3,469,623|
|Black-Litterman|101,383,675|101,305,372|0|
|EP (views)|101,983,809|100,654,139|2,780,066|
|EP + liabilities|101,956,300|101,465,160|182,755|
|EP+liab (multi-per)|101,890,604|101,409,434|157,864|
|EP+liab (scaled CARA)|101,962,785|101,476,509|182,272|
|1/N|101,532,508|101,001,263|838,101|
|EP+liab (MPEP)|101,233,924|101,258,743|0|
|robust CML|101,944,202|101,272,010|531,754|
|EP+liab (nominal)|102,000,618|101,386,503|402,310|

## Qualifications

- All liabilities, views, liquidity parameters and budgets are illustrative placeholders.
- Parametric evaluation uses fresh Monte Carlo draws, not unseen historical outcomes.
- Empirical judge overlaps estimation history; this is model sensitivity, not predictive validation.
- Fan denominator is total planned quarterly liability; wealth is gross before payouts.
- Frontier is model mean/variance without funding constraints, not a utility frontier.
- Robust CML uses 500 paths and a finite-posterior ambiguity set; its funding target can fail OOS.
- Surplus-scaled CARA is an approximation, not exact CRRA power utility.
- Chronological validation reserves a final window separately; the current-allocation runner uses full history.
