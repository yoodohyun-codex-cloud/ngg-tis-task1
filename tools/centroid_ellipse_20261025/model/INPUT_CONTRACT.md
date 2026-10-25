# Conditional centroid ellipse input contract

This is source preparation, not admission or an executed calculation. Import is
inert. `ellipse_inputs.make_spec(admission=None)` and `required_inputs` must only
be called by the existing root owner after it freezes all source and provides a
separate positive `task1-centroid-ellipse-root-admission-v1` decision.

The decision must bind the full canonical source inventory and a published,
reviewed outcome from the exact native `task1-P23-fineXY-20261025-run`. Synthetic
fineXY MMS runs cannot satisfy it. The fine outcome may be complete or an
explicit preserved failure. A failed outcome needs its actual publication,
known source-defined status, root review basis and nonempty missing-field list.
The receipt path is fixed to that exact native run's
`result-publication/result-publication.json`; another or synthetic publication
cannot substitute even if its file suffix happens to match.
No missing fields are inferred, and no fine numerical fields are transferred
into the ellipse model. Actual execution remains conditional on root selection.
Authenticated primary `holds`, `prospective_adjacent_grid_diagnostics` and
`diagnostics_not_run` are copied verbatim into review evidence only, with
explicit presence flags and null for absent fields. They never set solver,
material, contact, geometry or scaling parameters. The previously reviewed
f900ba92 input source is preserved outside live SOURCE as source evidence.

The context returns `catalog`, `controls.B0`, `controls.P23`, original coarse
graph and Q descriptors, the complete original/local/remote retained-Q proof
chain, common-grid ROI descriptor/receipt, P23 mask descriptor/receipt, receipt
centroids, frequency-specific material/contact receipts, source/input SHA maps
and the authenticated fine review. CSV, Q and scientific array contents are
never opened by this helper. The original Q manifest's historical verification
flags are not modified or treated as remote readback proof.

`new_geometry.candidate_id` is `E13-tangent-P23-centroids-225`. Its four top
ellipses use the published P23 per-pad area-weighted centroid, tangent major
axis length parameter `semimajor_mm=13`, and `semiminor_mm=225/(pi*13)`. These
are analytic source recipe parameters, not a generated contact mask. Each
analytic area is 225 mm², total 900 mm². Pads 0/1 connect to outputs 0/1; pads
2/3 share grounded return. There are two outputs, not four. Carriers remain
2000/2010 Hz, 1 Vpp high-impedance source amplitude, 50 Ω per output and the
existing termination/common-return model. Material/contact bytes, separate
frequency evaluation, Rs subtraction once and area conversion once are fixed.

The geometry uses the unchanged diameter 50 mm and 0.1/5/5/15 mm layers,
coarse 0.5 mm XY / 101 depth sampling, original native-half-face XY and analytic
normal-field ABI, and central-radius-5 mm depth-15–20 mm target ROI. Skin and
other non-target ROIs and original control normalization definitions remain
from the existing catalog. This is the same surrogate material/PBS-contact
comparison, not a verified thoracoabdominal human model.

The main owner must independently check the original CSV centroid exactly
against the published receipt, preserve both representations, then apply the
predeclared ellipse quadrature/area/containment/overlap gates. No automatic
centroid, axis or area repair is allowed. Pending checks remain pending in this
input context. The control records are immutable complete metric/scalar/raw
aliases; no control PDE, field reconstruction or angular recalculation is
authorized. Maximum new work is two driven RHS, one angular evaluation, zero
eigen solves and two control aliases. The coarse physical evaluation mesh is
793860 cells below the 800000 cap. Existing CPU4 / research RSS plus owned tmpfs
8e9-byte limit remains unchanged; there is no new worker or resource permission.

The nine new pure test definitions cover deferred input access, exact native
fine identity/accounting, preserved failure scope and retained-Q proof-chain
consistency, plus exact diagnostic copying without parameter transfer. The
source author has only parsed their AST, not run them. Root
must execute and publish actual test outcomes before numerical use. No
convergence, activation, safety, candidate adoption or Windows save is claimed.
