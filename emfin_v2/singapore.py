"""Public URA price-index history with source attribution and integrity check."""
import csv,hashlib,json
from functools import lru_cache
from pathlib import Path
import numpy as np
from emfin_v2.config import DATA_DIR
ROOT=DATA_DIR/'singapore'
TYPES=('All Residential','Landed','Non-Landed')
SOURCE='https://data.gov.sg/datasets/d_97f8a2e995022d311c6c68cfda6d034c/view'
LICENCE='https://data.gov.sg/open-data-licence'


@lru_cache(maxsize=128)
def history(property_type='All Residential',as_of=None,release_lag_days=45):
    if property_type not in TYPES:raise ValueError('unknown Singapore property type')
    manifest=json.loads((ROOT/'manifest.json').read_text());path=ROOT/'ura_private_residential_quarterly.csv'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('Singapore dataset hash mismatch')
    with path.open() as f:rows=[r for r in csv.DictReader(f) if r['property_type']==property_type]
    if as_of is not None:
        from datetime import date,timedelta
        import calendar
        cutoff=date.fromisoformat(str(as_of)[:10])
        def available(row):
            y=int(row['quarter'][:4]);q=int(row['quarter'][-1]);month=q*3
            return date(y,month,calendar.monthrange(y,month)[1])+timedelta(days=release_lag_days)<=cutoff
        rows=[r for r in rows if available(r)]
    periods=[int(r['quarter'][:4])*4+int(r['quarter'][-1])-1 for r in rows];values=np.array([float(r['index']) for r in rows])
    if len(rows)<20 or not np.isfinite(values).all() or (values<=0).any() or np.any(np.diff(periods)!=1):raise ValueError('Singapore price-index quarters must be positive, ordered and contiguous')
    returns=np.diff(np.log(values))
    metadata=dict(provenance='URA Private Residential Property Price Index via data.gov.sg, '+property_type,first_period=rows[0]['quarter'],last_period=rows[-1]['quarter'],observations=len(rows),return_count=len(returns),frequency='quarterly',periods_per_year=4,units='Price index,2009-Q1=100',property_type=property_type,source_url=SOURCE,licence_url=LICENCE,attribution=manifest['attribution'],sha256=manifest['sha256'],as_of=as_of,release_lag_days=release_lag_days,limitations='Private residential transaction price index, not HDB, rent, total return or a tradable fund. Aggregate index is not a specific property. Quarterly history does not identify weekly volatility, liquidity or execution costs. Latest vintage may revise earlier values; this is not vintage-correct historical backtesting.')
    return tuple(returns),metadata
