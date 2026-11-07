"""Resumable, bounded synthetic grid. No cloud writes or private imports."""
import os
for name in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[name]='1'
import argparse,concurrent.futures,contextlib,csv,fcntl,hashlib,itertools,json,sqlite3,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()


def provenance():
    code={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
          for folder in ['emfin_v2','experiments'] for p in sorted((ROOT/folder).rglob('*.py'))}
    data={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted((ROOT/'emfin_v2/resources/data').rglob('*')) if p.is_file()}
    import importlib.metadata as metadata
    versions={k:metadata.version(k) for k in ['numpy','pandas','scipy','cvxpy','clarabel','scs']}
    return dict(code_sha256=digest(dict(code=code,versions=versions)),data_sha256=digest(data),versions=versions,
                git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source='synthetic RE; bundled market snapshot',schema_version=1)


def configs(spec):
    from emfin_v2.default_run import load_config
    base=load_config();base.update(spec.get('engine',{}))
    base['real_estate'].update(spec.get('real_estate',{}))
    base['real_estate'].update(source='synthetic',enabled=True)
    if base.get('scenario_archives'):raise ValueError('shared grid forbids private scenario archives')
    if 'cases' in spec:
        from copy import deepcopy
        for case in spec['cases']:
            c=deepcopy(base)
            for key,value in case['overrides'].items():
                if '.' in key:
                    section,field=key.split('.',1);c[section][field]=value
                else:c[key]=value
            if c.get('scenario_archives') or c['real_estate']['source']!='synthetic':raise ValueError('shared studies forbid private sources')
            yield dict(study=case['study'],value=case['value']),c
        return
    # Force approved shared source regardless of a local import on the machine.
    keys=list(spec['axes']);payouts={'early':[4,8],'mixed':[7,13],'late':[10,13]}
    for values in itertools.product(*(spec['axes'][k] for k in keys)):
        point=dict(zip(keys,values));c=json.loads(canonical(base))
        c['risk_profile']=point['profile'];c['risk_tolerance']=c['wealth']*{'Preserve':.05,'Balanced':.1,'Growth':.2}[point['profile']]
        weeks=payouts[point['timing']]
        c['liabilities']=[dict(name='Grid payout '+str(i+1),week=w,amount=c['wealth']*point['payout_ratio']*f) for i,(w,f) in enumerate(zip(weeks,[35/95,60/95]))]
        c['wasserstein_radius']=point['radius'];c['real_estate'].update(minimum_weight=point['re_min'],equity_correlation=point['rho'])
        c['label']='Synthetic RE precomputed grid; not client evidence'
        yield point,c


def initialize(db,spec,prov):
    db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, point TEXT NOT NULL, config TEXT NOT NULL, provenance TEXT NOT NULL, status TEXT NOT NULL, seconds REAL, error TEXT, result_path TEXT)')
    for point,c in configs(spec):
        key=digest(dict(point=point,config=c,code=prov['code_sha256'],data=prov['data_sha256']))
        db.execute('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?,NULL,NULL,NULL)',(key,canonical(point),canonical(c),canonical(prov),'pending'))
    db.commit()


def worker(job):
    key,c,path=job;started=time.perf_counter()
    try:
        from emfin_v2.default_run import run
        result=run(c,path)
        from experiments.evidence import benchmark_evidence
        evidence=benchmark_evidence(c,result)
        (Path(path)/'benchmarks.json').write_text(json.dumps(evidence,indent=2)+'\n')
        # Never include local/private calibration in a shared synthetic artifact.
        assert result['config']['real_estate']['source']=='synthetic'
        assert result['dashboard']['re_data']['observed'] is None
        return key,'complete',time.perf_counter()-started,None,str(Path(path)/'results.json')
    except Exception as error:
        return key,'error',time.perf_counter()-started,type(error).__name__+': '+str(error),None


def execute(out,spec,workers=1,max_jobs=None,retry_errors=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/'runner.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('another grid writer owns this output directory')
        db=sqlite3.connect(out/'grid.sqlite');db.row_factory=sqlite3.Row
        prov=provenance();initialize(db,spec,prov)
        # A previous owning process exited before closeout. The OS lock ensures
        # no live writer can be mistaken for a stale process.
        db.execute("UPDATE jobs SET status='pending' WHERE status='running'")
        if retry_errors:db.execute("UPDATE jobs SET status='pending' WHERE status='error'")
        current=[digest(dict(point=point,config=c,code=prov['code_sha256'],data=prov['data_sha256'])) for point,c in configs(spec)]
        rows=[db.execute("SELECT * FROM jobs WHERE id=? AND status='pending'",(key,)).fetchone() for key in current]
        rows=[r for r in rows if r is not None][:max_jobs]
        for row in rows:db.execute("UPDATE jobs SET status='running' WHERE id=?",(row['id'],))
        db.commit()
        jobs=[(r['id'],json.loads(r['config']),str(out/'runs'/r['id'])) for r in rows]
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(worker,job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                key,status,seconds,error,path=future.result()
                db.execute('UPDATE jobs SET status=?,seconds=?,error=?,result_path=? WHERE id=?',(status,seconds,error,path,key));db.commit()
        manifest=dict(provenance=prov,spec=spec,job_ids=current,expected_count=len(current))
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        export(db,out,current)
        counts=dict(db.execute('SELECT status,count(*) FROM jobs WHERE id IN ('+','.join('?'*len(current))+') GROUP BY status',current))
        print(json.dumps(dict(expected=len(current),counts=counts,output=str(out))))
        db.close()


def export(db,out,ids):
    rows=[]
    for key in ids:
        row=db.execute('SELECT * FROM jobs WHERE id=?',(key,)).fetchone()
        item=dict(config_id=key,**json.loads(row['point']),status=row['status'],seconds=row['seconds'],error=row['error'],source='synthetic',code_sha256=json.loads(row['provenance'])['code_sha256'])
        if row['result_path']:
            r=json.loads(Path(row['result_path']).read_text());selected=r['dashboard']['selected'];item['verdict']='unavailable' if selected is None else 'pass' if r['dashboard']['evaluation_pass'] else 'fail'
            item['allocation']=canonical(r['weights'].get('proposed'))
            item['kpis']=canonical(next((x for x in r['rows'] if x['method']=='proposed'),None))
            item['dashboard']=canonical(r['dashboard'])
        else:item.update(verdict=row['status'],allocation='null',kpis='null',dashboard='null')
        rows.append(item)
    keys=sorted({k for r in rows for k in r})
    with (out/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    try:
        import pandas as pd
        pd.DataFrame(rows).to_parquet(out/'summary.parquet',index=False)
    except ImportError:
        (out/'parquet-unavailable.txt').write_text('Install requirements-science.txt for Parquet output. CSV/JSON/SQLite are complete.\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default='experiments/configs/grid729.json');p.add_argument('--output',default='artifacts/grid729');p.add_argument('--workers',type=int,default=1);p.add_argument('--max-jobs',type=int);p.add_argument('--retry-errors',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    spec=json.loads(Path(a.config).read_text())
    if not 1<=a.workers<=8:raise ValueError('workers must be 1-8; benchmark memory first')
    if a.dry_run:
        print(json.dumps(dict(count=sum(1 for _ in configs(spec)),axes=spec.get('axes',{}),fixed_re=spec.get('real_estate'),engine=spec.get('engine'))));return
    execute(a.output,spec,a.workers,a.max_jobs,a.retry_errors)

if __name__=='__main__':main()
