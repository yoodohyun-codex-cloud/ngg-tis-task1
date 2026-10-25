# Prospective column-streamed real-Q operator

This new source is unexecuted and unadmitted. Import is inert and stdlib-only.
NumPy is injected by the existing numerical owner after it sets the current
4-BLAS-thread policy. No native Q file, array, field, test, eigen decomposition
or PDE has been read or executed by the source author. Original retained chunks,
manifests, Q publication receipts, frozen numerical runs, failures and R6 browser
source remain unchanged. There is no resource-budget increase or deletion.

`StreamedRealQ(np, manifest, remote_proofs, input_sha256, guard,
deadline_monotonic=None, cache_name='xy100')` accepts the original real `<f8`,
Fortran-ordered square-Q manifest and the root-authenticated direct retained
chunk proofs at fixed commit `d725ee29ee568ef26a4b7579e9dfc55d23e0681a`.
The existing input provenance helper must first authenticate the normalized and
original publication receipts; this operator performs no network verification
and does not promote historical manifest flags into remote proof.

The intentionally narrow ABI matches frozen `fine_solver.py` and
`coarse_fields.py`: `Q.shape`, `Q.T @ real_values`, `Q @ real_values`,
and `Q[:, first:last]` with explicit contiguous bounds and at most128 columns.
RHS inputs must be finite real float64 ndarrays, one vector or at most16 columns;
their real/imaginary strided views are accepted without a complex-Q conversion.
Rows are capped at8184 (the original fine cache) and chunks at64, so result and
audit metadata limits remain bounded; the original coarse cache has7860 rows.
Scalar/fancy/stepped/whole-array slices, complex/float32/array-like RHS inputs,
left multiplication and implicit or explicit dense conversion fail. Each
operator is single-owner, serial and nonreentrant; BLAS parallelism stays under
the enclosing owner's existing policy. No caller may mutate its RHS during use.

Forward multiplication computes `sum_j(Q_j @ X_j)` in original ordered column
chunks. Transpose multiplication writes each `Q_j.T @ X` into its original
output-column range. A bounded diagonal slice copies only the requested original
columns. The original values, field/circuit equations, modal ordering, contact
model and material parameters are unchanged. Forward reduction grouping changes
floating-point rounding; bitwise equality is not claimed and a cancelling result
is not used as its own relative-error denominator.

At most one original chunk <=32MiB is read into an immutable byte buffer and
viewed as a real Fortran ndarray. The caller and context references are explicitly
released before the next chunk is loaded. No full494MB Q or complex Q is formed.
Slice output is at most n×128 doubles; transform output is at most n×16 doubles.
Finite checks and BLAS work may create bounded small temporaries. These are
structural allocation limits, not a measured RSS guarantee; NumPy/BLAS allocators
and all processes remain subject to the actual unchanged8e9-byte aggregate guard.

Every visit checks canonical nonsymlink path, pinned original inode/stat/size,
exact manifest order, local input SHA and direct remote proof identity. It hashes
the full bytes before numerical use and hashes the actual original file again
after use, with before/after stat and immutable metadata checks. The original
chunk files are never written. Per-chunk counts and the last immutable identity
are retained in a bounded aggregate receipt instead of an unbounded per-matvec
log. A failed after-use verification leaves unmatched before/after counts and
raises; the surrounding owner must preserve the exception and partial evidence.
Receipts describe only this operator's actions, not external PDE/restore counts.
Q matrix entries and cache bytes are storage, not physical3D mesh-cell counts;
this operator creates no physical mesh.

This exchanges resident memory for repeated reads and SHA work. One full
transform reads all494MB original real-Q bytes and hashes them again after use;
complex transforms call the real operator twice. It may be substantially slower
than the original resident matrix. The existing finite execution/time budget is
not increased, and no performance or resource-fit claim is made without actual
measurements. A timeout or RAM blocker must be preserved, not silently retried.

The12 prospective tests use only synthetic6×6 matrices (no more than36 doubles
each). They compare vector/matrix/strided real-imaginary transforms and cross-
chunk slices to a trusted small dense ndarray reference; cancellation errors
are checked against a conservative `32*eps*n*(abs(Q)@abs(X))` absolute-product
bound. They also exercise exact metadata/remote proofs, corruption, stat and
symlink changes, invalid conversions/indices/dtypes, lifecycle and untouched
historical flags. Synthetic fixture files are new and preserved, even on test
failure. Tests require `TASK1_STREAMED_Q_SYNTHETIC_DIR` to be the exact new
MFG run's canonical `OUT/synthetic` directory; no default/native/tmp fallback is
permitted. The source author only parsed their AST and did not run them.

Root must publish source and run those manufactured/operator tests first under
its existing authenticated owner. Afterward it must separately restore a cached
native B0 response through this operator, comparing modal coefficients, carrier
fields, currents/power, unchanged physical gates and full original data identity
against the existing resident-Q calculation before any new PDE candidate. The
native restore is prospective and absent here. Tiny tests or roundoff agreement
do not establish new continuum/MMS convergence, physiological activation,
experimental validation, safety or candidate adoption.
