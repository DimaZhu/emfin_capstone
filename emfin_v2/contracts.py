"""Typed contracts at the accounting boundaries (Phase 2 of the
shared-accounting refactor).

Immutable dataclasses with construction-time validation, plus adapters so the
existing dict/tuple call sites keep working. ScenarioBatch carries the
provenance fields the run manifest hashes (seed, law, draw tag), so a batch
can no longer silently cross seed families or laws. No behavior change: the
Phase 0 golden fixtures and the full suite stay green.
"""
from dataclasses import dataclass, field

import numpy as np

from emfin_v2.real_estate import ScenarioDraw


def _arr(x, name):
    a = np.asarray(x, float)
    if not np.isfinite(a).all():
        raise ValueError(f'{name} must be finite')
    return a


def money_market_provision(amounts, steps, growth, week):
    """Declared money-market valuation of a fixed liability schedule at a
    week: each due amount moved to `week` by the money-market ratio,
    (amount * growth[week-1]) / growth[due-1], accumulated in schedule
    order. This is the one provisioning primitive (Phase 4): the
    optimizer's native utility values the schedule at the horizon; the
    judge's per-due-week requirements accumulate it payment by payment.
    The accumulation order is part of the contract (legacy float op
    order), so callers keep their exact legacy numbers."""
    amounts = np.asarray(amounts, float)
    steps = np.asarray(steps)
    growth = np.asarray(growth, float)
    out = 0.0
    gw = growth[:, week - 1]
    for i, due in enumerate(steps):
        out = out + amounts[:, i] * gw / growth[:, due - 1]
    return out


def accumulated_requirement(amounts, steps, growth, index):
    """The judge's per-due-week requirement: the payment at `index` plus
    every earlier-due payment (and same-week payments earlier in schedule
    order) escalated to that due week at the money-market ratio - the
    arrears convention of the provisioning judge. Legacy float op order
    preserved."""
    amounts = np.asarray(amounts, float)
    steps = np.asarray(steps)
    growth = np.asarray(growth, float)
    step = steps[index]
    required = amounts[:, index].copy()
    for j, prior in enumerate(steps):
        if prior < step or (prior == step and j < index):
            required += amounts[:, j] * growth[:, step - 1] / growth[:, prior - 1]
    return required


@dataclass(frozen=True)
class LiabilitySchedule:
    """The declared fixed liability calendar: payment weeks and base amounts."""
    steps: tuple
    bases: tuple

    def __post_init__(self):
        steps = np.asarray(self.steps)
        bases = _arr(self.bases, 'bases')
        if steps.ndim != 1 or bases.ndim != 1 or len(steps) != len(bases) or len(steps) < 1:
            raise ValueError('aligned nonempty steps and bases required')
        if (steps != steps.astype(int)).any():
            raise ValueError('payment weeks must be integers')
        if (np.diff(steps.astype(int)) < 0).any():
            raise ValueError('payment weeks must be monotone nondecreasing')
        if (bases < 0).any():
            raise ValueError('liability amounts must be nonnegative')
        object.__setattr__(self, 'steps', tuple(int(s) for s in steps))
        object.__setattr__(self, 'bases', tuple(float(b) for b in bases))


@dataclass(frozen=True)
class ScenarioBatch:
    """One batch of scenario paths with provenance.

    prices (n,h,d) unit values, growth (n,h) money-market cumulative factors,
    amounts (n,k) per-path payment amounts, plus the declared schedule
    (steps, bases). Provenance (seed, law, draw_tag) is what the run manifest
    hashes; a batch without provenance is explicitly unprovenanced, never
    silently attributed.
    """
    prices: object
    amounts: object
    steps: object
    bases: object
    growth: object
    funding: object = None
    seed: int = None
    law: str = None
    draw_tag: str = None

    def __post_init__(self):
        prices = _arr(self.prices, 'prices')
        amounts = _arr(self.amounts, 'amounts')
        growth = _arr(self.growth, 'growth')
        steps = np.asarray(self.steps)
        bases = _arr(self.bases, 'bases')
        if prices.ndim != 3:
            raise ValueError('prices must be (paths, weeks, assets)')
        n, h, d = prices.shape
        if h < 1 or (prices < 0).any():
            raise ValueError('nonempty nonnegative price paths required')
        if growth.shape != (n, h) or (growth <= 0).any():
            raise ValueError('positive growth paths aligned with prices required')
        if amounts.ndim != 2 or amounts.shape[0] != n or (amounts < 0).any():
            raise ValueError('nonnegative per-path amounts aligned with prices required')
        k = amounts.shape[1]
        if steps.shape != (k,) or bases.shape != (k,):
            raise ValueError('steps and bases must align with amounts')
        if (steps != steps.astype(int)).any() or (steps < 1).any() or (steps > h).any():
            raise ValueError('integer payment weeks within the horizon required')
        if (np.diff(steps.astype(int)) < 0).any():
            raise ValueError('payment weeks must be monotone nondecreasing')
        funding = prices if self.funding is None else _arr(self.funding, 'funding')
        if funding.shape != prices.shape:
            raise ValueError('funding paths must align with prices')
        object.__setattr__(self, 'prices', prices)
        object.__setattr__(self, 'amounts', amounts)
        object.__setattr__(self, 'growth', growth)
        object.__setattr__(self, 'steps', steps.astype(int))
        object.__setattr__(self, 'bases', bases)
        object.__setattr__(self, 'funding', funding)

    @staticmethod
    def from_draw(draw, seed=None, law=None, draw_tag=None):
        """Adapter from the legacy ScenarioDraw tuple."""
        prices, amounts, steps, bases, growth = draw
        funding = getattr(draw, 'funding_paths', None)
        return ScenarioBatch(prices, amounts, steps, bases, growth,
                             funding=np.asarray(funding) if funding is not None else None,
                             seed=seed, law=law, draw_tag=draw_tag)

    def to_draw(self):
        """Adapter to the legacy ScenarioDraw tuple (re_price_logs unset)."""
        return ScenarioDraw((self.prices, self.amounts, self.steps, self.bases, self.growth),
                            self.funding)

    @property
    def schedule(self):
        return LiabilitySchedule(tuple(int(s) for s in self.steps), tuple(float(b) for b in self.bases))

    @property
    def shape(self):
        return self.prices.shape


@dataclass(frozen=True)
class Allocation:
    """Per-asset holdings in dollars (or the run's wealth unit), with ids."""
    values: object
    asset_ids: tuple
    wealth: float = None

    def __post_init__(self):
        values = _arr(self.values, 'allocation')
        if values.ndim != 1 or len(values) != len(self.asset_ids) or len(values) < 1:
            raise ValueError('allocation must be a nonempty vector aligned with asset_ids')
        if len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError('asset ids must be unique')
        wealth = float(self.wealth) if self.wealth is not None else float(np.abs(values).sum())
        if not np.isfinite(wealth) or wealth <= 0:
            raise ValueError('positive finite wealth required')
        tolerance = 1e-7 * wealth
        if (values < -tolerance).any():
            raise ValueError('holdings must be nonnegative within judge tolerance')
        object.__setattr__(self, 'values', values)
        object.__setattr__(self, 'asset_ids', tuple(self.asset_ids))
        object.__setattr__(self, 'wealth', wealth)

    def as_vector(self):
        return self.values


@dataclass(frozen=True)
class ModelSpec:
    """The model choices behind a run: scenario law, carry view, budgets."""
    law: str
    view: str
    cml_budget: float
    loss_budget: float
    wasserstein_radius: float

    def __post_init__(self):
        for name in ('cml_budget', 'loss_budget', 'wasserstein_radius'):
            v = float(getattr(self, name))
            if not np.isfinite(v) or v < 0:
                raise ValueError(f'{name} must be nonnegative and finite')
            object.__setattr__(self, name, v)
        if not self.law or not self.view:
            raise ValueError('law and view must be named')


@dataclass(frozen=True)
class Verdict:
    """A judge outcome: pass flags and named breaches, never bare booleans."""
    overall_pass: bool
    funding_pass: bool
    breaches: tuple
    scope: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'overall_pass', bool(self.overall_pass))
        object.__setattr__(self, 'funding_pass', bool(self.funding_pass))
        object.__setattr__(self, 'breaches', tuple(self.breaches))
