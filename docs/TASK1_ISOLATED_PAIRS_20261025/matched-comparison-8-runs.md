# Floating-pair matched comparisons

Every case uses FOUR physical pads and TWO independent source outputs, not four independent outputs. Effective positive/negative pad and frequency mappings are given by the explicit two pairs; diagonal conditions change original signal roles. Reference pad-name strings retained in old config metadata do not override circuit pairs.

All fields below are the original2074-direction sampled maxTIS (V/m), using the same volume ROI r<=5mm,z15–20mm. Surface is0–5mm includingSC; off-target is total minus fractional target. Source1Vpp is open-circuit differential amplitude; total resistance50ohm per pair. Inactive pair remains terminated.

These are provisional electrical comparisons; no deep-focus or physiological validation. P95-denominator improvements must not be described as increased target mean/P10.

| Case / pairs | Reference mean / P10 | Isolated1Vpp mean / P10 | Joint8 mean change / P10 change |
|---|---:|---:|---:|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | 0.06496335 / 0.05851064 | 0.04504655 / 0.04045349 | -15.102% / -15.350% |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | 0.06496335 / 0.05851064 | 0.04504606 / 0.04045745 | -15.102% / -15.342% |
| LOCAL14-c9-diagonal [[0, 1], [2, 3]] | 0.06496335 / 0.05851064 | 0.04853008 / 0.04400874 | -8.546% / -7.920% |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | 0.08054280 / 0.07252454 | 0.05594475 / 0.05026891 | -14.966% / -15.146% |
| LOCAL16-c8p5-diagonal [[0, 1], [2, 3]] | 0.08054280 / 0.07252454 | 0.05988156 / 0.05424671 | -9.002% / -8.451% |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | 0.08275756 / 0.07667868 | 0.05744947 / 0.05288116 | -15.014% / -15.570% |
| P23p5-peripheral-polyomino225 [[0, 1], [2, 3]] | 0.08275756 / 0.07667868 | 0.06151081 / 0.05768179 | -9.015% / -7.915% |
| P12-square-c11p5-diagonal [[0, 2], [1, 3]] | 0.05359291 / 0.04892025 | 0.03704667 / 0.03355702 | -15.358% / -16.008% |

## Explicit denominators

| Case / pairs | Mean/surface mean (ref → isolated) | Mean/surfaceP95 | Mean/off-target mean | Mean/off-targetP95 |
|---|---:|---:|---:|---:|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | 0.003227 → 0.491518 | 0.309412 → 0.343819 | 0.015910 → 1.029322 | 0.442338 → 0.547647 |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | 0.003227 → 0.491511 | 0.309412 → 0.343748 | 0.015910 → 1.029309 | 0.442338 → 0.547647 |
| LOCAL14-c9-diagonal [[0, 1], [2, 3]] | 0.003227 → 0.366968 | 0.309412 → 0.239928 | 0.015910 → 0.749267 | 0.442338 → 0.352520 |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | 0.003069 → 0.402921 | 0.322380 → 0.308556 | 0.015138 → 0.929615 | 0.452235 → 0.515962 |
| LOCAL16-c8p5-diagonal [[0, 1], [2, 3]] | 0.003069 → 0.298272 | 0.322380 → 0.213139 | 0.015138 → 0.686378 | 0.452235 → 0.340290 |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | 0.003576 → 0.426482 | 0.401233 → 0.421584 | 0.017589 → 0.922705 | 0.559511 → 0.561328 |
| P23p5-peripheral-polyomino225 [[0, 1], [2, 3]] | 0.003576 → 0.310059 | 0.401233 → 0.316324 | 0.017589 → 0.675169 | 0.559511 → 0.435772 |
| P12-square-c11p5-diagonal [[0, 2], [1, 3]] | 0.003615 → 0.624341 | 0.282183 → 0.481851 | 0.017795 → 1.150188 | 0.480030 → 0.640933 |

## Separate budgets

| Case / pairs | Equal-current target mean / P10 change | Equal-current source-power change | Equal-source-power mean / P10 change | Joint8 limiting constraints |
|---|---:|---:|---:|---|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | +9.589% / +9.268% | +65.811% | -14.894% / -15.143% | contact_power_W |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | +9.588% / +9.279% | +65.811% | -14.895% / -15.135% | contact_power_W |
| LOCAL14-c9-diagonal [[0, 1], [2, 3]] | +18.106% / +18.914% | +66.477% | -8.464% / -7.837% | skin_power_W |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | +9.758% / +9.526% | +65.542% | -14.694% / -14.874% | contact_power_W |
| LOCAL16-c8p5-diagonal [[0, 1], [2, 3]] | +17.540% / +18.252% | +66.435% | -8.890% / -8.339% | skin_power_W |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | +9.696% / +8.978% | +65.606% | -14.758% / -15.316% | contact_power_W |
| P23p5-peripheral-polyomino225 [[0, 1], [2, 3]] | +17.512% / +18.933% | +66.589% | -8.954% / -7.853% | skin_power_W |
| P12-square-c11p5-diagonal [[0, 2], [1, 3]] | +9.262% / +8.424% | +66.037% | -15.206% / -15.857% | contact_power_W |

Equal current means equal SUM of two output RMS currents (bookkeeping), not every output independently or equal skin burden. Joint8 uses five linear and three quadratic numerical-reference caps; its global amplitude factor is the minimum across all eight. No cap is a physiological safety threshold. Contact area is unchanged within each matched topology contrast but differs across geometries. Full individual currents, source/contact/skin powers, Jmax/P95 and contact voltage are in the JSON.

Diagonal pairs(0,1)/(2,3), if present, change signal roles and are not isolation-only matched contrasts. Every completed-case raw artifact and executed-source snapshot is retained privately with hashes; the companion execution evidence lists raw NPZ hashes.

The first run retained an inherited common-ground label in the unchanged metrics helper. Its isolated circuit equations/raw outputs and explicit correction govern. Later output metadata is corrected. No original record was overwritten.

## Why the denominator matters

For the original-signal-preserving P23.5 contrast, surface0–5mm mean maxTIS changes23.1429275→0.1347054 V/m, while surface mean vector RMS changes18.7567341→16.3909847 V/m. In SC alone mean maxTIS changes1150.714808→3.324841 V/m, while mean RMS remains932.129469→814.907819 V/m. Thus the very large mean-denominator ratio gain is mainly suppression of surface carrier overlap/modulation in the model. It is not equivalent to suppression of total carrier field/current, heat, or a safety finding. P95 uses a different distribution statistic and excludes the influence of the most extreme small-volume cells in a different way. Both definitions are reported without exchanging them.
