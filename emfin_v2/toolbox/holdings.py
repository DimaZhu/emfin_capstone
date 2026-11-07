"""Explicit fixed initial dollar-weight constraints, not dynamic rebalancing."""
import numpy as np

def validate_fixed(fixed,n,minimum=None):
    out={}
    for key,value in (fixed or {}).items():
        try:i=int(key)
        except (ValueError,TypeError):raise ValueError('fixed holding index must be an integer')
        if str(i)!=str(key) or not 0<=i<n or not isinstance(value,(float,int)) or not np.isfinite(value) or not 0<=value<=1:raise ValueError('invalid fixed holding')
        out[i]=float(value)
    if sum(out.values())>1+1e-12:raise ValueError('fixed holdings exceed capital')
    if minimum is not None and any(v<minimum[i]-1e-12 for i,v in out.items()):raise ValueError('fixed holding below minimum')
    if minimum is not None and sum(out.values())+sum(v for i,v in enumerate(minimum) if i not in out)>1+1e-12:raise ValueError('fixed and minimum holdings exceed capital')
    return out
