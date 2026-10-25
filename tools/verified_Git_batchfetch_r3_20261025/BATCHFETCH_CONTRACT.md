# Fresh empty remote verifier, source-only R3

This unique copy changes only the second verifier's initialization relative to
frozen publisher R2, SHA91b18f079c87227878b18e9fddc424cc96d99dc153d918076883cc88ae5c0f4b.
The second repository is still a new, independent bare object database at a
previously absent attempt-specific path. Instead of `clone --bare`, it is created
with `git init --bare`, followed by `remote add origin` using the same fixed URL.
All objects still arrive only through the subsequent remote exact-commit fetch
and the explicit unfiltered batch blob fetch. The original writer setup,
commit/push/CAS behavior is unchanged.

The no-alternates check, exact fetched commit, parent/tree/branch-ancestry proof,
validated unique full40hex wanted blobs, `--no-filter` on the one batch request,
unsupported-only fallback and every per-file full SHA256/byte-count proof remain
unchanged. So do CAP300, resource/command/output bounds, source/plan/parent/queue
authentication, TLS/credential handling, retry restrictions and optional comments.
Only the fresh verifier's local repository initialization changes. There is no
global Git, credential or security configuration change.

Root reported a real61-blob full readback pass with fresh init/remote-add/exact
fetch plus unfiltered wants, and a real matching clone-based failure even with
`--no-filter`. R2 is therefore not a sufficient fix. The source author did not
run those tests or receive their receipt descriptors; a specific root cause is
not established here. Both earlier publishers and all failures remain evidence.
The prior R2 source is copied byte-exactly under `previous-source-evidence/`.

`source-delta.json` records old/new source identities and the exact one-line
replacement. Source preparation used only source reads/writes, SHA and AST
parsing. No Git/network, publisher, import/test, native input, process or lock
operation was executed. A future Root controller must register and source-publish
this exact new code and evidence before its own finite publication. Runtime
success still requires actual complete remote readback; this document is not a
runtime or performance receipt.
