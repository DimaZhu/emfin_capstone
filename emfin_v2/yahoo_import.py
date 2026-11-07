"""Explicit opt-in private research import. No automatic run-time downloads.

The library's Apache licence does not license Yahoo data or waive Yahoo terms.
The owner accepted the automated-access terms risk for private research only.
Never distribute downloaded observations or derived output without approval.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
import pandas as pd

TERMS='https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html'
CAVEAT='Yahoo-sourced private research only. Owner accepted automated-access terms risk on2026-11-07. No redistribution or sharing derived outputs without separate owner approval. No representation of Yahoo permission.'
SYMBOLS={'VTI':'us_equity','VWO':'em_equity','GLD':'gold','IEF':'treasury'}


def total_return_from_adjusted(frame):
    """Adjusted close supplies provider dividend/split adjustment, not our proxy."""
    if frame.empty or 'Adj Close' not in frame:raise ValueError('nonempty Yahoo adjusted close required')
    index=pd.DatetimeIndex(pd.to_datetime(frame.index,utc=True)).tz_localize(None).normalize()
    value=pd.to_numeric(frame['Adj Close'],errors='raise').to_numpy()
    if index.duplicated().any() or not index.is_monotonic_increasing or not np.isfinite(value).all() or (value<=0).any():raise ValueError('invalid adjusted-close observations')
    return pd.DataFrame(dict(date=index,total_return_index=100*value/value[0]))


def fetch_private(symbols,folder,acknowledge=False,start='2000-01-01',end='2026-11-07'):
    if not acknowledge:raise ValueError('explicit Yahoo terms-risk acknowledgement required')
    if any(t not in SYMBOLS for t in symbols):raise ValueError('new-universe ETFs only')
    import yfinance as yf
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);results={}
    for symbol in symbols:
        f=folder/(symbol+'-raw.csv')
        if f.exists():frame=pd.read_csv(f,index_col=0,parse_dates=True)
        else:
            frame=yf.Ticker(symbol).history(start=start,end=end,auto_adjust=False,actions=True,repair=False,raise_errors=True,timeout=20)
            if frame.empty:raise ValueError('Yahoo returned no data; stop, do not retry/evade')
            frame.to_csv(f)
        result=total_return_from_adjusted(frame);csv=folder/(symbol+'-total-return.csv');result.to_csv(csv,index=False)
        manifest=dict(asset_id=SYMBOLS[symbol],ticker=symbol,currency='USD',return_type='total_return',adjustment_method='Yahoo adjusted close, provider-adjusted for splits and cash distributions, normalized to100; no splicing or price repair',source_url='https://finance.yahoo.com/quote/'+symbol+'/history/',terms_url=TERMS,use_terms=CAVEAT,library='yfinance '+yf.__version__,file=csv.name,sha256=hashlib.sha256(csv.read_bytes()).hexdigest(),raw_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),first=str(result.date.iloc[0].date()),last=str(result.date.iloc[-1].date()),observations=len(result),private_only=True)
        path=folder/(symbol+'-manifest.json');path.write_text(json.dumps(manifest,indent=2)+'\n');results[symbol]=str(path.resolve())
    return results


def main():
    p=argparse.ArgumentParser();p.add_argument('--symbols',nargs='+',choices=list(SYMBOLS),default=['VTI','VWO']);p.add_argument('--folder',required=True);p.add_argument('--ack-yahoo-terms-risk',action='store_true');a=p.parse_args()
    print(json.dumps(fetch_private(a.symbols,a.folder,a.ack_yahoo_terms_risk),indent=2))

if __name__=='__main__':main()
