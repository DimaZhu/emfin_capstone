# My market views

The first-class dashboard panel separates the sample-informed modeled horizon
prior, the requested view and achieved nominal/stressed posterior means.
Liquid-asset controls are simple horizon returns after configured haircuts, not
annual returns. RE uses an annual underlying price log-return view with rent
separate. The units appear beside the controls.

Optional explicit targets cover US/international/emerging equities, Treasury
bonds and investment-grade credit. Enabling them replaces the relative equity
ranking view. Cautious/central/optimistic presets shift modeled liquid-asset prior
means by -2/0/+2 percentage points over the horizon, and set the annual RE view
to 0/4/8%. These are illustrative input shortcuts, not recommended forecasts.
Reset restores no absolute liquid-asset targets, +0.5pp relative equity view,
+1pp expected equity path-loss stress and a 4% annual RE price log-return view.

The stress input is an increment in expected maximum equity-basket loss from
initial value. It is not a CML constraint, a crisis probability or a historical
replay. Explicit return means are preserved while the posterior stress tilt is
applied. Joint scenario support can make a combination impossible. Unsupported
views fail without clipping; previous results remain visible and marked stale.

Changing probabilities changes other moments and effective scenario count. The
panel reports achieved values and effective nominal scenarios; large inputs
raise a visible warning, but only the solve determines joint feasibility.
A supported target is not an economic validation or forecast guarantee.

Near floating-point precision, Newton's pure-equality KL dual can stall on
correlated multi-asset features. The same dual now has an L-BFGS-B fallback,
with unchanged independent view-residual validation. No targets are relaxed.

Default fresh held-out scenarios remain generated under the scenario-model prior.
Posterior-stressed checks are separate; do not label the nominal simulation as
a posterior forecasting guarantee.
