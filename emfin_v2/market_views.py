"""Typed horizon-return views, with explicit units and no text interpretation."""
import numpy as np
NAMES=['US equities','International equities','Emerging equities','US Treasury bonds','Investment-grade credit']


def validate_views(values,allowed_indices=None):
    if not isinstance(values,dict):raise ValueError('market_return_views must be an asset-index dictionary')
    allowed=[str(i) for i in (range(5) if allowed_indices is None else allowed_indices)]
    for key,value in values.items():
        if str(key) not in allowed or not isinstance(value,(float,int)) or not np.isfinite(value) or not -.5<=value<=.5:
            raise ValueError('market return targets need asset indices 0-4 and finite horizon returns -50% to 50%')


def evidence(c,draw,q,qs):
    from emfin_v2.default_run import ep
    terminal=draw[0][:,-1]-1
    rows=[];requested=c.get('market_return_views',{})
    indices=c.get('asset_layout',{}).get('view_indices',list(range(5)))
    names=c.get('asset_names',NAMES)
    for i in indices:
        name=names[i]
        rows.append(dict(asset_index=i,name=name,prior=float(terminal[:,i].mean()),requested=requested.get(str(i)),achieved=float(q@terminal[:,i]),stressed=float(qs@terminal[:,i]),prior_min=float(terminal[:,i].min()),prior_max=float(terminal[:,i].max())))
    members=c['view_instruments'];i,j=(members+[members[0]])[:2];loss=np.maximum(0,1-draw[0][:,:,members].mean(2)).max(1)
    return dict(units=f'Expected simple return over {c["horizon_weeks"]} weeks, after configured liquidity haircut; not annual return',rows=rows,
        stress=dict(increment=c['stress_mean_path_loss_increment'],prior=float(loss.mean()),nominal=float(loss@q),achieved=float(loss@qs),units='Expected maximum equity-basket loss from initial value over the horizon; not CML or a crisis probability'),
        relative_equity_spread=dict(requested=c['view_spread'] if not requested and c['view_spread'] else None,achieved=float(q@(terminal[:,j]-terminal[:,i])),note='Legacy relative view disabled for the registry universe; absolute targets use registered membership.' if c.get('asset_registry') else 'International less US expected horizon return; disabled when absolute asset targets are set'),
        posterior_effective_scenarios=float(np.exp(-np.sum(q*np.log(np.maximum(q,1e-300)*len(q))))*len(q)),
        note='Prior is a sample-informed modeled horizon distribution, not a realized historical return. Reweighting can move other asset moments. Targets outside joint scenario support fail explicitly.')
