# One human-reference/surrogate material comparison

SOURCE ONLY. No research-module import, tests, compilation, field/array decode,
PDE, lock, budget ledger or Git operation has been performed by the source author.
Existing source, results and failure evidence remain unchanged.

SOURCE `/dev/shm/task1-human-tissue-20261025/source`; exact RUN
`/dev/shm/task1-human-tissue-20261025-run`; CASE
`baseline-square15-human-reference-xy80`; native schema
`task1-human-tissue-native-v1`. Controller `human_run.py`, numerical adapter
`HumanTissueBasis.java`, input builder `human_inputs.py`, postprocessor
`human_post.py` are isolated from all earlier source/class directories.

The sole owner must supply SOURCE/material-input.json from independently checked
primary/model sources before preparation. There are no human material defaults.
The mandatory receipt schema is task1-human-tissue-materials-v1, status
source_verified_for_declared_scope, exactly16 unique rows for
sc/dermis/fat/muscle at3000/3030/9000/9090Hz. Each row requires finite positive
sigma_S_m and epsilon_r, units S/m and dimensionless, source_verified=true,
traceable source_id and source_location, assignment_type primary_measurement,
published_model or declared_surrogate. A surrogate must state its limitation.
Whole-skin data assigned to an individual layer remains an explicit surrogate,
never an independently measured SC or dermis property. Source verification does
not validate this phantom, body region, activation, skin contact or safety.

The input builder verifies original canonical configuration and mask SHA256,
removes all8 unused constant material keys, adds32 explicit layer.sigma.f /
layer.epsilon_r.f keys and3 material-receipt lookup keys, and remaps only the
mask storage path. All geometry/circuit/contact assignments remain byte-derived
from the original canonical template. The native adapter updates inherited
SIG/ER before each frequency's ShapeNet construction. No frozen numerical Java
source changes. Exact material receipt bytes are copied to RUN/material-input.json
and pinned in configuration, registration, Java parent guard and postprocessing.

Fixed model:50mm diameter,0.1/5/5/15mm layers, XY0.625mm, SC2 and bulk14/14/40,
351680cells, four15mm square pads at the canonical positions, two independent
outputs, pad2/3 common GND,50ohm output impedance, high-Z1Vpp basis before50ohm,
inactive output0V through50ohm. Four frequencies times two RHS = eight new
actual solves. The existing square3h coefficients are unchanged. PBS-derived
contact impedance is retained as uncertain contact assumption, not validated
human skin contact. No anatomical thoracoabdominal specificity is inferred.

Only one explicit condition is registered. The five stage caps are
45prepare/90source/180native/120post/300publish seconds, plus90seconds reserved
for the owner's separate final reporting =825seconds initial admission. CPU1,
2GiB Java heap, RSS plus ALL owned task1 tmpfs at most3GiB,800kcells and single
owner dual flock+lockf remain. The approved cumulative CPU/wall-time ledger
limit is unchanged. Storage capacity guards are disabled by the user's later
explicit instruction: no ROOT free-space reserve, no per-run output byte cap,
no destination free-space minimum. Current sanitized runtime storage policy is
pinned and archived. Reported Windows1TB capacity and destination access remain
unverified from this cloud workspace. Format and provider transport limits
remain64MiB/blob and96MiB API output; these are not storage capacity checks.

The owner must set the current expected topic commit before preparation and
freeze the complete source/material receipt. Use exact absolute paths:

```text
python -B SOURCE/human_run.py --prepare --output RUN
python -B SOURCE/human_run.py --publish-source --output RUN
python -B SOURCE/human_run.py --execute --output RUN
python -B SOURCE/human_run.py --postprocess --output RUN
python -B SOURCE/human_run.py --publish-results --output RUN
```

Preparation source/input tests and inherited analytic operator selftests produce
no phantom basis. Published source/config/material/classes must pass immutable
Gitblob full SHA/bytes readback before native execution. The native adapter
checks parent PID/startticks/argv, both live POSIX locks, registration,
source/classes/config/mask/material pins and stop markers. Deterministic Gitblob
GET/readback precedes creation; only a confirmed404 permits POST. Unknown
mutation failures are preserved, not blindly retried. No main merge, installation,
deletions, CPU/time budget expansion or automatic next condition occurs.

Native ABI remains lossless LE complex128 peak+jomega*t: E/Jtotal/Jconduction
(2,N,3), phi(2,N), contact density(2,ncontacts), source(2,2), losses(6,2,2),
plus actual grid, contact areas, per-frequency gamma, metadata and original five
residual/power/KCL/area/shared-flux gates. J exports are derived from stored E;
shared flux and phi-to-stored-E identity are not independent accuracy proofs.
Independent potential-only interface diagnostics remain separate and ungated.

Postprocessing uses the same exact canonical grid/ROI volume weights, original
raw baseline and the SCepsilon1100 sensitivity summary, while retaining the
historical SC2-to-SC4 diagnostic as applying only to that earlier material.
Differences between material models are not numerical convergence failures or
proof of improvement. New material SC/XY/bulk/edge/contact convergence remains
unperformed. Report target absolute mean/P10, non-target distributions, E RMS,
TIS and current/power/contact metrics separately, with fixed-voltage and separate
single-quantity normalizations. No physiological activation/safety equivalence.
