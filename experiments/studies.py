"""Scientific plots for explicit one-factor studies and synthetic history risk."""
import json
from pathlib import Path
import numpy as np


def build(out,plt):
    from emfin_v2.real_estate import history_statistics
    from emfin_v2.toolbox import entropy_pooling as ep
    out=Path(out);folder=out/'sensitivities';items=[]
    if (folder/'summary.json').exists():
        for row in json.loads((folder/'summary.json').read_text()):
            k=json.loads(row['kpis']);items.append(dict(study=row['study'],value=row['value'],verdict=row['verdict'],ce=None if k is None else k['net_ce']['mean'][0]/1e6,seconds=row['seconds']))
    def save(fig,name):
        fig.tight_layout();fig.savefig(out/'figures'/(name+'.svg'),bbox_inches='tight');fig.savefig(out/'figures'/(name+'.png'),dpi=150,bbox_inches='tight');plt.close(fig)
    names=sorted({r['study'] for r in items})
    if names:
        fig,axes=plt.subplots((len(names)+2)//3,3,figsize=(11,3*((len(names)+2)//3)),squeeze=False)
        for ax,name in zip(axes.flat,names):
            points=sorted([r for r in items if r['study']==name],key=lambda r:r['value']);low=min(r['value'] for r in points);high=max(r['value'] for r in points);pad=max((high-low)*.1,abs(low)*1e-8,1e-8);ax.set_xlim(low-pad,high+pad);valid=[r for r in points if r['ce'] is not None]
            ax.plot([r['value'] for r in valid],[r['ce'] for r in valid],'o-',color='#527d70');ax.set(title=name,xlabel='Configured value (see study manifest)',ylabel='Net CE (USD millions)');ax.ticklabel_format(useOffset=False,style='plain',axis='x');ax.tick_params(axis='x',rotation=25)
            for r in points:
                if r['ce'] is None:ax.annotate(r['verdict'],(r['value'],.05),xycoords=('data','axes fraction'),rotation=90,fontsize=8)
        for ax in list(axes.flat)[len(names):]:ax.set_visible(False)
        save(fig,'sensitivity_curves')
        # Single-panel versions remain readable on phones; the montage is
        # supplemental, not the only way to read a sensitivity result.
        for index,name in enumerate(names):
            points=sorted([r for r in items if r['study']==name],key=lambda r:r['value']);valid=[r for r in points if r['ce'] is not None]
            fig,ax=plt.subplots(figsize=(6.8,3.8));x=np.arange(len(points))
            percent=any(k in name for k in ['drift','vol','yield','haircut','radius','budget'])
            labels=[f"{r['value']*100:g}%" if percent else str(r['value']) for r in points]
            if name=='Forward vs boom sample':labels=['4% forward view','12.6% sample scenario']
            for j,r in enumerate(points):
                if r['ce'] is not None:ax.plot(j,r['ce'],'o',color='#527d70' if r['verdict']=='pass' else '#c0393b')
                else:ax.annotate(r['verdict'],(j,.1),xycoords=('data','axes fraction'),rotation=90)
            if len(valid)>1:
                indices=[points.index(r) for r in valid];ax.plot(indices,[r['ce'] for r in valid],color='#527d70',alpha=.5)
                if max(r['ce'] for r in valid)-min(r['ce'] for r in valid)<1e-6:
                    mid=np.mean([r['ce'] for r in valid]);ax.set_ylim(mid-.000001,mid+.000001);ax.text(.02,.92,'Variation below $1',transform=ax.transAxes)
            ax.set_xticks(x,labels);ax.set_xlim(-.3,len(points)-.7);ax.ticklabel_format(axis='y',style='plain',useOffset=False);ax.set(title=name.replace('_',' '),xlabel='Explicit sampled assumption',ylabel='Net certainty equivalent (USD millions)');ax.grid(alpha=.15);save(fig,'study_'+str(index))
        # Tornado uses lower/upper sampled CE minus central sampled CE only
        # when all three values are available, and never ranks an unavailable as zero.
        changes=[]
        for name in names:
            points=sorted([r for r in items if r['study']==name],key=lambda r:r['value'])
            if len(points)==3 and all(r['ce'] is not None for r in points):
                lo,mid,hi=[r['ce'] for r in points];changes.append((name,min(lo-mid,hi-mid),max(lo-mid,hi-mid)))
        changes.sort(key=lambda r:max(abs(r[1]),abs(r[2])))
        fig,ax=plt.subplots(figsize=(7.5,max(3,len(changes)*.4)))
        for i,(name,lo,hi) in enumerate(changes):ax.plot([lo,hi],[i,i],lw=7,color='#73a89a')
        ax.set_yticks(range(len(changes)),[r[0] for r in changes]);ax.axvline(0,color='#585254');ax.set(xlabel='Endpoint minus central net CE (USD millions)',title='One-factor tornado; incomplete triples omitted');save(fig,'tornado')
    # This does NOT load the user's private index. The synthetic construction
    # isolates what varying the smoothing model can and cannot do.
    rng=np.random.default_rng(54);latent=rng.normal(.003,.02,45);reported=[latent[0]]
    for r in latent[1:]:reported.append(.4*reported[-1]+.6*r)
    stats=[history_statistics(tuple(reported),a) for a in [0.,.2,.4,.6,.8]]
    fig,axes=plt.subplots(1,2,figsize=(9,3.5))
    for ax,key,label in zip(axes,['drift_range','vol_range'],['Annual log drift (%)','Annual volatility (%)']):
        mid=np.array([s[key][1]*100 for s in stats]);low=np.array([s[key][0]*100 for s in stats]);high=np.array([s[key][2]*100 for s in stats]);x=[s['smoothing_alpha'] for s in stats]
        ax.plot(x,mid,'o-',color='#527d70');ax.fill_between(x,low,high,color='#73a89a',alpha=.25);ax.set(xlabel='Assumed stale-price alpha',ylabel=label,title='Synthetic 45-return history')
    save(fig,'history_uncertainty');(out/'synthetic_history_sensitivity.json').write_text(json.dumps(stats,indent=2)+'\n')
    residual=[]
    for n in [10,25,50,100,250]:
        for seed in range(4):
            x=np.random.default_rng(seed).normal(size=n);target=x.mean()+.1*x.std()
            q=ep.joint_entropy_pooling(n,[ep.View(x,[target])]).posterior_probs
            residual.append(dict(n=n,seed=seed,residual=float(abs(x@q-target)),normalization=float(abs(q.sum()-1))))
    (out/'ep_residual_sweep.json').write_text(json.dumps(residual,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(6.8,3.5));ax.scatter([r['n'] for r in residual],[max(r['residual'],1e-16) for r in residual],color='#527d70');ax.set_yscale('log');ax.set(xlabel='Number of scenarios in a one-view constructed problem',ylabel='Absolute mean-view residual',title='Entropy-pooling numerical residual sweep, four seeds');save(fig,'ep_residual_sweep')
    # Solver tolerance study is a known analytic problem, not a claim about
    # tolerances on the full stochastic optimization pipeline.
    import cvxpy as cp,time
    convergence=[]
    for tolerance in [1e-4,1e-6,1e-8]:
        w=cp.Variable(2);problem=cp.Problem(cp.Maximize(w@np.array([1.,1.2])),[cp.sum(w)==1,w>=0,w[0]>=.75])
        start=time.perf_counter();problem.solve(solver='CLARABEL',tol_gap_abs=tolerance,tol_gap_rel=tolerance,tol_feas=tolerance)
        convergence.append(dict(tolerance=tolerance,weight_error=float(abs(w.value[1]-.25)),seconds=time.perf_counter()-start,status=problem.status,max_constraint_residual=max(float(np.max(c.violation())) for c in problem.constraints)))
    (out/'solver_tolerance.json').write_text(json.dumps(convergence,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(6.8,3.5));ax.loglog([r['tolerance'] for r in convergence],[max(r['weight_error'],1e-16) for r in convergence],'o-',color='#527d70');ax.set(xlabel='Configured feasibility/gap tolerance',ylabel='Absolute weight error vs analytic optimum',title='Tiny deterministic solver-tolerance study');save(fig,'solver_tolerance')
    return items
