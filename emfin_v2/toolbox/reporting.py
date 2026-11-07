"""Portable, dependency-light report exports from structured engine results."""
from pathlib import Path
import csv
import json
import numpy as np


def write_report(result, output_dir='artifacts/report'):
    dest=Path(output_dir);dest.mkdir(parents=True,exist_ok=True)
    (dest/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    fields=['method','parametric_ce','empirical_ce','parametric_gap_cvar','budget','solve_seconds']
    with (dest/'benchmarks.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fields);writer.writeheader();writer.writerows(result['benchmarks'])
    with (dest/'allocations.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['method']+result['assets'])
        for name,w in result['weights'].items():writer.writerow([name]+w)
    caveats='\n'.join('- '+c for c in result['caveats'])
    rows='\n'.join(f"|{r['method']}|{r['parametric_ce']:,.0f}|{r['empirical_ce']:,.0f}|{r['parametric_gap_cvar']:,.0f}|" for r in result['benchmarks'])
    (dest/'appendix.md').write_text(f"# Engine validation appendix\n\nSnapshot: {result['snapshot_end']}.\n\n|Method|Parametric CE ($)|Overlapping empirical CE ($)|Fresh MC gap CVaR ($)|\n|---|---:|---:|---:|\n{rows}\n\n## Qualifications\n\n{caveats}\n")
    return dest


def efficient_frontier(gross_samples, points=15):
    """Long-only model mean/variance frontier, without liability constraints."""
    import cvxpy as cp
    r=np.asarray(gross_samples)-1
    mu=r.mean(0);cov=np.cov(r,rowvar=False)
    w=cp.Variable(r.shape[1]);problem_min=cp.Problem(cp.Minimize(cp.quad_form(w,cp.psd_wrap(cov))),[cp.sum(w)==1,w>=0])
    problem_min.solve(solver='CLARABEL')
    if w.value is None:raise RuntimeError('minimum variance frontier failed')
    low=float(mu@w.value)
    rows=[]
    for target in np.linspace(low,float(mu.max()),points):
        problem=cp.Problem(cp.Minimize(cp.quad_form(w,cp.psd_wrap(cov))),[cp.sum(w)==1,w>=0,mu@w>=target])
        problem.solve(solver='CLARABEL')
        if w.value is None:continue
        rows.append(dict(risk=float(np.sqrt(max(w.value@cov@w.value,0))),mean=float(mu@w.value)))
    return rows
