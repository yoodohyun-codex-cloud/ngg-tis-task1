# Floating-pair matched comparison

New Task1 topology experiment, separate from existing common-ground runs. No main merge or hardware operation.

D50 mm; layers 0.1/5/5/15 mm; original 2000/2010 Hz material/contact inputs; same XY100 graph and 793860 evaluation cells; same fractional r<=5 mm, z15–20 mm ROI and 2074-direction sampled lower-bound metric. Existing field/contact convergence failures remain unresolved.

First finite cases: LOCAL14 geometry (14 mm square pads at +/-9 mm), signal positions preserved: pairs (0,2)/(1,3), then (0,3)/(1,2). Existing authenticated common-ground LOCAL14 results are the matched reference. LOCAL16 geometry is the next matched size comparison. Pair reassignment (0,1)/(2,3) changes signal roles and will be labeled separately.

Each pair is a galvanically isolated floating source: 1 Vpp means 0.5 V peak OPEN-CIRCUIT DIFFERENTIAL voltage, total series resistance 50 ohm per pair, not 50 ohm on each leg. Inactive-frequency source is 0 V differential behind 50 ohm, retaining passive induced pair currents. Unknown metal common modes are solved; mean metal voltage is only a gauge. Pair KCL must pass. Ideal current drive and real transformer equivalents are separate unexecuted factors.

Synthetic preflight: analytic complex two-pad series circuit, gauge translation, four-port reciprocity, inactive induced current and source/contact/resistor/tissue complex power. Numerical acceptance <=2e-7 relative residual/current/power and passive real powers >=-1e-14 W; original solver tolerance 1e-12, restart80, maximum40 cycles. No post-hoc tolerance relaxation.

Windows: eight distinct physical cores, one logical processor each; 4000000000-byte cap with page-aligned Job commit readback3999997952; whole-job plus controller RSS sampling; existing shared device lock; one research worker at a time. Each finite run watchdog3500 s, worker deadline3300 s; no cumulative runtime cap. Existing workers and leases untouched; each isolated run has a unique identity. Sources/cache are copied and SHA verified before use.

Raw potentials, fields, contact states, solver failures, fractional ROI arrays, checkpoints and resource receipts are retained locally and copied with readback hashes to the user-selected isolated-pair destination. No private paths or raw conversations are published.

Report target mean/P10, surface and off-target burden/selectivity, total currents/power/contact area, skin/contact burden separately at fixed voltage and equal-current/equal-power scales. No point maximum, amplitude gain, synthetic validation or provisional screen is a deep-focus success or physiological validation.
