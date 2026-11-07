# Rebalancing and dynamic execution: what the model supports
7 November 2026, private capstone research. No default or financial trade changed.

## Answer
Annual/no within-year rebalancing is the highest-scoring of monthly, quarterly,
semiannual and annual schedules on the original cash-heavy target in validation
and all four fresh final model laws. This is a one-year experiment: annual means
hold through the year, not an established multi-year optimum. Learned repeated
feedback has not earned adoption: it loses to its same-first-trade-only comparator
in post-hoc attribution; the exploratory four-model robust search found no
validation-accepted candidate. Simple original-target baselines pass all four
fresh final models. This is mathematical modeling plus simulation, not a global
optimality proof or a historical investment backtest.

## Fixed inputs and criteria
Only the payment amount was user-confirmed: 250k/month, modeled as 12 payments
at weeks 4,8,13,17,21,26,30,34,39,43,47,52, totaling 3M. Dollar figures use the
existing USD research convention. Other inputs are research assumptions:
100M initial wealth, original target 4.5812% US equity, approximately zero EM
and gold, 9.0334% Treasuries, 76.3853% zero-rate cash and 10% unsold Singapore
property; zero rent, no property sale, no borrowing/shorting. Property prices
and SGD/USD factor remain modeled, not a saleable funding source.

The new ledger adds 5bps on each buy/sell and one-week sale settlement. Those
are explicit coarse assumptions, not checked broker policies. Existing
provisioning haircuts are not charged a second time. Buys use settled cash;
pending fixed sale receipts count in marked wealth but cannot pay an early bill.
Payments reduce cash once. Unpaid amounts remain arrears and lower terminal net
wealth. This is a separate executed-policy experiment, not a silent alteration
of the production static provisioning judge.

Rank policies by terminal net CARA certainty equivalent, tolerance 10M, only
after all-risk and joint-paid-all screens. CE is a utility-adjusted dollar
score, not expected return. All policies share exact paths within each law,
initial holdings, fees, settlement, probability measures and risk judge.
Risk paths add actually paid withdrawals accrued at cash to net wealth so a
scheduled withdrawal alone is not labeled an investment loss. Risk checks cover
actual dated arrears, shadow path/terminal losses and the joint paid-all event.
The old W1 additive buffer is retained only as a heuristic stress screen, NOT
a nonlinear dynamic DRO certificate. The selected radius remains uncalibrated.

## Mathematical problem, not a bucket rule
Let state s_t contain liquid units q_t, settled cash c_t, settlement queue p_t,
fixed property units r, arrears a_t, observed price history and the remaining
known payment schedule. Full risk-constrained dynamic programming would also
augment the state with the necessary running path-loss/payment event statistics.
An admissible action consists of nonnegative purchases b_t and sales v_t with
v_t <= q_t P_t. Holdings change by (b_t-v_t)/P_t. Cash pays purchases including
fees, receives only matured net sale proceeds, and pays due liabilities. No
future return or future random liability is observable. The experimental
implementation rejects scenario-varying future liability amounts rather than
feeding them into controls.

The objective is max_pi -T log E[exp(-X_H(pi)/T)], where
X_H = settled cash + marked remaining units/property + pending receipts - arrears.
Already paid withdrawals are not subtracted again. Constraints include long-only,
self-financing/settlement and P(all dated calls fully paid) >= .99, plus declared
CVaR-type path/terminal/arrears budgets under the specified measures. Under a
finite known law, exact augmented-state Bellman recursion or a complete
nonanticipative scenario-tree solve can establish conditional optimality, subject
to solving that exact model. A clairvoyant optimization is not such a solution.

We did NOT globally solve that full problem. We searched a bounded eight-parameter
causal softmax policy: four relative risky intercepts, plus observed funding ratio,
remaining known liabilities, observed equity drawdown and trailing four-week
sleeve momentum. Differential evolution searched 360 candidate parameter vectors;
it is not a convex solver/global certificate. A tiny two-period two-asset test
matches Bellman recursion to exhaustive nonanticipative enumeration on a fixed
action grid; it validates that small oracle only, not the full learned policy.

## Primary dynamic search and attribution
100 training paths, validation 4x200 and final 4x400 per law. A training penalty
ranks candidates, then the top 12 training-feasible distinct candidates can be
validated. The first passing candidate was training rank 10. On primary IID
final paths, original cash-first CE=98.252660M and feedback CE=98.810853M;
on bounded-volatility paths, 98.240332M versus 98.832610M. All pass those
nominal final screens. This gain is not proof that later feedback helps.

Post-hoc same-first-trade-only CE=98.839217M IID and 98.852218M bounded:
repeated feedback is lower by roughly 28k and 20k. The initial target change
explains the apparent gain. Original feedback fails the prespecified -2pp
annual-drift sensitivity. It passes the fixed +/-fee/settlement, covariance
and tiny chosen price-downshift diagnostics, but one shock is not a W1 worst law.
The source-constructor technical retry is preserved; corrected rerun exactly
matches the original training/validation selections, no outcome-driven tuning.

## Exploratory robust redesign and fresh outcomes
After seeing that failure, freeze a new four-law objective: IID nominal, bounded
nominal, IID drift -2pp/year, and IID drift -2pp plus covariance x1.2. This is
an exploratory finite set, not an economic confidence region. New disjoint
training/validation/final seeds. Same 360 evaluations, worst-law CE and violation
penalty, same bounded class. Forty evaluated candidates pass training screens;
none of the top 12 passes all four validation screens. No robust policy is
selected, and there is no final-data repair or search expansion.

Fresh final rows preserve original policies: cash-first, pro-rata and monthly
static target pass all four laws. Original feedback and same-first-trade-only
pass both nominal laws but fail the shadow path-loss screen under both lower-
drift laws. This supersedes any impression from the older-path attribution
that the first-trade-only policy was robust to lower drift. All these final
policies still pay 1600/1600 calls jointly per law; funding alone is insufficient.
A failed bounded search does not establish that no robust dynamic policy exists.

## Frequency result on separate fresh paths
No new parameter fitting. Fixed original target, not the learned first-action
target. Rebalance at time zero and modeled months divisible by 1/3/6/12, before
settlement, excluding a useless terminal rebalance. Fund payments monthly at
all intermediate dates. Select using fresh 4x200 validation paths; freeze before
4x400 final paths per law. Annual ranks first in worst-model validation CE.

Final net CARA CE, USD millions:

| Law | Monthly | Quarterly | Semiannual | Annual/hold |
| --- | ---: | ---: | ---: | ---: |
| IID nominal | 98.217254 | 98.223660 | 98.230418 | 98.246273 |
| Bounded nominal | 98.209127 | 98.215720 | 98.223824 | 98.241122 |
| Drift -2pp | 97.945954 | 97.949964 | 97.953151 | 97.961745 |
| Drift -2pp, covariance x1.2 | 97.949082 | 97.953113 | 97.955864 | 97.964012 |

All 16 frequency/law rows pass the fixed all-risk and funding screens. Each has
1600/1600 fully paid reference paths, one-sided binomial lower95=99.8129%,
conditional on the frozen generated law, not economic truth. Nominal IID mean
fees: 1,674 / 864 / 444 / 0 dollars. The unusually large cash buffer covers the
entire annual payments without sales under hold; it is not evidence that all
portfolios should rebalance annually. Annual-minus-monthly pooled CE differences
are about 29k/32k/16k/15k across the four laws. Paired four-batch MC differences
use a simultaneous 12-comparison Bonferroni interval. Only the bounded-law
comparisons are clearly separated after that conservative adjustment; elsewhere
intervals can include zero. Pooled CE differences and mean batch CE differences
are distinct estimates and are preserved separately.

## Bound and remaining uncertainty
A frictionless, weekly, clairvoyant relaxation selects the next realized best
liquid gross factor including unit cash. With fixed property, zero-rate cash,
nonnegative liabilities covered by initial liquid wealth, dropping costs, delay,
nonanticipativity and loss limits gives a pathwise terminal-wealth upper bound.
Induction: if relaxed wealth dominates current implementable liquid marked wealth,
the best realized weekly factor dominates any long-only mix; nonnegative fees
only reduce the implementable value; the same payment is deducted. Pending
nominal receivables are covered by the free unit-cash option.

Sample upper CE is 241.071M IID and 196.752M bounded (237.421M/253.172M for the
two drift laws). These enormous, unattainable bounds are far above policy values:
there is NO near-optimality certificate. They are bounds on the shared sample
relaxation, not a confidence interval on the true-law optimum or achieved profit.

To establish an economically useful optimum would require a better calibrated
return/expense law, horizon appropriate to real holdings, real trading costs and
taxes, a tighter certified bound or exact solvable formulation, and chronological
out-of-sample validation. Mathematical policy search is a way to test hypotheses,
not permission to label its best sampled candidate "how it should always be done."

## Reproduction and sources
Run `python -m experiments.dynamic_execution`, `dynamic_attribution`,
`dynamic_robust`, `dynamic_bounds`, `dynamic_frequency`, then
`dynamic_science_bundle`. These use snapshots, no live trade execution. Preserve
selection locks and earlier results. Final packaging includes hashes and tests.
The dashboard research panel is a frozen snapshot, not a live dynamic optimizer.
Sources support modeling/methods only; their special-case optimality theorems do
not transfer to this CARA/settlement/chance-constrained model.

- Skaf/Boyd, Multi-Period Portfolio Optimization with Constraints and Transaction Costs (2009): https://stanford.edu/~boyd/papers/pdf/dyn_port_opt.pdf
- Lobo/Fazel/Boyd, Portfolio optimization with linear and fixed transaction costs (2007): https://stanford.edu/~boyd/papers/pdf/portfolio.pdf
- Boyd et al., Performance Bounds and Suboptimal Policies for Multi-Period Investment (2014): https://web.stanford.edu/~boyd/papers/port_opt_bound.html
- Dupacova, Portfolio optimization via stochastic programming: Methods of output analysis (1999): https://www.karlin.mff.cuni.cz/~kopa/papers/Portfolio.pdf
- Dupacova/Consigli/Wallace, Scenarios for multistage stochastic programs (2000): https://www.karlin.mff.cuni.cz/~kopa/papers/vanc-ed.pdf
- Kuchler/Vigerske, Numerical Evaluation of Approximation Methods in Stochastic Programming: https://www.gams.com/~svigerske/publications/outofsample.pdf

## Multi-year follow-up, fresh frozen comparisons
The user approved testing a multi-year horizon. Three and five years are chosen
duration sensitivities, not confirmed obligation durations. Monthly250k extends
to36/60calls (9M/15M). Same initial target, fees, settlement and four laws; annual
now really rebalances between years. No parameters or loss budgets are refit.
Long-run extrapolation from fixed one-week moments and the same EP horizon views
is a modeling assumption, not new long-run evidence.

Each horizon uses fresh4x200validation paths/law and4x400final/law, with disjoint
seed offsets. No frequency passes all four validation laws, so selection is NONE
at both horizons. On fresh3year finals all four frequencies fail the path-loss
screen under nominal IID and both lower-drift laws; all four pass bounded nominal.
On5year finals all16rows fail path-loss. All still fund every modeled payment.
The original path budget is left unchanged, not relaxed to create a winner.

Nominal IID terminal net CE, millions:

| Horizon | Monthly | Quarterly | Semiannual | Annual | All-four-law accepted? |
| --- | ---: | ---: | ---: | ---: | --- |
| 3years |94.457073|94.477522|94.500840|94.551980|No frequency |
| 5years |90.704862|90.734636|90.771331|90.865717|No frequency |

Annual ranks first by CE in all four final laws at both horizons; gain versus
monthly is about54k-102k over3years and89k-174k over5years across laws. That is a
score ranking of tested schedules, NOT a feasible optimum. Mean modeled IID
annual fees are1,486/2,948 dollars versus monthly5,301/8,745 for3/5years.
Paired4batch conditional intervals use simultaneous24comparison adjustment;
see full JSON for differences and wide intervals. Do not compare terminal CEs
across horizons as annualized return: withdrawals and time at risk differ.
The14.72s study does not justify changing the portfolio or relaxing constraints.

A fresh clone can run `python -m experiments.restore_dynamic_evidence` before
inspecting/rebuilding archived panels. It refuses to overwrite changed local
results. The original utility prerequisite is archived; `dynamic_execution`
falls back to it if the earlier ignored utility artifacts are absent. This
restoration is not a new experiment. The evidence ZIP contains both frozen
results and the scripts, tests, report and hashes.
