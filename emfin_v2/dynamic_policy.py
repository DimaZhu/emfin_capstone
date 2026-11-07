"""Causal long-only execution experiment. No universal or W1 optimality claim."""
import numpy as np
from scipy.special import softmax,logsumexp


def execute(c,draw,initial,theta=None,mode='feedback',fee=.0005,delay=1,record=True,rebalance_months=None):
    prices,amounts,steps,bases,growth=draw;n,h,d=prices.shape;a=np.asarray(initial,float);cash_ix=c['cash_index'];prop=c.get('asset_layout',{}).get('property_indices',[]);risky=[i for i in range(d) if i!=cash_ix and i not in prop];liquid=[cash_ix,*risky]
    if prices.ndim!=3 or amounts.shape!=(n,len(steps)) or growth.shape!=(n,h) or len(bases)!=len(steps) or h<1:raise ValueError('consistent nonempty path dimensions required')
    if not np.isfinite(prices).all() or (prices<=0).any() or not np.isfinite(growth).all() or (growth<=0).any():raise ValueError('positive finite prices and cash growth required')
    if not np.isfinite(amounts).all() or (amounts<0).any() or not np.allclose(amounts,bases[None,:],rtol=0,atol=1e-8):raise ValueError('fixed known nonnegative liabilities only; future scenario amounts cannot be observed')
    if (np.asarray(steps)!=np.asarray(steps,dtype=int)).any() or (np.asarray(steps)<1).any() or (np.asarray(steps)>h).any():raise ValueError('integer payment weeks within horizon required')
    if len(risky)!=4 or a.shape!=(d,) or (a<-1e-6).any() or not np.isfinite(a).all():raise ValueError('four liquid risky sleeves and finite long-only initial holdings required')
    if type(delay) is not int or delay<0 or not 0<=fee<1 or mode not in ('feedback','cash_first','pro_rata','static_target','feedback_initial_only','feedback_static_target','static_frequency'):raise ValueError('valid fee/delay/policy required')
    if mode=='static_frequency' and rebalance_months not in (1,3,6,12):raise ValueError('frequency must be 1,3,6 or12months')
    if c['real_estate'].get('sale_week',0) or c['real_estate'].get('annual_rent_yield',0) or c['real_estate'].get('net_rental_yield',0):raise ValueError('dynamic study requires unsold property and zero rent')
    if mode in ('feedback','feedback_initial_only','feedback_static_target') and theta is None:raise ValueError('feedback parameters required')
    if theta is not None and (np.asarray(theta).shape!=(8,) or not np.isfinite(theta).all()):raise ValueError('eight finite feedback parameters required')
    units=np.broadcast_to(np.maximum(a,0),(n,d)).copy();units[:,cash_ix]=0.;cash=np.full(n,max(a[cash_ix],0));pending=np.zeros((n,h+delay+2));arrears=np.zeros(n);paid_carry=np.zeros(n);short=np.zeros_like(amounts);cost=np.zeros(n);turnover=np.zeros(n);netpath=np.zeros((n,h));shadow=np.zeros((n,h));cashpath=np.zeros((n,h)) if record else None;decisions=sorted(set([0,*[max(0,int(t)-delay) for t in steps if int(t)-delay<h]]));base_liquid=float(a[liquid].sum());weights=a[liquid]/base_liquid;running=np.ones(n);numtrades=np.zeros(n,int);initial_prices=np.ones((n,d))
    rebalance_dates=set([0,*[max(0,int(steps[k-1])-delay) for k in range(1,len(steps)) if rebalance_months and k%rebalance_months==0]])
    for t in range(h+1):
        px=initial_prices if t==0 else prices[:,t-1,:]
        if t:
            ratio=growth[:,t-1]/(growth[:,t-2] if t>1 else 1.);cash*=ratio;arrears*=ratio;paid_carry*=ratio
        cash+=pending[:,t];pending[:,t]=0
        due_ix=np.flatnonzero(steps==t);due=amounts[:,due_ix].sum(1) if len(due_ix) else np.zeros(n)
        running=np.maximum(running,px[:,risky[0]])
        if t in decisions:
            active_mode=mode
            if mode=='static_frequency':active_mode='static_target' if t in rebalance_dates else 'cash_first'
            if mode=='feedback_initial_only':active_mode='feedback' if t==0 else 'cash_first'
            if mode=='feedback_static_target':active_mode='feedback' if t==0 else 'static_target'
            values=units[:,risky]*px[:,risky];spendable=cash+values.sum(1)
            if active_mode=='feedback':
                th=np.asarray(theta,float);remaining=amounts[:,steps>=max(1,t)].sum(1);past=initial_prices[:,risky] if t<=4 else prices[:,t-5,risky];momentum=np.log(np.maximum(px[:,risky],1e-300)/np.maximum(past,1e-300));feature=th[4]*(spendable/base_liquid-1)+th[5]*remaining/base_liquid+th[6]*(px[:,risky[0]]/running-1)
                target=softmax(np.c_[np.zeros(n),np.broadcast_to(th[:4],(n,4))+feature[:,None]+th[7]*momentum],axis=1)*spendable[:,None]
                if mode=='feedback_static_target' and t==0:weights=target[0]/spendable[0]
            elif active_mode=='static_target':target=spendable[:,None]*weights[None,:]
            else:
                # Only the known dated requirement, no future price, is used.
                next_decision=min([z for z in decisions if z>t]+[h+1]);need=amounts[:,(steps>=t+delay)&(steps<next_decision+delay)].sum(1)+arrears
                if active_mode=='cash_first':sale=np.minimum(np.maximum(need-cash,0)/(1-fee),values.sum(1))
                else:sale=np.minimum(need*np.divide(values.sum(1),spendable,out=np.zeros(n),where=spendable>0)/(1-fee),values.sum(1))
                fraction=np.divide(sale,values.sum(1),out=np.zeros(n),where=values.sum(1)>0);target=np.c_[cash+sale,values*(1-fraction[:,None])]
            sell=np.maximum(values-target[:,1:],0);sell=np.minimum(sell,values);units[:,risky]-=np.divide(sell,px[:,risky],out=np.zeros_like(sell),where=px[:,risky]>0);proceeds=sell.sum(1)*(1-fee);cost+=sell.sum(1)*fee;turnover+=sell.sum(1);numtrades+=(sell>1e-6).sum(1)
            if delay:pending[:,t+delay]+=proceeds
            else:cash+=proceeds
            if active_mode in ('feedback','static_target'):
                after=units[:,risky]*px[:,risky];buy=np.maximum(target[:,1:]-after,0);need=buy.sum(1)*(1+fee);fraction=np.minimum(1.,np.divide(cash,need,out=np.zeros(n),where=need>0));buy*=fraction[:,None];spent=buy.sum(1)*(1+fee);cash-=spent;units[:,risky]+=np.divide(buy,px[:,risky],out=np.zeros_like(buy),where=px[:,risky]>0);cost+=buy.sum(1)*fee;turnover+=buy.sum(1);numtrades+=(buy>1e-6).sum(1)
        for k in due_ix:
            required=amounts[:,k]+arrears;paid=np.minimum(np.maximum(cash,0),required);cash-=paid;arrears=required-paid;paid_carry+=paid;short[:,k]=arrears
        if t:
            net=cash+(units*px).sum(1)+pending.sum(1)-arrears;netpath[:,t-1]=net;shadow[:,t-1]=net+paid_carry
            if record:cashpath[:,t-1]=cash
        if (cash < -1e-5).any() or (units < -1e-6).any():raise ValueError('self-financing/long-only violation')
    return dict(terminal_net=netpath[:,-1],net_wealth_paths=netpath,shadow_wealth_paths=shadow,shortfalls=short,funded=np.all(short<=1e-6,axis=1),cost=cost,turnover=turnover,trades=numtrades,cash_paths=cashpath,pending_terminal=pending.sum(1),units_terminal=units,scope='Executed policy; shadow wealth adds actually-paid withdrawals accrued at cash. Pending fixed receivables count in marked wealth but cannot pay before settlement. Weekly timing assumptions, not broker evidence.')


def logits(allocation,c):
    a=np.asarray(allocation,float);cash=c['cash_index'];prop=c.get('asset_layout',{}).get('property_indices',[]);risky=[i for i in range(len(a)) if i!=cash and i not in prop]
    return np.r_[np.clip(np.log(np.maximum(a[risky],1)/max(a[cash],1)),-8,8),np.zeros(4)]


def ce(outcome,tolerance):return float(-tolerance*(logsumexp(-np.asarray(outcome)/tolerance)-np.log(len(outcome))))


def perfect_foresight_relaxation(c,draw,initial):
    """Pathwise upper wealth bound, NOT implementable or a fitted-model CI.

    Drop nonanticipativity, costs, delays, risky limits and the monthly action
    restriction. Frictionless weekly liquid investment selects the next week's
    best realized gross factor, including free unit cash. Property stays fixed.
    Induction dominates every admissible real policy in the experiment pathwise.
    """
    prices,amounts,steps,bases,growth=draw;a=np.asarray(initial,float);cash=c['cash_index'];prop=c.get('asset_layout',{}).get('property_indices',[]);liquid=[i for i in range(len(a)) if i not in prop];n,h,d=prices.shape
    if not np.allclose(growth,1.) or not np.allclose(prices[:,:,cash],1.) or (amounts<0).any() or np.max(amounts.sum(1))>a[liquid].sum():raise ValueError('bound requires unit cash and liabilities covered by initial liquid wealth')
    if not np.isfinite(prices).all() or (prices[:,:,liquid]<=0).any():raise ValueError('positive finite liquid price primitives required')
    value=np.full(n,a[liquid].sum());previous=np.ones((n,len(liquid)))
    for t in range(h):
        current=prices[:,t,liquid];best=np.maximum(1.,(current/previous).max(1));value=value*best-amounts[:,steps==t+1].sum(1);previous=current
    return value+prices[:,-1,prop]@a[prop]
