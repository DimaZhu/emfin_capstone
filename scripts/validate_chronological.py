"""Exploratory chronological calibration with a reserved, unevaluated final window."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
from emfin_capstone.toolbox import dataset, validation, shrinkage, liabilities, risk_stats


def run():
    data = dataset.weekly_dataset()
    folds, dev_stop = validation.chronological_folds(len(data))
    nu_grid = [5., 8., 30., 200.]
    multipliers = [.25, .5, 1.]
    records = []
    fitted_nu = []
    for fold_id, fold in enumerate(folds):
        train = data.iloc[:fold.train_stop]
        val = data.iloc[fold.train_stop:fold.validation_stop]
        x = train[dataset.COLUMNS].to_numpy()
        cov, delta = shrinkage.ledoit_wolf_cov(x)
        raw = x.mean(0)
        target = np.array([raw[:3].mean()]*3+[0., 0., raw[5]])
        mean, _ = shrinkage.shrink_mean(raw, target, len(x), 156.)
        fitted_nu.append(validation.fit_student_nu(x, mean, cov))
        anchor = train.iloc[-1]
        held_market = dataset.gross_market(validation.horizon_sums(val[dataset.COLUMNS]), anchor.YIELD_LEVEL, anchor.SPREAD_LEVEL)
        nlls = {nu: validation.variance_matched_t_nll(val[dataset.COLUMNS], mean, cov, nu) for nu in nu_grid}
        rng = np.random.default_rng(20261107 + fold_id)
        z = rng.standard_normal((1000, 6)) @ np.linalg.cholesky(13*cov + 1e-12*np.eye(6)).T
        for nu in nu_grid:
            rng_nu = np.random.default_rng(20261107 + fold_id)
            inv = 13*mean + z / np.sqrt(rng_nu.chisquare(nu, (1000, 1))/(nu-2))
            market = dataset.gross_market(inv, anchor.YIELD_LEVEL, anchor.SPREAD_LEVEL)
            for mult in multipliers:
                try:
                    a, diag = liabilities.optimization_liability_aware(
                        market, np.ones(6), 1e6, 950000., 25000., .95, .1, .002*mult)
                    gap = np.maximum(950000.-held_market@a, 0.)
                    gap_score = risk_stats.empirical_cvar(gap, .95)
                    status = diag['status']
                except RuntimeError:
                    gap_score = None
                    status = 'unavailable: solver validation failed'
                records.append(dict(fold=fold_id, train_stop=str(train.index[-1].date()),
                    validation_start=str(val.index[0].date()), validation_stop=str(val.index[-1].date()),
                    nu=nu, multiplier=mult, weekly_nll=nlls[nu], gap_cvar=gap_score,
                    rolling_paths=len(held_market), nonoverlap_paths=len(val)//13, solver_status=status))
    mean_nll = {nu: float(np.mean([r['weekly_nll'] for r in records if r['nu']==nu])) for nu in nu_grid}
    selected_nu = min(mean_nll, key=mean_nll.get)
    # Worst development-fold risk, not a pooled average that can hide one breach.
    feasible = [m for m in multipliers if max(r['gap_cvar'] if r['gap_cvar'] is not None else float('inf') for r in records if r['nu']==selected_nu and r['multiplier']==m) <= 1900.]
    selected_mult = max(feasible) if feasible else None
    return dict(label='exploratory short-history calibration, not a validated 95% tail guarantee',
        assumptions=['13-week elliptical t horizon approximation', 'synthetic constant-maturity bonds',
                     'no transaction/liquidity costs in this diagnostic', 'validation horizons overlap within each block',
                     'nu is selected by weekly predictive log likelihood; multiplier by worst-fold empirical gap CVaR'],
        final_window=dict(start=str(data.index[dev_stop].date()), stop=str(data.index[-1].date()),
                          observations=len(data)-dev_stop, evaluated=False),
        selected_nu=selected_nu, selected_multiplier=selected_mult, fold_fitted_nu=fitted_nu,
        mean_validation_nll=mean_nll, records=records)

if __name__ == '__main__':
    result = run()
    dest = Path('artifacts/chronological_validation.json')
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}, indent=2))
    print(dest)
