# Hypothetical P23 floating-output comparison — SOURCE ONLY

These files are a proposal. They create no numerical admission, process, lease,
calculated result, hardware wiring change, candidate adoption, publication, or
activation/safety claim. Root must first review the synthetic MNA suites and
then explicitly decide whether to admit the finite physical comparison. No
scientific import, test, array decode, PDE/eigensolve, numerical worker, Git,
Windows assignment, installation, or publication occurred while preparing this
proposal. Existing source/data/result trees remain read only.

## Fixed scientific question

Compare the published P23 common-return result with a separately named
**hypothetical** two-isolated-output model, using the exact same original P23
physical mask, D50 phantom, 0.1/5/5/15 mm layers, HREF-MIX material/contact model,
2000/2010 Hz carriers, and 1 Vpp high-impedance source settings. Four physical
pads and two outputs remain. B0 common-return is a separately preserved control.

| Source output | Active carrier | Positive physical pad | Floating negative physical pad |
| --- | --- | --- | --- |
| 0 | 2000 Hz | 0 | 2 |
| 1 | 2010 Hz | 1 | 3 |

Positive source pads 0 and 1 therefore keep their original opposite-diagonal
positions and carrier/output assignments. Pads 2 and 3 become separate
negative terminals in this scenario. The actual hardware wiring is unconfirmed;
the result must never state that the instrument actually has isolated outputs.
The earlier hypothetical pairing (0,1)/(2,3) remains frozen separately and is
not substituted as the physical circuit for this comparison.

Each output has **50 ohm TOTAL differential series resistance**, rather than
50 ohm at each terminal. The active ideal source is 0.5 V peak before that one
50 ohm resistance. At the other carrier its ideal differential voltage is zero,
so its own 50 ohm resistance remains connected between its two floating
terminals. Its induced current and resistor loss are retained. There is no
earth, chassis, shared-ground or other parasitic branch in this hypothetical
model. No open-circuit substitution or independent grounding is allowed.

The original common-return control remains the original circuit: positive pads
0/1 driven by out0/out1, pads 2/3 hard at common 0 V, one 50 ohm resistance per
source, and the inactive ideal output at 0 V through its own resistance.
Control aliases cannot be reused as floating solutions.

## Exact original geometry and published identities

Use the original candidate `P23p5-peripheral-polyomino225` from:

`/dev/shm/task1-peripheral-fourpad-20261025-run/catalog-inputs.json`

This is four connected, hole-free pixelated polyomino pads. Each has 900 full
0.5 mm cells, area 225 mm², perimeter 88 mm, and centroids at signed
12.54888888888889 mm. The recipe's outer-radius parameter is 23.5 mm. It is
not a newly generated smooth sector or a donor-decorated later geometry receipt.

| Identity | SHA256 |
| --- | --- |
| Original catalog | `123c580b2c9ec1128174ddb9c5840fb6f27b6d4ba351cc0039fff77cc56bcdf0` |
| Original P23 mask | `09f29590ff68d7768550a20013ce3748e8ff5ea2df71af746eb42577b703540d` |
| Original P23 mask receipt | `03cdc589407f50753dbf1203723909bc1bf4f8581b915e77027da5658d26634e` |
| Common grid/ROI archive | `f88e921b2d2877482ff368f39e52fea2bd4217fb70037072cda96892b5891d6b` |

`failure2d` is the authentic preserved partial publication commit
`2d8ad63f714e549c60e1db4d78792a193ed83c2c`. Its receipt is:

`/dev/shm/task1-local-lease-and-cloud-failure-20261025-run/failure-publication/result-publication.json`

Receipt SHA256:
`2cae4bdbc3580ec14653eb5b23e1b48ca15c2851323bf89386e2e02e52040a07`.
It directly proves the original P23 mask, both passed common-return raw RHS and
their solve proofs, common grid/ROI, catalog/material/contact snapshots and B0
alias. The failed metrics-stage MemoryError and its source evidence stay held.

The completed common-P23 metrics/scalars come from recovery commit
`b30e7b7bd200170ff2b45f2a103c37ddff582a3f`, receipt:

`/dev/shm/task1-peripheral-recovery-20261025-run/result-publication/result-publication.json`

Receipt SHA256:
`5da8f476cacd4ee323d781f08f3a0a89e7e02d64c1b3a1674069d10ee1eb698d`.
That record explicitly reuses the two prior P23 RHS without recalculating them.
The B0 alias retains the original coarse raw/scalar descriptors and original
normalizations. Every selected file must have a unique direct full-readback
proof and unchanged local SHA/bytes before use. The proposal never invents a
descriptor from a filename or treats receipt presence alone as proof.

The common grid stays 7860 XY nodes × 101 depth planes = 793,860 physical
evaluation cells; XY spacing 0.5 mm; radius 25 mm; layer counts [8,19,18,56].
The original fractional m³ ROI weights are reused exactly, including target
r≤5 mm and 15≤z≤20 mm. There is no cell-count weighting or volume renormalization.

## Frozen CEM and physical pad adapter

The original `floating_cem.py`, its original tests and original contract in
`/dev/shm/task1-floating-bipolar-20261025/source` remain unchanged. This proposal
contains a byte-identical core as `frozen_floating_cem.py`, SHA256
`b3751e20fe97f6eac334c5af09c9954bfad2646748abe00128d9782524a6b17f`.

The core uses solver pairs (0+,1-)/(2+,3-). `p23_adapter.py` applies the
physical→solver permutation [0,2,1,3] without changing contact-patch order,
areas, impedances or source-output order. It returns metals and per-pad proof
currents in physical order 0/1/2/3; source currents remain out0/out1. Geometry
metadata names all four distinct metal nodes and records output index and
polarity separately. The original common-return node labels stay in a clearly
named historical metadata field only.

For q_p positive tissue→metal, physical pair equations are:

    I0 = -q0 = +q2; I1 = -q1 = +q3
    V0 - V2 + 50 I0 = Vs0
    V1 - V3 + 50 I1 = Vs1

V3=0 is purely a numerical gauge. The tissue DtN operator annihilates constants;
pair KCL and global KCL imply no spurious gauge/ground current. All four terminal
currents, both pair sums, global KCL, fresh unpreconditioned residuals against
source and loaded-current scales, analytic layer/tissue-boundary power agreement,
signed complex power balance and passivity retain the original strict gates.
Peak-phasor convention is exp(+jωt), S=VI*/2. Capacitive reactive power is
negative; no absolute-value replacement of signed source/layer/contact powers.

Synthetic source tests independently assemble full passive tissue/contact MNA
with four metal KCL rows, two branch currents and a gauge multiplier. The new
tests write physical pair incidence literally as (0,2)/(1,3), independently of
the adapter. They compare both carrier/output bases, inactive floating loading,
all physical pad signs, power balance, gauge shifts and same-frequency reciprocal
port response. A reciprocity check across 2000 and 2010 Hz would be invalid.
The tiny dense synthetic solver does not establish real-data GMRES convergence
or validate frozen physical layer/field reconstruction.

## Deferred pipeline and exact finite scope

The public APIs are `make_spec(admission)`, `required_inputs(admission)` and
`build(spec, guard, deadline_monotonic, output_dir, *, resource_probe)` in
`p23_comparison.py`. No source file performs scientific work at import.
Canonical source locations and frozen dependency hashes are literal, without
deriving identities from a module's runtime file location.

The only new physical solves are:

1. P23 hypothetical floating out0 active at 2000 Hz, out1 terminated at 0 V diff/50 ohm.
2. Same mask, out1 active at 2010 Hz, out0 terminated at 0 V diff/50 ohm.

There are zero new common-return/B0 RHS and zero eigensolves. Material, contact
and analytic profiles are evaluated at their own carrier frequency. The original
cached real-Q is authenticated before decode and its complete chunks checked
again after the two solves. `frozen_design_screen._fields` rebuilds actual fields
from the new floating solution coefficients, explicitly using the frozen
`provisional_field.lateral_field` and analytic normal-current reconstruction.
It preserves the original coarse provisional ABI and all accuracy holds.

Each carrier preserves full raw complex phi/E, interface J, modal and surface
states, four physical metal potentials, patch and per-pad signed q, both source
currents including the inactive branch, contact J/drop/physical indices/areas,
signed source/contact/tissue/layer power and R50 loss, plus the full passed solve
proof. The old two-metal archive ABI must not be silently reused.

The raw stage is a separate function frame and returns JSON identities/proofs
only. It writes each carrier independently and drops its full fields before the
next carrier. Its frame ends, numerical-object leakage is rejected, and GC runs
before the metric stage starts. No cached Q, profiles or numerical solver state
crosses that boundary. This boundary preserves the prior MemoryError lesson;
no address-space limit or aggregate cap is enlarged.

One full new metric evaluation uses both saved floating complex E vectors and
the exact six fractional ROI weights. It preserves volume-weighted AM/RMS
distributions, the completed sampled 2074-direction AM lower bound, all eight
skin/contact burdens and the four separate normalizations. Common P23 and B0
retain their completed fields/metrics/scalars as aliases, with no field rebuild
or angular recalculation. The frozen metric/electrical arithmetic contains old
hard-coded common-return descriptions; the adapter explicitly replaces those
descriptive labels for the new floating result without changing arithmetic.

The four normalizations remain separate: same voltage, same sum of individual
output RMS magnitudes (bookkeeping), same source real power, and joint eight
surface/contact burden caps. Nothing assumes all are equal simultaneously.
For every mode, report absolute values and min4 relative to common B0. Also
report the same four separate comparisons relative to same-mask common P23.
Min4 is the minimum of gains in target AM mean, target AM P10, target/surface
mean ratio and target/off-target mean ratio. Zero/missing references make the
ratio/score unavailable. Burden caps are numerical comparison values, not human
safety limits. No physiological high-modulation cutoff is introduced.

## Admission, resources, and blockers

No root-admission file is supplied. An eventual explicit new root admission must
select `selected_finite_hypothetical_P23_topology_comparison`, bind the complete
canonical source SHA inventory, record a decision basis, and bind a reviewed
synthetic-test receipt. The receipt must report 15 tests, zero failures/errors/
skips, and passed suites
`frozen_test_floating_cem` and `test_p23_comparison` for that exact source snapshot.
Both `root_selected` and `root_reviewed_synthetic_MNA` must be true. The admission
fixes two new floating RHS, one full new metric evaluation, two immutable common
aliases, physical pairs/frequency assignments, fixed amplitudes, unchanged
resource caps, no hardware claim, no adoption, and unchanged Windows assignments.
It explicitly names a new root-created output directory under `/dev/shm` with
prefix `task1-floating-P23-comparison-20261025-run`. A previous unrelated admission
or this source-only request cannot satisfy that contract.

Before any scientific import, `build` requires a live root-provided
`resource_probe()` snapshot whose scope is **ALL RSS plus ALL owned
`/dev/shm/task1-*` tmpfs**. It must be current and include existing artifacts.
The conservative forecast reserves 800 MB additional child RSS and 200 MB new
output (forecast output range 150–200 MB). Existing aggregate usage plus this
1 GB reserve must fit at most **8,000,000,000 bytes**; otherwise build blocks.
An absent, stale, partial or over-cap snapshot blocks. The continuous root guard
still enforces actual aggregate usage during and after each stage; the forecast
is not a grant to exceed the cap. CPU remains 4 and physical evaluation cells
remain 793,860, below the unchanged 800,000 maximum.

The owner must configure CPU/BLAS and its watchdog before deferred NumPy/SciPy
imports. Only root may decide on and own numerical execution. The proposal
creates no worker, process admission, lease or resource reservation. No numerical
results or test pass are claimed here. All original convergence, SC/XY/contact/
edge, material/contact/hardware and experimental uncertainty holds remain.
