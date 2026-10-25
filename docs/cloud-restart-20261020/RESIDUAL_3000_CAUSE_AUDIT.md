# 3000 Hz residual diagnostic: cause assessment and next-step scope

The new diagnostic supports continuing a finite **unadopted coarse geometry comparison**. It does not resolve the failed historical componentwise reproduction gate. The evidence points to iterative numerical sensitivity in the same intended finite-volume circuit; it does not yet identify a unique cause for every historical difference.

The diagnostic run is `cloud-residual-20261020T001300Z`. Its elapsed controller time was 67.235153824 s. This audit reads existing receipts, matrices and frozen sources; it executes no PDE and changes no earlier receipt.

## What the new experiment established

The default-tolerance new producer reproduced all five cached coarse arrays **byte for byte after lossless decompression**: E, phi, contact density, source and loss. Grid and contact row bytes also matched. Thus the residual wrapper preserves the original default numerical calculation for this tested coarse case. This is a producer regression, not independent solver validation.

On the held fine grid (XY 50/120 mm, SC2, bulk 14/14/40), both tighter solves used 979 iterations. Recomputed relative residuals were 3.6453043971430534e-12 and 3.6447294155660225e-12. The previous fine run printed 9.32e-10 at 3000 Hz. Its source reciprocity defect fell from 4.163852013669081e-12 A to 1.957105896651555e-15 A. The imaginary cross terms of the layer losses also moved from numerical asymmetries near 1e-13 W toward 1e-17 W. Current conservation, Hermitian positive loss matrices and fixed complex-coefficient power checks passed.

However, a reciprocal matrix can retain a shared symmetric error. Tighter solves moved both source cross terms together, away from the historical values. Improved reciprocity therefore cannot certify historical accuracy.

| Comparison | Observed maximum change | Result under the original componentwise gate |
|---|---:|---|
| Tight vs historical source | 4.5812512761299784e-12 A; global relative maximum 2.5348847265438033e-9 | Failed: four real/imaginary components |
| Tight vs historical loss | 2.762954998797827e-13 W; global relative maximum 9.477708407927134e-10 | Failed: two muscle diagonal real components |
| Tight vs prior fine E | 3.089198680239491e-5 V/m; global relative maximum 2.3046156440496943e-8 | Sensitivity diagnostic, not a candidate acceptance gate |
| Tight vs prior fine phi | 3.6993424816500475e-9 V; global relative maximum 8.956882440149965e-9 | Sensitivity diagnostic |
| Tight vs prior fine contact density | 3.4712670071712637e-7 A/m²; global relative maximum 1.3816335816955982e-8 | Sensitivity diagnostic |

The source failure includes two imaginary cross terms with approximately 4.57–4.58 pA differences and two real cross terms with approximately 3.01–3.04 pA differences. The remaining historical loss failures are muscle diagonal differences of 2.2311149205000904e-13 W and 2.2360366562620883e-13 W. Every failed entry remains in the new comparison receipt. The criterion stays `abs(new_i-old_i) <= 1e-14 + 1e-8*abs(old_i)` for each Float64 real/imaginary component. A global norm passing is a separate observation and does not change this failed verdict or the original D failed receipt.

## Actual historical producer and model comparison

The historical case `coat010-f0500-minusRs` records producer `private_RsWindowTisBasis`, source SHA `f8047bfb6243123619acb8e9f127d3430b84dda15288f7aac55a9fb16eed7d1e`. That matches the packaged `tis-java/RsWindowTisBasis.java`. Its main method constructs `ValidationMesh` and `ExploreBasis.GNet` (lines 285–298). The released source/loss 3000 Hz hashes match that historical case's output manifest; they are not a newly manufactured reference.

The old `RsWindowTisBasis.ValidationMesh` (lines 212–235) and new `SelectivityShapeBasis.ValidationMesh` (160–183) use the same coordinates, layer thicknesses and counts for this case. `ExploreBasis.GNet` bulk conductances (27–31), contact impedance plus half-SC impedance (33–38), physical-pad node mapping, 50-ohm terminations and loss equations (44–67) agree with `SelectivityShapeBasis.ShapeNet` (194–207, 240–263). Both original producers inherit the same COCG arithmetic with 1e-9 stopping and 12000 iterations from `TisSweep.Net.solve` (73–82).

There are numerical implementation differences:

- GNet interleaves contacts with the bulk cell loop. ShapeNet builds all bulk edges and then contacts from the physical mask. This changes diagonal addition, matrix-vector reduction and loss accumulation order.
- GNet calculates rectangle overlap in metres. The new canonical full-face mask changes contact areas by at most 1.2656542480726785e-14 relative in the existing audit. All 5184 `(pad,i,j)` faces match and no old cutoff-discarded faces occur in this Best1 case.
- The old field exporter averages contact E over overlap area; the new exporter averages over the whole cell face. Here every contact is a full face to roundoff, so this is not a source/loss circuit discrepancy. Generic fractional contacts must retain this separate measurement definition.

No substantive physical source/loss model difference was found in this exact full-face case. These static observations do not prove that floating-point order is the unique cause. Old full native phi/E arrays are missing, so their residuals, full-field errors and goal-oriented error estimates cannot be reconstructed from the released matrices alone.

## Practical uncertainty and permission to continue research

The measured changes are an **observed sensitivity scale**, not a rigorous universal error floor or an upper bound. They apply to this one geometry, grid and 3000 Hz operator. They do not establish the error of ROI P10 near zero, other geometries, other carriers, harmonics, edge peaks, contact hypotheses or continuum extrapolation.

A fixed 1% candidate comparison margin is over 400000 times the observed fine E global relative change. It is reasonable to use that as a coarse screening margin while keeping every new geometry unadopted. Coarse comparisons must use the same current producer, physics, circuit, measurement definitions and matched coarse baseline. Each case must pass its own native/current/area/power gates. A difference below the screening margin does not establish a ranking. A larger difference only nominates a candidate for its own solver, grid, edge and contact sensitivity checks; it does not bypass them.

This separates two scientific questions: whether the old strict componentwise result has been reproduced, and whether the current controlled model can screen electrode geometries with practically separated effects. The first remains failed/held. The second can proceed as a finite reconstruction batch without claiming adoption, deep-focus feasibility, activation, human safety or experimental validation.

## Bounded route to stronger causal evidence

If further numerical diagnosis is needed, first preregister a no-solve readback of the existing fine vectors. Recover the two terminal potentials from `S_ca = .01*delta_ca - .02*x_a(port_c)`, then apply the frozen GNet and ShapeNet operators to the same existing vectors. Record coefficient/order differences, residual vectors and contact-area perturbations. For a complex symmetric operator, the existing two tight basis vectors can also evaluate a port error identity using a transpose (not conjugate transpose): with `r_a=A*x_a-b_a` and `b_c=.01*e_c`, the approximate source error from a residual is `-2*x_c^T*r_a`, with the nonzero tight residual correction explicitly retained. This requires matrix application and readback, not a new PDE solve.

That audit should have an explicit one-CPU deadline, existing global locks, source/input pins and cumulative budget charge. It cannot recover the missing historical full vectors. If strict historical closure is still necessary afterward, a separately guarded, preregistered 3000 Hz GNet reproduction is the direct comparison to consider. Neither action is executed or promised by this audit.

Evidence: the sibling `residual-3000-cause-audit-20261020.json` pins the raw diagnostic summaries, comparisons, original failed receipt, historical case/config and relevant source files. Existing originals and all failure evidence remain unchanged.
