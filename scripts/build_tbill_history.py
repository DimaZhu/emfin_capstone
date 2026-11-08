"""Build the T-bill total-return history from the bundled FRED DGS3MO series.

Asset: a rolling constant-maturity 3-month (13-week) US Treasury bill position,
the engine's money-market convention (emfin_v2/toolbox/moneymarket.py):

    weekly log return = carry - duration * rate change
    carry    = r(t-1) / 52            (r = DGS3MO, decimal)
    duration = 0.25 years             (a 3-month bill)

Source: FRED DGS3MO (Board of Governors H.15, 3-month Treasury constant
maturity), bundled snapshot emfin_v2/resources/data/raw/fred/2026-11-07/.
Friday samples match the actual-ETF bundle's W-FRI weekly grid. A Friday that
is a US market holiday uses the most recent prior observation (age check <= 7
days, asserted); no forward reads.

The output is a total-return index (date,total_return_index) plus a manifest
with the same contract as the other actual_etfs histories, so the registry
adapter loads it exactly like a fund history.

Cross-check: if yfinance is installed, the script also compares the built
weekly series with BIL (SPDR Bloomberg 1-3 Month T-Bill ETF, dividend-adjusted)
over their common window and prints agreement statistics. BIL charges a fee
and holds 1-3 month paper, so small level and duration differences are
expected; the check exists to catch construction errors, not to force equality.
"""
import hashlib, json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'emfin_v2/resources/data/raw/fred/2026-11-07/dgs3mo_3m_treasury.csv'
OUT_DIR = ROOT / 'emfin_v2/resources/data/actual_etfs'
DURATION_YEARS = 0.25
WEEKS_PER_YEAR = 52.0


def build(rate: pd.Series) -> pd.Series:
    """Total-return index from a decimal Friday-sampled rate series."""
    carry = rate.shift(1) / WEEKS_PER_YEAR
    rate_risk = -DURATION_YEARS * rate.diff()
    weekly = (carry + rate_risk).dropna()
    return np.exp(weekly.cumsum())


def main() -> None:
    raw = pd.read_csv(SRC)
    raw.columns = ['date', 'rate_pct']
    raw['rate_pct'] = pd.to_numeric(raw['rate_pct'], errors='coerce')
    raw['date'] = pd.to_datetime(raw['date'])
    raw = raw.dropna().set_index('date').sort_index()
    rate_daily = raw['rate_pct'] / 100.0

    grid = pd.date_range(rate_daily.index.min(), rate_daily.index.max(), freq='W-FRI')
    pos = rate_daily.index.get_indexer(grid, method='pad')
    if (pos < 0).any():
        raise ValueError('no past-only Friday anchor')
    ages = (grid - rate_daily.index[pos]).days
    if (ages > 7).any():
        raise ValueError('stale Friday rate sample beyond one week')
    friday_rate = pd.Series(rate_daily.iloc[pos].to_numpy(), index=grid)

    index = build(friday_rate)
    out = pd.DataFrame({'date': index.index.strftime('%Y-%m-%d'),
                        'total_return_index': index.to_numpy()})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / 'tbill-total-return.csv'
    out.to_csv(csv_path, index=False)
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    weekly = np.diff(np.log(index.to_numpy()))
    manifest = {
        'asset_id': 'tbill',
        'ticker': 'DGS3MO',
        'currency': 'USD',
        'return_type': 'total_return',
        'file': 'tbill-total-return.csv',
        'sha256': digest,
        'source_url': 'https://fred.stlouisfed.org/series/DGS3MO',
        'use_terms': 'FRED public data (Board of Governors H.15); citation required, redistribution of derived research series inside this private repo only.',
        'adjustment_method': ('Constructed constant-maturity 13-week T-bill roll: weekly log return '
                              '= prior Friday DGS3MO/52 - 0.25y * weekly DGS3MO change, Friday samples, '
                              'holiday Fridays use the prior observation (<=7d). Same convention as '
                              'emfin_v2/toolbox/moneymarket.py. Validated against BIL ETF when network available.'),
        'constructed': True,
        'source_series': 'DGS3MO',
        'source_snapshot': 'raw/fred/2026-11-07/dgs3mo_3m_treasury.csv',
        'built_at': '2026-11-08',
    }
    (OUT_DIR / 'tbill-manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')

    print(f'weeks={len(weekly)} span={out.date.iloc[0]}..{out.date.iloc[-1]}')
    print(f'annualized mean={weekly.mean()*52:.4%} vol={weekly.std(ddof=1)*np.sqrt(52):.4%} '
          f'worst week={weekly.min():.4%} best week={weekly.max():.4%}')

    try:
        import yfinance as yf
        bil = yf.download('BIL', start='2007-05-25', auto_adjust=True, progress=False)['Close']
        bil_w = bil.resample('W-FRI').last().dropna()
        bil_r = np.log(bil_w).diff().dropna()
        mine = pd.Series(weekly, index=index.index[1:])
        common = pd.concat([mine.rename('tbill'), bil_r.rename('bil')], axis=1, join='inner').dropna()
        print(f'BIL cross-check: common weeks={len(common)} corr={common.tbill.corr(common.bil):.4f}')
        print(f'  tbill mean={common.tbill.mean()*52:.4%} vol={common.tbill.std()*np.sqrt(52):.4%}; '
              f'BIL mean={common.bil.mean()*52:.4%} vol={common.bil.std()*np.sqrt(52):.4%}')
        print(f'  mean weekly tracking diff={((common.tbill-common.bil).abs()).mean():.5%} '
              f'max abs diff={((common.tbill-common.bil).abs()).max():.4%}')
    except Exception as exc:  # network/yfinance optional
        print(f'BIL cross-check skipped: {exc}')


if __name__ == '__main__':
    main()
