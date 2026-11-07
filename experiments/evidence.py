"""Independent small numerical checks and matched-scenario benchmark evidence."""
import time
import numpy as np
from emfin_v2.default_run import setup,draw_paths,metrics,interval,probabilities,dro_buffer
from emfin_v2.real_estate import funding_paths
from emfin_v2.toolbox import liabilities,mpep,entropy_pooling as ep


def benchmark_evidence(config,result):
    import cvxpy as cp
    c=config;fit=setup(c);train=draw_paths(c,fit,c['train_scenarios'],c['seed'])
    d=train[0].shape[2];wealth=c['wealth'];mins=np.r_[np.zeros(6),c['real_estate']['minimum_weight']]
    allocations={k:np.array(v)*wealth for k,v in result['weights'].items() if k!='without posterior stress'}
    cash=mins.copy();cash[c['cash_index']]+=1-cash.sum()
    allocations['cash + RE floor' if mins.sum() else 'cash']=cash*wealth
    cov=np.cov(train[0][:,-1].T);w=cp.Variable(d)
    problem=cp.Problem(cp.Minimize(cp.quad_form(w,cp.psd_wrap(cov))),[cp.sum(w)==1,w>=mins])
    started=time.perf_counter();problem.solve(solver='CLARABEL');minimum_variance_seconds=time.perf_counter()-started
    if w.value is not None:allocations['minimum variance']=w.value*wealth
    batches=[]
    for j in range(c['evaluation_seeds']):
        draw=draw_paths(c,fit,c['evaluation_scenarios'],c['seed']+10000+j)
        q,qs=probabilities(c,draw[0])
        for name,a in allocations.items():
            gap,ce=metrics(c,draw,a);stress_gap,_=metrics(c,draw,a,qs)
            returns=draw[0][:,-1]@a/wealth-1
            values=draw[0]@a/wealth
            losses=np.maximum(0,1-values).max(1)
            batches.append(dict(method=name,seed=c['seed']+10000+j,net_ce=ce,
                expected_return=float(returns.mean()),volatility=float(returns.std(ddof=1)),
                cml=mpep.cml_of_paths(losses,np.full(len(losses),1/len(losses)),c['confidence']),
                gap_cvar=gap.tolist(),stressed_gap_cvar=stress_gap.tolist(),
                allocation=(a/wealth).tolist(),cash_weight=float(a[c['cash_index']]/wealth),
                constraint_scope='Common minima and no leverage. Benchmarks do not enforce funding or loss budgets; all are evaluated against those budgets.'))
    names=list(allocations);summary=[]
    base=np.array([x['net_ce'] for x in batches if x['method']==names[0]])
    for name in names:
        b=[x for x in batches if x['method']==name];ce=np.array([x['net_ce'] for x in b]);gap=interval([x['gap_cvar'] for x in b]);stress=interval([x['stressed_gap_cvar'] for x in b])
        upper=np.maximum(gap['high'],stress['high'])+dro_buffer(c,allocations[name]);budgets=np.array([p['amount'] for p in c['liabilities']])*c['funding_budget_fraction']
        summary.append(dict(method=name,net_ce=interval(ce),paired_ce_difference=interval(ce-base),paired_reference=names[0],
            expected_return=float(np.mean([x['expected_return'] for x in b])),volatility=float(np.mean([x['volatility'] for x in b])),
            cml=float(np.mean([x['cml'] for x in b])),cash_weight=b[0]['cash_weight'],
            funding_upper=upper.tolist(),funding_budgets=budgets.tolist(),heldout_funding_pass=bool(np.all(upper<=budgets)),
            allocation=b[0]['allocation']))
    return dict(summary=summary,batches=batches,minimum_variance_seconds=minimum_variance_seconds,
        interval_note='95% Student-t intervals across batch estimates, conditional on fitted scenario model. Paired differences share scenario seeds. These do not measure parameter uncertainty or economic forecast coverage.')


def proof_points():
    from scipy.optimize import linprog
    from emfin_v2.real_estate import unsmooth,cash_and_mark
    rows=[]
    def add(name,expected,observed,tolerance,claim):
        error=float(abs(observed-expected));rows.append(dict(test=name,expected=float(expected),observed=float(observed),absolute_error=error,tolerance=tolerance,passed=error<=tolerance,claim=claim))
    # Deterministic cash-account conservation with two payouts.
    v=np.array([[100.,100.]])
    m=liabilities.multiperiod_gap_metrics(v,np.array([[30.,40.]]),np.array([1,2]),np.ones((1,2)),.95)
    add('Cumulative terminal payout accounting',30.,m.terminal_net[0],1e-10,'Identity for a deterministic unit cash account, not a funding guarantee')
    alpha=.4;x=np.array([.01,.03,-.02,.04]);reported=[.01]
    for y in x:reported.append(alpha*reported[-1]+(1-alpha)*y)
    add('Smoothing inversion',0.,np.max(np.abs(unsmooth(reported,alpha)-x)),1e-12,'Algebraic inverse under the assumed first-order log-return model')
    mark,cash=cash_and_mark(np.ones((1,4)),np.ones((1,4)),dict(sale_week=1,sale_delay_weeks=2,liquidation_haircut=.1))
    add('Unsettled proceeds are not cash',0.,cash[0,1],1e-12,'Contract settlement convention, not an actual transaction guarantee')
    add('Sale cost deducted once',.9,cash[0,3],1e-12,'One fixed sale with no rent or interest')
    z=np.array([-1.,0.,1.]);pooled=ep.joint_entropy_pooling(3,[ep.View(z,[.2])]).posterior_probs
    add('Entropy-pooling probability normalization',1.,pooled.sum(),1e-10,'Numerical feasibility on a tiny known feature set')
    add('Entropy-pooling mean view',.2,z@pooled,1e-8,'Numerical constraint residual, not a general proof of the solver')
    paths=np.tile(np.array([[[1.,1.2]]]),(4,1,1));spend=paths.copy();spend[:,:,1]=0
    a,_=liabilities.optimization_multiperiod(paths,np.ones(2),100.,np.full((4,1),75.),np.array([1]),np.array([75.]),np.ones((4,1)),100.,.5,1.,0.,funding_market_paths=spend)
    add('Known-solution portfolio risky weight',.25,a[1]/100.,1e-5,'Deterministic two-asset problem with binding cash funding; analytic optimum')
    weights=np.linspace(0,1,10001);feasible=weights[100*(1-weights)>=75]
    brute=feasible[np.argmax(100*(1+.2*feasible)-75)]
    add('Exhaustive simplex reference weight',brute,a[1]/100.,1e-5,'10,001-point two-asset grid under the same deterministic funding constraint')
    from emfin_v2.toolbox.wasserstein import penalty
    add('W1 zero-radius identity',0.,penalty([.75,.25],0.,.95,.01),1e-12,'Penalty identity only; optimization equivalence is also unit-tested')
    transport=[]
    for far in [10.,100.,1000.,10000.]:
        eps=.01;weight=.5;eta=.1;support=np.array([0.,-far]);loss=np.maximum(0,-weight*support-eta)
        p=linprog(-loss,A_ub=[np.abs(support)],b_ub=[eps],A_eq=[[1.,1.]],b_eq=[1.],bounds=(0,None),method='highs')
        transport.append(dict(distance=far,lp_hinge=-float(p.fun),dual_bound=eps*weight,gap=eps*weight+float(p.fun)))
    add('W1 transport bound at far support',.005,transport[-1]['lp_hinge'],1e-6,'Finite transport approaches fixed-threshold unrestricted-support dual bound; not a coverage claim')
    return rows,transport
