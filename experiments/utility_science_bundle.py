"""Rebuild compact dashboard research snapshot from preserved studies."""
import json
from pathlib import Path
ROOT=Path('artifacts/utility-comparison-20261107');DEST=Path('emfin_v2/resources/data/science/utility-comparison-20261107.json')


def main():
    out=json.loads(DEST.read_text());out['studies']=[]
    out['scope']='FROZEN RETROSPECTIVE RESEARCH. User confirmed $250k/month; 12 modeled monthly calls total $3M. Due weeks are approximate, not calendar settlement dates. Other amounts are labelled sensitivities or check stress tests, NOT user obligations. Fixed research inputs: $100M wealth, 10% unsold property, zero rent/cash, 100 train / 200 validation / 400 final paths x4. Not recomputed when controls change. Same paths, EP and all-risk+strict judge. Default remains CARA; native gross/net CEs are not cross-family rankings.'
    out['takeaway']='No utility winner established for the confirmed $250k/month schedule: all four choose a 25% candidate / 75% anchor blend and pass this final fitted-model judge. Hard constraints mostly dominate. Sensitivities are not obligations. Extreme check stress tests establish limits, not realistic payment scenarios. Raw HARA has domain failures there; the family name cannot cure infeasibility.'
    for source in [ROOT/'summary.json',ROOT/'sensitivity'/'summary.json']:
      r=json.loads(source.read_text())
      for s in r['studies']:
        z=dict(name=s['name'],model=s['model'],utilities=[])
        for d in out['definitions']:
          raw=next((x for x in s['rows'] if x['kind']==d['kind'] and x['variant']=='raw'),None);selected=next((x for x in s['rows'] if x['kind']==d['kind'] and x['variant']=='validated'),None);status=next(x['status'] for x in s['specifications'] if x['kind']==d['kind'])
          def reduced(x):
            if x is None:return None
            v=x['verdict'];return dict(fraction=x['fraction'],cash=x['cash_weight'],all_risk=v['overall_pass'],strict=v['strict_funding']['passed'],funded=v['strict_funding']['reference_fraction'],funded_lower=v['strict_funding']['reference_lower95'],common_ce=x['common_cara_ledger_ce'],mean=x['ledger_net_mean'],quantiles=x['ledger_quantiles'],native=x['native_provisioning_ce'],breaches=v['breaches'])
          z['utilities'].append(dict(kind=d['kind'],raw=reduced(raw),selected=reduced(selected),status=status['kind'],solver=status.get('solver'),first_failure=status.get('first_formulation_failure')))
        out['studies'].append(z)
    DEST.write_text(json.dumps(out,indent=2))

if __name__=='__main__':main()
