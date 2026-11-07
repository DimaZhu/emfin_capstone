"""Shared pinned weekly invariants, no downloads or implicit data refreshes."""
from pathlib import Path
import pandas as pd
from emfin_capstone.toolbox import snapshot, moneymarket, bonds
import numpy as np

COLUMNS = ['DFUS', 'DFAI', 'DFAE', snapshot.YIELD_TICKER, 'DSPREAD', 'MMKT']


def weekly_dataset():
    snap = snapshot.load_snapshot()
    joint = snapshot.weekly_log_returns(snap).join(snapshot.weekly_yield_changes(snap), how='inner')
    joint[snapshot.YIELD_TICKER] /= 100
    root = Path(__file__).resolve().parents[2] / 'data/raw/fred/2026-11-07'
    oas = pd.read_csv(root / 'ice_bofa_ig_oas_bamlc0a0cm.csv', index_col=0, parse_dates=True).iloc[:, 0].astype(float)
    ow = oas[oas.index.weekday == 2] / 100
    joint = joint.join(ow.diff().rename('DSPREAD'), how='inner')
    mm = pd.read_csv(root / 'dgs3mo_3m_treasury.csv', index_col=0, parse_dates=True).iloc[:, 0].astype(float)
    joint = joint.join((mm[mm.index.weekday == 2]/100).rename('MMRATE'), how='inner')
    joint['MMKT'] = moneymarket.money_market_weekly_returns(joint['MMRATE'])
    # Levels are lag-safe pricing anchors for fold-specific bond repricing.
    joint['YIELD_LEVEL'] = snap.closes[snapshot.YIELD_TICKER].reindex(joint.index) / 100
    joint['SPREAD_LEVEL'] = ow.reindex(joint.index)
    return joint.dropna()


def gross_market(cumulative, ytm, spread, weeks=13):
    """Unit-price equity/MM sleeves and exact fixed-coupon bond gross values.

    Both bonds are synthetic constant-maturity instruments (10y, 4% coupon).
    Fold anchors come only from the last training date. No liquidity overlay
    is assumed in the chronological diagnostic, unlike the full engine.
    """
    x = np.asarray(cumulative, float)
    out = np.empty_like(x)
    out[:, :3] = np.exp(x[:, :3])
    for col, base in ((3, ytm), (4, ytm+spread)):
        b = bonds.Bond('validation bond', 100., .04, 10., base)
        delta = x[:, 3] if col == 3 else x[:, 3]+x[:, 4]
        out[:, col] = bonds.bond_price_scenarios(b, base+delta, weeks) / bonds.price_from_ytm(base, 10., .04, 100.)[0]
    out[:, 5] = np.exp(x[:, 5])
    return out
