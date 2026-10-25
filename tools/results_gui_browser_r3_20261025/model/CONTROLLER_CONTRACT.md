This controller performs actual browser quality assurance on the unchanged,
already published consolidated HTML. It performs no native field decoding,
scientific array import, PDE/eigen solve, angular search or candidate adoption.

Root creates `source/root-admission.json` after consolidated result and transfer
completion, then invokes:

```
TASK1_GUI_BROWSER_EXPECTED_PARENT=<actual current topic branch 40hex> \
python -B /dev/shm/task1-results-gui-browser-r3-20261025/source/guardian.py
```

Required admission fields:

```
schema: task1-results-gui-browser-root-admission-v1
status: selected_finite_browser_validation
root_selected: true
consolidation_run: /dev/shm/task1-results-consolidation-20261025-run
consolidation_result_publication_path: <run>/result-publication/result-publication.json
consolidation_result_publication_sha256: <actual full-readback receipt SHA256>
consolidation_result_commit: <actual verified R 40hex>
decision_basis: <root rationale after result/transfer completion>
new_PDE_RHS: 0
new_angular_evaluations: 0
candidate_adopted: false
```

The actual R must provide direct full SHA/byte readback proofs for `index.html`,
`summary.json` and `views.json`. The controller publishes all its source,
registration, admission and exact input hashes before browser launch. Worker
checks the actual parent PID/startticks/script SHA, both FLOCK and POSIX locks on
all three task locks, source-publication plan and full readbacks, and exact spec.
Sources and inputs receive full before/after SHA verification; the 250 ms parent
monitor checks immutable identities, descendants, RSS plus every task1-owned
tmpfs directory. CPU <=4 and aggregate RSS+all task tmpfs <=8e9 remain unchanged.

Outer watchdog: 600 s. Browser child: 180 s. Each unchanged supported r3 Git
publisher: <=330 s and always bounded by remaining outer time. Chromium/V8's
virtual reservations are not restricted by a numerical-child RLIMIT_AS; actual
aggregate RSS and all task tmpfs remain monitored under the same 8e9 cap.

The browser uses the installed Playwright and `/usr/bin/chromium` without any
installation or security flag changes. Exact admitted HTML/JSON files are
fulfilled at `https://tis-results.test/`; external requests are blocked and fail
the check. This follows the existing managed-file-navigation workaround.

Actual checks include whole HTML payload versus admitted summary/views,
baseline/mandatory multipad/Top5 and all-native views, LOCAL separation, 60
normalization table rows, real contour metadata and native canvas creation,
physical axes/colour/bar range changes and persistence, distinct AM/RMS labels,
vector controls, 600 probe rows across 15 selections, real settings download and
upload including invalid-profile preservation, immutable complete payload and
source identities, JS/console/request failures, desktop and mobile screenshots.
No spatial-profile graph exists in this renderer; settings-profile export/import
is tested and no absent plot is claimed. Canvas QA does not validate numerical
fields, convergence, hardware loading, physiology or human safety.

Successful outputs include `browser-receipt.json`, `worker-receipt.json`, input
SHA proof, desktop/mobile JPEGs and actual settings fixtures, with full supported
Git readback. Fresh Chromium profile/cache remains local and is excluded from
publication. A GUI defect preserves `browser-failure.json`, screenshot/logs and
failed owner/worker receipts; the HTML is never patched automatically. Root
can publish that failure and authorize a separate versioned GUI source fix.

No tests, browser, imports of research modules, input data, locks, ledger writes,
Git operations or research/browser workers were executed by the source-authoring agents.


R2 preserves the first attempt and its source publication9299f993e5e655ee6dcb2710a4bbee17af5f5e76. The old failure happened before page navigation: Chromium's nested UNIX singleton socket path exceeded108 bytes. Exact owner/worker/log/publication evidence is bundled as prior-browser-launch-failure-evidence.json. Only controller/run/publication namespaces and scratch paths change; browser gates, CPU/memory/time limits, flags and admitted HTML remain unchanged. R2 scratch is an exclusive /dev/shm/task1-gbr3-<workerPID> with p/t/c subdirectories. The conservative nested singleton path is checked below90 bytes before launch, and the existing all-task1-tmpfs monitor covers it. Scratch/profile/cache and earlier failure evidence are preserved, never deleted by this controller. The R2 result includes browser-scratch.json.


R3 preserves the byte-identical R1 launch-failure evidence and additionally pins the actual R2 supervisor memory failure: peak aggregate 8,031,614,299 bytes, with no worker or browser PASS receipt. Missing receipts are recorded as missing, never fabricated. Original R1/R2 outputs, scratch and admitted HTML remain untouched.

The only browser allocation change is exact recursive JSON semantic comparison of the published summary/views against the embedded payload. It rejects type/null/primitive differences, non-finite/non-JSON primitives, different ordered arrays and different own object-keysets/values, without canonical deep clones or serialization of whole payloads. All full-D/source identity pre/post SHA and DOM checks remain. The forecast is structural: zero new full-payload comparison clones/JSON strings; actual byte savings remain unmeasured until R3 and the unchanged 250ms 8e9 aggregate watchdog remains decisive.
