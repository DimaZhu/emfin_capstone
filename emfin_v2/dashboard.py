"""Evidence-backed, plain-language dashboard data, never mockup numbers."""
import numpy as np
from emfin_v2.toolbox import mpep


def summarize(c,draw,q,qs,evaluation,allocations,rows,status,assets):
    selected='proposed' if 'proposed' in allocations else None
    h=c['horizon_weeks'];wealth=c['wealth']
    result=dict(wealth=wealth,horizon_weeks=h,payouts=c['liabilities'],selected=selected,satellite_indices=c.get('asset_layout',{}).get('property_indices',[6] if len(assets)==7 and c['real_estate']['enabled'] else []),
        status={k:status[k] for k in ('kind','risky_fraction','optimality_claim','reason') if k in status},confidence=c['confidence'],loss_budget=c['loss_budget'],cml_budget=c['cml_budget'],
        cash_index=c['cash_index'],wasserstein_radius=c.get('wasserstein_radius',0.),wasserstein_liability_scale=c.get('wasserstein_liability_scale',.01),risk_tolerance=c['risk_tolerance'],profile=c.get('risk_profile','Balanced'),
        liability_vol=c['liability_vol'],haircuts=c['liquidity_haircuts'],
        qualifications=['Illustrative, not client-calibrated. All dollar amounts are USD.',
        'Expected return and volatility are model estimates over this horizon, not annual forecasts. Certainty equivalent is risk-adjusted net wealth, not expected profit.',
        'CML is a tail average of loss from initial capital before payouts, not peak-to-trough maximum drawdown. Observed maximum loss is not a guaranteed limit.',
        'The fan is marked wealth, not available cash, after cumulative payouts and configured synthetic liquidity haircuts, with money-market opportunity costs. RE follows an explicit fixed sale/settlement plan, not a dynamic asset-sale policy.',
        'Stress cards are deterministic simplified shocks, not calibrated historical crisis replays or probability forecasts.',
        'Time-to-cash has not been calibrated. A liquid-market label does not guarantee same-day sale or settlement.',
        'Wasserstein risk bounds use a development radius and unrestricted-support L1 transport; utility is nominal. No probability coverage is guaranteed by the radius.',
        'Zero observed losses is not a bound on unseen tails.'])
    lower_buffer=wealth*c.get('wasserstein_radius',0.)/(1-c['confidence'])/len(assets)
    smallest=min(p['amount']*c['funding_budget_fraction'] for p in c['liabilities'])
    result['budget_warning']=f'Incompatible risk settings: W1 buffer is at least ${lower_buffer:,.0f}, above the smallest per-payment tail-gap budget ${smallest:,.0f}. No solver can fix this parameter conflict.' if lower_buffer>smallest+1e-8 else None
    result['history_evidence']=c.get('history_evidence')
    result['scenario_tier']=c.get('scenario_tier','full')
    result['scenario_counts']={k:c[k] for k in ('train_scenarios','validation_scenarios','evaluation_scenarios','validation_seeds','evaluation_seeds')}
    result['recurring_payout']=c.get('recurring_payout')
    result['one_off_payouts']=c.get('one_off_liabilities',[p for p in c['liabilities'] if p.get('schedule')!='recurring'])
    from emfin_v2.market_views import evidence
    result['market_views']=evidence(c,draw,q,qs)
    from emfin_v2.abu_dhabi import local_calibration
    observed=local_calibration() if c['real_estate'].get('source')=='abu_dhabi_private' else None
    if c['real_estate'].get('source')=='singapore_ura':
        from emfin_v2.singapore import history
        _,observed=history(c['real_estate'].get('sg_property_type','All Residential'))
    from emfin_v2.real_estate import calibration,assumptions
    result['re_data']=dict(available=observed is not None,source=c['real_estate'].get('source','synthetic'),enabled=c['real_estate']['enabled'],observed=observed,
        assumptions=assumptions(c['real_estate']),calibration=calibration(c['real_estate']) if c['real_estate']['enabled'] else None)

    if c['real_estate']['enabled'] and getattr(draw,'re_price_logs',None) is not None:
        result['re_data']['ep_achieved_annual_log_drift']={name:float(p@draw.re_price_logs[:,-1]*52/c['horizon_weeks']) for name,p in [('nominal',q),('stressed',qs)]}
    result['sfo_inputs']=dict(status='Default placeholder, not real SFO/client evidence',
        investable_wealth=c['wealth'],currency='USD',horizon_weeks=c['horizon_weeks'],payouts=c['liabilities'],
        wasserstein_radius=c.get('wasserstein_radius',0.),wasserstein_liability_scale=c.get('wasserstein_liability_scale',.01),risk_tolerance=c['risk_tolerance'],company_value=0.,company_note='Not provided; excluded, not measured as zero',
        evidence_status=c.get('client_evidence',{}).get('status','not provided'),missing=['verified holdings/units and prices','dated obligations and currency','company cash flows/valuation and sector exposure','property rent/cost/debt and sale-delay evidence','risk limits and approval owner','independent training/validation/evaluation scenarios'],
        private_import_format='scenario_archives: training NPZ, validation NPZ list, evaluation NPZ list. See docs/CLIENT_INPUTS.md. Never upload client data to GitHub.')
    if selected is None:return dict(result,unavailable='No proposed allocation passed calibration. Baselines are comparators, not approved alternatives.',guardrails=[],shocks=[])
    a=allocations[selected];w=a/wealth;v=evaluation[0]
    gross=v[0]@a/wealth;returns=np.concatenate([item[0][:,-1]@a/wealth-1 for item in evaluation])
    losses=np.maximum(0,1-gross).max(1)
    train_loss=np.maximum(0,1-draw[0]@a/wealth).max(1)
    cmls=[mpep.cml_of_paths(train_loss,p,c['confidence']) for p in (q,qs)]
    row=next(r for r in rows if r['method']==selected)
    def guard(name,current,limit,note,unit='fraction'):
        tolerance=max(1e-7,abs(limit)*.01)
        state='Breached' if current>limit+tolerance else 'Binding' if current>=limit-tolerance else 'Met'
        return dict(name=name,current=float(current),limit=float(limit),state=state,note=note,unit=unit)
    guards=[]
    from emfin_v2.default_run import metrics,dro_buffer
    training_gaps=np.maximum(metrics(c,draw,a,q)[0],metrics(c,draw,a,qs)[0])+dro_buffer(c,a)
    for i,payout in enumerate(c['liabilities']):
        current=training_gaps[i]
        guards.append(guard('Funding: '+payout['name'],current,row['budgets'][i],f"Training nominal/stressed tail gap plus W1 buffer at week {payout['week']}",'usd'))
    guards.append(guard('Path-loss tail',max(cmls)+dro_buffer(c,a,False)/wealth,c['cml_budget'],'Training nominal/stressed CML plus W1 buffer, before payouts'))
    guards.append(guard('Initial-loss tail',mpep.cml_of_paths(1-draw[0][:,-1]@a/wealth,q,c['confidence'])+dro_buffer(c,a,False)/wealth,c['loss_budget'],'Nominal terminal loss tail plus W1 buffer, before payouts'))
    guards.append(guard('No leverage',abs(w.sum()-1),0.,'Fully invested within numerical tolerance'))
    guards.append(guard('No shorting',max(0.,float(-w.min())),0.,'All holdings nonnegative'))
    # Equality constraints are met, not economically binding inequality budgets.
    for g in guards[-2:]:
        if g['state']!='Breached':g['state']='Met'
    property_indices=c.get('asset_layout',{}).get('property_indices',[6] if len(w)==7 else [])
    if property_indices:
        re_index=property_indices[0]
        if c['real_estate'].get('holding_mode')=='fixed':
            g=guard('Fixed RE holding',abs(c['real_estate']['fixed_weight']-w[re_index]),0.,'Fixed initial capital fraction, not an optimized RE weight or ongoing rebalancing')
            if g['state']!='Breached':g['state']='Met'
            guards.append(g)
        else:guards.append(guard('RE minimum',c['real_estate']['minimum_weight']-w[re_index],0.,'Minimum holding, NOT an illiquid-asset cap'))
    for i in range(len(c['liabilities'])):
        current=row['wasserstein_gap_upper'][i]
        g=guard('Held-out funding: week '+str(c['liabilities'][i]['week']),current,row['budgets'][i],'Conditional batch-mean upper interval plus W1 buffer; no distribution-coverage guarantee','usd')
        g['scope']='Evaluation';guards.append(g)
    # These are deliberately transparent deterministic shocks, not event returns.
    specs=[('2008-style equity shock',[-.40,-.45,-.50,-.03,-.15,0.,-.25],1.),
           ('2022-style rate shock',[-.20,-.20,-.25,-.15,-.18,0.,-.15],1.),
           ('Stagflation shock',[-.25,-.25,-.30,-.10,-.15,0.,-.20],1.),
           ('Business liquidity-call proxy',[-.15,-.15,-.20,-.05,-.08,0.,-.15],1.2)]
    shocks=[]
    if c.get('asset_registry') or len(w) not in (6,7) or c['cash_index']!=5:specs=[]
    for name,shock,last_call in specs:
        changes=np.asarray(shock[:len(w)])
        growth=np.mean(draw[4],axis=0)
        path=1+np.arange(1,h+1)[:,None]/h*changes
        path[:,c['cash_index']]=growth
        path[:,:6]*=1-np.asarray(c['liquidity_haircuts'])
        spendable=path.copy()
        if len(w)>6:
            from emfin_v2.real_estate import cash_and_mark
            mark,cash=cash_and_mark(path[:,6][None,:],growth[None,:],c['real_estate'])
            path[:,6]=mark[0];spendable[:,6]=cash[0]
        values=path@a;available=spendable@a;due=np.array([p['amount'] for p in c['liabilities']],float);due[-1]*=last_call
        payments=[]
        for i,pay in enumerate(c['liabilities']):
            step=pay['week'];need=due[i]
            for j,prior in enumerate(c['liabilities']):
                if prior['week']<step or (prior['week']==step and j<i):need+=due[j]*growth[step-1]/growth[prior['week']-1]
            gap=float(max(need-available[step-1],0))
            payments.append(dict(name=pay['name'],week=step,shortfall=gap,funded=gap<.01))
        net=float(values[-1]-sum(due[i]*growth[-1]/growth[p['week']-1] for i,p in enumerate(c['liabilities'])))
        shocks.append(dict(name=name,shocks=dict(zip(assets,changes.tolist())),final_call_multiplier=last_call,
            capital_change=float(values[-1]-wealth),terminal_net=net,payouts=payments,
            funded=all(p['funded'] for p in payments),kind='Simplified deterministic shock, not a historical replay'))
    return dict(result,expected_return=float(returns.mean()),volatility=float(returns.std(ddof=1)),
        cml=float(mpep.cml_of_paths(losses,np.full(len(losses),1/len(losses)),c['confidence'])),
        observed_max_loss=float(losses.max()),guardrails=guards,shocks=shocks,
        evaluation_pass=row['evaluation_pass'],liquidity_amount=float(a[c['cash_index']]),
        payout_coverage=float(a[c['cash_index']]/sum(p['amount'] for p in c['liabilities'])) if sum(p['amount'] for p in c['liabilities']) else None)
