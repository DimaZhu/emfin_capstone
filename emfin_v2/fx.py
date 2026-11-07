"""Official SGD/USD reference factor, not a tradable allocation sleeve."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from emfin_v2.config import DATA_DIR

COLUMN='__fx_usd_per_sgd'
DEFAULT_MANIFEST=DATA_DIR/'fx'/'manifest.json'


def load_reference(manifest_path=None):
    p=Path(manifest_path or DEFAULT_MANIFEST);m=json.loads(p.read_text());f=p.parent/m['file']
    if m.get('currency_pair')!='SGD_per_USD' or m.get('series')!='RXI_N.B.SI':raise ValueError('expected official SGD per USD quote identity')
    if hashlib.sha256(f.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('FX history SHA256 mismatch')
    data=pd.read_csv(f)
    if list(data.columns)!=['date','sgd_per_usd']:raise ValueError('FX CSV date,sgd_per_usd required')
    dates=pd.to_datetime(data.date,errors='raise');v=pd.to_numeric(data.sgd_per_usd,errors='raise').to_numpy()
    if dates.duplicated().any() or not dates.is_monotonic_increasing or not np.isfinite(v).all() or (v<=0).any():raise ValueError('positive chronological FX quotes required')
    return pd.Series(1/v,index=pd.DatetimeIndex(dates),name=COLUMN),m


def weekly_factor(weekly_index,manifest_path=None,max_age_days=5):
    """Inverse-quote log changes using past-only same Friday anchors as ETFs."""
    s,m=load_reference(manifest_path)
    grid=pd.DatetimeIndex(weekly_index)
    if len(grid)<1 or not grid.is_monotonic_increasing:raise ValueError('weekly FX grid required')
    anchors=grid.insert(0,grid[0]-pd.Timedelta(days=7));pos=s.index.get_indexer(anchors,method='pad')
    if (pos<0).any() or ((anchors-s.index[pos]).days>max_age_days).any():raise ValueError('stale or missing past-only weekly FX observation')
    return pd.Series(np.diff(np.log(s.iloc[pos].to_numpy())),index=grid,name=COLUMN),m
