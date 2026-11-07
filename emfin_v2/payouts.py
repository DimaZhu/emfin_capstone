"""Deterministic recurring modeled payments, not a calendar-date contract."""
import math


def expand_recurring(schedule,horizon,one_off=()):
    if type(horizon) is not int or horizon<1:raise ValueError('positive whole-week horizon required')
    rows=[dict(p) for p in one_off]
    if schedule is None:return rows
    if not isinstance(schedule,dict):raise ValueError('recurring payout must be a dictionary or null')
    amount=schedule.get('amount');months=schedule.get('months');first=schedule.get('first_week',4);spacing=schedule.get('spacing_weeks',52/12)
    if type(months) is not int or not 1<=months<=60 or type(first) is not int or first<1:raise ValueError('recurring months1-60 and positive first due week required')
    if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not math.isfinite(amount) or amount<0:raise ValueError('finite nonnegative monthly payment required')
    if isinstance(spacing,bool) or not isinstance(spacing,(int,float)) or not math.isfinite(spacing) or spacing<1:raise ValueError('payment spacing must be at least1 week')
    for i in range(months):
        week=round(first+i*spacing)
        if not 1<=week<=horizon:raise ValueError('Recurring payment '+str(i+1)+' falls outside the horizon; shorten the schedule or extend the horizon')
        rows.append(dict(name='Monthly payment '+str(i+1),week=week,amount=float(amount),schedule='recurring',month=i+1))
    # Preserve order within equal-week payouts; cumulative accounting handles it.
    return sorted(rows,key=lambda r:r['week'])
