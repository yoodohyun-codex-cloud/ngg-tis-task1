# FixedSC8 viable-skin estimator/operator diagnostic

This source-only proposal registers15 planar periodic manufactured cases, not a
real phantom calculation. Neither existing source nor original output is edited.
The actual SC4→8 study retained13scalar stability while its independent jump
changed little or worsened, with prior signed decomposition dominated by the VS
side. This motivates separating sampling/fit bias from vertical FVM error.

Candidates are fixed before execution: U18 = SC8/VS18uniform/fat18/muscle56;
U19 = SC8/VS19uniform/fat18/muscle56; G18 = SC8/VS18/fat18/muscle56, with VS
weights proportional to1.15^min(j,17−j). This symmetric grade clusters toward
SC/VS andVS/fat and avoids silently sacrificing the second boundary. It is one
predeclared grading, not a result-tuned ratio or search. Physical VS thickness
stays5mm; every other physical layer/domain/material remains fixed. Modes
1/2/4/8/16 and XY0.5mm stay unchanged. Fixed2/2 and3/3 fits use actual centre
positions in each candidate and remain separate.

Owner make_spec computes and freezes exact faces, all VS widths/min/maxdz,
physical boundaries, real-equivalent cylinder columns/cells and face-table SHA
BEFORE build. Each candidate must fit the unchanged800000 real-equivalent-cell
cap. These equivalent counts are not actual native computations. Source agents
have evaluated none of the geometry, models or cases.

References are deliberately distinct:

- Analytic continuum at physical k: physical periodic manufactured truth.
- Analytic continuum at k_fd: vertical-discretization reference; comparison with
  physical k isolates the unchanged lateral modified-wavenumber error.
- Solved discrete network: Thomas solution crosschecked by independent downward
  admittance reduction. It validates algebra and supplies a shared discrete-face
  reference ONLY; it is not true continuum/PDE accuracy.
- One-sided fits on exact continuum samples: pure sampling/estimator bias.

For each side of SC/VS retain signed complex identities:
Jfit(FVM)−Jcontinuum = [Jfit(FVM)−Jdiscrete]+[Jdiscrete−Jcontinuum]
and = [Jfit(exact continuum samples)−Jcontinuum]+[Jfit(FVM)−Jfit(exact samples)].
Absolute/spatialRMS/relative errors, signed cross terms, denominator floors,
all three interfaces and all5%flags stay visible. No manufactured bias is
subtracted from actual native data and no5%criterion is relaxed.

Predeclared engineering REVIEW screens use worst envelopes across all declared
modes/interfaces: no more than1% relative worsening plus1e−10 dimensionless
roundoff allowance in continuum-kfd SC/all-face conservative-flux errors,
VS-profile L2 and combined physical-k profile L2. A10% reduction is the proposed
meaningful-gain screen, never evaluated from a zero baseline. Physical-error
improvement and estimator-localization improvement in BOTH fixed fit orders are
separate review flags. They do not automatically select a winner or admit a
native case, and the full per-mode/interface rows must be considered; envelope
nonregression does not imply pointwise monotonicity. These are numerical study
screens, not physical tolerances, activation thresholds or safety limits.

Native followup blockers are explicit: the current frozen ValidationMesh permits
neither VS19 nor gradedVS18. Any real followup needs a separately source-published
and validated geometry adapter, actual count/resource admission and root review.
No native calculation or mesh implementation is introduced by this MMS source.

API: required_inputs() hashes small completed SC8/prior-MMS metadata only;
make_spec(receipt_bytes,config_bytes) validates the existing published2000Hz
material/config and freezes geometry; build(spec,guard,deadline_monotonic=None)
returns {summary,arrays} without file writes or a native worker. Root's finite
owner applies locks/watchdog/4CPU/aggregate8GB policy and runs only after actual
SC8 completion. Original continuum/solver helper is an unchanged byte copy.
