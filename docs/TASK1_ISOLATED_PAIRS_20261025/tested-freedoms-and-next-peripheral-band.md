# Reciprocal allocation results and next design freedom

Both fixed-power allocations completed. Their common baseline is balanced isolated P23.5 at1Vpp/1Vpp, pairs(0,2)/(1,3),900mm2 contact area and total source real power1.728322400e-6W. This is not a comparison with common ground.

| Allocation Vpp2000/Vpp2010 | Mean/P10 at fixed power V/m | Mean/P10 change | Joint8 mean/P10 change | Targetmean/adjacent10-15mean | TargetP10/annulusP95 |
|---|---|---|---|---:|---:|
| Balanced1/1 |.05744947/.05288116|reference|reference|.837594|.868528|
| .816224570/1.154315856 |.05015386/.04421146|-12.699%/-16.395%|-24.370%/-27.572%|.819327|.731066|
|1.155085605/.816768864 |.05038097/.04441518|-12.304%/-16.009%|-23.974%/-27.187%|.819606|.734502|

The reciprocal test is slightly different from the first; it is not an exact equality assumption. Both are worse than balanced drive under fixed power, equal sum-outputRMS current and joint skin/contact budgets. At equal-current bookkeeping the reciprocal targetmean/P10 changes-11.019%/-14.779% while sourcepower increases2.951%. Its joint cap is contact-voltage RMS maximum; the first allocation is limited by contact-normal current-density RMS maximum. The two frequencies have distinct material/contact responses and the calculation retains their labels. The observed asymmetry is not attributed to one cause without further decomposition.

Corrected geometric-support weights are used throughout. Adjacent-depth and robust annular ratios remain below1 in both directions. Thus neither tested redistribution achieves15-20mm volume concentration. The earlier reflection test measured only one angular-sampling covariance sensitivity and did not establish full angular or mesh convergence.

## What has and has not been tested

Fourteen independently solved equal-drive isolated conditions cover selected square sizes and spacings, one peripheral polyomino, equal-area rectangles, one asymmetric-area layout, two original-role return pairings and selected role-changing diagonal pairings. Controlled12mm and16mm outward-spacing comparisons improved some amplitude and P95 selectivity measures, but all corrected regional concentration checks failed. The12to15mm size comparison increased area576to900mm2(+56.25%) and showed an amplitude/selectivity tradeoff. The G4 return comparison's-6.97% and-23.94% are specifically vertical relative to horizontal G4 at equalpower and joint8caps; they are not P23 or common-ground differences.

Only the listed cases and two allocation ratios are completed; no continuous design freedom is globally exhausted. The exact G5/G6 reflection-equivalent geometry need not be counted as an independent improvement. Peripheral radial contact width, other connected shapes/positions, finer nearby ratios and spatial/contact discretization remain untested. Ideal-current sources and real transformer circuits are separate model factors and have not replaced the voltage-source baseline. Sidewall or penetrating electrodes, phantom changes and physiological claims are not introduced.

## Next finite comparison

P23.5 had the best observed original-role target/adjacent-depth mean ratio among the completed layouts, but its ratio was still below1. The next candidate removes inner radial contact faces: four connected top-surface patches built from all0.5mm full squares lying wholly between radii21 and23.5mm, with at least1mm axis-face clearance. Exact integer corner tests establish containment, disjointness and four-neighbor connectivity. Each patch has245cells and61.25mm2; total area is245mm2, versus900mm2 for P23.5. The patches are pixelated unions, not smooth ideal annular sectors.

This tests peripheral band width and footprint, with area changing explicitly. It is not a pure placement-only comparison and cannot claim concentration by raising current density or ignoring lost area. The old failed P24 recipe is neither used nor repaired. The phantom,layers,top contact model,ROI,frequencies and793860-cell graph are unchanged.

One finite worker computes the new geometry's own common-ground control first, then floating pairs(0,2)/(1,3), with2operatingRHS and1reciprocityRHS per topology. This new matched control belongs only to this isolated-research package; it does not alter or replace the original common-ground worker. Both use four pads,two outputs,1Vpp sources and50ohm total source resistance per output/pair. The isolated gauge is distinct from physical common ground. Corrected adjacent-depth/annular metrics and geometry-specific current,power,skin/contact normalization will be evaluated before comparison to P23.5 budgets. Results remain pending until terminal artifacts exist.

Original failed metrics and convergence evidence are preserved. ExistingCPU8/RAM4GB,cell ceiling,shared single-worker slot and finite watchdog remain. No full spatial convergence,physiological validation,hardware stimulation or COMSOL execution is claimed.
