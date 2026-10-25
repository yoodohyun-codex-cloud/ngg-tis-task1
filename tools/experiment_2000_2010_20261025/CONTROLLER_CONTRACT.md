# Finite2000/2010Hz sine experiment-model case

Source-only preparation: no module import, numerical evaluation, tests, compile,
PDE, locks, ledger or Git action by the source author. Root owns all actual stages.
SOURCE `/dev/shm/task1-experiment-2000-2010-20261025/source`; RUN
`/workspace/task1-experiment-2000-2010-20261025-run`; CASE
`baseline-square15-human-sine2000-2010-xy80`; controller `experiment_run.py`;
class `ExperimentSineBasis`; inputs `experiment_inputs.py`; post `experiment_post.py`.

The fixed50mm phantom keeps0.1/5/5/15mm layers,SC2/XY0.625mm/bulk14·14·40,
351680cells and four canonical225mm2 top pads. Two outputs, common pad2/3 return,
50ohm each; inactive other-frequency output0V through50ohm. Source code anchors
are registered for ground assignments,0.02S output termination, selected RHS,
and current=(source-metal)/50. Independent isolated bipolar pairs are a separate
UNRUN scenario. Actual equipment waveform/wiring remains unverified.

New actual frequencies2000/2010Hz, each1Vpp SINE before50ohm, c=[1,0]/[0,1].
There are two frequencies times two RHS =4 actual solves. No harmonics or Jraw
copies. Native complexE/phi/grid/contactdensity/source/loss are retained; post
computes gammaE and sigmaE as derived quantities, not independent validation.
Eight material rows are selected byte-derived from the already-published24row
HREF-MIX function audit; no literature function is reevaluated and no new values
are invented. SC100um stays fixed. SC14vs100um comparison is ONLY analytic
specificZ=t/gamma, ratio100/14, with no geometry/PDE thickness change.

Nominal10nm contact uses the frozen500Hz lower-fit-window case, NOT500ohm Rs.
Actual selectedRs236.5717747232937ohm is subtracted ONCE from the raw measured
complex spectrum. Original XLSX SHA3ecc99... and30point canonicalSHAd578804...
are verified. Frozen stdlib XML reader and log-frequency interpolation are
reapplied at actual2000/2010Hz, no refit or3kHz boundary reuse. Measurement
area1e-4m2 multiplies lumped measured-minus-Rs once; the unchanged CEM then uses
actual pad patch areas once. No division by two. PBS impedance remains an
unvalidated human-contact surrogate. Contact receipt, config and raw pins are
archived and published before native execution.

Caps15prepare/35source/60native/35post/75publish/10persist =230seconds; GUI has
its separate allocation. Existing cumulative13800seconds,CPU1/heap2GiB,
RSS+ALLownedtask1tmpfs3GiB,800kcells, source/class/input pins, dual locks and
original five conservation gates remain. Storage capacity guards remain OFF
under the user's explicit policy. Real cloud disk is used; Windows1TB access is
not claimed. Provider64MiB/blob and96MiB API output are transport constraints.

Root sets the actual expected topic parent before preparation. Published source,
configuration, material/contact receipts, class pins and selftests precede any
native arrays. Existing byte-identical immutable blobs may reuse prior FULL
SHA/bytes readback proof from the pinned published humanSC2 receipt, explicitly
labelled as such. Every new blob requires fresh full readback; only confirmed404
permits creation and unknown mutation failure is never blindly retried.

Post compares this new2k sine case with3k sine references from actual raw fields,
source/contact/loss data, using exact existing ROI weights. It reports volume
mean/P10 and distributions plus separate current/power and burden-cap comparisons.
Predeclared5percent normalized-L2 independent-interface QA flags are non-aborting
numerical screening only, not physical accuracy, safety or activation limits.
Failure flags and all original results remain. A next scientific step is selected
from actual results subject to remaining budget; no infinite worker promise.

```text
python -B SOURCE/experiment_run.py --prepare --output RUN
python -B SOURCE/experiment_run.py --publish-source --output RUN
python -B SOURCE/experiment_run.py --execute --output RUN
python -B SOURCE/experiment_run.py --postprocess --output RUN
python -B SOURCE/experiment_run.py --publish-results --output RUN
python -B SOURCE/experiment_run.py --persist --output RUN
```

Persist rechecks already disk-backed native/post hashes and publication; it does
not claim Windows saving/sync or duplicate the PDE. No installation, deletion,
security change, main merge or CPU/time expansion.
