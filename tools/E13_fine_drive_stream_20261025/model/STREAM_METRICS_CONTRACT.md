# E13 streamed metrics source contract

This is new source for sole-owner review and later controlled execution. The
source author has not imported it, executed tests, or opened native arrays.
Source/AST checks establish syntax and preservation only; they do not establish
manufactured-test PASS or numerical baseline agreement.

The fixed physical problem remains D50 mm, layers 0.1/5/5/15 mm, four physical
pads, two outputs, common return, 50 ohm and actual 2000/2010 Hz peak phasors.
There are zero new PDE solves, Q matrices, eigensystems, topology or material
changes. The two new relative active-current multipliers are 0.8 and 1.25, with
carrier amplitudes (0.8,1) and (1,0.8). Maximum original high-Z source amplitude
remains 1 Vpp. No physiological, safety, activation or deep-focus claim follows.

## API

```python
evaluate(np, grid, weights, carrier_factory,
         gamma0_by_layer, gamma1_by_layer, electrical,
         a0=1., a1=1., take_rows=None, guard=lambda: None, deadline=None,
         baseline_arrays=None, baseline_summary=None,
         baseline_gate=None, export_maps=True)
```

`grid` is the original Float64 N by 5 native grid, or a compatible lazy adapter:
x/y/depth mm, exact integer layer index 0..3, actual cell volume m3. The current
controller supplies the original full grid. Maximum N is 800000; actual E13
registration is 793848. A lazy adapter must support `len`, `shape`, bounded
`grid[first:last,:]`, and `grid[index,:3]` accesses.

`weights` exposes exactly `total`, `target`, `surface_0_5`, `subsurface_5_10`,
`remaining`, `off_target` through mapping iteration and indexing. Each access
returns the original complete Float64 native volume weights, without analytic
regeneration, clipping or normalization. The controller must use a lazy provider
that does not cache all six arrays. Optional `read_rows(key,first,last)` makes
the initial three-weight identity check bounded as well; without it, at most
three weights coexist briefly before the scalar workspace is allocated.

`carrier_factory()` is repeatable and yields `(first,last,E0,E1)`, with exact
contiguous half-open native indices and C-order complex128 arrays of shape
`(last-first,3)`, at most128 rows. Three-tuples `(first,E0,E1)` are also accepted.
Arrays represent the original unscaled coherent carrier responses. Reader
buffers may be readonly reusable views valid until the next iterator advance;
the evaluator does not retain or mutate them. It allocates a scaled chunk only
for the reduced carrier. No full E vector is created or returned.

`take_rows(indices)` optionally returns the two original carrier arrays in the
requested order for the at most two global/target maximum representatives.
Without it, the evaluator rescans the bounded carrier factory. All original
x/y/z/sampled-winner exact-envelope and 0.1s/8192-sample waveform checks remain.

The electrical input is the small result of the original `synthesize` semantics:
coherent scaling of both output currents, per-carrier signed complex powers
scaled by its own amplitude squared, original contact area ECDF and 50-ohm loss.
Candidate electrical inputs must declare matching `source_Vpp_by_frequency`.
Skin vector J is independently derived from total gamma*E and added by metrics.

## Baseline and metrics gate

Baseline (1,1) must finish before either new condition. The callback
`baseline_arrays(name,first,last)` supplies bounded frozen scalar rows for
AM_max2074, carrier_RMS, Jtotal_vector_RMS and AM_direction_index. These are the
only pixel maps actually saved by the original E13 producer. It must use independent monotonic
forward streams, avoiding reopening and rescanning ZIP members from zero for
each chunk. All three saved Float64 maps gate agreement pointwise; direction first-tie
index differences are explicitly reported as a separate diagnostic.

The five unsaved original pixel maps AM_x/y/z and carrier0/1_RMS are explicitly
listed as unavailable for pointwise QA. Their original summary statistics for
every scope remain required and gated. No generated or reconstructed map is
treated as an original pixel reference. The sole owner authorized this source
scope correction after auditing the producer and before any manufactured test
or native execution; numerical tolerance values remain unchanged.

`baseline_summary` is the complete original E13 JSON-shaped summary. All original
ROI/scalar/electrical/waveform fields are required and checked; additional new
electrical provenance is permitted. All six original scopes, non-SC surface,
SC+dermis skin, and each of four individual layers retain all eight scalar
metrics. The original inverse-volume ECDF includes all sorted cells and uses
`cumulative[-1]`; zero weights and tied representatives retain original
semantics. E13 CV is `std/mean` when mean is positive, otherwise null.

The original source bodies for `directions`, `weighted_stats`, `normalize`,
`_cap`, and the structured electrical scaler are copied byte for byte. There
are exactly26 original lattice directions plus2048 original Fibonacci
directions, in the original order. The angular result remains a sampled lower
bound, with no continuum maximum or omitted-direction finalization.

Tolerances are fixed in source before owner execution:

| Gate | Absolute tolerance | Relative tolerance |
|---|---:|---:|
| Float64 scalar maps and numerical field statistics | 1e-10 | 2e-7 |
| Electrical summary quantities | 1e-15 | 2e-7 |
| Volume quantities | 1e-25 | 1e-12 |
| Native extrema coordinates in mm | 1e-12 | 1e-12 |
| Exact representative waveform identity | 1e-10 | 1e-10 |

Integer counts/indices and all old categorical fields are exact. A full baseline
gate records the native cell count, three complete saved-map passes, complete
direction diagnostic and all original summary physics. A new call requires a
passed gate for the same cell count. A failed or incomplete baseline blocks both
new conditions. No tolerance may be relaxed to match observed results.

`normalize` retains separate same-voltage, same sum-output-RMS-current
bookkeeping, same real-source-power and joint-eight-burden scenarios. Five
linear burdens and three quadratic powers remain distinct. These are baseline
numerical comparison caps, with no simultaneous-equality or safety claim.

## Bounded allocations and outputs

Eight Float64 scalar N-vectors plus one int32 winner vector occupy68*N bytes.
All complete scalar statistics are JSON metadata; no full scalar arrays besides
the two requested maps leave a candidate call. Added layer/skin scopes are
materialized one at a time; there are never six persistent added masks or a
persistent integer layer array. The 128 by2074 angular workspace is released
before sorting/statistics. Conservative stable-sort storage includes both the
index vector and a full N-index workspace.

At N=793848, `allocation_budget()` forecasts the following worst-case live
allocation accounting. This includes a supplied full grid, one resident
original weight, and conservative double counting of a fetched weight during
scope construction.

| Allocation | Bytes |
|---|---:|
| Full supplied grid | 31,753,920 |
| One resident original weight | 6,350,784 |
| Eight scalar vectors and winner | 53,981,664 |
| One scope plus original weight | 12,701,568 |
| Stable sort indices and workspace | 12,701,568 |
| Original weighted_stats scratch bound | 33,341,616 |
| Interpreter, NumPy and allocator margin | 60,000,000 |
| Conservative phase maximum total | 210,831,120 |

The angular+carrier chunk phase is separately bounded at9,000,000 bytes and
does not overlap the statistics scratch phase. The lazy-provider forecast fits
the provisional220,000,000-byte workspace envelope. Keeping all six original
weights with the same runtime margin would forecast242,585,040 bytes and is
explicitly not admitted by that envelope. The owner must measure and enforce
actual aggregate RSS plus **all** task-owned tmpfs in both roots at or below
8,000,000,000 bytes; this source forecast never overrides that hard guard.

Candidate returns contain only `arrays['AM_max2074']` and
`arrays['carrier_RMS']`, each Float64 N. Baseline returns `arrays={}` even if
export_maps is requested. The owner serializes these two maps per new condition,
then releases the result before evaluating the next condition. The four new
maps occupy25,403,136 raw bytes, below the35,000,000-byte provisional output
forecast. This is an estimate, not a storage quota or capacity stopping guard.
Original E/phi remain exact input references plus amplitude weights;
no duplicate E/phi or baseline maps are written.

The owner retains one numerical executor, CPU<=4, finite per-condition
timeouts, watchdog/resource checks and failure evidence. This module neither
launches workers nor changes guards, CPU affinity, threads, files or storage.
