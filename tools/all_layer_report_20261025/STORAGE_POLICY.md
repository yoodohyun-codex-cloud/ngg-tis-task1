# Active storage policy — 2026-10-25

The user explicitly removed storage-capacity stopping guards and confirmed that the reported storage of at least 1 TB is the previously configured private Windows C: destination. This instruction supersedes historical storage quotas and free-space reserves for active continuations and subsequent authorized batches. Historical registrations and failure evidence remain immutable.

The active SC4 postprocessing/publication continuation and the report/Windows exporter have no minimum-free-disk or per-run-output quota checks. The former 2 GiB root reserve, 768 MiB native-run cap, 128 MiB report cap, temporary-ledger free-space preflight, and Windows download free-space rejection are disabled. Actual OS write failures still produce failure/partial evidence; they are not successful saves.

CPU, memory, time, single-owner locks, source/input hashes, exact format decoding and transport/provider constraints remain unchanged. In particular, tmpfs consumes RAM and still counts toward the original 3 GiB RSS plus all owned tmpfs memory limit. This is a memory condition, not a storage-capacity guard.

The observed cloud root filesystem has 33,770,192,896 total bytes. Windows C: is not mounted or remotely connected. The user's reported capacity is not a measured cloud capacity and this policy does not establish actual Windows storage or OneDrive synchronization. The full destination is kept in private runtime configuration and is not published.

Canonical operational policy: `runtime/task1-storage-policy.json`. A sanitized immutable copy is published with the continuation/report source. Future registrations must apply this user override rather than silently reinstate the historical storage limits. CPU/time budget expansion was not requested by this storage change.
