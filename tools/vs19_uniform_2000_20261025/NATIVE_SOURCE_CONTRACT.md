# U19 native source proposal

This source is prepared for the owner's review. It has not been compiled, imported,
tested, prepared or executed by the source authors. The owner must bind the actual
MMS publication and positive root decision before preparing a new run. A matching
commit string alone is insufficient: the owner must authenticate immutable public
readback of the exact decision/spec/summary and the completed SC8 comparator.

The rejected G18 draft remains under its separate original tmpfs source directory.
No G18 native admission or solve is authorized by this U19 source.

- Run: `/dev/shm/task1-vs19-uniform-2000-20261025-run`
- Case: `baseline-square15-human-sine2000-sc8-vs19uniform-bulk19-18-56-xy100`
- Controller/class: `u19_run.py` / `VS19UniformSingleCarrierBasis`
- Preregistration schema: `task1-vs19-uniform-2000-native-v1`
- Fixed D50, thickness0.1/5/5/15mm, XY0.5mm, counts8/19/18/56,
  793860cells<=800000, four225mm2 squares, twooutputs/commonGND/50ohm.
- One2000Hz carrier and two transfer RHS. Each is0.5Vpeak through50ohm,
  with the other output terminated at0V through50ohm. No TIS modulation claim.

`u19_inputs.derive_config(template_raw, mask_raw, material_raw, *, contact_raw,
spec_raw, summary_raw, decision_raw, root_decision_public_commit, run=RUN)` is
pure. It returns the original proposal keys plus new `z_faces_bytes`,
`mms_spec_bytes`, `mms_summary_bytes`, `root_decision_bytes` and their hashes.
The owner writes these only to new `z-faces.json`, `mms-spec.json`,
`mms-summary.json` and `mms-native-admission.json` in the new run.

The face file uses schema `task1-u19-explicit-z-faces-v1`, units`m`, grid_id`U19`,
layer_counts`[8,19,18,56]`, `z_faces_m`, `face_table_sha256`, `mms_spec_sha256`.
Its face array exactly matches MMSspec.geometry.U19.faces_m. Config adds
`mesh.z_faces_path`, `mesh.z_faces_sha256`, `mesh.face_table_sha256`,
`mesh.mms_spec_sha256`. The raw face-file hash is distinct from the MMS hash of
compact JSON containing only the face array.

Preregistration additionally requires `z_faces_file`, `z_faces_sha256`,
`mms_spec_sha256`, `mms_summary_sha256`, `root_decision_sha256`,
`root_decision_public_commit`. The last value is separate from decision contents
to avoid a self-referential commit hash. The decision schema is
`task1-u19-native-root-admission-v1`, with status`admitted_native_diagnostic`,
candidate`U19`, root_review_positive`true`, automatic_native_admission`false`,
candidate_adopted`false`, new_native_conditions`1`, maximum_native_RHS`2`,
the exact MMS spec/summary SHA256, actual mms_result_commit/sc8_result_commit,
and a nonempty decision_basis. No success receipt is synthesized by the inputs.

The new explicit-face mesh inherits `Mesh`, reconstructs only the mesh indices,
and feeds unchanged `ShapeNet`/COCG/field/loss arithmetic. Native metadata emits
all102 actual faces from the stored array, with mesh_face_file_sha256,
mesh_face_table_sha256 and mms_spec_sha256. Old uniform Java face accumulation
may differ by binary roundoff from the MMS formula; compare unaffected physical
faces with the predeclared tight tolerance, and do not claim old bit identity.

Keep five original conservation gates and the separate5percent potential-only
screen. Compare actual new versus completed SC8-U18 using native volume weights,
both2/2 and3/3 fits and identical fixedr23.75/native24 scopes. Preserve every
failure. Source/runtime authentication, discrete conservation and one adjacency
do not certify full convergence, material/phantom calibration or experiment.

Exact Java invocation after source publication, owner admission and compilation:

```
java -Xmx2g -XX:+UseSerialGC -XX:ActiveProcessorCount=EFFECTIVE_CAP \
  -cp RUN/classes VS19UniformSingleCarrierBasis \
  --execute-parent OWNER_PID OWNER_STARTTICKS CONFIG_ABSOLUTE NEW_BASIS_ABSOLUTE
```

The owner retains both repository locks, a finite watchdog, live descendants and
RSS plus all task-owned tmpfs accounting under the active policy, source/input
SHA rechecks, failure preservation and immutable raw-artifact publication/readback.
Tmpfs alone is volatile. No installation, deletion, policy relaxation or main merge.
