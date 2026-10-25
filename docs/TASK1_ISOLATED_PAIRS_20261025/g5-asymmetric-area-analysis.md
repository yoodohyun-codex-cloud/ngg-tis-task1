# G5 asymmetric pad areas and explicit comparison baselines

G5 keeps four pads and two floating bipolar outputs, pairs(0,2)/(1,3), original signal electrodes0/1,2000/2010Hz and1Vpp open differential source drive with50ohm total resistance per pair. Total contact area is900mm2; individual areas are200,200,250,250mm2. Shapes and centroids also change relative toB0/G4, so this is a combined geometry candidate, not a pure area-allocation experiment.

G5 completed with targetmean/P10 0.04677610/0.04189720V/m. Its geometry-matched common-ground targetmean is0.06756265V/m; under that common-ground reference's joint8 burden caps, isolated G5 targetmean is18.102percent lower. Source-output count remains2; pad count remains4.

| Candidate relative to reference | Equal sourcepower targetmean change | Reference skin/contact joint8 targetmean change | Joint8 limiting constraint |
|---|---:|---:|---|
| G5 relative to isolated B0 horizontal pairs | -12.461% | -21.766% | contact voltage RMS maximum |
| G5 relative to isolated G4 horizontal pairs | -13.746% | -22.912% | contact voltage RMS maximum |
| G4 vertical pairs relative to isolated G4 horizontal pairs | -6.969% | -23.936% | skin vector current-density RMS maximum |

The last row is the previously reported return-direction comparison. Its-6.97percent and-23.94percent values are not G5 versus common ground. Every row uses its explicitly named reference; the separate geometry-matched common-ground table has different baselines. Equal current means sum of two outputRMS magnitudes as bookkeeping. For G5 at equal current, targetmean changes-12.037percent vsB0 and-13.309percent vsG4horizontal, with sourcepower+0.972percent and+1.015percent respectively. Full electrical values remain in g5-common-budgets.json.

Corrected support-aware regional metrics remain unfavorable: targetmean/central10-15mm mean0.740191; targetmean/same-depth annulusmean1.101921; targetP10/annulusP950.849656. Thus the fourteenth condition also fails the adjacent-depth and robust annular concentration checks. Targetmean/surfaceP95 is0.312269 and targetmean/off-targetP95 is0.540816; mean-denominator ratios are0.466619 and1.020138. These statistics must not be interchanged or interpreted as heat suppression.

The original failed annulus-support artifacts remain preserved. This G5 audit uses direct dyadic XY overlap fractions with exactly zero weights on wholly excluded cells; boundary-cell extrema are native-cell representatives, not physical point hotspots. No new circuitRHS was needed for the regional audit. The12to15mm size comparison elsewhere increases area576to900mm2(+56.25percent); present G5/B0/G4 comparisons keep total900mm2 but redistribute shape and area.

The next bounded validation is motivated by exact symmetry: G6's mask is G5 reflected acrossx=0 with pad permutation0<->2 and1<->3, followed by reversal of both source solutions to retain the positive differential convention. Every mask cell and area matches. In this isotropic layered cylinder with floating pairs this predicts equivalent reflected physical fields, so G6 should not be counted as an independent geometric improvement. This inference does not equate the physically grounded common-ground baselines. The fixed2074direction sampling set is not exactly reflection-closed; re-evaluating transformed G5 fields measures that orientation sensitivity without a new PDE solve. Results remain pending until its terminal receipt; it is not proof of full angular or spatial convergence.

Original common-ground research, source-publication restrictions and previous convergence failures remain unchanged. No physiological, hardware, COMSOL or full mesh validation is claimed.
