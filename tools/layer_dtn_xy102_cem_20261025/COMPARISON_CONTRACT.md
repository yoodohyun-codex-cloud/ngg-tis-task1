# XY100 versus XY102 continuous-z CEM comparison

Source-only; agents executed no geometry, arrays, tests or solves. Root runs the
new reference condition, saves its outputs, then invokes the comparison so a
postprocessing error never causes a reference RHS repeat.

`required_inputs()` returns exact published coarse reference-array/summary
hashes plus fine phase1/cache/admission/input declarations. No coarse Q is
loaded. `build(fine_result,fine_spec,guard,deadline_monotonic=None)` returns
`{summary,arrays}` with no file writes. Existing source is unchanged.

The two XY grids have different nodes and different whole-square staircase
domains. Sparse exact square intersections, in physical millimetres, define the
common represented area. Primary L2 sums each coarse/fine field difference on
every intersection. A separate conservative fine-to-coarse average is secondary
because averaging can hide within-cell variation. Both domains' unmatched
boundary areas remain explicit. There is no node-index subtraction or gauge fit.

All/interior r<=23.75mm/periphery common-area interface comparisons use analytic
disk/rectangle intersections to clip the overlap rectangles. This is version2
physical-area quadrature, separate from previous centre-selected face masks.
The r<=5mm,z15–20mm potential comparison uses the same analytic areas and exact
z overlap. Its muscle56 planes already match on both references, so no coarse
97-plane reconstruction or Q reload is necessary. Differing SC8/SC4 sampling is
outside this ROI; no global-SC potential delta is computed. Previous128²target
masks and outputs remain unchanged. New norms compare cellconstant
reconstructions, not exact continuously integrated3D fields.

The physical pad rectangles remain225mm² each. Every contact patch is checked
against cell/rectangle clipping without area renormalization. A fixed0.5mm
physical pad-edge ring, not an index-dependent edge row, gives edge-weighted
Jmax/J95 and loss. Aggregate and per-patch area errors use1e-10 relative bound.
Current fields are contact-normal temporal carrier RMS; skin vector J is not
invented when E is absent. Powers are real time-average W. Output-current sums
are bookkeeping, not net common-ground current.

Available contactJmax/J95/contactV screens remain5%; real power screens remain2%.
Prospective edge-strip Jmax/J95 use5%, edge loss2%. They are engineering review
screens, not safety limits or automatic adoption. Old targetEmean/P10 gates are
explicitly not evaluated because reference E is not exported.

Old native and coarse-reference sampled2/2 and3/3 five-percent flags are retained
verbatim. FineSC4/97-plane sampled flags are reported separately from old
SC8/101-plane flags, without a like-sample delta or cherry-picking. The
conditional continuous-z reference still depends on the staircase XY graph,
eigen/solver tolerance, surrogate materials and contact model. No E/TIS,
physiology, safety, experiment or candidate-convergence claim follows.
