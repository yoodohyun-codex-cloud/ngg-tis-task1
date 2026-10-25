# Floating-pair matched comparisons

All fields below are the original2074-direction sampled maxTIS (V/m), using the same volume ROI r<=5mm,z15–20mm. Surface is0–5mm includingSC; off-target is total minus fractional target. Source1Vpp is open-circuit differential amplitude; total resistance50ohm per pair. Inactive pair remains terminated.

These are provisional electrical comparisons; no deep-focus or physiological validation. P95-denominator improvements must not be described as increased target mean/P10.

| Case / pairs | Reference mean / P10 | Isolated1Vpp mean / P10 | Joint8 mean change / P10 change |
|---|---:|---:|---:|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | 0.06496335 / 0.05851064 | 0.04504655 / 0.04045349 | -15.102% / -15.350% |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | 0.06496335 / 0.05851064 | 0.04504606 / 0.04045745 | -15.102% / -15.342% |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | 0.08054280 / 0.07252454 | 0.05594475 / 0.05026891 | -14.966% / -15.146% |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | 0.08275756 / 0.07667868 | 0.05744947 / 0.05288116 | -15.014% / -15.570% |

## Explicit denominators

| Case / pairs | Mean/surface mean (ref → isolated) | Mean/surfaceP95 | Mean/off-target mean | Mean/off-targetP95 |
|---|---:|---:|---:|---:|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | 0.003227 → 0.491518 | 0.309412 → 0.343819 | 0.015910 → 1.029322 | 0.442338 → 0.547647 |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | 0.003227 → 0.491511 | 0.309412 → 0.343748 | 0.015910 → 1.029309 | 0.442338 → 0.547647 |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | 0.003069 → 0.402921 | 0.322380 → 0.308556 | 0.015138 → 0.929615 | 0.452235 → 0.515962 |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | 0.003576 → 0.426482 | 0.401233 → 0.421584 | 0.017589 → 0.922705 | 0.559511 → 0.561328 |

## Separate budgets

| Case / pairs | Equal-current target mean / P10 change | Equal-source-power mean / P10 change | Joint8 limiting constraints |
|---|---:|---:|---|
| LOCAL14-c9-diagonal [[0, 2], [1, 3]] | +9.589% / +9.268% | -14.894% / -15.143% | contact_power_W |
| LOCAL14-c9-diagonal [[0, 3], [1, 2]] | +9.588% / +9.279% | -14.895% / -15.135% | contact_power_W |
| LOCAL16-c8p5-diagonal [[0, 2], [1, 3]] | +9.758% / +9.526% | -14.694% / -14.874% | contact_power_W |
| P23p5-peripheral-polyomino225 [[0, 2], [1, 3]] | +9.696% / +8.978% | -14.758% / -15.316% | contact_power_W |

Equal current means equal SUM of two output RMS currents (bookkeeping), not every output independently or equal skin burden. Joint8 uses five linear and three quadratic numerical-reference caps; its global amplitude factor is the minimum across all eight. No cap is a physiological safety threshold. Contact area is unchanged within each matched topology contrast but differs across geometries. Full individual currents, source/contact/skin powers, Jmax/P95 and contact voltage are in the JSON.

Diagonal pairs(0,1)/(2,3), if present, change signal roles and are not isolation-only matched contrasts. Every completed-case raw artifact and executed-source snapshot is retained privately with hashes; the companion execution evidence lists raw NPZ hashes.

The first run retained an inherited common-ground label in the unchanged metrics helper. Its isolated circuit equations/raw outputs and explicit correction govern. Later output metadata is corrected. No original record was overwritten.

## Why the denominator matters

For the original-signal-preserving P23.5 contrast, surface0–5mm mean maxTIS changes23.1429275→0.1347054 V/m, while surface mean vector RMS changes18.7567341→16.3909847 V/m. In SC alone mean maxTIS changes1150.714808→3.324841 V/m, while mean RMS remains932.129469→814.907819 V/m. Thus the very large mean-denominator ratio gain is mainly suppression of surface carrier overlap/modulation in the model. It is not equivalent to suppression of total carrier field/current, heat, or a safety finding. P95 uses a different distribution statistic and excludes the influence of the most extreme small-volume cells in a different way. Both definitions are reported without exchanging them.
