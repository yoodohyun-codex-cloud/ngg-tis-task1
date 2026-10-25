# Fine XY102 CEM and contact-discretization diagnosis

Completed new fine condition:2RHS,2000Hz,793848evaluationcells;21contracts passed. Source6e5e4de75d9330a60e0eb1340497c9be8318b64f,resultd2456af62d0686e06555d9e6664ee5d3504d8c64. OriginalU19/basis/coarseDtN/XY102benchmarks were not rerun. Old PIDs90469/90191 completed normally; allthreeglobaldual locks were verified free before this continuation.

D50mm,physical0.1/5/5/15mm layers,samefrequency-dependent scalar surrogate inputs/contactreceipt,4physical15×15mmpads and2outputs/commonreturn remain fixed. Everyoutput has50ohm; at eachbasis the otheridealsource is0V behind50ohm. Finecontacts use exactrational physicalrectangle/pixelintersection, not copiedindices orrenormalizedareas. Eachpad's225mm² partition passesrelative1e-10. FineSC4 here is analyticdepthsampling,not a changedSCthickness.

| Source0 metric | Coarse XY100 | Fine XY102 | Change /screen |
|---|---:|---:|---|
| ContactJ RMSmax,A/m² |0.06995376|0.14263729|+103.90%,fails5%|
| WholecontactJ RMSareaP95,A/m² |0.06810383|0.06809729|−0.00960%,passes5%|
| ContactvoltageRMSmax,V |9.44487e-6|1.92583e-5|+103.90%,fails5%|
| Physical0.5mmedge J RMSP95,A/m² |0.06902031|0.09854833|+42.78%,fails5%|
| Sourcepower,W |1.29653441e-6|1.33144469e-6|+2.6926%,fails2%|
| Edgecontactloss,W |1.02247501e-11|1.51269251e-11|+47.94%,fails2%|

Bothbases fail13/14available electricalscreens. Solver/current/power-balance tests pass; these are separate from mesh/contactburden convergence. TargetEmean/P10 are unavailable,never counted as passed. No E-field,TIS,physiology orhuman-safetyconvergence claim. Oldfailed5%flags andboth2/2and3/3fits remain; fineSC4versuscoarseSC8fits arenot claimedlike-sampledconvergence.

Physicalcomparison uses31360sparse square-cellintersection links. Commonrepresentedarea1957.5221mm²; coarse-only7.47789mm² andfine-only9.02922mm² boundaryareas are separatelyretained. AtSCinterface/source0, primarypairwisecomplexspatialL2difference is0.00594391337A/m²/0.0376498438=15.78735%; secondaryfine-to-coarse averaging gives0.00294560515A/m²/0.0376498438=7.82368%. Averaging hides variation. Noindexwise delta orgauge/phasefit. Targetr5mm,z15–20mm usesmatchedphysical56muscleplanes andexactdisk×zquadrature; smallpotentialchange doesnotprovegradient/E/TISconvergence. Original128²-weightedresults remain unchanged.

Next mechanismcheck completed: sixfixed manufactured independentSC-column cases,6purecontracts passed,17.09s,newphantomPDE0. Unit1Vpeak(2Vpp) prescribedcolumn difference, no laterallayerspread/50ohmsource/fullphantom/TIS. Physicalcontactinputs were neverchanged. Coarse f=A/h² is1 throughout;fine minimumf=.49. Eachfinepad'sactualarea225mm² toucheswholepixels totaling230.9208mm² (ratio1.0263147). In the predeclaredcolumnlimit, thewholepixelmodel/area-column Jmax ratio atactualz is2.0407438; this demonstrates a possiblefractionalcoverage/wholepixelDOF mechanism. It is not a fitted correction,3Dtruth,orproofthattheobserved2.039×peak isfullyexplained. Contactscales1,1e3,1e5 are toy sensitivities only. Actualfinecase remainsfailed/unadopted. A nextvalidscientificstep is contact-subcell/boundary-resolved verification,not furtherpadoptimization oracceptancebasedonarea/phi alone.

Preservation:all31originalrealQchunks(total1,030,059,648bytes) are now tracked atfixedd725ee29ee568ef26a4b7579e9dfc55d23e0681a withfullblobSHA256/size/GitSHAreadbackandcommittree/refchecks. Originalcloudfiles andtheHTTP503publicationfailure are preserved; recoveryusedpreviousblobproofs,not numericalreruns orduplicateuploads.

Transfermanifest/receiver are separate frombackupcompletion: published fixed paths/hashes plus downloadablebytes do notestablish a write to Windows orOneDrivesync. The Windowsdestination isnotaccessible fromthiscloud. Publictransferlists useonlyrepositoryrelativepaths andshortcontent-addressedrelative destinations; originalprovenancereceiptsremain byte-exact. CPU4,totalRSS+allownedtmpfs8,000,000,000bytes,800000evaluationcells,singleowner andfinitewatchdogs remain; cumulativetime unlimited. No install,securitychange,originaldeletion,billingchange ormainmerge.
