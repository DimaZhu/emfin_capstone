"""Empirical W1 radius diagnostic (docs/NEXT_RESEARCH_PLAN.md, item 2).

Owner-approved 8 Nov 2026 ("Yes, a and b"). Uses exactly the existing max_path
ground metric and block construction as emfin_v2.radius_calibration (price
term: chebyshev distance on concatenated per-dollar path/funding blocks,
52-week blocks, deterministic liabilities have zero displacement).

What this adds beyond radius_calibration.calibrate:
- strict chronological train/heldout split of the 21 available 52-week blocks;
- radii selected from training-only data at several quantiles, frozen before
  heldout scoring;
- dependence-aware block-bootstrap stability of the selected radius;
- heldout nearest-train-block inclusion frequency per frozen radius;
- sample-size and seed sensitivity.

This is an empirical finite-sample diagnostic conditional on data and
resampling choices: NOT a theorem-backed out-of-sample guarantee, NOT a
familywise guarantee, and no 95% coverage claim follows from using a 95th
percentile. With 21 blocks (14 train / 7 heldout) every heldout frequency has
a denominator of 7 - instability is shown honestly rather than smoothed over.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / 'results'

sys.path.insert(0, str(ROOT / 'studies' / 'backtest_20261108'))
from emfin_v2.radius_calibration import balanced_distances  # engine's exact metric
from backtest import build_config, full_frame  # shared study helpers

import csv, calendar
from datetime import date, timedelta


def build_blocks(c, frame, block_weeks=52):
    """Copy of radius_calibration.calibrate's block construction (RE-enabled path).

    Returns list of (flattened block vector, {first,last} dates). Per-dollar
    liquid funding paths (haircut-netted growth) plus property mark/spendable,
    concatenated price block then funding block - identical to calibrate().
    """
    from emfin_v2.singapore import ROOT as SG_ROOT
    from emfin_v2.real_estate import cash_and_mark
    re = c['real_estate']
    liquid = len(c['liquidity_haircuts'])
    quarter = []
    with (SG_ROOT / 'ura_private_residential_quarterly.csv').open() as f:
        for row in csv.DictReader(f):
            if row['property_type'] == re['sg_property_type']:
                year = int(row['quarter'][:4]); month = int(row['quarter'][-1]) * 3
                quarter.append((date(year, month, calendar.monthrange(year, month)[1]) + timedelta(days=45),
                                float(row['index'])))
    quarter.sort()

    def index_at(day):
        return [v for release, v in quarter if release <= pd.Timestamp(day).date()][-1]

    h = block_weeks
    blocks, dates = [], []
    for start in range(0, len(frame) - h + 1, h):
        data = frame.iloc[start:start + h]
        paths = np.exp(np.cumsum(data.iloc[:, :liquid].to_numpy(), axis=0))[None, :, :]
        growth = paths[:, :, c['cash_index']].copy()
        paths *= 1 - np.asarray(c['liquidity_haircuts'])
        initial = index_at(data.index[0] - pd.Timedelta(days=7))
        local = np.array([[index_at(day) / initial for day in data.index]])
        fx = np.exp(np.cumsum(data.iloc[:, -1].to_numpy()))[None]
        mark, spendable = cash_and_mark(local, growth, re, fx_paths=fx)
        paths = np.concatenate([paths, mark[:, :, None]], axis=2)
        funding = np.concatenate([paths[:, :, :liquid], spendable[:, :, None]], axis=2)
        blocks.append(np.r_[paths.ravel(), funding.ravel()])
        dates.append(dict(first=str(data.index[0].date()), last=str(data.index[-1].date())))
    return blocks, dates


def radius_at(blocks, quantile, repetitions=64, seed=20261107):
    return float(np.quantile(balanced_distances(blocks, repetitions=repetitions, seed=seed),
                             quantile, method='inverted_cdf'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c = build_config()
    frame = full_frame(c)
    blocks, dates = build_blocks(c, frame)
    n = len(blocks)
    x = np.asarray(blocks)
    from scipy.spatial.distance import cdist
    cost = cdist(x, x, metric='chebyshev')

    n_train = (2 * n) // 3  # 14 of 21
    train_idx = list(range(n_train))
    heldout_idx = list(range(n_train, n))
    train_blocks = [blocks[i] for i in train_idx]

    # Full-sample reference (replicates calibrate()'s number as a sanity anchor)
    full_q90 = radius_at(blocks, 0.9)

    quantiles = [0.5, 0.75, 0.9, 0.95]
    train_radii = {str(q): radius_at(train_blocks, q) for q in quantiles}

    # Dependence-aware block bootstrap over training blocks: circular moving
    # block bootstrap with 3-block runs, radius recomputed per resample.
    rng = np.random.default_rng(20261108)
    boot_radii = []
    n_boot = 200
    bl = 3
    for b in range(n_boot):
        starts = rng.integers(0, n_train, (n_train + bl - 1) // bl)
        idx = np.concatenate([(np.arange(bl) + s) % n_train for s in starts])[:n_train]
        boot_radii.append(radius_at([train_blocks[i] for i in idx], 0.9, repetitions=32, seed=20261108 + b))
    boot_radii = np.array(boot_radii)

    # Frozen-radius heldout coverage: nearest training block within radius?
    heldout_nearest = cost[np.ix_(heldout_idx, train_idx)].min(axis=1)
    coverage = {str(q): dict(radius=train_radii[str(q)],
                             covered=int((heldout_nearest <= train_radii[str(q)]).sum()),
                             of=len(heldout_idx),
                             uncovered_dates=[dates[heldout_idx[i]] for i in range(len(heldout_idx))
                                              if heldout_nearest[i] > train_radii[str(q)]])
                for q in quantiles}

    # Train-to-heldout assignment distance (rectangular transport)
    from scipy.optimize import linear_sum_assignment
    i, j = linear_sum_assignment(cost[np.ix_(train_idx, heldout_idx)].T)
    assignment_distance = float(cost[np.ix_(train_idx, heldout_idx)].T[i, j].mean())

    # Sample-size sensitivity: radius vs number of chronological training blocks
    size_sensitivity = {}
    for m in (8, 11, 14):
        size_sensitivity[str(m)] = radius_at([blocks[i] for i in range(m)], 0.9)

    # Seed sensitivity of the half-split estimator on the full training set
    seed_radii = [radius_at(train_blocks, 0.9, seed=s) for s in (1, 7, 2026, 31415, 999983)]

    result = dict(
        blocks=n, block_weeks=52, dates=dates,
        metric='chebyshev (max) on concatenated per-dollar path+funding blocks, engine max_path price term',
        train_blocks=n_train, heldout_blocks=len(heldout_idx),
        full_sample_radius_q90=full_q90,
        train_radii=train_radii,
        default_config_radius=2e-05,
        radius_vs_default={str(q): train_radii[str(q)] / 2e-05 for q in quantiles},
        bootstrap_q90=dict(n=n_boot, block_run=bl, mean=float(boot_radii.mean()),
                           std=float(boot_radii.std(ddof=1)),
                           quantiles=np.quantile(boot_radii, [0.05, 0.5, 0.95]).tolist()),
        heldout_nearest_train_distance=heldout_nearest.tolist(),
        heldout_coverage=coverage,
        train_to_heldout_assignment_distance=assignment_distance,
        sample_size_sensitivity_q90=size_sensitivity,
        seed_sensitivity_q90=seed_radii,
        scope='Empirical finite-sample diagnostic conditional on data and resampling choices. Not a theorem-backed out-of-sample or familywise guarantee. 95th-percentile radius does not imply 95% coverage. Property marks at quarterly URA index granularity.',
    )
    (OUT / 'radius_diagnostic.json').write_text(json.dumps(result, indent=1, default=str) + '\n')
    print(json.dumps({k: result[k] for k in ('blocks', 'full_sample_radius_q90', 'train_radii',
                                             'radius_vs_default', 'heldout_coverage')}, indent=1, default=str))


if __name__ == '__main__':
    main()
