"""Regenerate the golden fixtures for every dynamic_policy.execute mode.

Run intentionally: python tests/golden/generate_dynamic_modes.py
Fixtures were captured from _execute_legacy (the retired twin loop) at the
Phase 3 migration; the shared engine reproduces them bit-for-bit
(rtol 1e-9, atol 1e-12), so this records zero behavior deltas.
"""
import json
from pathlib import Path

import numpy as np

from emfin_v2.dynamic_policy import _execute_legacy
from tests.test_golden_ledgers import scenarios, CONFIG, ALLOC, _draw, _flat

FIX = Path(__file__).parent
THETA = [0.1, -0.2, 0.05, 0.3, 0.5, -0.1, 0.2, 0.1]
MODES = [('cash_first', {}), ('pro_rata', {}),
         ('feedback', dict(theta=THETA)), ('static_target', {}),
         ('feedback_initial_only', dict(theta=THETA)),
         ('feedback_static_target', dict(theta=THETA)),
         ('static_frequency', dict(rebalance_months=3))]

if __name__ == '__main__':
    for name, spec in (('calm', scenarios()[0]), ('stress', scenarios()[1])):
        draw = _draw(spec)
        for mode, kw in MODES:
            out = _execute_legacy(CONFIG, draw, ALLOC, mode=mode, **kw)
            flat = _flat(out)
            flat['_theta'] = THETA
            flat['_rebalance_months'] = kw.get('rebalance_months')
            (FIX / f'dynamic_{mode}_{name}.json').write_text(json.dumps(flat))
            print('wrote', f'dynamic_{mode}_{name}.json')
