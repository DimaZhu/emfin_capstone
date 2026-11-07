"""Prepare synthetic lookup files locally. Never uploads or deploys."""
import argparse,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def build(source,output):
    source=Path(source);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'manifest.json').read_text());summary=json.loads((source/'summary.json').read_text());spec=manifest['spec']
    if not spec.get('axes') or 'prototype' not in spec.get('tier',''):raise ValueError('viewer requires explicit prototype-tier synthetic grid')
    rows=[]
    for row in summary:
        if row.get('source')!='synthetic':raise ValueError('private or unknown grid row rejected')
        result=None
        path=source/'runs'/row['config_id']/'results.json'
        if row['status']=='complete':
            result=json.loads(path.read_text());re=result['config']['real_estate']
            if re['source']!='synthetic' or result['dashboard']['re_data']['observed'] is not None:raise ValueError('private calibration rejected')
        k=None if result is None else next((x for x in result['rows'] if x['method']=='proposed'),None)
        allocation=None if result is None else result['weights'].get('proposed')
        rows.append(dict(point={key:row[key] for key in spec['axes']},config_id=row['config_id'],status=row['status'],verdict=row['verdict'],error=row.get('error'),source='synthetic',tier=spec['tier'],code_sha256=manifest['provenance']['code_sha256'],data_sha256=manifest['provenance']['data_sha256'],assets=[] if result is None else result['assets'],allocation=allocation,kpis=None if k is None else dict(ce=k['net_ce']['mean'][0],upper=k['wasserstein_gap_upper'],budgets=k['budgets'],cash_weight=allocation[result['config']['cash_index']])))
    data=dict(source='synthetic',tier=spec['tier'],axes=spec['axes'],expected_count=manifest['expected_count'],engine=spec['engine'],fixed_re=spec['real_estate'],rows=rows)
    # JSON is embedded as a JS string, not executable code. Escape '<' to prevent
    # an input label terminating the script element.
    text=(ROOT/'prototype/apps-script/Index.html').read_text()
    payload=json.dumps(json.dumps(data,separators=(',',':'))).replace('<','\\u003c')
    text=text.replace('<?!= JSON.stringify(data) ?>',payload).replace('<?!= lookup ?>',(ROOT/'prototype/apps-script/Lookup.js').read_text())
    (out/'index.html').write_text(text)
    (out/'lookup-data.json').write_text(json.dumps(data,indent=2)+'\n')
    # Single-column CSV for a later, separately authorized Sheet import:
    # header, metadata row (without payload rows), then one JSON row per cell.
    meta=dict(data,rows=[])
    with (out/'synthetic-grid-sheet.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['dataset']);w.writerow([json.dumps(meta,separators=(',',':'))])
        for r in rows:
            value=json.dumps(r,separators=(',',':'))
            if len(value)>40000:raise ValueError('row too large for intended Sheet cell')
            w.writerow([value])
    for name in ['Code.gs','Index.html','Lookup.js']:
        (out/name).write_text((ROOT/'prototype/apps-script'/name).read_text())
    print(json.dumps(dict(local_html=str(out/'index.html'),complete=sum(r['status']=='complete' for r in rows),expected=len(rows),deployed=False)))
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--grid',default='artifacts/grid729-prototype-final');p.add_argument('--output',default='artifacts/lookup-viewer');a=p.parse_args();build(a.grid,a.output)
if __name__=='__main__':main()
