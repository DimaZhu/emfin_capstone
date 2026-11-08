"""Causal long-only execution experiment. No universal or W1 optimality claim."""
import numpy as np
from scipy.special import logsumexp

from emfin_v2.event_ledger import LedgerSpec, run_event_ledger

_SCOPE = ('Executed policy; shadow wealth adds actually-paid withdrawals accrued at cash. '
          'Pending fixed receivables count in marked wealth but cannot pay before settlement. '
          'Weekly timing assumptions, not broker evidence.')


def _spec_for_mode(mode, theta, fee, delay, rebalance_months):
    fb = fee * 1e4
    if mode == 'cash_first':
        return LedgerSpec.dynamic_cash_first(fee_bps=fb, settlement_lag_weeks=delay)
    if mode == 'pro_rata':
        return LedgerSpec.dynamic_pro_rata(fee_bps=fb, settlement_lag_weeks=delay)
    if mode == 'feedback':
        return LedgerSpec.dynamic_feedback(theta, fee_bps=fb, settlement_lag_weeks=delay)
    if mode == 'static_target':
        return LedgerSpec.dynamic_static_target(fee_bps=fb, settlement_lag_weeks=delay)
    if mode == 'feedback_initial_only':
        return LedgerSpec.dynamic_feedback_initial_only(theta, fee_bps=fb, settlement_lag_weeks=delay)
    if mode == 'feedback_static_target':
        return LedgerSpec.dynamic_feedback_static_target(theta, fee_bps=fb, settlement_lag_weeks=delay)
    if mode == 'static_frequency':
        return LedgerSpec.dynamic_static_frequency(rebalance_months, fee_bps=fb,
                                                   settlement_lag_weeks=delay)
    raise ValueError('valid fee/delay/policy required')


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
    spec = _spec_for_mode(mode, theta, fee, delay, rebalance_months)
    r = run_event_ledger(c, draw, initial, spec)
    return dict(terminal_net=r['terminal_net'], net_wealth_paths=r['net_wealth_paths'],
                shadow_wealth_paths=r['shadow_wealth_paths'], shortfalls=r['payment_shortfalls'],
                funded=r['funded'], cost=r['cost'], turnover=r['turnover'], trades=r['trades'],
                cash_paths=r['cash_paths'] if record else None,
                pending_terminal=r['pending_terminal'], units_terminal=r['terminal_units'],
                scope=_SCOPE)


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
