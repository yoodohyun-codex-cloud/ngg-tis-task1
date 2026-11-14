# TIS thickness × placement comparison — revised 2026-11-14

**Current request: dermis and fat independently take 2, 2.5, …, 10 mm, giving 17 × 17 = 289 thickness combinations. SC stays 0.1 mm; diameter stays 50 mm. Use the previously used computation mode/environment. New PDE results: 0.**

This supersedes the earlier five one-factor conditions in commit `1ef869145e9cffa0a7b79860ae9f257edb795fc3`. No five-case result existed. The original 0.1/5/5/15 mm results, raw inputs, failures, GUI pointers and Task 2 remain untouched. The alternate dot-cloud workspace performed repository clone/fetch only according to the coordinating task; it is not the original native filesystem and no calculation there is planned.

## Actual environment status and the computation that must be recovered

The earlier command-provider failure was real: `No usable execution environment is available`. After the environment context changed, a single read-only retry succeeded on November 14. The present review executor is therefore no longer described as wholly unavailable. It still does **not** expose the original Task1 computation filesystem:

- The observed checkout is `/workspace/ngg-tis-simulation`, branch `work`, HEAD `3feb66b4015fea968c4775e65ac176366853cc2e`.
- It has pre-existing modified MPH/CSV/binary paths. Their origin/content was not inferred; none was reset, hydrated, repaired or overwritten.
- `/workspace/ngg-tis-task1` does not exist; there are no task1/TIS entries in this executor's /dev/shm.
- In the current visible PID namespace there was no Java numerical worker; the only Python process observed was the read-only inventory. This says nothing about a worker in the original remote task. No ownership lock was acquired, removed or copied.
- The environment-status API identifies a managed cloud saved configuration for **this review task**. Its identifier is not evidence of the original numerical task's saved configuration. No original saved-configuration name/ID/version binding was found in the inspected public execution receipts.
- The original numerical task identity is tracked by the coordinating task from its prior task inspection. Public sources below independently establish the runtime, numerical implementation and completed work, not a live task connection. This review cannot reconnect or control that original task.

| Historical mode | Direct evidence | What is established |
|---|---|---|
| Task1 Linux Codex Cloud, initial restart | [execution report](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/docs/CLOUD_RESTART_EXECUTION_20261020.md), [CLOUD_START](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/CLOUD_START.md) | Original numerical work used /workspace/ngg-tis-task1, Java/Javac21.0.12.1, Python3.12.14 and NumPy2.3.5 at the restart. Java complex FVM/COCG and Python postprocessing ran actual finite batches. The bootstrap was separately validated/recalculated; it was not a complete restoration of every older native file. |
| Task1 Linux Codex Cloud, later 2000/2010 Hz E13 fine run | [worker receipt](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/data-native/E13-fineXY-20261025/worker-receipt.json), [execution stage](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/data-native/E13-fineXY-20261025/execution-stage.json), [registration](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/data-native/E13-fineXY-20261025/registration.json) | Actual two new driven fine RHS completed, exit0, source commit50a930fbe1fe08b0b0af2d00d99c79eec3b96fb4. New coarse RHS/eigensolves/FVM RHS were0. Numerical-worker elapsed860.685s. Run namespace was /dev/shm/task1-E13-fineXY-20261025-run under the original Task1 controller. |
| Actual latest solver family | [fine_solver](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tools/E13_fineXY_20261025/model/fine_solver.py), [layer DtN backend](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/tools/E13_fineXY_20261025/model/frozen_layer_dtn_backend.py), [BLAS runtime](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/data-native/E13-fineXY-20261025/threadpool-runtime.json) | Python/NumPy/SciPy layered modal/DtN response plus coupled surface/contact/source GMRES; real Q streamed in bounded chunks. Python3.12.14 is recorded; OpenBLAS0.3.30 reported4threads. This is a later method than the Java FVM and must not be misreported as COMSOL or a new FVM solve. |
| Latest E13 drive-ratio comparison | [root review](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/docs/TASK1_CONTACT_EDGE_20261025/E13-fine-drive-stream-root-review.md) | Reconstructed existing complex fields and evaluated metrics; new PDE/Q/eigensolves0. This later postprocessing is not another geometry solve. |
| Windows work | Separate windows-owner-adapter/isolated-pairs branches exist | Their existence does not identify the cloud common-GND calculation as Windows execution. Floating isolated pairs are a different source topology. Windows saving was false in the cited E13 worker receipt. No Windows worker is started or resumed here. |
| COMSOL | Initial execution report and current instructions | Version constraint remains5.3a/planned5.3.1.201; installation/license/runtime unverified. No installation or activation. |
| Alternate dot cloud / current review checkout | Separate task report and this read-only inventory | Repository availability and installed numerical packages do not prove original owner state, raw restore or equivalence of execution mode. No substitute calculation. |

The historical E13 registration binds CPU4, aggregate owned-process RSS plus all owned tmpfs at most8,000,000,000 B, one numerical owner/solve, maximum800000cells and finite watchdogs. It records numerical child timeout1200s and outer timeout2400s for that specific run. The cumulative research-time ceiling was previously removed; this does not authorize unbounded stages or extra paid resources. Historical Java heap remains2GiB. Runtime policy SHA was `3f1cf1bced28489b85f0f8795b81c0a20aab2950ab70c91c8ac2018034256804`; the operational file and approval must be recovered and reverified, not recreated from this summary.

The latest E11 admission forecast was8,300,885,378 B numerical /8,410,885,378 B publication, above the8GB task cap. This is an October25 forecast for E11, not current measured occupancy or proof that any289-case batch fits. No budget/security/storage policy has been changed in this review.

## Concrete recovery path, without changing execution mode

1. Reopen/reconnect the original Task1 numerical task through its existing managed Codex Cloud configuration. First identify the original task's configuration name/ID/version in that task's settings; do not select this review task's configuration or an arbitrary repository-matched configuration as an assumed equivalent. No tool in this review exposes that original binding.
2. In that original executor, inspect the repository HEAD/local changes, all recorded owner PID+startticks and the actual global/owner lock mechanism. Old receipts are history, not live-lock proof. If an owner is active, coordinate at a safe boundary; never start another owner or stop it to make space.
3. Inventory original runtime policy/approval/ledger files and surviving native/cache files. /dev/shm is ephemeral: a restarted configuration does not guarantee those files survived. Verify saved bytes, shapes, dtypes, units and source/config/input hashes against immutable run manifests.
4. If particular files are missing, recover only the required pinned objects into a unique restore directory using the existing verified transfer manifest. The [E13 fine raw manifest](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/data-native/E13-fineXY-20261025/raw-manifest.json) and the [latest transfer manifest](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/95b346bcae8c1b0eaebd4b7ebf00e7a78d1ece98/docs/TASK1_CONTACT_EDGE_20261025/E13-fine-drive-stream-20261025-transfer-manifest.json) distinguish objects/aliases. Public clone/fetch alone is not native restoration; no substitute values or silent baseline recomputation.
5. Reproduce a representative saved2000/2010 Hz baseline and its circuit/field/ROI quantities with the same pinned pipeline before admitting thickness changes. The latest source identifies modal/DtN + GMRES; reverting to the older Java implementation is a separate method change, not automatic recovery.
6. Freeze the executable/config/model manifest, update only the new thickness/placement implementation on this separate branch, and pass analytic/geometry/circuit and baseline-reproduction checks. Revalidate live effective CPU/memory and retained-storage capacity for every finite batch. If runtime/policy/cache/native dependencies cannot be recovered within existing access and resources, retain an exact blocked/not_run record.

No recovery, dependency installation, scientific module import, numerical test, solver start or new worker has been performed by this review. The read-only shell inventory and the elementary interval-overlap arithmetic below are not simulation execution.

## 289-condition geometry specification

`dermis_mm = 2 + 0.5*i`, `fat_mm = 2 + 0.5*j`, `i,j = 0,…,16`.

The full manifest is [THICKNESS_GRID_20261114.csv](THICKNESS_GRID_20261114.csv), in dermis-major then fat-major order. It contains289 unique combinations including(5,5), all with `simulation_status=not_run` and no electrical result. It is a geometry plan, not a field/result table.

Retain muscle thickness15 mm unless the user explicitly changes that geometry. Derived coordinates are:

- SC/dermis boundary: z=.1 mm.
- Dermis/fat boundary: z=.1+dermis_mm.
- Fat/muscle boundary: z_m=.1+dermis_mm+fat_mm.
- Bottom: z_b=z_m+15 mm.
- Primary ROI: r≤5 mm, **absolute surface depth15≤z≤20 mm**, ideal volume125π mm³.

The original five-case assertion “all ROI is muscle” is no longer valid. The plane-layer geometry gives the following exact interval classifications before any mesh or PDE:

| ROI composition | Number of cases | Interpretation |
|---|---:|---|
| Fully inside domain and entirely muscle | 220 | Same absolute-depth volume, but different depth below muscle surface |
| Fully inside domain, partly fat and partly muscle | 65 | Report separate tissue-weighted fractions and statistics; whole-ROI electrical matching is not equal muscle exposure |
| Entirely fat | 1: dermis10/fat10 | Muscle begins at20.1 mm; no muscle exists within the15–20 mm primary ROI |
| Partly outside the domain | 3 | Full fixed-ROI matching is not defined under the unchanged15 mm muscle thickness |

The three truncated cases are(2,2), bottom19.1 mm with18% of the requested ROI outside the domain, and(2,2.5)/(2.5,2), bottom19.6 mm with8% outside. They remain in the289-condition manifest. Do not move the ROI upward, extend muscle silently, treat absent cells as zero field or renormalize the covered volume as though it were the full ROI. Mark full-ROI mean/P10, spatial matching and compensation as `not_comparable_missing_domain`. Any covered-subvolume metric must have its own explicit name and denominator.

For every case, store the analytical fractions and actual discretized fractions for SC/dermis/fat/muscle/**outside-domain**. SC and dermis have zero overlap with z15–20 in this specific range, but still keep their named fields. For any interval[a,b], the axial fraction is max(0,min(20,b)−max(15,a))/5. Native ROI weights must also account for radial/cell overlap; actual represented volumes and errors must be reported.

Record the requested ROI relative to muscle as[15−z_m,20−z_m] without clipping. Negative relative depths explicitly lie above muscle. A separate ROI∩muscle statistic can be reported; if its volume is zero, mean/P10 are null/unavailable, not zero. The primary ROI never moves after seeing the results. Moving bottom depth is a separate boundary-condition sensitivity and must be disclosed.

## Fixed electrical questions and unresolved run binding

User-fixed requirements remain four physical pads, two source outputs, explicit return topology,2000/2010 Hz reference sine condition, no diameter enlargement, unchanged original data and no physiological/activation/safety claim. The original cloud common-return model uses one common GND,50Ω per output and inactive-source0V/50Ω termination. Use peak phasors exp(+jωt), distinguish1Vpp high-Z command from0.5Vpeak before50Ω and loaded tissue/contact voltage, and report solved currents rather than prescribing a current without a current-source model.

The earlier PR proposal selected the historical bare-NGG10×10mm-pad exploratory cohort and L0 centres(−12.5,−12.5),(+12.5,+12.5),(+12.5,−12.5),(−12.5,+12.5)mm, with L1/L2 inward centres±10/±7.5mm. Those were **unexecuted design proposals**. They have not been verified as the original owner's current selected model and must not be called a restoration of latest B0/P23/E13. The latest completed cloud E13 condition has225mm² pads, a different geometry and mixed provisional materials. Source identity, pad dimensions/coordinates, material table, contact table and waveform coefficients must therefore be bound to the intended original baseline before an executable289-case registration. No legacy values or later E13 target number are silently substituted.

Until that binding is verified, source/config/material hashes, numerical baseline mean/P10, required voltage and current remain null/not_run. The range289 is confirmed; exact executable-model restoration is blocked. This distinguishes requested conditions from proposals and from actual results.

## A–D comparisons after original-mode recovery

The scalar target remains the same ordered2074-direction sampled maximum
`M(x)=max_u 2 min(|u·E2000(x)|,|u·E2010(x)|)`.
It is a sampled angular lower bound, not neural recruitment. Also report fixed x/y/z TIS and carrier RMS `sqrt((||E2000||²+||E2010||²)/2)`. Same-frequency contributions are combined as complex vectors before norms/power.

| Group | Planned scope | Calculation type |
|---|---|---|
| A | All289 thickness combinations, baseline placement and fixed waveform/input | Actual new geometry-dependent solves unless an exactly matching, verified cache exists; count each true RHS and alias separately |
| B | Each full-domain A case matched to the same T0(5,5) target mean, with residual P10/map errors | Common linear voltage rescaling, no new PDE; truncated-domain cases have no full-ROI match |
| C | Same fixed input, bounded placement alternatives after A exposes a specific mismatch | New placement solves; additional conditions must be registered separately, not hidden inside the289 count |
| D | Placement plus common-voltage compensation if required | Linear rescaling of each C solution; no additional PDE for an unchanged linear model |

A289-case scope is finite but is **not admission to launch289 workers or an unattended unvalidated queue**. First reproduce/admit the5/5 baseline, then one finite sequential batch at a time under the original single-owner controls; a proposed batch can follow one dermis row of17 fat values with per-case checkpoints. Actual timeouts, output retention and resource forecasts must be bound before execution. The previous maximum7primary/9total geometry cap belongs to the superseded five-case design and no longer describes this request. Placement and paired-grid counts remain separately registered after baseline/model binding; no automatic full Cartesian product with placement.

Let μ0,q0 be T0 mean and P10. Common positive voltage scaling is k=μ0/μ; φ,E,J and currents scale by k, powers by k². Report q0/P10 separately and never imply one amplitude necessarily matches both. If either reference metric or the case mean is non-positive/non-finite, report not_matchable. Do not construct infinite voltages.

The previously proposed numerical comparison tolerance remains mean/P10 each within1% and common-physical-ROI map relative L2 difference≤5%, explicitly a **provisional comparison tolerance**, not a safety threshold, numerical convergence proof or experimental equivalence. Use conservative physical overlap between grids, never equal array indices. Mixed/fat-only ROI composition must remain visible in any matching table.

Compare raw command, target matching, equal source real power, equal sum-of-output-RMS bookkeeping and simultaneous baseline-relative burden ceilings separately. Report surface/SC vector Jmax/J95, contact-normal Jmax/J95, contact voltage, source/return currents, signed source/layer/contact/50Ω powers and off-target distributions. Baseline-relative limits are numerical comparison caps, not human safety limits. Net return RMS requires summing complex return currents at each frequency before taking RMS; Σoutput RMS is only bookkeeping.

## Implementation and validation requirements

The prior Java mesh/exporter hard-coded layer thicknesses and z boundaries. The latest modal backend likewise has fixed `physical_layers_m`, reference paths and depth-evaluation partitions. The new range needs consistent parameterization of the **original recovered pipeline**, not a properties-only edit or a silent alternative SciPy solver.

Only a verified XY eigenbasis whose cache identity is mathematically independent of layer thickness may be reused. Layer transfer/admittance profiles, coupled contact/source response, φ/E/J and ROI weights depend on the new thickness and must be recomputed. Do not reuse an old full field by moving labels or interpolating thickness.

Required checks: units and derived boundaries; all289 geometry/domain-coverage entries; exact pad area/no overlap; homogeneous/complex layered analytic cases; independent interface gradients; source/contact/passivity/current/power balance; complex two-tone envelope examples; and a representative original baseline reproduction. Shared-face flux self-consistency and actual one-sided interface accuracy remain distinct.

Any new grid must obey800000cells. The earlier universal .5mm XY check is **not admitted over the extended range**: larger z counts can exceed the cell cap. Preserve the actual modal/FVM discretization identity, sample locations, physical overlap weights and case-specific mesh counts; register supported paired checks separately. Do not coarsen a failing case silently, change matching tolerances afterward or claim full convergence from one grid pair.

Save complex128/Float64 φ/E/J, grid/weights, circuit quantities, configuration and hashes in unique runs with actual UTC start/end/exit, PID/startticks, lock proof, resource maxima, native manifests and preserved failures. Common-scale maps need unclipped ranges/colorbars and tissue/domain labels. No current.json update without review. No scientific fields or maps were generated in this review.

## Status and next dependency

| Item | Current state |
|---|---|
|289-condition Cartesian specification and analytical tissue/domain fractions|prepared, checked; not a PDE result|
|Current review executor|read-only shell available; original Task1 root/tmpfs absent|
|Original saved cloud configuration binding/current owner/locks/runtime|not verified; blocking original-mode recovery|
|Original cloud method and prior actual completion|public receipts/code inspected; Java FVM history and later Python modal/DtN+GMRES distinguished|
|Alternate dot-cloud computation|not started; reported clone/fetch only|
|289-case implementation, numerical tests, baseline solve, A/B/C/D outcomes|not_run; zero new PDE and zero numerical field rescaling|
|Windows/COMSOL fallback, installation, new worker/resources, deletion, security/main merge|not performed|

Resume through the original task/configuration with verified retained or explicitly restored inputs and current resource admission. If the original configuration or native dependencies cannot be recovered, report that exact blocker. Do not quietly change to the current review checkout, dot cloud or Windows.
