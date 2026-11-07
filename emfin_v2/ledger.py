"""Cash-first executable fixed-policy ledger, separate from provisioning optimizer.

No borrowing, dynamic rebalancing, or forced sale of unscheduled property.
After cash is exhausted, sell every liquid noncash sleeve pro rata by its
current value. This is a declared trading rule, not an optimal trading policy.
Input unit values already include configured liquidation haircuts; do not
charge them a second time. Property spendable value is credited when received
and removed from the marked holding to prevent double counting.
"""
import numpy as np
from emfin_v2.real_estate import funding_paths


def cash_first(c,draw,allocation):
    paths,amounts,steps,bases,growth=draw;prices=np.asarray(paths,float);a=np.asarray(allocation,float);n,h,d=prices.shape;cash_index=c['cash_index']
    if a.shape!=(d,) or not np.isfinite(a).all() or (a<-1e-7).any() or not np.isfinite(prices).all() or (prices<0).any():raise ValueError('finite nonnegative aligned holdings and prices required')
    if not np.isfinite(amounts).all() or (amounts<0).any():raise ValueError('finite nonnegative liabilities required')
    properties=c.get('asset_layout',{}).get('property_indices',[6] if c['real_estate']['enabled'] and d==7 else [])
    liquid=[i for i in range(d) if i!=cash_index and i not in properties]
    units=np.broadcast_to(a,(n,d)).copy();units[:,cash_index]=0.;cash=np.full(n,a[cash_index]);arrears=np.zeros(n);values=np.zeros((n,h));cash_path=np.zeros((n,h));shortfalls=np.zeros_like(amounts);paid=np.zeros_like(amounts);units_path=np.zeros((n,h,d));sold=np.zeros((n,h,d));last_property_cash=np.zeros(n)
    funding=funding_paths(draw)
    for t in range(h):
        ratio=growth[:,t]/(growth[:,t-1] if t else 1.)
        cash*=ratio;arrears*=ratio
        property_cash=funding[:,t,properties]@a[properties] if properties else np.zeros(n)
        received=property_cash-last_property_cash*ratio
        if (received < -1e-5).any():raise ValueError('property funding path removes previously settled cash')
        cash+=np.maximum(received,0.);last_property_cash=property_cash
        for k in np.flatnonzero(steps==t+1):
            due=amounts[:,k]+arrears
            # cash first, then one common fraction of all liquid units.
            need=np.maximum(due-cash,0.)
            available=prices[:,t,liquid]*units[:,liquid]
            total=available.sum(1);fraction=np.minimum(1.,np.divide(need,total,out=np.zeros(n),where=total>0))
            liquidation=available*fraction[:,None]
            sold[:,t,liquid]+=liquidation
            units[:,liquid]*=1-fraction[:,None];cash+=liquidation.sum(1)
            payment=np.minimum(cash,due);cash-=payment;arrears=due-payment
            paid[:,k]=payment;shortfalls[:,k]=arrears
        # Property cash is now held in cash, not marked a second time.
        property_mark=prices[:,t,properties]@a[properties]-property_cash if properties else np.zeros(n)
        values[:,t]=cash+(prices[:,t,liquid]*units[:,liquid]).sum(1)+property_mark-arrears
        cash_path[:,t]=cash;units_path[:,t]=units
    return dict(net_wealth_paths=values,cash_paths=cash_path,units_paths=units_path,sold_value_paths=sold,payment_shortfalls=shortfalls,payments=paid,terminal_unpaid=arrears,terminal_net=values[:,-1],funded=np.all(shortfalls<=1e-6,axis=1),policy='Cash first, then proportional liquidation of liquid sleeves at configured net unit values, assumed immediately spendable within the modeled week; no rebalance/borrowing; property only scheduled rent/sale receipts.',scope='Independent executable policy audit. Optimizer still uses money-market provisioning, not this policy. Unit values already include configured liquidity haircuts.')
