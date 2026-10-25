# One2000Hz XY0.625-to0.5mm numerical diagnostic

SOURCE ONLY. No research import, cell-count evaluation, tests, compile, native
array decode, PDE, locks, ledger or Git action by the source author. Root is the
sole actual calculator. Existing source, originals and failures remain intact.

SOURCE `/dev/shm/task1-xy100-2000-20261025/source`; exact disk-backed RUN
`/workspace/task1-xy100-2000-20261025-run-r2`; CASE
`baseline-square15-human-sine2000-xy100`; class `XY100SingleCarrierBasis`;
controller `xy_run.py`, builder `xy_inputs.py`, post `xy_post.py`. Parent topic
commit03009dbd82bd4f54ef451ca5aea9dc802ee0b8a3 includes the explicit cumulative
time-limit override. It must match live expected-parent checks before publication.

The user removed cumulative research time and storage capacity limits. Policy
APIs represent the approved cumulative cap and remaining time as null/None,
never infinity or a fabricated huge finite budget. require_time_budget validates
approval pins; receipts use cumulative_time_unlimited=true and remaining=null.
All previous spent time/run history stays preserved, new actual elapsed time is
still recorded. Each batch remains finite:30prepare/60source/120native/90post/
180publish/20persist seconds, one case only. After results and feedback root
chooses the next finite step. No perpetual background-worker promise.

CPU1, Java heap2GiB, RSS plus ALL owned task1 tmpfs3GiB, single owner, dual
flock+lockf,800kcells, native5gates and provider/file validation remain unchanged.
No ROOT free-space reserve or per-run byte capacity guard; actual ENOSPC/write
failure preserves partial evidence. Actual cloud disk is used; unmounted Windows
capacity is not claimed. Source and result publication require full immutable
readback proof. Already identical blobs may reuse earlier fullreadback receipts
with explicit provenance; new blobs require fresh fullreadback. Only confirmed
404 permits blob creation and unknown mutation failures are never blindly retried.

The physical phantom stays50mm diameter and0.1/5/5/15mm thick. SC2 and bulk
14/14/40 stay fixed. Four15mm square225mm2 top pads keep their physical positions,
rotation and shape. Two outputs with shared pad2/3 GND,50ohm each; inactive
output0V through50ohm. This is a single-carrier basis diagnostic, c=[1,0] at
2000Hz with two independent RHS exported. No TIS modulation is inferred from
one carrier and no isolated bipolar-pair topology is assumed. Actual equipment
waveform/wiring remains unverified.

The builder computes the XY100 cylinder count ONLY during ownerprepare, pins
validation.expected_cells, and creates3600 full-face contact patches with the
same225mm2 perpad physical area. No count is guessed by the source author.
Native Java constructs XY0.5mm and checks actual cells against that pinned count
and800k limit. The old coarse2000 configuration SHA61830d8... and mask SHA7cfc...
are validated first. Only XY lattice, represented mask, frequency-list reduction
and declared storage mappings change. Unused2010 config keys are removed;
receipts retain their exact two-frequency historical content.

Material receipt SHA
cccca81905a4db874184d35b1343ece700e45091693a34ab811cf363c0f9c469 and contact receipt
SHA cdf186c9d00876474b6fb0c10ae33e6a69d75e8fb41031b9ec0145a3e40dc40b are copied
byte-identically from the actual published2000/2010 experiment. No material model,
contact interpolation or fit is reevaluated. All actual2000 sigma/epsilon/z strings
match coarse. The same uncertain human-reference substitutes and PBS contact
assumptions remain; no tissue/anatomic/contact/activation/safety validation.

Native export keeps one frequency times two RHS: complex peak+jomega*t E(2,N,3),
phi(2,N), density(2,ncontacts), source(2,2), loss(6,2,2), grid/contactareas and
gamma metadata. No duplicate rawJ arrays; gammaE andsigmaE are post-derived.
Config, mask, material/contact receipts, source/classes and preparation selftests
are published and read back before native execution. Java checks parent argv,
PID/startticks, both locks, path/class/input hashes and stop markers. The exact
new /workspace RUN is allowed; no prior controller/path guard is edited.

Postprocessing recomputes physical ROI masks for BOTH meshes with the frozen
128x128 fractional method, compares per-region carrier RMS/current/power, and
separates fixed voltage from same-current, same-power and joint burden caps.
No stale coarse spatial mask is reindexed onto the fine grid. Independent
potential diagnostics use common2point SC fits and separate up3point fits,
native interior masks and fixed23.75mm matched masks. The predeclared5percent
normalized-L2 screening flags are non-aborting numerical QA only. Named RMS1%,
J/contactV5%, power2% adjacent checks apply to this singlecarrier XY pair;
TIS metrics remain unavailable. Any failure stays visible and fullSC/XY/bulk/
edge/contact/material/experimental accuracy is not inferred from one pair.

```text
python -B SOURCE/xy_run.py --prepare --output RUN
python -B SOURCE/xy_run.py --publish-source --output RUN
python -B SOURCE/xy_run.py --execute --output RUN
python -B SOURCE/xy_run.py --postprocess --output RUN
python -B SOURCE/xy_run.py --publish-results --output RUN
python -B SOURCE/xy_run.py --persist --output RUN
```

Persist verifies existing disk-backed hashes/publication without duplicating the
PDE or claiming Windows synchronization. No install, delete, security change or
main merge.
