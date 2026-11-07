import numpy as np
import pytest
from emfin_v2.default_run import load_config,setup,draw_paths,probabilities
from emfin_v2.explorer import Controls
from emfin_v2.market_views import validate_views,evidence


def test_absolute_horizon_views_hold_in_nominal_and_stressed_posteriors():
    c=load_config();c.update(market_return_views={'0':.01,'1':.015,'2':.012,'3':.005,'4':.008},stress_mean_path_loss_increment=.002)
    draw=draw_paths(c,setup(c),600,54);q,qs=probabilities(c,draw[0],draw.re_price_logs)
    target=list(c['market_return_views'].values())
    assert np.allclose(q@(draw[0][:,-1,:5]-1),target,atol=1e-6)
    assert np.allclose(qs@(draw[0][:,-1,:5]-1),target,atol=1e-6)
    ev=evidence(c,draw,q,qs)
    assert ev['relative_equity_spread']['requested'] is None
    assert len(ev['rows'])==5 and 'not a realized historical' in ev['note']


def test_extreme_unsupported_view_fails_not_clipped():
    c=load_config();c['market_return_views']={'3':.5};draw=draw_paths(c,setup(c),100,3)
    with pytest.raises((ValueError,RuntimeError)):probabilities(c,draw[0],draw.re_price_logs)


@pytest.mark.parametrize('v',[{'5':.1},{'0':float('nan')},{'0':.6},[]])
def test_view_validation(v):
    with pytest.raises(ValueError):validate_views(v)


def test_controls_hashable_and_invalid_targets_rejected():
    assert hash(Controls(asset_views=(1.,2.,3.,4.,5.)))
    with pytest.raises(ValueError):Controls(asset_views=()).validate()
    with pytest.raises(ValueError):Controls(stress_increment=11).validate()
