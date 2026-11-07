"""Local-only REIDIN-derived sheet adapter, not a redistribution grant."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,os
import numpy as np


def default_path():
    supplied=os.environ.get('EMFIN_V2_RE_IMPORT')
    if supplied:return Path(supplied).expanduser()
    local=Path.cwd()/'.private/abu_dhabi_sheet.json'
    if local.exists():return local
    return Path.home()/'.config/emfin-v2/abu_dhabi_sheet.json'


@lru_cache(maxsize=8)
def load_observed(path,mtime=None):
    file=Path(path);raw=file.read_bytes();doc=json.loads(raw)
    tabs=doc.get('tabs',[])
    found=[t for t in tabs if t.get('range','').startswith('AD_Apt_Monthly!')]
    if len(found)!=1:raise ValueError('private import needs one AD_Apt_Monthly tab')
    records=[]
    for row in found[0]['values'][6:]:
        if len(row)>5 and isinstance(row[1],(int,float)) and str(row[4]).startswith('Observed'):
            records.append((str(row[0]),float(row[1])))
    if len(records)<13:raise ValueError('need at least 13 observed monthly levels, not proxies/forecasts')
    records.sort()
    indices=[int(month[:4])*12+int(month[5:7]) for month,_ in records]
    if len(set(indices))!=len(indices) or any(b-a!=1 for a,b in zip(indices,indices[1:])):
        raise ValueError('observed monthly levels must be consecutive with no duplicates')
    levels=np.array([level for _,level in records])
    if not np.isfinite(levels).all() or (levels<=0).any():raise ValueError('invalid observed index levels')
    ret=np.diff(np.log(levels))
    synthetic='synthetic' in str(found[0]['values'][0]).lower()
    return dict(synthetic_fixture=synthetic,first_month=records[0][0],last_month=records[-1][0],observations=len(records),
        annual_log_drift=float(ret.mean()*12),annual_vol=float(ret.std(ddof=1)*np.sqrt(12)),
        sha256=hashlib.sha256(raw).hexdigest(),
        provenance='Synthetic test fixture, not Abu Dhabi data' if synthetic else 'Local private import from user-provided Google Sheet, gid=8 AD_Apt_Monthly; observed values only, not independently re-extracted from REIDIN PDFs',
        limitations='Index price returns only. Unsmoothing, dependence, rental income and liquidity remain assumptions. Earlier proxies/backcasts and future extrapolations are excluded.')


def local_calibration():
    path=default_path()
    if not path.is_file():return None
    return load_observed(str(path),path.stat().st_mtime_ns)
