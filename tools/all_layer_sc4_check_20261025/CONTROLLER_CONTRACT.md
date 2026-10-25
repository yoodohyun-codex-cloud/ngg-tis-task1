# Single SC2-to-SC4 check of the completed material sensitivity

This is source-only preparation. The source author has not imported, tested,
compiled or executed this controller, run a phantom PDE, registered a worker,
written a budget ledger, or published anything. The sole owner reviews and runs
all actual stages. The existing SC2 source and all results remain unchanged.

- SOURCE: `/dev/shm/task1-all-layer-sc4-check-20261025/source`
- RUN: `/dev/shm/task1-all-layer-sc4-check-20261025-run` (exact unique path)
- CASE: `baseline-square15-sc-eps1100-sc4-xy80`
- Controller: `SOURCE/all_layer_run.py --execute --output RUN`
- Native wrapper: `WholeLayerSensitivityBasis.java`, isolated in RUN/classes
- Comparator: `/dev/shm/task1-all-layer-sensitivity-20261025-run`,
  case `baseline-square15-sc-eps1100-xy80`
- Schema: `task1-whole-layer-sc4-check-native-v1`

The prior SC2 result completed eight actual RHS in81.8654seconds and its first
independent potential-gradient normal-current diagnostic at SC/dermis was about
7.8percent, whereas the shared-face check was near roundoff. That diagnostic
motivates this single additional mesh condition. It is not an established
accuracy gate or a material measurement. No third condition is automatic.

## Frozen model and exact differences

The phantom remains50mm diameter and0.1/5/5/15mm thick SC/dermis/fat/muscle.
XY remains0.625mm and bulk counts14/14/40. Only SC cells change2to4; resulting
z count72, total cells361728. No geometry, electrode area/shape/position/rotation,
contact number, material parameter, waveform or drive topology changes.

`all_layer_inputs.derive_config` checks the actual SC2 config SHA256
`a9d2d08d7e69d3cf1b21e50c1af44510ba416cee95e101c77f5581dcfae1269b`
and mask SHA256
`7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2`.
Only two assignments differ: `validation.sc_cells=4` and the declared mask storage
path. Mask bytes stay identical. Sigma S/m remains0.0002/0.2/0.04/0.3 and relative
permittivity1100/10000/1000/100000, all explicitly uncalibrated assumptions.
The prior SCepsilon110000→1100 scenario remains historical context, not a new
material change in this mesh check. Evidence-backed material calibration is
still blocked by the recorded skin-layer and carrier-specific raw-data gaps.

Four physical15mm square pads225mm2 each occupy the same canonical patches.
There are two independent outputs, with pad0/1 signal and pad2/3 common GND.
The peak complex basis is0.5V before50ohm, i.e.1Vpp high-Z basis. The inactive
output is0V through50ohm at each basis frequency. All four frequencies
3000/3030/9000/9090Hz and the square3h synthesis coefficients are unchanged.
There are four frequencies times two RHS, exactly eight actual new solves.

## Five explicit stages and resource admission

Before preparation the sole owner must replace the explicit PARENT placeholder
with the actual current topic-branch commit after first-result publication and
any intervening owner GUI publication. Preparation rejects the placeholder.
All source bytes freeze before compile/class pins/preregistration/publication.

```text
python -B SOURCE/all_layer_run.py --prepare --output RUN
python -B SOURCE/all_layer_run.py --publish-source --output RUN
python -B SOURCE/all_layer_run.py --execute --output RUN
python -B SOURCE/all_layer_run.py --postprocess --output RUN
python -B SOURCE/all_layer_run.py --publish-results --output RUN
```

Stage caps45/120/240/300/360seconds total1065seconds. Each stage rechecks the
live original approved ledger and reserves the remaining registered caps.
This is inside the original13800second cumulative authorization, with CPU1,
existing absolute JDK21,2GiB Java heap, RSS plus ALL owned task1 tmpfs at most
3GiB, run cap768MiB within the original2GiB output cap, native cells below800k,
and ROOT2GiB plus exact compact atomic-ledger temporary reserve. Actual oldSC2
run408132949bytes is evidence; SC4 cost around1.029times that is only an
estimate. All guards stay active and existing data is never removed to fit.

Both global execution and loop locks require flock plus full-file POSIX lockf.
Java verifies direct parent PID/startticks, exact argv/source file, registration,
class pins, config/mask and both lock owners before native work and at frequency
boundaries. Existing absolute Java/javac run under setpriv parent-death KILL,
SerialGC, CPU1, no UsePerfData and RUN/tmp. STOP/needs_attention/
needs_physical_validation markers block the run. No overlapping PDE worker.

Preparation performs source/input contract tests, existing numerical analytic
selftests and compile/class pinning; it produces no phantom basis. Source,
config, mask, material audit, tests/classes and preregistration must be published
and every immutable Gitblob fully SHA/bytes read back before native execution.
No blind mutation retry, main merge, installation, deletion, budget expansion or
private approval/ledger/Windows-destination publication occurs. Partial and
failed outputs are preserved. Immutable stage receipts require an explicit
reviewed recovery rather than automatic retry or overwrite.

## Native data and postprocessing

Native ABI is identical to the SC2 exporter with N=361728 and actual SC4 faces:

- `grid.csv.gz`: x_mm,y_mm,z_mm,layer,volume_m3.
- Per frequency E, Jtotal, Jconduction: lossless gzip LE complex128 `(2,N,3)`.
- Potential: lossless gzip LE complex128 `(2,N)`.
- Contacts: pad,x_mm,y_mm,area_m2; density LE complex128 `(2,ncontacts)`.
- Source transfer LE complex128 `(2,2)`; loss matrices `(6,2,2)` with tissue,
  contact and50ohm convention inherited unchanged.
- Effective per-frequency gamma, mesh metadata, original five native gates,
  validation receipt and BASIS_COMPLETE last.

Jtotal=gamma*storedE and Jconduction=sigma*storedE are derived exports, not
independent verification. Source/class/config/raw hashes are retained. The
independent phi-only interface reconstruction remains separate from shared-FVM
face-flux self consistency and phi-to-stored-E identity.

`sc4_post.required_inputs()` supplies pinned actual SC2 native/post files.
`sc4_post.build(run,guard,declared_sha256=...,deadline_monotonic=...,
include_max_direction=True)` returns JSON summary and derived scalar arrays,
without writing or solving. New physical fractional ROI volume weights use the
same frozen mask method, with exact bulk-coordinate identity and a separate
volume-average comparison of SC cells. No SC2 scalar mask is blindly reindexed
onto the larger SC4 grid. The target stays central radius5mm/depth15–20mm,
surface0–5mm, and total complement, with the same depth origin and volume rules.

SC2 and SC4 independent interface diagnostics must share a two-point linear SC
fit for comparison; the SC4 three-point quadratic fit is additionally reported.
A changed fit order is not interpreted as mesh improvement. Independent
interface accuracy remains diagnostic-only because no accuracy threshold was
established. Existing adjacent-metric limits stay1percent for named target/ROI
TIS/RMS/selectivity,5percent for contact Jmax/J95/contactV and2percent for
SC/contact/source power. They apply only to this grid pair, not a continuum,
physiological activation threshold, safety limit or full convergence proof.
Prior XY/edge/bulk/contact/material/experimental holds remain even if this one
SC comparison passes. Publication status and Windows saving/synchronization
remain separate; no connected Windows destination is available here.
