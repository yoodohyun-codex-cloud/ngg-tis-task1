# Hypothetical floating bipolar comparison — source preparation only

This directory prepares a separate, explicitly hypothetical isolation scenario.
It does not establish the actual instrument wiring and does not authorize a
numerical run, experiment rewiring, candidate adoption, publication, activation,
or any new safety claim. The completed common-return baseline stays unchanged
and must be named and reported separately. Existing geometry, material,
contact, convergence, and hardware uncertainty holds remain in force.

## Geometry and comparison identity

Use the original B0 physical four-pad masks and coordinates, in millimetres:

| Physical pad | Centre (x, y) | Hypothetical connection |
| --- | --- | --- |
| 0 | (-10, -10) | output 0 positive |
| 1 | (+10, +10) | output 0 negative |
| 2 | (+10, -10) | output 1 positive |
| 3 | (-10, +10) | output 1 negative |

The cylinder diameter remains 50 mm; layers remain 0.1/5/5/15 mm. Carrier
frequencies remain fixed at 2000 and 2010 Hz. All material/contact/profile
values must come from their own actual carrier frequency; never copy 2000 Hz
material or contact impedance into the 2010 Hz solve.

For this scenario, 2000 Hz drives the differential pair (0+, 1-), and 2010 Hz
drives (2+, 3-). Each active ideal differential voltage is 0.5 V peak, using the
1 Vpp high-impedance convention before the source resistance.

The original common-return scenario drives physical pad 0 at 2000 Hz and
physical pad 1 at 2010 Hz through one 50 ohm resistance per output, with pads
2 and 3 at the common reference. Therefore the proposed floating comparison
changes both circuit topology and the physical pad/frequency assignment. It is
not a topology-only change with every pad's frequency unchanged. Any eventual
metric comparison must state both differences; it cannot infer which wiring
the unconfirmed hardware actually has.

## Circuit definition and inactive-output condition

There are two isolated differential source outputs and exactly four terminals.
Each output has **50 ohm TOTAL differential series resistance**, not 50 ohm
at each terminal. The circuit contains no earth, shared return, shield, chassis,
or parasitic branch. Those effects are outside this hypothetical model.

At a given carrier, the other ideal source is set to **zero differential
voltage**, leaving its own 50 ohm floating termination between its two terminals.
It is neither opened nor independently grounded. Its induced current and
resistor power must be retained. The active source setting is 0.5 V peak
open-circuit differential voltage; it is not a prescribed loaded pad voltage.

Let q_p be total contact current from tissue into metal pad p. Let I_k flow
from source output k's positive terminal into tissue. Then:

    I0 = -q0 = +q1;  I1 = -q2 = +q3
    V0 - V1 + 50 I0 = Vs0
    V2 - V3 + 50 I1 = Vs1

For the inactive output Vs=0, so its terminal voltage is -50 I. Both branch
currents are needed even though only one ideal source has nonzero voltage.

## Tissue and reduced equations

The original insulated cached-XY DtN tissue operator is:

    A phi = h^2 Q diag(Y) Q^T phi;  A 1 = 0
    g_c = area_c / zA
    q_c = g_c (phi_cell(c) - V_pad(c))
    A phi + sum_contacts_at_cell q_c = 0

Use unknowns [phi (n entries), V0, V1, V2] and set V3=0 solely to choose the
arbitrary potential reference. The three additional rows, all in amperes, are:

    q0 + q1 = 0
    (V0 - V1)/50 - q0 = Vs0/50
    (V2 - V3)/50 - q2 = Vs1/50

Summing all tissue rows gives sum_p q_p=0 because the tissue operator has both
constant left and right nullspaces. Pair-0 KCL therefore implies pair-1 KCL.
Nevertheless both pair residuals and all-pad KCL are checked independently.
V3=0 supplies no physical ground branch or shunt admittance. The source checks
the insulated constant modal state and its transformed nullspace before solve.

An all-node strictly positive definite tissue matrix would violate the constant
nullspace assumption. Synthetic tests use a connected reciprocal graph
Laplacian with positive real edge admittances, which is positive definite on
the mean-zero subspace. No synthetic eigensolver is needed: the test graph's
Walsh eigenbasis and eigenvalues are analytic.

The 3x3 metal block preconditioner is the exact reduced metal block, with the
tissue diagonal plus contact conductance as the other block. It does not add
an artificial ground or alter any physical equation. Convergence of the full
7860-node problem has not been tested or promised by this preparation.

## Signed complex powers and independent verification

Use peak complex phasors with exp(+j omega t):

    Ssource = 0.5 sum_k Vs_k conj(I_k)
    PR50 = 0.5 * 50 * sum_k |I_k|^2
    Scontact = 0.5 sum_c (phi_c - Vp) conj(g_c (phi_c - Vp))
    Stissue = 0.5 sum_i phi_i conj((A phi)_i)
    Ssource = sum_layer Slayer + Scontact + PR50

The layer powers use the unchanged analytic modal boundary-flux profiles, with
an additional check that their sum matches Stissue. Cell-centred reconstructed
field sums must not replace this power calculation. Capacitive reactive power
is negative with this convention. Direct `vdot(phi, A @ phi)` has the opposite
reactive sign; it needs conjugation to represent the stated Stissue convention.

Each layer's real power, contact real power, and both outputs' combined resistor
power must pass passivity checks. The source branch currents inferred from
(Vs - differential voltage)/50 must independently agree with contact currents
at **all four** terminals. Residuals are evaluated afresh in physical current
units and against both source-RHS and loaded-current scales.

The synthetic independent reference assembles all passive tissue/contact nodes
into K, adds differential pair incidence B and two branch-current unknowns I,
and imposes a gauge through a Lagrange multiplier lambda:

    K u - B I + c lambda = 0
    B^T u + 50 I = Vs
    c^T u = prescribed_gauge

It enforces every metal KCL equation directly, without the reduced row choice.
Both a V3 gauge and a mean-all-nodes gauge are checked. Summing the nodal rows
forces lambda=0 for the isolated model, independently checking absence of
spurious current through the numerical gauge. A deliberate added shunt-to-
reference fault must fail this property and expose the otherwise omitted
pair-1 KCL row as an independent diagnostic.

Reciprocity compares the two source basis responses at **one same frequency,
material, geometry and contact model**, using a transpose without conjugation.
A 2000 Hz response and a 2010 Hz response do not constitute a reciprocity test.
Synthetic source symmetry, orientation changes, pair permutation, complex
superposition, inactive-output loading, and the distinction between 50 and
100 ohm differential resistance are covered in the unexecuted test source.

## Deferred API, ownership, and remaining work

`floating_cem.solve(np, Q, profiles, pads, cells, areas, zA, activepair, guard,
deadline, *, transform, gmres, linear_operator)` explicitly injects the frozen
real/complex transform and the owner's numerical dependencies. It imports no
scientific modules and reads no files. Original profile and continuous-z field
reconstruction callbacks can be reused; the old common-ground solver cannot.
The returned `metal` has FOUR entries and requires explicit adaptation of any
old two-metal archive schema. No common-return surface state is reused.

The numerical owner must still authenticate immutable cache, masks, material,
contact and carrier identities, record hypothetical topology provenance, decide
the finite comparison scope, arrange any separately authorized execution, and
apply its resource/deadline guards. This preparation creates no admission,
lease, worker, numerical result, or publication. Root remains the sole numerical
owner: CPU4; aggregate ALL RSS plus ALL owned `/dev/shm/task1-*` tmpfs at most
8,000,000,000 bytes; at most 800,000 physical evaluation cells. Those limits
are not expanded by this directory. No Windows candidate assignment changes.

`test_floating_cem.py` is source only. Its pure tests and tiny NumPy synthetic
tests have **not been run** during this preparation. The dense injected solver
tests algebra and power paths, not real-data iterative performance. No actual
graph/cache arrays or source datasets were loaded, no PDE/eigensolve was run,
and no scientific module was imported. Static syntax/AST review is the only
local executable validation intended for this source-preparation task.
