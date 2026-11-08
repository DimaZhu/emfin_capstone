"""Current-market-quotes carry view: the second default view.

Owner plan (8 Nov 2026): the fitted estimation-window carry of the safe
listed assets gets a companion view at current market quotes, because the
fitted window quietly drives the answer (fitted bill carry 1.81%/yr vs the
live 4.17% quote).

Labeled simplifications, stated wherever the view is used:
  - IEF expected log return is set to the current 10y yield. IEF is a 7-10y
    rolling ETF, not a fixed-maturity bond: this assumes no average rate
    change and models no roll or term-premium adjustment.
  - TIP expected log return is set to the current 10y TIPS real yield plus
    the 10y breakeven (DGS10 - DFII10), i.e. the same nominal carry as IEF.
  - Volatilities, correlations and all risky-asset means stay as fitted on
    the full history. Quotes are a dated snapshot, not a maintained feed.
"""
import numpy as np

QUOTES_20261105 = dict(asof='2026-11-05', dgs3mo=0.0417, dgs10=0.0484, dfii10=0.0260,
                       source='FRED H.15 daily (DGS3MO/DGS10/DFII10), fetched 8 Nov 2026')

CARRY_VIEWS = ('fitted', 'current_quotes')

SIMPLIFICATION = ('current-quotes carry: IEF/TIP expected log return set to the current yield '
                  '(no roll/term-premium model); vols, correlations and risky means unchanged '
                  'from the full-history fit; quotes are a dated snapshot')


def validate_carry_view(c):
    view = c.get('carry_view', 'fitted')
    if view not in CARRY_VIEWS:
        raise ValueError('unknown carry_view: ' + str(view))
    quotes = c.get('carry_quotes')
    if quotes is not None:
        if not isinstance(quotes, dict):
            raise ValueError('carry_quotes must be an object with finite dgs3mo/dgs10/dfii10 rates')
        for key in ('dgs3mo', 'dgs10', 'dfii10'):
            if not isinstance(quotes.get(key), (int, float)) or not np.isfinite(quotes[key]) or not -.05 <= quotes[key] <= .5:
                raise ValueError('carry_quotes.' + key + ' must be a finite rate in [-5%, 50%]')
        if not isinstance(quotes.get('asof'), str) or not quotes['asof']:
            raise ValueError('carry_quotes.asof date string required')
    secondary = c.get('secondary_carry_view')
    if secondary is not None and secondary not in CARRY_VIEWS:
        raise ValueError('unknown secondary_carry_view: ' + str(secondary))
    if secondary is not None and secondary == view:
        raise ValueError('secondary_carry_view duplicates the primary carry_view')
    return view


def carry_quotes(c):
    return c.get('carry_quotes') or QUOTES_20261105


def apply_carry_view(c, fit):
    """Replace fitted weekly log means of the safe listed assets by current quotes."""
    if c.get('carry_view', 'fitted') != 'current_quotes':
        return fit
    quotes = carry_quotes(c)
    frame, mu, cov = fit
    ids = list(frame.columns)
    mu = np.array(mu, float, copy=True)
    breakeven = quotes['dgs10'] - quotes['dfii10']
    targets = dict(tbill=quotes['dgs3mo'], treasury=quotes['dgs10'],
                   tips=quotes['dfii10'] + breakeven)
    applied = {name: annual for name, annual in targets.items() if name in ids}
    if not applied:
        raise ValueError('current_quotes carry view needs at least one safe listed asset among: '
                         + ', '.join(targets))
    for name, annual in applied.items():
        mu[ids.index(name)] = np.log1p(annual) / 52
    c['_carry_applied'] = applied
    return frame, mu, cov
