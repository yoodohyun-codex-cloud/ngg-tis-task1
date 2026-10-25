# SC4→SC8 actual continuation and independent QA — 2026-10-25

The old PID66055 ended at 03:26:38 UTC after SC4 push succeeded but its next REST ref GET returned HTTP401. SC8 was not run. Recovery commit f139de1dcce34600514b55f6e182e15ee058d5fd proves the existing c440ccec SC4 commit by full readback of all31 files and preserves the original failure. No native SC4 repeat or credential/security change was needed.

Root then completed10 manufactured Fourier cases (same2/2 and3/3 fits on SC4/SC8), froze source/config/mask, published preregistration at6c2fc21cc122b490d40519073c00b01d6f8bdfe7, and ran one actual SC8 condition:786000 cells,2000Hz,two basis RHS. This is a single-carrier interface diagnostic; it is a one-carrier four-pad/two-output common-return diagnostic; no new TIS modulation is claimed. All4 top pads,2outputs/common return,50ohm each and inactiveotheroutput0V/50ohm are retained; experimental wiring remains unverified.

D50mm and0.1/5/5/15mm layers,XY0.5mm,bulk18/18/56,material/contact/pad-mask bytes are fixed. The human-reference/surrogate material assignment is unchanged, not directly validated human thoracoabdominal tissue. TargetROI:r<=5mm,z=15–20mm,with physical-volume weighting; original surface/non-target metrics are retained in summary.

| Quantity | SC4 | SC8 |
|---|---:|---:|
| Target carrier E RMS mean,V/m |0.0289431733|0.0289437188|
| Target carrier E RMS P10,V/m |0.0255994505|0.0255999433|
| Contact normal J RMS max,A/m2 |0.0699226581|0.0699455368|
| Skin vector J RMS max,A/m2 |0.1081663894|0.1081710124|
| Source power,W |1.29650885e-6|1.29653710e-6|
| Common2 SC-interface all,normalizedL2 |14.5392%|14.5037%|
| Common2 SC-interface periphery,normalizedL2 |50.5628%|50.4677%|
| Same3/3 SC-interface all,normalizedL2 |6.3948%|6.4874%|

All13 preregistered scalar adjacency checks and5 discrete algebraic gates passed. **Independent5% flags remain failed; full convergence and adoption remain false.** Fixed physical interior r<=23.75mm/periphery r>23.75mm is used on both meshes; native24mm scopes are preserved separately. Both2/2 and3/3 orders, all3 interfaces and all regions remain reported. `absolute-interface-QA.json` retains absolute differences, both side norms, denominator/floor and maximum difference. For example common2all absolute difference is0.005464269→0.005450378 A/m2, not a known continuum error. Its spatial complex-amplitude norm is distinct from temporal carrierRMS.

The manufactured periodic planar diagnostic has exact analytic truth, no cylindrical electrode/contact circuit. Atmode16, SC4→8 FVM shared-interface flux error relative to the exact continuum solution at k_fd improves0.0200608%→0.00576461%, while exact-continuum3/3 fitted jump rises17.0459%→17.1970%. UpperSC estimator absolute error improves0.000438624→0.000109521 A/m2, while lowerVS error stays0.031191553 A/m2. This demonstrates estimator bias/cancellation can move the diagnostic independently of trueFVMerror. It does not establish the real-cylinder error, authorize bias subtraction or clear the unchanged5% flags.

Next finite scientific batch:holdSC8/XY and compare preregistered VS18uniform,VS19uniform andVS18graded manufactured cases, independently retaining trueFVMerror, continuum error and each-side estimator bias. No blindSC16; native-equivalent count must stay<=800000. A real graded-mesh run requires review of those results and verified implementation.

SC8 native wall51.366s,observedCPU/wall1.054cores(existing serial Java solver),peak accountedRSS+allownedtmpfs3,192,767,888bytes. Postprocess14.749s. Approved uppercapsCPU4 and8,000,000,000bytes(decimal8GB,7.45058GiB),Javaheap2GiB,max800000cells and one owner remain. Cumulative time is unlimited; finite per-stage watchdogs remain.

Native complex potential/E,grid,source/contact/loss,all diagnostics and hashes are preserved. Git-supported HTTPS publication with a fresh separate remote object readback avoids making optional REST comments a prerequisite for scientific publication. Original failure evidence is preserved. Localtmpfs is not durable across environment shutdown. Windows/OneDrive target is not connected and is **not saved/verified**. No installation,original deletion,securitychange,resource/billing expansion ormainmerge. No activation/safety/experimental validation claimed.
