# One same-material human SC2-to-SC4 check

SOURCE ONLY. The source author has not imported research modules, run tests,
compiled, decoded native arrays, solved a PDE, acquired execution locks, changed
a ledger or performed Git actions. Existing sources and results remain intact.

SOURCE `/dev/shm/task1-human-sc4-20261025/source`; exact disk-backed RUN
`/workspace/task1-human-sc4-20261025-run`; CASE
`baseline-square15-human-reference-sc4-xy80`; schema `task1-human-sc4-native-v1`.
Controller `human_sc4_run.py`, numerical wrapper `HumanTissueSC4Basis.java`,
input builder `human_sc4_inputs.py`, postprocessor `human_sc4_post.py`.

The actual human-reference SC2 calculation completed eight RHS and independent
SC/VS normal-current diagnostics near7.6percent. This one additional check
refines the SC thickness direction; it does not select or reevaluate materials.
The whole material receipt is byte-identical to actual SC2, SHA256
`d1cae451cfce3cbed3aa51d0a84621690af46aec29f0db08949fcca337e80ced`.
All four layers remain explicitly declared surrogates: Tsai2018 SC and viable
skin, Kangasmaa real conductivity with mathematical isotropic muscle trace proxy,
and Gabriel mixed-source permittivity. VS is LE+dermis excluding SC, assigned as
a dermis-slot proxy; it is not independent dermis measurement or duplicated
whole skin. No anatomic thoracoabdominal, activation or safety validation.

The builder derives from actual humanSC2 configuration SHA256
`8820712d379574c307328096a2b6817da8b59aca9d5be97aa5306668f48633a0`.
Only three assignments change: SC cells2to4, mask storage path, material-receipt
storage path. All32 per-frequency sigma/epsilon strings, receipt SHA, geometry,
contact, circuit, frequencies and waveform coefficients remain identical.
Primary evidence and material audit are copied JSON only; no article images/PDF
or material-evaluation worker is introduced. The original model code/source
receipt remain preserved and pinned through the already-published SC2 source.

Fixed model50mm diameter and0.1/5/5/15mm layers; XY0.625mm and bulk14/14/40.
SC4 gives72z and361728cells. Four canonical15mm square225mm2 top pads, two
independent outputs, pad0/1 outputs and pad2/3 common GND,50ohm, high-Z1Vpp
basis0.5Vpeak; inactive output0V through50ohm. Four frequencies
3000/3030/9000/9090 times two RHS =8 actual new solves. PBS interface data remains
an uncertain contact assumption. The three frozen numerical Java sources stay
unchanged; only the distinct wrapper sets the same per-frequency SIG/ER values
before each frequency and constructs the SC4 mesh.

Registration and execution occur only after actual humanSC2 native/postprocess
results are published with full SHA/bytes readback. The new source owner must
set the actual current topic parent before preparation. A placeholder blocks
admission. At most one humanSC4 condition; no automatic next condition.

Caps30prepare/60source/180native/90post/240publish total600seconds plus180seconds
reserved for the owner's final GUI =780seconds admission. Tail reservations are
750/690/510/420seconds. The same approved cumulative CPU/time ledger remains;
no budget expansion. Both global locks require flock plus full-file POSIX lockf.
CPU1, existing JDK21, Java heap2GiB, RSS plus ALL owned task1 tmpfs3GiB and
800kcells remain. Storage capacity guards are disabled by the user's explicit
later policy; no free-space reserve or per-run output capacity stop. Actual
cloud disk capacity must be reported without claiming access to Windows1TB.
Provider64MiB/blob and96MiB output limits are transport/format constraints.

The new wrapper explicitly permits only the canonical new /workspace RUN,
requires absent basis and canonical config/mask/material/classes paths, and
checks the exact parent PID/startticks/argv, source/classes/material hashes,
preregistration and live lock ownership before solving and at frequency
boundaries. Disk output avoids a second raw dataset in owned tmpfs while all old
RAM data remains intact. STOP/needs_attention/needs_physical_validation block
the run. No installation, deletion, security change or main merge.

```text
python -B SOURCE/human_sc4_run.py --prepare --output RUN
python -B SOURCE/human_sc4_run.py --publish-source --output RUN
python -B SOURCE/human_sc4_run.py --execute --output RUN
python -B SOURCE/human_sc4_run.py --postprocess --output RUN
python -B SOURCE/human_sc4_run.py --publish-results --output RUN
```

Source/config/material/classes are published and fully read back before native
arrays. Deterministic Gitblob GET/readback precedes creation; only confirmed404
permits POST. Unknown mutation failure is preserved, never blindly retried.
All stage receipts/partial outputs and previous originals are preserved.

Native ABI remains lossless LE complex128 peak+jomega*t: E/Jtotal/Jconduction
(2,N,3), phi(2,N), contact density(2,ncontacts), source(2,2), loss(6,2,2), grid,
contacts, actual per-frequency gamma, original five conservation gates and
BASIS_COMPLETE last. J exports are derived from stored E, not independent proof.

Postprocessing pins actual humanSC2 native/scalars/summary, verifies identical
material bytes and32keys, recomputes physical fractional ROI volume masks with
the same frozen algorithm, checks unchanged bulk coordinates, and compares SC
column volume averages. Both meshes get the same two-point linear SC interface
fit; the SC4 quadratic fit is additional and separately labelled. Independent
phi-only interface errors remain diagnostic-only and are not replaced by the
shared-face flux check or phi-to-stored-E identity.

Only this same-material humanSC2→SC4 pair uses the original adjacent-metric
limits1percent for named target/ROI TIS/RMS/ratio,5percent Jmax/J95/contactV,
2percent SC/contact/source power. The earlier SCepsilon1100 material's SC check
cannot be transferred. Even if this pair passes, fullSC/XY/bulk/edge/contact,
material/anatomic/experimental/activation/safety holds remain. Fixed voltage and
separate named burden/power normalizations stay distinct. Windows saving and
sync remain unverified without an actual connected destination.
