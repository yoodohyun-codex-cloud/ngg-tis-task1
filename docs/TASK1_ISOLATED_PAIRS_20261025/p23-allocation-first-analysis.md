# First fixed-power allocation result on isolated P23.5

This is a drive-allocation comparison against balanced isolated P23.5 original pairs(0,2)/(1,3), not against common ground. Four pads, two floating voltage outputs, total area900mm2,2000/2010Hz and50ohm total source resistance per pair remain unchanged. Inactive-frequency finite impedance remains in the cached linear solutions.

The sourceVpp values0.816224570 and1.154315856 keep total source real power at1.728322400e-6W, identical to balanced1Vpp/1Vpp. The ratioVpp2000/Vpp2010 is sqrt(.5). Linear reconstruction of unscaled source/contact/skin quantities reproduced the original results before this evaluation.

| Budget relative to balanced isolated P23.5 | Target mean V/m | Target P10 V/m | Mean change | P10 change | Source power change |
|---|---:|---:|---:|---:|---:|
| Equal total source real power |0.05015386|0.04421146|-12.699%|-16.395%|0%|
| Equal sum of two outputRMS current magnitudes |0.05088487|0.04485586|-11.427%|-15.176%|+2.936%|
| Joint eight skin/contact reference caps |0.04344899|0.03830101|-24.370%|-27.572%|-24.950%|

The joint cap is limited by contact-normal current-density RMS maximum. These numerical-reference caps are not physiological safety thresholds. Equal-current bookkeeping is separate from equal power, and neither implies independently equal currents in both outputs.

Corrected regional support gives targetmean/central10-15mm mean0.819327, worse than balanced0.837594. TargetP10/same-depth annulusP95 is0.731066, worse than0.868528. Global amplitude rescaling does not change those ratios. The result therefore does not achieve15-20mm volume concentration; emphasizing one channel worsens both the absolute target statistics and these regional comparisons.

One reciprocal control is next: Vpp2000/Vpp2010=sqrt(2), again normalized to the same total real source power. The two carrier frequencies have different material/contact responses, so reciprocal allocations are not assumed exactly equal. This tests directionality without a new PDE or an unlimited ratio sweep. Results remain pending until its terminal receipt.

The completed first allocation used cached linear bases and zero new circuitRHS; it is an additional allocation condition, not a new independently solved layout. Existing14layout negative concentration evidence and original failed-support artifacts remain preserved. Corrected support weights are reused. The earlier reflection sensitivity result is not full angular convergence; neither this allocation nor that test establishes full spatial convergence, physiology, hardware or COMSOL validation.
