"""Declarative asset metadata. No ticker substitution or data downloading.

The registry owns IDs, positions, roles and feature membership. Unsupported
return models fail before a numerical solve rather than guessing a sleeve.
"""
import copy,json,math
from pathlib import Path
from emfin_v2.config import CONFIG_DIR
MODELS={'etf_total_return','quarterly_property','cash_account'}


def load_registry(path=None):
    document=json.loads(Path(path or CONFIG_DIR/'assets.json').read_text())
    return validate_registry(document)


def validate_registry(document):
    d=copy.deepcopy(document)
    if d.get('schema_version')!=1 or not isinstance(d.get('assets'),list):raise ValueError('asset registry schema1 and assets list required')
    seen=set()
    for a in d['assets']:
        required=['id','name','ticker','asset_class','currency','return_model','liquidity','cash','factors','mean_view','source','enabled','minimum_weight','haircut']
        if not isinstance(a,dict) or any(k not in a for k in required):raise ValueError('incomplete asset metadata')
        if not isinstance(a['id'],str) or not a['id'] or a['id'] in seen:raise ValueError('unique stable asset IDs required')
        seen.add(a['id'])
        if a['return_model'] not in MODELS:raise ValueError('unsupported asset return model: '+str(a['return_model']))
        if not isinstance(a['factors'],list) or any(not isinstance(v,str) for v in a['factors']):raise ValueError('factor names must be strings')
        if any(type(a[k]) is not bool for k in ['enabled','cash','mean_view']):raise ValueError('asset flags must be booleans')
        if not all(isinstance(a[k],(float,int)) and not isinstance(a[k],bool) and math.isfinite(a[k]) for k in ['minimum_weight','haircut']):raise ValueError('finite asset bounds and haircut required')
        if not 0<=a['minimum_weight']<=1 or not 0<=a['haircut']<1:raise ValueError('invalid asset bound/haircut')
        if a['return_model']=='etf_total_return' and (not a['ticker'] or a['liquidity']!='listed'):raise ValueError('listed ETF requires ticker and listed liquidity')
        if a['return_model']=='cash_account' and (not a['cash'] or a['ticker'] is not None):raise ValueError('cash account requires cash role and no ETF ticker')
        if a['return_model']=='quarterly_property' and (a['cash'] or a['liquidity']!='planned_sale_only'):raise ValueError('property cannot be cash or a listed-liquid asset')
        if not isinstance(a['source'],dict) or not a['source'].get('kind'):raise ValueError('asset source kind required')
    active=[a for a in d['assets'] if a['enabled']]
    if len(active)<2 or sum(a['cash'] for a in active)!=1:raise ValueError('at least2 assets and exactly1 enabled cash/numeraire role required')
    if sum(a['return_model']=='quarterly_property' for a in active)>1:raise ValueError('current adapter supports at most1 property sleeve')
    if sum(a['minimum_weight'] for a in active)>1:raise ValueError('minimum holdings exceed wealth')
    return d


def active_assets(document):return [a for a in validate_registry(document)['assets'] if a['enabled']]


def layout(document):
    assets=active_assets(document);index={a['id']:i for i,a in enumerate(assets)}
    factors={name:[index[a['id']] for a in assets if name in a['factors']] for name in {f for a in assets for f in a['factors']}}
    return dict(ids=[a['id'] for a in assets],names=[a['name'] for a in assets],index=index,cash_index=next(i for i,a in enumerate(assets) if a['cash']),liquid_indices=[i for i,a in enumerate(assets) if a['liquidity']=='listed'],property_indices=[i for i,a in enumerate(assets) if a['return_model']=='quarterly_property'],view_indices=[i for i,a in enumerate(assets) if a['mean_view']],factor_indices=factors,minimum_weights=[a['minimum_weight'] for a in assets],haircuts=[a['haircut'] for a in assets])


def wasserstein_minimum_buffer(document,wealth,radius,confidence):
    if not all(math.isfinite(v) for v in (wealth,radius,confidence)) or wealth<=0 or radius<0 or not 0<confidence<1:raise ValueError('invalid wealth/radius/confidence')
    a=active_assets(document);smallest_linf=max(1/len(a),max(x['minimum_weight'] for x in a))
    return wealth*radius*smallest_linf/(1-confidence)
