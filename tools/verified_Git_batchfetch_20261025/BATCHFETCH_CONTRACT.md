# Fresh-verifier batch blob prefetch, source only

This unique publisher copy preserves the original frozen r3 source at
`/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py`, SHA256
`e29f03472c430598d9b7599eee28416b3453653b977a00c3d1999fa363f75f45`.
The new source is `source/git_publish_verified.py`. `source-delta.json` records
both byte identities. Authors have only read source, written this copy and
parsed its AST. No publisher, Git, network, research helper, test or native work
has run as part of preparation.

The original Git wrapper already accepts `body=None` and forwards it to the
existing bounded command's stdin. That wrapper is unchanged. After the fresh
second remote object database has authenticated the exact commit, parent, tree,
branch ancestry and no alternates, the copy validates every selected tree entry
and every unique full40hex blob ID. It then sends the sorted unique IDs as one
newline-delimited stdin body to `git fetch --no-tags --stdin origin`, inside
that same fresh verifier. No writer objects or local alternates are used.

Every original per-file tree-entry check and complete `cat-file` byte count and
SHA256 check still runs. The batch request is an optimization, never publication
proof. A small attempt-local `batch-prefetch-<attempt>.json` records the unique
blob count, want-list SHA256, exit code and fallback decision without credentials
or raw stderr. The same metadata is included in the attempt receipt.

Only a rejected stdin option or unsupported unadvertised blob request permits
the original per-file remote promisor fetch behavior. Other errors, including
authentication/network failures, preserve failure evidence and abort. Existing
command failure logs remain under the original bounded logging policy. Even an
allowed fallback cannot bypass any file/tree/parent/readback proof.

CAP remains300seconds, publication files remain at most80MiB, command output
bounds, CPU/RAM guards, authentication/TLS/credential transport, explicit-parent
CAS, one-commit/push rules, fresh second database, full plan/source hashes,
queue-parent identity/dual locks, retry restrictions and all optional-comment
semantics remain unchanged. This source cannot resume an old differently hashed
publisher output: the original same-plan/same-source resume guard remains.
Controllers must register this exact new publisher path and SHA before use.

The runtime optimization has not been measured by its source author. Root's
separate completed GUI5 readback recovery supplies prior evidence that a single
blob request can avoid repeated lazy-fetch latency; it is not a pass result for
this new publisher copy. Root alone may execute a future registered publication
after independent source review and the normal resource checks.
