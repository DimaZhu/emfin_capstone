"""Regenerate a local scientific report from the resumable synthetic grid."""
import argparse,csv,html,json,math,shutil,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from experiments.grid import execute,ROOT


def table(rows,columns):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+html.escape(c)+'</th>' for c in columns)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(row.get(c,'')))+'</td>' for c in columns)+'</tr>' for row in rows)+'</tbody></table></div>'


def write_csv(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(rows)


def analyze(out,skip_tests=False):
    import numpy as np
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from experiments.evidence import proof_points
    out=Path(out);figdir=out/'figures';figdir.mkdir(exist_ok=True)
    manifest=json.loads((out/'manifest.json').read_text());allrows=json.loads((out/'summary.json').read_text());ids=set(manifest['job_ids'])
    rows=[r for r in allrows if r['config_id'] in ids];complete=[r for r in rows if r['status']=='complete'];errors=[r for r in rows if r['status']=='error']
    proof,transport=proof_points();(out/'proof_points.json').write_text(json.dumps(proof,indent=2)+'\n');write_csv(out/'proof_points.csv',proof)
    testing=dict(status='not run',tests=None,failures=None,errors=None,skipped=None)
    if not skip_tests:
        p=subprocess.run([sys.executable,'-m','pytest','tests/','-q','--junitxml='+str((out/'tests.xml').resolve())],cwd=ROOT,text=True,capture_output=True)
        (out/'tests.txt').write_text(p.stdout+p.stderr)
        node=ET.parse(out/'tests.xml').getroot();suites=list(node) if node.tag=='testsuites' else [node]
        testing={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};testing['status']='pass' if p.returncode==0 else 'fail'
    (out/'testing.json').write_text(json.dumps(testing,indent=2)+'\n')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.facecolor':'white','text.color':'#251f21','axes.labelcolor':'#251f21','svg.fonttype':'none','savefig.bbox':'tight'})
    def save(fig,name):
        fig.tight_layout();fig.savefig(figdir/(name+'.svg'));fig.savefig(figdir/(name+'.png'),dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.8,3.6));ax.loglog([x['distance'] for x in transport],[x['gap'] for x in transport],'o-',color='#527d70');ax.set(xlabel='Adversarial support distance (normalized price units)',ylabel='Dual bound minus transport LP hinge',title='Numerical check of the W1 fixed-threshold envelope');ax.grid(alpha=.2);save(fig,'transport')
    fig,ax=plt.subplots(figsize=(6.8,3.6));ax.barh([x['test'] for x in proof],[max(x['absolute_error'],1e-16)/x['tolerance'] for x in proof],color=['#527d70' if x['passed'] else '#c0393b' for x in proof]);ax.axvline(1,color='#c0393b',ls='--');ax.set_xscale('log');ax.set(xlabel='Absolute error / stated tolerance (log scale)',title='Known-case residuals; below 1 passes');save(fig,'proof_residuals')
    # Reference point is an explicit config, not the best-performing cell.
    target=dict(profile='Balanced',payout_ratio=.75,timing='late',re_min=.1,radius=.00002,rho=.3)
    selected=next((r for r in complete if all(r[k]==v for k,v in target.items())),complete[0] if complete else None)
    bench=[];batches=[]
    if selected:
        b=json.loads((out/'runs'/selected['config_id']/'benchmarks.json').read_text());bench=b['summary'];batches=b['batches'];(out/'benchmark_reference.json').write_text(json.dumps(dict(config_id=selected['config_id'],point={k:selected[k] for k in target},evidence=b),indent=2)+'\n')
        fig,axes=plt.subplots(1,2,figsize=(10,4));names=[b['method'] for b in bench];means=np.array([b['net_ce']['mean'][0]/1e6 for b in bench]);lo=np.array([b['net_ce']['low'][0]/1e6 for b in bench]);hi=np.array([b['net_ce']['high'][0]/1e6 for b in bench]);colors=['#527d70' if b['heldout_funding_pass'] else '#c0393b' for b in bench]
        axes[0].barh(names,means,color=colors);axes[0].errorbar(means,np.arange(len(names)),xerr=[np.maximum(0,means-lo),np.maximum(0,hi-means)],fmt='none',ecolor='#251f21',capsize=3);axes[0].set(xlabel='Net certainty equivalent (USD millions)',title='Matched-seed held-out comparison')
        for bi,b in enumerate(bench):axes[1].scatter(b['volatility']*100,b['expected_return']*100,color='#527d70' if b['heldout_funding_pass'] else '#c0393b',marker='o' if b['method']=='proposed' else 'x');axes[1].annotate(b['method'],(b['volatility']*100,b['expected_return']*100),fontsize=8,xytext=(4,5 if bi!=len(bench)-1 else -14),textcoords='offset points')
        axes[1].set(xlabel='Horizon return volatility (%)',ylabel='Expected horizon gross return (%)',title='Green: held-out funding budgets passed');save(fig,'benchmarks')
        write_csv(out/'benchmark_summary.csv',[dict(method=b['method'],net_ce_usd=b['net_ce']['mean'][0],conditional_ci_low=b['net_ce']['low'][0],conditional_ci_high=b['net_ce']['high'][0],paired_ce_difference_usd=b['paired_ce_difference']['mean'][0],paired_reference=b['paired_reference'],heldout_funding_pass=b['heldout_funding_pass'],cml=b['cml'],cash_weight=b['cash_weight']) for b in bench])
        write_csv(out/'benchmark_batches.csv',batches)
    ratios=sorted({r['payout_ratio'] for r in rows});mins=sorted({r['re_min'] for r in rows})
    # Never average away other parameters. A heatmap is one named fixed slice.
    fixed=dict(profile='Balanced',timing='late',radius=.00002,rho=.3)
    slice_=[r for r in rows if all(r[k]==v for k,v in fixed.items())]
    if not slice_:slice_=[]
    verdict=np.full((len(mins),len(ratios)),np.nan);ce=np.full_like(verdict,np.nan)
    for r in slice_:
        i=mins.index(r['re_min']);j=ratios.index(r['payout_ratio']);verdict[i,j]={'pass':1,'fail':0,'unavailable':-1,'error':-2,'pending':-3}.get(r['verdict'],-3)
        if r['verdict'] in ('pass','fail'):ce[i,j]=json.loads(r['kpis'])['net_ce']['mean'][0]/1e6
    fig,ax=plt.subplots(figsize=(6.8,4));im=ax.imshow(verdict,cmap=ListedColormap(['#e1e1e1','#d56a6a','#e7c27b','#c0393b','#73a89a']),vmin=-3.5,vmax=1.5,origin='lower',aspect='auto');ax.set_xticks(range(len(ratios)),[f'{x:.0%}' for x in ratios]);ax.set_yticks(range(len(mins)),[f'{x:.0%}' for x in mins]);ax.set(xlabel='Total planned payout / initial capital',ylabel='Minimum RE holding',title='Funding verdict, no interpolation')
    label={1:'pass',0:'fail',-1:'unavailable',-2:'error',-3:'pending'}
    for (i,j),x in np.ndenumerate(verdict):ax.text(j,i,label.get(x,'not in grid'),ha='center',va='center',fontsize=9)
    save(fig,'funding_heatmap')
    # Two named one-dimensional slices through the same reference point.
    fig,axes=plt.subplots(1,2,figsize=(9,3.6))
    for ax,key,label_ in zip(axes,['payout_ratio','re_min'],['Payout / capital','Minimum RE holding']):
        cut=[r for r in complete if all(r[k]==v for k,v in target.items() if k!=key)]
        cut=sorted(cut,key=lambda r:r[key]);good=[r for r in cut if r['verdict'] in ('pass','fail')]
        ax.plot([r[key]*100 for r in good],[json.loads(r['kpis'])['net_ce']['mean'][0]/1e6 for r in good],'o-',color='#527d70')
        ax.set(xlabel=label_+' (%)',ylabel='Net CE (USD millions)',title='Fixed reference slice');ax.grid(alpha=.2)
        for r in cut:
            if r['verdict'] not in ('pass','fail'):ax.annotate(r['verdict'],(r[key]*100,.05),xycoords=('data','axes fraction'),rotation=90,fontsize=8)
    save(fig,'one_dimensional')
    # Parallel coordinates retain all six dimensions, not an averaged surface.
    axes_keys=list(manifest['spec']['axes']);fig,ax=plt.subplots(figsize=(9,3.8))
    for r in rows:
        y=[]
        for key in axes_keys:
            options=manifest['spec']['axes'][key]
            ordered=sorted(options) if all(isinstance(x,(int,float)) for x in options) else options
            y.append(ordered.index(r[key])/max(1,len(ordered)-1))
        ax.plot(range(len(y)),y,color={'pass':'#527d70','fail':'#c0393b','unavailable':'#b58a45'}.get(r['verdict'],'#b0b0b0'),alpha=.22)
    ax.set_xticks(range(len(axes_keys)),axes_keys);ax.set(ylabel='Discrete level (0 = first/minimum, 1 = last/maximum)',title='Grid combinations: each line is one stored run');save(fig,'parallel_coordinates')
    from experiments.studies import build
    studies=build(out,plt)
    write_csv(out/'one_factor_studies.csv',studies)
    status_counts={k:sum(r['verdict']==k for r in rows) for k in sorted({r['verdict'] for r in rows})}
    claims=[dict(claim='Payout conservation / settlement cash',test='test_real_estate_v2.py, test_multiperiod*',limit='Specified cash-flow convention only'),dict(claim='Entropy-pooling / W1 implementation',test='test_entropy_pooling.py, test_wasserstein.py',limit='Finite numerical cases and mathematical bounds, not forecast coverage'),dict(claim='Packaging / private-source boundary',test='installed smoke and archive/provenance tests',limit='Local evidence; CI status is separate'),dict(claim='General economic usefulness',test='Not established by unit tests',limit='Requires real client evidence and external validation')]
    captions={'proof_residuals':'Analytic identities and tiny constructed examples. Tolerances are declared in proof_points.csv; not universal proof of the model.','transport':'A finite transport LP approaches the fixed-threshold dual bound as support expands. It does not validate the selected Wasserstein radius.','benchmarks':'Same evaluation seeds and minimum holdings. Red means a funding-budget failure, not a worse return. Error bars are conditional batch-mean 95% Student-t intervals. Some baselines do not enforce funding/loss constraints.','funding_heatmap':'Fixed: Balanced profile, late timing, W1 radius 0.00002, rho 0.3. Pending/error/unavailable are not safe zero-loss cells.','one_dimensional':'Other inputs fixed to Balanced, payout ratio .75, late timing, RE floor .10, radius .00002, rho .3. Lines connect sampled points, not a continuous optimizer guarantee.','parallel_coordinates':'Six discrete axes as configured in manifest.json. This is a grid view, not Sobol attribution or a probability-weighted forecast.'}
    captions.update(solver_tolerance='Three CLARABEL tolerances on a deterministic two-asset known-solution problem. Not a full-model solver convergence proof.',sensitivity_curves='One factor at a time; synthetic RE reference with all other inputs fixed. Settlement cases use sale agreement week 1. Scenario-count and seed panels are numerical stability checks, not proof of statistical convergence.',tornado='Endpoint CE minus central CE in each three-point study. Only complete, available triples are ranked; omitted failures remain in one_factor_studies.csv.',history_uncertainty='A generated 45-return smoothed series, not the private Abu Dhabi index. Shading is marginal 5-95% circular block-bootstrap range. Alpha is assumed. Missing regimes and model uncertainty remain unmeasured.',ep_residual_sweep='Twenty constructed one-view entropy-pooling problems over five scenario counts. Small residuals demonstrate numerical constraint satisfaction only.')
    def figure(name):
        caption=captions.get(name,'One-factor study with fixed remaining inputs. Green passes held-out funding; red fails; unavailable is not zero CE. Open the SVG for full-size inspection.')
        return f'<figure><a href="figures/{name}.svg"><img src="figures/{name}.svg" alt="{html.escape(name.replace("_"," "))}"></a><figcaption>{html.escape(caption)}</figcaption></figure>'

    benchmark_table=[dict(method=b['method'],net_CE_USDm=round(b['net_ce']['mean'][0]/1e6,4),funding_pass=b['heldout_funding_pass'],cash_weight=round(b['cash_weight'],4),CML=round(b['cml'],4)) for b in bench]
    source=manifest['provenance'];intro=f"{len(complete)} / {len(rows)} grid runs complete. Verdict counts: {status_counts}. RE is synthetic; market returns use the bundled historical snapshot. This reference is a small numerical demonstration, not publication-grade evidence."
    report='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EMFin scientific evidence</title><style>body{font:15px/1.65 Arial,sans-serif;color:#251f21;background:white;margin:0}main{max-width:1080px;margin:auto;padding:28px}h1,h2{font-family:Georgia,serif;font-weight:400;line-height:1.2}h1{font-size:36px}h2{margin-top:42px;font-size:28px}p,li{max-width:85ch}.callout{background:#f4efec;padding:18px;border-radius:8px}figure{margin:24px 0;padding:12px;border:1px solid #eae9ea;border-radius:8px}img{max-width:100%;height:auto}figcaption{font-size:13px;color:#585254}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid #eae9ea;text-align:left;padding:10px;vertical-align:top}.table-wrap{overflow:auto}code{overflow-wrap:anywhere}a{color:#426a5e}@media(max-width:600px){main{padding:20px}h1{font-size:28px}h2{font-size:24px}figure{padding:6px}table{font-size:12px}}</style></head><body><main><h1>EMFin scientific evidence</h1>'''
    report+=f'<p class="callout">{html.escape(intro)}</p><p>Code digest: <code>{source["code_sha256"]}</code>. Re-run definitions and exact input hashes are in manifest.json. Model valuation and execution seeds are in each stored result.</p>'
    report+='<h2>1. Testing</h2><p>'+html.escape(str(testing))+'</p>'+table(claims,['claim','test','limit'])+'<p>Passing tests show that the named checks passed. They cannot establish economic truth, data independence or safe real-world execution. An installed-wheel smoke is a separate command and CI result, not inferred from this table.</p>'
    report+=figure('ep_residual_sweep')+figure('solver_tolerance')
    report+='<h2>2. Matched-scenario benchmarks</h2>'+(figure('benchmarks')+table(benchmark_table,['method','net_CE_USDm','funding_pass','cash_weight','CML']) if bench else '<p>No completed benchmark result. Nothing is substituted.</p>')+''.join('<p class="callout">'+html.escape(b['method'])+': net CE $'+f'{b["net_ce"]["mean"][0]/1e6:.3f}'+'M; held-out funding '+('passed' if b['heldout_funding_pass'] else 'failed')+'; cash '+f'{b["cash_weight"]:.1%}'+'.</p>' for b in bench)+'<p>Reference config: <code>'+html.escape(selected['config_id'] if selected else 'none')+'</code>. These are fresh simulated held-out paths, not chronological historical out-of-sample returns. Sample size and seed counts come from the selected config. Funding pass is not a universal risk pass or a recommendation. Raw paired batches are in benchmark_batches.csv.</p>'
    report+='<h2>3. Numerical proof points</h2>'+figure('proof_residuals')+figure('transport')+table(proof,['test','expected','observed','absolute_error','tolerance','passed'])
    report+='<h2>4. Sensitivity and grid evidence</h2>'+figure('funding_heatmap')+figure('one_dimensional')+figure('parallel_coordinates')+figure('history_uncertainty')+(figure('tornado')+''.join(figure('study_'+str(i)) for i,_ in enumerate(sorted({r['study'] for r in studies}))) if studies else '<p>One-factor studies have not been run.</p>')+'<p>Only the configured axes are tested. Full RE history/unsmoothing uncertainty is in the private local model, not copied into this synthetic report. Sobol attribution is not reported because no justified joint input distribution has been supplied. The small sample-count and seed panels do not establish asymptotic convergence. Larger sample-count, solver-tolerance and seed convergence studies remain necessary for publication-grade conclusions. The full grid and the reference grid are separate experiment definitions, not interchangeable evidence.</p>'
    report+='<h2>Failures and incomplete runs</h2>'+table([dict(config_id=r['config_id'],status=r['status'],verdict=r['verdict'],error=r.get('error')) for r in rows if r['status']!='complete'],['config_id','status','verdict','error'])
    report+='<h2>Reproduce and inspect</h2><p><code>python -m experiments.scientific_report --config experiments/configs/reference.json --output artifacts/scientific</code></p><p>SQLite is the resumable ledger. summary.csv / summary.json / optional Parquet are analysis tables. Per-config JSON holds allocations, KPIs, all payout checks and fans. Changing model/config/data hashes creates new job IDs; it does not overwrite an old scientific claim. No external deployment or sharing occurs.</p></main></body></html>'
    (out/'report.html').write_text(report)
    print(json.dumps(dict(report=str(out/'report.html'),testing=testing,proof_pass=all(r['passed'] for r in proof),complete=len(complete),expected=len(rows))))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default='experiments/configs/reference.json');p.add_argument('--output',default='artifacts/scientific');p.add_argument('--workers',type=int,default=1);p.add_argument('--max-jobs',type=int);p.add_argument('--stage',choices=['all','grid','analysis'],default='all');p.add_argument('--skip-tests',action='store_true');p.add_argument('--skip-studies',action='store_true');a=p.parse_args()
    if not 1<=a.workers<=8:raise ValueError('workers must be 1-8')
    if a.stage in ('all','grid'):execute(a.output,json.loads(Path(a.config).read_text()),a.workers,a.max_jobs)
    if a.stage=='all' and not a.skip_studies:
        execute(Path(a.output)/'sensitivities',json.loads((ROOT/'experiments/configs/sensitivities.json').read_text()),a.workers,a.max_jobs)
    if a.stage in ('all','analysis'):analyze(a.output,a.skip_tests)

if __name__=='__main__':main()
