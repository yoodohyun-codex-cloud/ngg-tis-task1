# FixedSC8 VS-spacing manufactured diagnostic — 2026-10-25

After actualSC8 completion/publication(a31cabc8), root preregistered and completed15 analytic manufactured cases: five spatial Fourier modes1,2,4,8,16 for uniformVS18(U18),uniformVS19(U19) and symmetric ratio1.15 gradedVS18(G18). SC8/XY0.5mm and physical0.1/5/5/15mm layers stay fixed. Native-equivalent counts:786000/793860/786000, all<=800000; no new cylinder/CEM/electrode/source-circuit PDE was run in this study. Exactface coordinates,min/maxwidths,source/input hashes and fixed screens were pinned before computation. Three code contracts plus inherited analytic contracts passed; wall0.81135s,observedCPU~0.999cores,peakRSS+allownedtmpfs2,589,770,192bytes.

The same2/2 and3/3 one-sided fits are retained. Errors are separated into FVM versus exact analytic continuum at k_fd(vertical discretization), exactcontinuumk_fd versus physicalk(lateral symbol), exact-sample estimator bias, and algebraic discrete-network reconstruction. Independent Thomas/admittance agreement is an algebraic check, not continuum truth. Signed error components/identities, absolute quantities, denominators and every case/interface are preserved. No nativefield bias correction or5%threshold change.

| Worst envelope over declared modes |U18|U19|G18|
|---|---:|---:|---:|
| SC-interface flux error vs continuumk_fd,relative |5.764608e-5|5.655970e-5|5.175965e-5|
| All-interface flux error vs continuumk_fd,relative |0.250967813|0.234540960|0.286386610|
| VSprofile relativeL2 error vs continuumk_fd |0.0084253385|0.0075543919|0.0060677202|
| Physicalk whole-profile relativeL2 |0.0002365546|0.0002354646|0.0002316177|
| LowerVS exactsamplefit bias,2points(relative) |0.40748058|0.39129225|0.25457406|
| LowerVS exactsamplefit bias,3points(relative) |0.16188379|0.14916903|0.06628280|

The25–29% all-interface worst envelope occurs only here at mode16,z10.1mm,where exactJ=(3.7349598e-10+j8.9440165e-10)A/m². Its absolute error is U18:2.4325159e-10,U19:2.2732979e-10,G18:2.7758140e-10A/m². This relativeworst-case value is not a general whole-field orSCerror. Allper-mode/face errors remain in summary.

**Next selected actual diagnostic:U19uniform,793860cells.** U19passes the preregistered1%worst-envelope nonregression and achieves>=10%VSprofile error improvement(about10.34%). This does not establish pointwise error monotonicity, actualcylinder accuracy orcandidate adoption. G18improves purefitbias andSCfluxerror but fails the same all-interface nonregression screen; it is retained as a proposed,not-run native case. We do not relax the rule after seeing results. Existing nativeValidationMesh supports neithernewcase directly: a separately frozen explicitface adapter, geometry contracts, root admission and source publication are required before U19starts.

AlloldSC8/SC4 fields andfailed5%flags remain. Root-native admission is a separate future immutable receipt with this MMSresultcommit andverifiedSC8commit; this report is a selection,not proof of a newnative start/completion. CPU4/aggregateRSS+allownedtmpfs8,000,000,000bytes(7.45058GiB)/800000cells/singleowner/finitewatchdogs remain; cumulativetime unlimited. Noinstall/deletion/security/resourcebilling/mainmerge changes. Windows/OneDrive saving is notverified. Noactivation/safety/experimental orcompleteconvergence claim.

The SC8 report terminology correction is preserved separately under docs/TASK1_SC8_2000_20261025/ERRATA.md and REPORT-v2.md; originalREPORT.md/data remain unchanged.
