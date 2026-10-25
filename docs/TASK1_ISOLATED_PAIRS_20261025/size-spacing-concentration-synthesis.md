# Size, spacing and direct regional concentration

All eleven completed isolated conditions fail this diagnostic of a15-20mm depth maximum: the target volume mean is lower than the same-radius10-15mm volume mean. The same-depth annulus has only slightly lower mean, and targetP10 remains below annulusP95 in every condition. This establishes a limitation of these sampled electrical results, not an impossibility theorem or physiological conclusion.

Four physical pads, two floating sources,2000/2010Hz. Targetr<=5mm,z15-20mm retained. Adjacent central cylinders have identical radius and5mm depth; the annulus5<r<=sqrt(50)mm,z15-20mm has the same analytic volume. Actual fractional volumes are reported without renormalization. Nativecellconstant maxTIS uses the existing2074direction samples.

| Case and pairs | Target mean V/m | Target P10 V/m | Target mean / central10-15mean | Target mean / annulus mean | Target P10 / annulus P95 |
|---|---:|---:|---:|---:|---:|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | 0.04504655 | 0.04045349 | 0.746999 | 1.096614 | 0.847095 |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | 0.04504606 | 0.04045745 | 0.746986 | 1.096658 | 0.846995 |
| LOCAL14-c9-diagonal [[0, 1], [2, 3]] | 0.04853008 | 0.04400874 | 0.720344 | 1.025128 | 0.822650 |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | 0.05594475 | 0.05026891 | 0.738487 | 1.092961 | 0.846773 |
| LOCAL16-c8p5-diagonal [[0, 1], [2, 3]] | 0.05988156 | 0.05424671 | 0.715884 | 1.027718 | 0.823753 |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | 0.05744947 | 0.05288116 | 0.837594 | 1.075299 | 0.868528 |
| P23p5-peripheral-polyomino225 [[0, 1], [2, 3]] | 0.06151081 | 0.05768179 | 0.821372 | 1.011935 | 0.871824 |
| P12-square-c11p5-diagonal [[0, 2], [1, 3]] | 0.03704667 | 0.03355702 | 0.803395 | 1.095899 | 0.856017 |
| G1-square12-c10-diagonal [[0, 2], [1, 3]] | 0.03524422 | 0.03174496 | 0.770614 | 1.098258 | 0.850141 |
| B0-square15-c10-diagonal [[0, 2], [1, 3]] | 0.05382289 | 0.04859414 | 0.770137 | 1.094408 | 0.852673 |
| G3-square16-c9p5-diagonal [[0, 2], [1, 3]] | 0.05926703 | 0.05346973 | 0.759861 | 1.093065 | 0.851556 |

Controlled spacing:12mm,c10 to c11.5 gives equal-source-power mean+5.017percent and surfaceP95ratio+17.480percent;16mm,c8.5 to c9.5 gives equal-power mean+5.832percent and surfaceP95ratio .308556to.354668. At16mm equalcurrentmean+5.964percent costs+.251percent sourcepower; common skin/contactcapmean+5.899percent costs+.127percent power. Total area remains576mm2 and1024mm2 respectively. These improvements do not create a target depth maximum.

Controlled size atc10,12to15mm: area576to900mm2(+56.25percent); mean+21.855percent at equalpower but-2.164percent at equalcurrent. SurfaceP95 selectivity worsens.410156to.387619. Thus larger area improves some amplitude budgets while reducing selectivity.

G3 absolute mean/P10 .05926703/.05346973V/m still loses targetmean15.074percent under its own geometry-matched common-ground joint8caps. Geometry-specific common-ground contrasts and common isolated-family budgets are distinct comparisons. Current means sum of outputRMS magnitudes bookkeeping. Skin/contact caps are numerical reference values, not safety thresholds. Modulation suppression is not carrierRMS or heat suppression.

Validation scope:zero new circuitRHS, existing raw scalar/source hashes pinned, exact target mean/P10/P95 reproduction within1e-10relative. Annulus boundary subcells128vs256 change its mean by less than0.000010percent; this is only overlap-weight sensitivity, not field or mesh convergence. CarrierRMS regional statistics are separately retained. No common-ground regional scalar reconstruction was performed; original aggregate common-ground baselines remain separate. Old convergence failures preserved; no COMSOL/hardware/physiology validation.

Next:G4 equal-area12.5x18mm rectangles probe anisotropic spatial distribution at225mm2/pad(900total), with original signal roles. Compared withB0 the centroids also move from±10,±10 to±9.75,±9.5mm, so this is explicitly a combined shape/position candidate, not a shape-only causal contrast. Its exact common-ground baseline is retained. Ranking will include target-versus-adjacent-depth and same-depth-annulus metrics under common current,power,skin/contact budgets.
