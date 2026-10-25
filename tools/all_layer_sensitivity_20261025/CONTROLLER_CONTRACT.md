# New four-layer SC-permittivity sensitivity: controller contract

Source-only preparation. Nothing here executes a solver or registers a worker on
import. The parent must perform admission, preregister inputs/limits/gates, compile
and pin classes, publish/verify source, and own both full-file POSIX locks.

- Source directory: `/dev/shm/task1-all-layer-sensitivity-20261025/source`
- Exact parent: `all_layer_run.py --execute --output RUN`
- RUN: new direct tmpfs child `/dev/shm/task1-all-layer-sensitivity-20261025-run`
  (this controller and postprocessor require this exact run; an existing basis
  is always rejected).
- CASE: `baseline-square15-sc-eps1100-xy80`
- Config: `RUN/configs/CASE.properties`
- Mask: `RUN/masks/CASE.csv`
- Basis: `RUN/bases/CASE` (absent at start)
- Existing JDK: `/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin/`

`all_layer_inputs.derive_config(template_raw,mask_raw,run)` is pure and returns
config/mask bytes, files/hashes, the exact two-key diff and all-four-layer material
assumption rows. The two changed config assignments are SC epsilon and the explicit
mask path mapping; mask bytes/hash and all other material/contact/geometry/circuit
properties stay unchanged. The evidence-backed material reset is DEFERRED, not
claimed. Goyal/Anand contextual audits should be registered by the parent as
separate evidence; none of their bulk numeric values is fabricated here.

Compile sources together into `RUN/classes`, never the frozen checkout:

```
setpriv --pdeathsig KILL javac -J-Xmx2g -J-XX:+UseSerialGC \
  -J-XX:ActiveProcessorCount=1 -J-XX:-UsePerfData \
  -J-Djava.io.tmpdir=RUN/tmp -encoding UTF-8 -d RUN/classes \
  ROOT/tis-java/TisSweep.java ROOT/tis-java/ExploreBasis.java \
  ROOT/tis-java/SelectivityShapeBasis.java SOURCE/WholeLayerSensitivityBasis.java
```

Actual parent-run child command after source/config/class SHA admission:

```
setpriv --pdeathsig KILL java -Xmx2g -XX:+UseSerialGC \
  -XX:ActiveProcessorCount=1 -XX:-UsePerfData -Djava.io.tmpdir=RUN/tmp \
  -cp RUN/classes WholeLayerSensitivityBasis \
  --execute-parent PYTHON_PID PYTHON_STARTTICKS CONFIG BASIS
```

Use the absolute existing executables; the placeholders above are notation, not a
shell script. Never install software, alter credentials, delete failure evidence
or relax the reserved disk/memory/time/cell budget. A `--selftest` invocation runs
inherited small analytic/operator/format tests and new source guards, not the
phantom batch. This child agent has NOT compiled or run it.

## Immutable preregistration fields used by Java

```
schema = task1-whole-layer-sensitivity-native-v1
status = prepared
repository_root = /workspace/ngg-tis-task1
run_directory = RUN
case_id = CASE
controller_path = SOURCE/all_layer_run.py
controller_sha256 = sha256(controller bytes)
config_sha256 = sha256(new config bytes)
mask_sha256 = 7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2
source_sha256 = {absolute source path: SHA256}
class_sha256 = {every absolute RUN/classes/*.class path: SHA256}
```

Source pins must include all three frozen Java numerical sources and the new Java
wrapper, `all_layer_inputs.py` and `all_layer_run.py`. Every class in the classpath
directory must be pinned with no extras. The loaded classes must all be from this
run directory.

The separate mutable `RUN/controller.json` must contain:

```
status = running
current_case = CASE
pid = sole Python parent PID
proc_start_ticks = actual /proc startticks
preregistration_sha256 = hash of unchanged preregistration bytes
current_config_sha256 = hash of unchanged config bytes
```

The parent must own both `ROOT/.task1-loop.lock` and
`ROOT/.task1-execution.lock` via full-file `fcntl.lockf` plus `flock`. Java checks
direct parent PID/startticks, exact argv/controller file, paths, config/mask,
source/classes and both live locks before the solve and at frequency boundaries.
STOP/needs_attention/needs_physical_validation markers block the run.

## Output ABI and budget admission

One condition, four frequencies, two native RHS each: eight actual phantom solves.
No new solve is done for potential or current export.

- `grid.csv.gz`: x_mm,y_mm,z_mm,layer,volume_m3; N=351680 rows.
- For each f=3000/3030/9000/9090, `field-f.bin.gz`, `Jtotal-f.bin.gz`,
  `Jconduction-f.bin.gz`: LE complex128 shape `(2,N,3)`, peak +jωt.
- `potential-f.bin.gz`: LE complex128 shape `(2,N)`.
- `contacts-f.csv`: pad,x_mm,y_mm,area_m2. Pad0/1 signal outputs and pad2/3
  common GND, four physical pads, two real outputs.
- `density-f.bin`: LE complex128 shape `(2,ncontacts)`, contact-normal density.
- `source-f.bin`: LE complex128 shape `(2,2)`, output row then driven RHS column.
- `loss-f.bin`: LE complex128 shape `(6,2,2)`; layers SC/dermis/fat/muscle,
  contact,50Ω; inherited loss matrix already includes its power convention.
- `effective-materials.json`: actual per-frequency/layer sigma/epsilon/gamma,
  units, explicit uncalibrated assumption label; no sigma/epsilon dispersion fit.
- `mesh-metadata.json`, `validation.json`, zero-byte `BASIS_COMPLETE` last.

Stored J arrays are DERIVED from stored E by gamma*E and sigma*E. They cannot be
counted as an independent reconstruction/continuity proof. Shared-flux interface
gate is likewise self consistency; independent phi gradients remain separate.

Original E/phi-only analogous basis is about156MiB. Two extra J copies make a
rough400–500MiB native estimate, NOT a fresh measurement/admission. Reserve a
finite maximum (parent proposed768MiB within the existing2GiB batch output cap),
postprocessing + publication/base64/readback peak, all owned tmpfs and Python/JVM
RSS under3GiB; CPU1/heap2GiB/cells<800k/condition600s/root2GiB reserve remain.
Individual compressed field/J blobs are expected below50MiB; verify actual sizes
and remote policy rather than inheriting the old32MiB C1 guard.

SC2 means only two SC centres. Do not infer independent interface convergence or
full SC/XY/bulk/edge/contact convergence from five discrete residual/power/current/
area/shared-interface gates. Preserve prior XY failures and original results.

## Finite controller stages

`all_layer_run.py` is an explicit five-stage owner. The source author has not
run, imported, compiled or tested it. The sole owner must review and execute:

```text
python -B SOURCE/all_layer_run.py --prepare --output RUN
python -B SOURCE/all_layer_run.py --publish-source --output RUN
python -B SOURCE/all_layer_run.py --execute --output RUN
python -B SOURCE/all_layer_run.py --postprocess --output RUN
python -B SOURCE/all_layer_run.py --publish-results --output RUN
```

SOURCE and RUN above mean the exact absolute paths at the start of this file.
Preparation compiles and selftests existing sources, checks only pure unit
fixtures, derives the new configuration and freezes all source/class/input pins.
It launches no phantom solve. Source publication and full immutable readback
must succeed before execution. Postprocessing reuses the one new eight-RHS
basis and the old canonical comparator; it launches no extra PDE condition.

Stage caps are90/120/600/600/360seconds, a1770second first-batch reservation.
Later stages recheck both the live ledger and all unchanged source/old input
pins. No stage automatically repeats or registers a second condition. Existing
stage receipts and partial output are immutable; a failed attempt requires
review of its preserved evidence and an explicit recovery decision. The
publication stages use expected-parent checks and no blind mutation retry.
No full budget ledger, private approval text or private Windows destination is
published. Windows saving and synchronization remain unverified.
