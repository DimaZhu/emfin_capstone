import pytest
from emfin_v2.explorer import compute,Controls,template


def test_explorer_default_and_cached_result():
    a=compute();b=compute()
    assert a is b
    assert not a['errors']
    assert {'1/N','shrunk MV','proposed','without posterior stress'} <= set(a['weights'])
    for w in a['weights'].values():assert sum(w)==pytest.approx(1.,abs=1e-5)
    assert len(a['fan'])==5
    assert 'const STATIC=true' in template(a,True)


def test_bad_controls_rejected():
    with pytest.raises(ValueError):compute(Controls(liability=-1))


def test_optional_flags_have_actual_model_effect():
    a=compute(Controls(view=0,sequential=False,fat_tails=True,stress=True))
    assert a['controls']['fat_tails']
    assert a['controls']['stress']
    assert len(a['frontier'])>=10
