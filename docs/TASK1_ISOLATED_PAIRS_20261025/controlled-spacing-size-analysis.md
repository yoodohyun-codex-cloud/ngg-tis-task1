# Controlled spacing and size comparisons

Four physical pads, two floating bipolar outputs; original signal roles retained. Same 2000/2010Hz, 1Vpp differential open-circuit drive and50ohm total series resistance per pair, including inactive-frequency termination. Target r<=5mm and depth15-20mm. All quantities below are model electrical proxies.

The common cross-geometry budget reference here is isolated G1:12mm squares centered at coordinate magnitudes10mm, targetmean0.0352442153 andP10 0.0317449616V/m. This differs from the geometry-specific common-ground reference used in the topology tables.

| Change | Budget fixed to isolated G1 | Target mean V/m | Target P10 V/m | Mean change | Source real power change |
|---|---|---:|---:|---:|---:|
| spacing only:12mm,c10 to c11.5 | same_source_voltage | 0.03704667 | 0.03355702 | +5.114% | +0.185% |
| spacing only:12mm,c10 to c11.5 | same_sum_output_RMS_current_bookkeeping | 0.03705461 | 0.03356422 | +5.137% | +0.228% |
| spacing only:12mm,c10 to c11.5 | same_source_real_power | 0.03701238 | 0.03352597 | +5.017% | +0.000% |
| spacing only:12mm,c10 to c11.5 | joint_eight_surface_contact_burden_caps | 0.03703570 | 0.03354709 | +5.083% | +0.126% |
| spacing only:12mm,c10 to c11.5 | joint_four_skin_only_caps | 0.03703570 | 0.03354709 | +5.083% | +0.126% |
| size only:c10,12mm to15mm | same_source_voltage | 0.05382289 | 0.04859414 | +52.714% | +57.061% |
| size only:c10,12mm to15mm | same_sum_output_RMS_current_bookkeeping | 0.03448154 | 0.03113175 | -2.164% | -35.537% |
| size only:c10,12mm to15mm | same_source_real_power | 0.04294695 | 0.03877476 | +21.855% | +0.000% |
| size only:c10,12mm to15mm | joint_eight_surface_contact_burden_caps | 0.04304192 | 0.03886051 | +22.125% | +0.443% |
| size only:c10,12mm to15mm | joint_four_skin_only_caps | 0.04304192 | 0.03886051 | +22.125% | +0.443% |

Spacing: moving12mm pads fromc10 toc11.5 raises targetmean about5percent under every listed budget, with total contact area fixed576mm2. Targetmean/surfaceP95 rises.410156to.481851 and targetmean/off-targetP95 rises.597105to.640933. Mean-denominator ratios rise.595536to.624341(surface) and1.126560to1.150188(off-target). These are specific to this modeled layout and unchanged discretization.

Size: increasing12to15mm atc10 raises total contact area576to900mm2(+56.25percent). Same-voltage mean gain52.714percent comes with57.061percent more source power. At equal sum-output RMS current, mean instead falls2.164percent; at equal sourcepower it rises21.855percent. Thus the result depends on which resource is held fixed. Targetmean/surfaceP95 worsens.410156to.387619, and off-targetP95 .597105to.577713; mean-denominator ratios also fall(surface.595536to.480193;off-target1.126560to1.019933). Increased target amplitude is not improved selectivity.

Current is the sum of two output RMS magnitudes as bookkeeping, not independent equality of each output. Five contact/skin density or voltage caps plus three integrated loss-power caps define joint8; skin-only uses skinJmax/P95 and SC/skin loss power. These are numerical reference caps, not human safety limits. Larger area is explicitly retained, not normalized away: density limits alone would overlook integrated power. Full electrical values and scales are in the companion JSON.

B0 absolute targetmean/P10 .0538228942/.0485941428V/m remains below its matched common-ground reference at1Vpp; under its own matched joint8 caps targetmean is15.159percent lower. The isolated-family spacing benefit does not establish an isolation advantage over common ground or achievement of the original deep-concentration objective.

Next bounded test: G3 same16mm pads as existing LOCAL16, move centersc8.5toc9.5. This tests whether the beneficial12mm spacing trend also holds at larger area, where the fixed-center size test revealed an amplitude/selectivity tradeoff. Four pads and two outputs remain unchanged.

Limitations: sampled2074direction maxTIS, unchanged XY/contact discretization and material surrogate; prior convergence failures retained. Depth quadrature stability is not full mesh convergence. No physiological/hardware/COMSOL validation, no heating or safety conclusion from modulation suppression.
