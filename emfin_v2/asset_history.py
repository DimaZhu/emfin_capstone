"""Private actual-instrument data contract for the registry adapter.

CSV inputs contain date,total_return_index. A NAV alone is not accepted as a
claim of total return. No automatic market downloads or synthetic proxy joins.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from emfin_v2.assets import active_assets


def load_total_return(asset,manifest_path):
    p=Path(manifest_path);m=json.loads(p.read_text())
    if m.get('asset_id')!=asset['id'] or m.get('ticker')!=asset['ticker'] or m.get('currency')!=asset['currency']:raise ValueError('history identity/currency differs from registry')
    if m.get('return_type')!='total_return' or not m.get('adjustment_method') or not m.get('source_url') or not m.get('use_terms'):raise ValueError('total-return adjustment, source and use terms required')
    f=(p.parent/m['file']).resolve()
    if hashlib.sha256(f.read_bytes()).hexdigest()!=m.get('sha256'):raise ValueError('history SHA256 differs from manifest')
    data=pd.read_csv(f)
    if list(data.columns)!=['date','total_return_index']:raise ValueError('history CSV must contain date,total_return_index')
    index=pd.to_datetime(data['date'],errors='raise');v=pd.to_numeric(data['total_return_index'],errors='raise').to_numpy()
    if index.duplicated().any() or not index.is_monotonic_increasing or len(v)<3 or not np.isfinite(v).all() or (v<=0).any():raise ValueError('positive unique chronological total-return observations required')
    return pd.Series(v,index=pd.DatetimeIndex(index),name=asset['id'])


def weekly_returns(document,manifests,end=None,max_age_days=5):
    """Common Friday as-of closes, with no forward reads and no gap-as-week lie.

    Missing stale observations reject the dataset, not rescale 3-week returns
    as 1-week changes. Quarter property is deliberately outside this matrix.
    """
    assets=active_assets(document);listed=[a for a in assets if a['return_model']=='etf_total_return']
    if not listed:raise ValueError('at least one actual liquid risky history required')
    histories=[load_total_return(a,manifests[a['id']]) for a in listed]
    start=max(s.index.min() for s in histories);stop=min(s.index.max() for s in histories)
    if end is not None:stop=min(stop,pd.Timestamp(end))
    grid=pd.date_range(start,stop,freq='W-FRI');columns={}
    for s in histories:
        pos=s.index.get_indexer(grid,method='pad')
        if (pos<0).any():raise ValueError('no past-only weekly anchor')
        ages=(grid-s.index[pos]).days
        if (ages>max_age_days).any():raise ValueError('stale/missing weekly history for '+s.name)
        columns[s.name]=np.log(s.iloc[pos].to_numpy())
    logs=pd.DataFrame(columns,index=grid).diff().iloc[1:]
    cash=next(a for a in assets if a['cash'])
    if cash['return_model']=='cash_account':
        rate=cash['source'].get('annual_rate')
        if not isinstance(rate,(float,int)) or not np.isfinite(rate) or rate<=-1:raise ValueError('explicit valid cash annual rate required')
        logs[cash['id']]=np.log1p(rate)/52
    order=[a['id'] for a in assets if a['return_model']!='quarterly_property']
    return logs[order]
