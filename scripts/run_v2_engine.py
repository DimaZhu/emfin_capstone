"""End-to-end v2 engine run on the pinned snapshot: the benchmark Massa asked for.

Pipeline: pinned snapshot -> weekly invariants (equity log returns + 10Y
yield changes) -> joint moments -> horizon projection -> Gaussian invariant
scenarios -> market map (lognormal equities, exact bond repricing) ->
entropy-pooled views -> liquidity convolution -> allocations by four
methods -> paired-seed out-of-sample judging.

Illustrative views and the example liability schedule are PLACEHOLDERS to
exercise the machinery — the real views come from the team's investment
committee, the real schedule from the client case.

Run: python scripts/run_v2_engine.py
"""

from __future__ import annotations

import numpy as np

from emfin_capstone.toolbox import (
    benchmark,
    black_litterman,
    bonds,
    entropy_pooling as ep,
    liabilities as liab,
    liquidity as liq,
    snapshot,
)

# --------------------------------------------------------------------------
# Configuration (pinned: same numbers every run)
# --------------------------------------------------------------------------
HORIZON_WEEKS = 13  # one quarter
N_SCENARIOS = 100_000
SCENARIO_SEED = 42
COST_SEED = 43
N_JUDGE_SEEDS = 5
JUDGE_SEED_BASE = 1000

WEALTH = 100e6
RISK_TOLERANCE = 10e6
CONFIDENCE = 0.95
# The notebook's 4.1% CVaR budget is a *weekly* scale; at the quarterly
# horizon the same risk appetite is ~4.1% * sqrt(13) ~ 15%.  Exact budget
# calibration is a client conversation, not a code default - flagged as an
# open modelling decision.
GAMMA_LOSS = 0.15  # quarterly scale, placeholder calibration
GAMMA_SHORTFALL = 0.002  # funding-gap CVaR budget: 0.2% of the liability - tight enough to bind in-solver given SAA tail noise

EQUITY_TICKERS = snapshot.EQUITY_TICKERS
BOND = bonds.Bond("UST10", face_value=100.0, coupon_rate=0.04, years_to_maturity=10.0, ytm=0.0)
# ^ placeholder ytm replaced from the snapshot below

# Example client: a near-total funding event within the quarter (property
# purchase + PE capital call), sized so the funding-gap constraint visibly
# engages.  Note the theory: CARA CE and CVaR are translation-invariant, so
# a deterministic liability changes the optimal mix ONLY through the
# shortfall probability / gap-CVaR constraint - a finding for the paper.
# Real schedule: client case.
LIABILITIES = liab.LiabilitySchedule(items=(
    liab.Liability("PE capital call", 35_000_000, week=10),
    liab.Liability("property purchase", 60_000_000, week=13),
))

# Illustrative committee views (NOT research-backed):
VIEWS = [
    ("DFAI beats DFUS by 50bp over the quarter", "relative_mean", 0.005),
    ("DFAE quarterly vol rises to 6.5%", "vol", 0.065),
    ("DFUS quarterly skew stays above -0.5", "skew_floor", -0.5),
]


def main() -> None:
    snap = snapshot.load_snapshot()
    weekly_eq = snapshot.weekly_log_returns(snap)  # DFUS, DFAI, DFAE
    weekly_dy = snapshot.weekly_yield_changes(snap)

    # Align equity returns and yield changes on shared Wednesdays
    joint = weekly_eq.join(weekly_dy, how="inner")
    joint[snapshot.YIELD_TICKER] = joint[snapshot.YIELD_TICKER] / 100.0  # pp -> decimal
    # Cash (T-bill proxy): weekly accrual at the lagged 10Y yield.  Real
    # liability-aware allocation needs a riskless sleeve; without it a
    # near-total payout is simply infeasible (duration risk on the bond).
    joint["CASH"] = (joint[snapshot.YIELD_TICKER].shift(1).bfill()) / 52.0
    print(f"snapshot: {snap.manifest['rows']} daily rows through {snap.manifest['end']}; "
          f"{len(joint)} aligned weekly observations")

    invariants = joint.to_numpy()  # DFUS, DFAI, DFAE, dYield, cash log return
    inv_mean = invariants.mean(axis=0)
    inv_cov = np.cov(invariants, rowvar=False, ddof=1)

    # Projection: i.i.d. weekly invariants -> tau-week horizon (square-root rule)
    mu_tau = HORIZON_WEEKS * inv_mean
    cov_tau = HORIZON_WEEKS * inv_cov

    # Scenario invariants (Gaussian; the EP layer is distribution-agnostic,
    # Student-t or bootstrap slot in here unchanged)
    rng = np.random.default_rng(SCENARIO_SEED)
    chol = np.linalg.cholesky(cov_tau + 1e-12 * np.eye(len(mu_tau)))
    inv_scen = mu_tau + rng.standard_normal((N_SCENARIOS, len(mu_tau))) @ chol.T

    # Market map: equities lognormal, bond exact repricing with roll-down
    prices_eq = snap.closes[EQUITY_TICKERS].iloc[-1].to_numpy()
    current_ytm = snap.closes[snapshot.YIELD_TICKER].iloc[-1] / 100.0
    bond = bonds.Bond(BOND.name, BOND.face_value, BOND.coupon_rate, BOND.years_to_maturity, current_ytm)
    bond_p0 = bonds.price_from_ytm(current_ytm, bond.years_to_maturity, bond.coupon_rate, bond.face_value)[0]

    def market_from_invariants(inv: np.ndarray) -> np.ndarray:
        eq = prices_eq * np.exp(inv[:, :3])
        bond_prices = bonds.bond_price_scenarios(bond, current_ytm + inv[:, 3], HORIZON_WEEKS)
        cash = 1.0 * np.exp(inv[:, 4])  # T-bill: $1 accrues
        return np.column_stack([eq, bond_prices, cash])

    market = market_from_invariants(inv_scen)
    prices_vector = np.concatenate([prices_eq, [bond_p0, 1.0]])
    names = EQUITY_TICKERS + [bond.name, "CASH"]
    print(f"universe: {names}; current prices {np.round(prices_vector, 2)}")
    print(f"10Y yield: {current_ytm:.3%}; weekly dYield mean {joint[snapshot.YIELD_TICKER].mean()*1e4:.2f}bp, "
          f"std {joint[snapshot.YIELD_TICKER].std()*1e4:.1f}bp")

    # ---- Views via entropy pooling (on the invariant scenarios) ----------
    views = [
        ep.relative_mean_view(inv_scen, 1, 0, min_spread=VIEWS[0][2], name=VIEWS[0][0]),
        ep.volatility_view(inv_scen, 2, VIEWS[1][2], pin_mean=float(inv_scen[:, 2].mean()),
                           name=VIEWS[1][0]),
        # Inequality view (skewness floor): binds only if the view is violated
        # by the prior - the Gq <= h block of the classic EP formulation.
        ep.skewness_view(inv_scen, 0, VIEWS[2][2], sense="ge", name=VIEWS[2][0]),
    ]
    pooled = ep.joint_entropy_pooling(N_SCENARIOS, views)
    q = pooled.posterior_probs
    print(f"views pooled: KL {pooled.kl_divergence:.3f} nats, "
          f"effective scenarios {pooled.effective_n_scenarios:,.0f} / {N_SCENARIOS:,} "
          f"(ENS ratio {pooled.effective_n_scenarios_ratio:.1%})")
    for name, achieved, view in zip(pooled.view_names, pooled.per_view_achieved, views):
        print(f"  {name}: achieved {np.round(achieved, 5)} vs target {view.target}")

    # ---- Liquidity convolution (upstream of every optimizer) -------------
    cost_params = [liq.LiquidationCostParams(mean_cost=0.002, max_cost=0.02)] * 3 + \
                  [liq.LiquidationCostParams(mean_cost=0.0005, max_cost=0.005),
                   liq.LiquidationCostParams(mean_cost=0.0, max_cost=0.0)]  # cash settles at par
    market_net = liq.apply_liquidation_cost(market, cost_params, seed=COST_SEED)

    liability_due = LIABILITIES.amount_due_by(HORIZON_WEEKS)
    print(f"liabilities due within {HORIZON_WEEKS} weeks: ${liability_due:,.0f}")

    # ---- Four allocations -------------------------------------------------
    mu_market = market.mean(axis=0)  # moments of the mapped market for MV/BL
    cov_market = np.cov(market.T)

    # 1. vanilla mean-variance on sample moments
    alloc_mv = benchmark.mean_variance_allocation(mu_market, cov_market, prices_vector, WEALTH, RISK_TOLERANCE)

    # 2. Black-Litterman in gross-return space (the equilibrium prior is a
    #    return-space formula; running it on price moments mixes units).
    #    BL takes the mean view but not the vol view — one of the reasons
    #    the team chose EP.
    g_prior = mu_market / prices_vector  # expected gross returns
    cov_ret = cov_market / np.outer(prices_vector, prices_vector)
    w_mkt = np.array([0.40, 0.22, 0.09, 0.18, 0.11])  # documented assumption, not observable
    pi = black_litterman.equilibrium_prior(cov_ret, w_mkt, risk_aversion=2.5)
    P = np.array([[-1.0, 1.0, 0.0, 0.0, 0.0]])  # E[g_DFAI] - E[g_DFUS] = 50bp
    Q = np.array([0.005])
    mu_bl_ret, cov_bl_ret = black_litterman.posterior(cov_ret, pi, P, Q, tau=0.05)
    alloc_bl = benchmark.mean_variance_allocation(
        mu_bl_ret * prices_vector, cov_bl_ret * np.outer(prices_vector, prices_vector),
        prices_vector, WEALTH, RISK_TOLERANCE)

    # 3. entropy-pooled scenarios through the SAA optimizer (uniform-prob
    #    optimizer on resampled scenarios would add noise; we use the
    #    weighted form instead)
    alloc_ep, _ = liab.optimization_liability_aware(
        market_samples=market_net, prices_vector=prices_vector, wealth=WEALTH,
        liability_due=0.0, risk_tolerance=RISK_TOLERANCE, confidence_level=CONFIDENCE,
        gamma_loss=GAMMA_LOSS, gamma_shortfall=1.0, scenario_probs=q,
    )

    # 4. entropy-pooled + liability-aware
    alloc_lace, _ = liab.optimization_liability_aware(
        market_samples=market_net, prices_vector=prices_vector, wealth=WEALTH,
        liability_due=liability_due, risk_tolerance=RISK_TOLERANCE, confidence_level=CONFIDENCE,
        gamma_loss=GAMMA_LOSS, gamma_shortfall=GAMMA_SHORTFALL, scenario_probs=q,
    )

    allocations = {
        "vanilla MV": alloc_mv,
        "Black-Litterman": alloc_bl,
        "EP (views)": alloc_ep,
        "EP + liabilities": alloc_lace,
    }
    for name, a in allocations.items():
        print(f"{name:>18}: " + ", ".join(f"{n} {w:+.1%}" for n, w in zip(names, a * prices_vector / WEALTH)))

    # ---- Judging: paired fresh seeds under the prior (no views) ----------
    def judge_sample_fn(seed: int) -> np.ndarray:
        rng_j = np.random.default_rng(seed)
        inv_j = mu_tau + rng_j.standard_normal((N_SCENARIOS, len(mu_tau))) @ chol.T
        return liq.apply_liquidation_cost(market_from_invariants(inv_j), cost_params, seed=seed + 50_000)

    result = benchmark.judge_allocations(
        allocations, judge_sample_fn, N_JUDGE_SEEDS, JUDGE_SEED_BASE,
        WEALTH, RISK_TOLERANCE, liability_due=liability_due, confidence_level=CONFIDENCE,
    )
    print("\n=== Judge (out-of-sample, paired seeds, liability-adjusted CE in $) ===")
    summary = result.summary()
    for name in result.names:
        s = summary[name]
        print(f"{name:>18}: CE {s['ce_mean']:>14,.0f} +/- {s['ce_se']:,.0f}")
    print("\nPaired CE differences vs vanilla MV:")
    for name, d in summary["paired_diff_vs_vanilla MV"].items():
        print(f"{name:>18}: {d['mean']:>+12,.0f} +/- {d['se']:,.0f}")
    if result.shortfall_prob_by_seed is not None:
        print("\nShortfall probability vs ${:,.0f} due:".format(liability_due))
        for name, sf in zip(result.names, result.shortfall_prob_by_seed.mean(axis=0)):
            print(f"{name:>18}: {sf:.1%}")
        print("\nFunding-gap CVaR (95%) - budget was ${:,.0f}:".format(GAMMA_SHORTFALL * liability_due))
        for name, sc in zip(result.names, result.shortfall_cvar_by_seed.mean(axis=0)):
            print(f"{name:>18}: ${sc:,.0f}")


if __name__ == "__main__":
    main()
