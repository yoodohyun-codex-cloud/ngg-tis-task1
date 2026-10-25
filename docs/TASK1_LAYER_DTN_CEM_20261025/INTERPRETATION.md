# What the continuous-z reference establishes — 2026-10-25

Actual reference run: layer-dtn-cem-20261025, source dadeeb1a6804159c4ec440fdeead7ceb3b602e41, result e4c09902bf529b4111c006dd4b4fb6681ca81252. One2000Hz condition/two RHS was actually solved;17tests passed. The reference and native U19 use the sameD50mm,0.1/5/5/15mm layers,scalar surrogate material inputs,XY0.5mm staircase graph,physical pad locations/areas,4pads/2outputs/50ohm/common return. The inactiveotheridealoutput is0V behind50ohm. Physical-topcontact isA/z; continuousSC alreadycontainsitswhole thickness,so no FVMhalf-cell isdouble-added.

The reference is continuous only in depth, conditional on its fixed discreteXY graph,eigensystem/GMRES tolerances and surrogate material/contact model. It is not exact smooth3D/anatomical/skin-contact/experimental truth. Its actualnewPDE count is2RHS; the subsequent comparison adds0PDE.

| Source0 measure | Native/reference comparison |
|---|---:|
| SCinterface sharedFVflux error,all,absolute |7.88284049e-7A/m²|
| SCinterface sharedFVflux error,all,reference-normalized |0.00209772%|
| SCinterface sharedFVflux error,fixedperiphery |0.00775856%|
| Original2/2fit jump,all:native / sampledreference |13.9403213% /13.8688672%|
| Original2/2fit jump,periphery:native /sampledreference |48.5892219% /48.3344875%|
| Original3/3fit jump,all:native /sampledreference |6.0638597% /5.8933069%|
| Original3/3fit jump,periphery:native /sampledreference |22.8428952% /22.2224694%|

Allquantities above retain complexpeak phasors and spatialnorms,not temporalRMS. The true-referenceerror denominator is the conditionalreferenceJ norm; the originalfit-jump denominator is max(upper/lowerfitnorms,1e-12). They are different metrics. The maximum sharedflux reference-normalizedL2 acrossbothbases/all3interfaces/allscopes is0.01641214%,atbasis1,z5.1mm,fixedperiphery: absolute1.783803275e-6A/m²,denominator0.01086880422A/m². The SCtopnumber mustnot be generalized to all3D errors.

The large fit discrepancy persists when an analytic-depth reference is sampled at the same original cells. For source0/common2/all, lowerVS-side pure sampled-estimator bias has spatialRMS0.00520660A/m²,while native-minus-reference solution propagated through the same estimator is3.06693e-5A/m². For3/3 these are0.00222561 and6.88060e-5A/m². Signedcomplex components,cross terms andidentityclosures are preserved; magnitudes mustnot be summed or subtracted as corrections to realfields. This supports estimatorbias as the main cause of the large jump in this model. It doesnot permit removing original flags.

**The unchanged5%screening flags remain:32native and32sampled-reference rows fail. No full convergence orcandidateadoption is declared.** Independentnumerical current,power,residual/reciprocity checks pass for the new reference. A targetROI potential difference of5.14528nV against roughly0.124957V commonmode potential doesnot establish E-field/TIS/activation/safety convergence. No new referenceE orTISmetric was exported; phi andnormalJ have explicit newABIs.

Actualkernelwall9.63086s,wholechildincludingcomparison14.09964s;observedaverage2.485CPUcores,not a4-core utilizationclaim. MaximumaggregateownedRSS+alltasktmpfs4,104,250,092bytes; CPUcap4/8,000,000,000byte(7.45058GiB)aggregatecap/800000evaluationcells retained. Cumulativetimeunlimited,600schild and1500sparent watchdogs remain.

Next selected finitebatch: nx102 graph/eigen/MMSpreprocessing forXYsensitivity. h=50/102mm andD50/layersfixed. The prospective continuous-depth sampling usesSC4/VS19/fat18/muscle56=97planes solely to keepactualNxy×97<=800000. PhysicalSC remains0.1mm; oldSC8datasets persist. No newverticalFVMmeshaccuracy claim. The futurefineCEMrequires a newphysicalfractionalcontactmask withsame225mm²pads androotadmission; preprocessing alone is not a completedfineCEM orXYconvergence test. FuturecrossXYcomparisons needphysical-volume statistics or an explicit projection; arrays mustnot be subtracted byindex.

Originals/failures retained. No installation,security/credential/billing/mainmerge change. Windows/OneDrive destination is notconnected or saved/verified. The eigenbasis is a recomputable localtmpfscache; its manifest/hash andmeasuredrecomputationcost are remote,butQcacheitself hasnotbeenremotelysaved. Allactualreferencephi/current/power outputs are remotelypublished/readbackverified.
