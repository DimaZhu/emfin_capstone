"""One-page PDF for the MR scenario: VR curve, horizon effect, terminal tail."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emfin_v2.mean_reversion import variance_ratio  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RES = Path(__file__).resolve().parent / 'results'
GREEN = '#1a7a4a'
GREY = '#888888'
BLUE = '#2b6cb0'

mr_h = json.loads((RES / 'mr_horizon.json').read_text())
mr_p = json.loads((RES / 'mr_sens_policies.json').read_text())
base_h = json.loads((ROOT / 'studies/final5/results/final5_horizon.json').read_text())
band_h = json.loads((ROOT / 'studies/final5/results/final5_sens_seeds.json').read_text())
base_p = json.loads((ROOT / 'studies/final5/results/final5_sens_policies.json').read_text())

fig = plt.figure(figsize=(8.5, 11))
fig.suptitle('Mean-reversion scenario: what changes if "a down cycle never lasts 30 years" is true',
             fontsize=11.5, color=GREEN, fontweight='bold', y=0.98)

# Panel 1: variance ratio curves
ax1 = fig.add_subplot(3, 1, 1)
T = np.arange(1, 31)
for name, style in (('weak', '--'), ('central', '-'), ('strong', '-.')):
    p = dict(weak=dict(half_life_years=3.0, variance_share=0.20),
             central=dict(half_life_years=2.0, variance_share=0.40),
             strong=dict(half_life_years=1.5, variance_share=0.50))[name]
    ax1.plot(T, variance_ratio(p, 52 * T), style, color=GREEN, lw=2 if name == 'central' else 1.2,
             label=f'{name} (half-life {p["half_life_years"]}y, share {p["variance_share"]:.0%})')
ax1.plot([8], [0.58], 'o', color=GREY, ms=7)
ax1.annotate('Poterba-Summers 1988\nVR(8y) ~ 0.58 (US 1926-85)', (8, 0.58),
             xytext=(10.5, 0.5), fontsize=8, color=GREY,
             arrowprops=dict(arrowstyle='-', color=GREY, lw=0.8))
ax1.axhline(1.0, color=GREY, lw=0.8)
ax1.annotate('iid base = 1.0 (variance grows linearly)', (1, 1.01), fontsize=8, color=GREY)
ax1.set_xlabel('holding period (years)')
ax1.set_ylabel('equity variance ratio vs iid')
ax1.set_title('How much less risky equity becomes with horizon, under each declared calibration',
              fontsize=10)
ax1.legend(fontsize=8, loc='lower left')
ax1.set_ylim(0.35, 1.08)

# Panel 2: horizon safe share, iid vs MR, both seed families
ax2 = fig.add_subplot(3, 1, 2)
years = [5, 10, 15, 20, 30]
for view, col in (('fitted', GREEN), ('current_quotes', BLUE)):
    for seed, mk, lab in (('20261109', 'o', 'family 1'), ('20261111', 's', 'family 2')):
        iid, mrv = [], []
        for y in years:
            bc = base_h[view][f'{y}y']['search'] if seed == '20261109' else band_h[view][f'{y}y_t0.15']['search']
            mc = mr_h[f'{view}_s{seed}'][f'{y}y']['search']
            iid.append(bc.get('chosen_safe'))
            mrv.append(mc.get('chosen_safe'))
        ax2.plot(years, iid, mk + ':', color=GREY, ms=5, lw=1,
                 label=f'iid, {lab}' if view == 'fitted' else None)
        ax2.plot(years, mrv, mk + '-', color=col, ms=5, lw=1.5,
                 label=f'MR {view.replace("_", " ")}, {lab}')
ax2.set_xlabel('horizon (years)')
ax2.set_ylabel('validated safe (bills) share')
ax2.set_title('Horizon effect unchanged in shape: safe share still rises with horizon under MR',
              fontsize=10)
ax2.legend(fontsize=7, ncol=2)

# Panel 3: terminal loss upper bound for the frozen 10y mix, iid vs MR
ax3 = fig.add_subplot(3, 1, 3)
pols = [('buy_hold_mark', 'buy & hold'), ('cash_first', 'cash-first'), ('annual_rebal', 'annual rebal')]
x = np.arange(9)
w = 0.18
for j, (view, col) in enumerate((('fitted', GREEN), ('current_quotes', BLUE))):
    for k, law in enumerate(('iid', 'MR')):
        src = base_p if law == 'iid' else mr_p
        vals = [src[view][f'{y}y'][p]['terminal_ru'] for y in (10, 20, 30) for p, _ in pols]
        # grouped: 3 horizon clusters x 3 policies -> simplify to policy rows at 30y + 20y + 10y
        ax3.bar(x + (j * 2 + k - 1.5) * w, vals, w * 0.9,
                color=col if law == 'MR' else GREY,
                alpha=1.0 if law == 'MR' else 0.7,
                label=f'{law}, {view.replace("_", " ")}' if j + k == 0 or (law == 'iid' and j == 0) else None)
labels = [f'{pretty}\n{y}y' for y in (10, 20, 30) for _, pretty in pols]
ax3.set_xticks(x)
ax3.set_xticklabels(labels, fontsize=7)
ax3.axhline(0, color='black', lw=0.8)
ax3.set_ylabel('upper bound on terminal loss\n(lower = safer; >1 = can lose everything)')
ax3.set_title('Terminal left tail of the frozen 10y mix: much safer at 20-30y under MR', fontsize=10)
handles = [plt.Rectangle((0, 0), 1, 1, color=GREY, alpha=0.7), plt.Rectangle((0, 0), 1, 1, color=GREEN),
           plt.Rectangle((0, 0), 1, 1, color=BLUE)]
ax3.legend(handles, ['iid base (both views)', 'MR, fitted view', 'MR, current-quotes view'], fontsize=8)

fig.text(0.5, 0.012,
         'Research-only scenario: shared transitory AR(1) equity cycle (Poterba-Summers style), parameters treated as KNOWN -\n'
         'the best case for mean reversion. Weekly moments identical to the iid base by construction. Caveat: Pastor-Stambaugh (2012) -\n'
         'with estimation uncertainty, long-horizon predictive variance is HIGHER than iid. Japan 1989-2024 shows the claim can fail.',
         fontsize=7.5, color=GREY, ha='center')
fig.tight_layout(rect=(0, 0.03, 1, 0.96))
out = RES / 'ballast-mean-reversion-scenario-20261108.pdf'
fig.savefig(out)
print(out)
