# Two local TIS assignments — Windows execution remains conditional

Fixed source commit: `6694e1a2931c149d0cb62ba5098e858464d75318`. The cloud calculation owner and its CPU4/8,000,000,000-byte limits remain unchanged.

| Candidate | Run ID | Canonical configuration SHA256 |
|---|---|---|
| LOCAL14-c9-diagonal | task1-local-L14-c9-20261025 | f3a56046aa93f9413a531b045387559501be861002cfab4b607e2f2e7d6f2720 |
| LOCAL16-c8p5-diagonal | task1-local-L16-c8p5-20261025 | 43175402aedcd4395057ecc32fa1d0fe363fd090b9d5d8a0d4771efab1366126 |

Both cases use D50mm/layers0.1/5/5/15mm, four top pads/two independent outputs/common return, one50ohm per output,1Vpp high-Z sine drives at2000/2010Hz. Each case requires exactly two NEW driven RHS. This handoff solved no PDE and read no Q/NPZ/raw-field bytes.

Status: `assigned_waiting_adapter_and_lease`; lease/PID/CreationTime remain null and execution is false. The separate Windows owner/Job/local-lock adapter, fresh RAM/commit check and a remotely read-back central CAS lease are required before any local study starts. Runtime/Job tests are not PDE or8-core speedup validation.

Use `transfer-manifest.json` with the existing safe receiver; it downloads SHA-addressed objects. `layout-mapping.json` is a separate reviewed layout-copy plan and never extracts, installs, executes, overwrites or auto-starts anything. The original input manifest’s new ROI source reference is resolved to the fixed source commit by this outer transfer manifest. Prepared public spec contains only safe relative paths; the Windows owner regenerates its private deployment paths and checks canonical/mask hashes.

The registry at `docs/TASK1_LOCAL_HANDOFF_20261025/candidate-ownership.json` is authoritative; historical source-only protocol templates retain their old placeholder runtime path. A stale heartbeat or elapsed TTL alone does not transfer ownership. No Windows save/OneDrive completion, convergence, experimental validation, activation or safety claim is made.
