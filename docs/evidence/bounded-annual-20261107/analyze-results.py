from pathlib import Path
import json,numpy as np,pandas as pd,collections
p=Path('artifacts/bounded-annual-20261107');r=json.loads((p/'historical.json').read_text());w=json.loads((p/'weekly.json').read_text());c=json.loads((p/'confirm.json').read_text());assert len(r['origins'])==19 and not any('error'in x for x in r['origins']);scores=[];annual=[];statuses=[]
for x in r['origins']:
 assert x['fit_last']<x['holdout_first'];assert x['study']['selection_lock']['final_scored']==False
 for y in x['multihorizon']:scores.append(dict(origin=x['origin'],**y))
 for y in x['results']:annual.append(dict(origin=x['origin'],**y))
 for name,st in x['study']['statuses'].items():statuses.append(dict(origin=x['origin'],method=name,kind=st.get('kind'),status=st.get('status'),error=st.get('error'),first_formulation_failure=st.get('first_formulation_failure')))
f=pd.DataFrame(scores);print('horizon',f.groupby(['weeks','model']).crps.mean().to_string());print('asset52',f.loc[f.weeks==52].groupby(['asset','model']).crps.mean().to_string())
a=pd.DataFrame(annual);print('annual methods',a.groupby('method').agg(n=('origin','count'),return_mean=('net_return','mean'),return_min=('net_return','min'),funded=('funded','sum')).to_string());print('statuscounts',collections.Counter((s['method'],s['kind']) for s in statuses));print('first fails',sum(bool(s['first_formulation_failure']) for s in statuses));print('errors',[s for s in statuses if s['error']])
wd=pd.DataFrame(w['summary']);print('weekly',wd.groupby(['stage','method']).agg(crps=('crps','mean'),q=('qlike','mean'),e1=('exceptions1','sum'),e5=('exceptions5','sum'),n=('n','sum')).to_string());print('interval',w['paired']);print('weeklyhits',[(x['year'],x['hits']['9.0'])for x in w['fits']]);
print('simhits')
for model,ds in c['judge_diagnostics'].items():
 if ds:
  print(model,dict(up=sum(sum(d['simulated_upper_hits']) for d in ds),lo=sum(sum(d['simulated_lower_hits']) for d in ds),total=sum(d['simulated_updates'] for d in ds)*5,initial=ds[0]['initial_variance'],base=ds[0]['baseline_variance']))
# Complete-case paired annual ledger differences. No selecting the best method.
pairs=[]
for name in ['cara','mv_matched']:
 for variant in ['raw','cross_validated']:
  aa=a.loc[a.method==f'gaussian_scale_mixture:{name}:{variant}'].set_index('origin');bb=a.loc[a.method==f'bounded_ewma_mixture:{name}:{variant}'].set_index('origin');common=sorted(set(aa.index)&set(bb.index));diff=bb.loc[common].net_return-aa.loc[common].net_return
  pairs.append(dict(objective=name,variant=variant,n=len(common),mean=float(diff.mean()) if len(common) else None,minimum=float(diff.min()) if len(common) else None,maximum=float(diff.max()) if len(common) else None,omitted_origins=sorted(set(a.origin)-set(common))))
print('annualpairs',pairs)
# Summaries of final all-risk pass counts, separate origin and law.
judges=[]
for x in r['origins']:
 for row in x['study']['rows']:
  for model,z in row['judges'].items():judges.append(dict(origin=x['origin'],method=row['method'],judge=model,passed=z['final']['overall_pass'],funding_passed=z['final']['funding_pass']))
j=pd.DataFrame(judges);print(j.groupby(['method','judge']).agg(n=('origin','count'),passed=('passed','sum')).to_string())
summary=dict(horizon=f.groupby(['weeks','model']).crps.mean().reset_index().to_dict('records'),annual=a.groupby('method').agg(n=('origin','count'),return_mean=('net_return','mean'),return_min=('net_return','min'),funded=('funded','sum')).reset_index().to_dict('records'),statuses=statuses,paired_annual=pairs,allrisk=j.groupby(['method','judge']).agg(n=('origin','count'),passed=('passed','sum')).reset_index().to_dict('records'),weekly_aggregate=wd.groupby(['stage','method']).agg(crps=('crps','mean'),qlike=('qlike','mean'),exception1=('exceptions1','sum'),exception5=('exceptions5','sum'),n=('n','sum')).reset_index().to_dict('records'))
(p/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
