# 작업1: Original opposite sine-gauge cached drive (2026-10-21)

원래opposite4square배치의actualcached구동탐색이다. 신규full 1개와과거pure3ksine/exactweak-r.05-φ90를분리했고모든후보미채택이다. 첫행은originalsquare3h이며같은원래8caps/ROI/단위를사용한다. main표는3+신규조건수행,기존strong8/weak6전체는원본15alias catalog로보존했다. 과거결과를새global정규화로바꾸거나새full검증으로세지않는다.

[4행 오프라인GUI](CLOUD_ORIGINAL_CACHED_DRIVE_RESULTS_20261021.html) · [정확한5모드/출처brief](ORIGINAL_CACHED_DRIVE_RESULTS_20261021.result-brief.json) · [원본summary](cloud-original-cached-drive-20261021T221000Z/summary.json)

## 실제신규결과와종료이유

신규 original-drive-3f40b4b8948b의actualgenes는[0.03,0,0.005,0,0.985]이고8개중5PASS/3FAIL로미채택이다. 목표mean/P10과surfaceP95는FAIL,complementP95와표면/비표적기준mean/P10이상체적4개만PASS다. raw목표mean/P10=3.66895502112/3.28820635157V/m,skin8=4.0116379224455185/3.595327067481046V/m로원래목표기준4.061848941601601/3.6457357391300533V/m에미달한다. skin8 surfaceP95=25.276747253768526/complementP95=23.406128940632524V/m다. 활성limiter는SC_power_W이며skin8actualsourceupper[1.0826313166348176,1.0934006820351052]Vpp가1을넘으므로동일전압개선으로표현하지않는다.

실제72proxy가완료됐고proxy_budget_exhausted_partial/stop_reason=evaluation_cap으로평가개수상한에닿았다. 시간timeout이나모든level완료가아니다. source/candidate1개full검증을끝냈으나전역탐색/연속방향수렴/성공은아니다. puretargetregression은정확한oldoriginal-squarecapcohort에서mean/P10오차0을확인했고새purefull계산또는freshsinecap검증으로바꾸지않았다.

## 기하·회로·실제sourceVpp

D50mm/SC·dermis·fat·muscle0.1·5·5·15mm/윗면/XY.625SC2bulk14·14·40/351680cells와15×15mm square225mm²×4=900mm²를유지했다. 원래opposite source0SW(−10,−10),source1NE(+10,+10),GND2SE(+10,−10),GND3NW(−10,+10)다. 앞선adjacent sourceSW/SE와다른회로배치다. 모든행물리4pads/독립2outputs/공통GND1/50Ω·비구동주파수0Vthrough50Ω다. PBS specificΩm²/Rs차감·접촉면적스케일링을추가하지않고원래물성·접촉모델을유지한다.

새sine phase gauge는frequency-rows/output-columns c3000=−j[1,z0],c3030=−j[z1,rho]이며peak0.5V·+jωt basis에ONEglobalg만곱한다. 각출력whole-waveVpp upper의최대만1Vpp이고각출력이exact1Vpp라는뜻은아니다. 반면과거strong8/weak6는−junitaryseed뒤OUTPUTWISE Vpp정규화였고원래columnscales/실제벡터/rawVpp/probes를불변재사용한다. exactweak의actualgenes는[-3.0616341296444263e−18,.050000279783135114,3.061616997868383e−18,.05,1.000005595662702]로tinyreal/rho drift를보존하고[0,.05,0,.05,1]로반올림하거나새globalrawalias로바꾸지않는다. 기본파3000/3030Hz·beat30Hz,9k명령0이며square3h첫행만9000/9090고조파가있다. 초기2/2.01kHz기록과별도다.

주ROI r≤5mm·깊이15–20mm,+z안쪽,x/y수평이다. E/TIS V/m,CV/P10mean무차원. maxTIS는실제SHA고정2074방향표본최대(연속방향최대하한),fixedTIS는(X+Y)/√2기본파변조,fullRMS는전체활성선벡터RMS다. fractionalROI/가중ECDF/exactzoverlap/staircasegeometry/원래square rawcutoff를고정하고analytic volume재정규화없이기록했다. SC전역최대를깊이집중으로해석하지않는다.

## raw source whole-wave Vpp 기준

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래4-square/opposite square3h|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cachedpure3ksine (originalsquarecaps)|{"stored_pure_sine_analytic_Vpp_by_output": [1.0, 1.0]}|3.82954790768 / 3.43723261807|0.0807616216391|4.68701222214|23.8146227262 / 22.0954073744|2.06559715647 / 1.88460293972|
|cached exactweak-r.05-φ90|[[0.9999992611357055, 1.0], [0.9999992477075699, 1.0]]|3.65471251241 / 3.28204794328|0.0804434346243|4.46944418982|22.8314101041 / 21.3045325858|1.96970800796 / 1.79711226725|
|original-drive-3f40b4b8948b|[[0.9901499323661015, 0.990150577389212], [0.9999992474453329, 1.0]]|3.66895502112 / 3.28820635157|0.0818417226832|4.4793266739|23.1175521189 / 21.4067261208|1.98518797709 / 1.80970102987|

## 동일8개 피부·접촉부담 (skin8)

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래4-square/opposite square3h|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cachedpure3ksine (originalsquarecaps)|{"stored_pure_sine_analytic_Vpp_by_output": [1.0698639023477048, 1.0698639023477048]}|4.09709506874 / 3.67737110205|0.0807616216391|5.01446518633|25.4784052028 / 23.6390787575|2.2099078345 / 2.01626865546|
|cached exactweak-r.05-φ90|[[1.1219461167451346, 1.121946945711673], [1.1219461016794787, 1.121946945711673]]|4.10039354075 / 3.68228366564|0.0804434346243|5.0144792578|25.6156308326 / 23.9025552644|2.20990788348 / 2.01626461934|
|original-drive-3f40b4b8948b|[[1.0826306113661086, 1.0826313166348176], [1.093399859191319, 1.0934006820351052]]|4.01163792245 / 3.59532706748|0.0818417226832|4.8976988403|25.2767472538 / 23.4061289406|2.17060588811 / 1.97872834034|

5모드공통표의raw표시만producer key map으로연결한다. pure는cohorts.cached_original_square_3000_3030_caps.normalizations와raw_sine_1Vpp원형키를그대로유지하며fresh_sine_3000_3030_caps는사용하지않는다. pure의skin8A1.0698639023477048/ROImean4.097095068740712/P103.677371102045917V/m를검증했다. skin8는원래square8개피부·접촉수치한도이고sourcepower/1Vpp상한없음,legacy만이둘을추가하며동일전류/전력에도1Vpp상한없음이다. sourceVpp>1인모드의결과를raw동일전압gain으로표현하지않는다. 수치제한은인체안전한계가아니다.

5모드의절대목표mean/P10/CV/P10mean/max·fixedTIS/fullRMS·wholeXY보조ROI·표면/전체비표적P95·원래cutoff이상체적·전역hotspot과각burden을GUI/brief에보존했다. 전역SC최대값은깊이집중이아니다.

## 원본제공 weak/신규8gate (pure N/A) · 원래square raw기준 고정

|조건|mean|P10|surfaceP95|surface high@mean|surface high@P10|complementP95|complement high@mean|complement high@P10|
|---|---|---|---|---|---|---|---|---|
|coherent-weak-r0p05-p090|PASS|PASS|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|
|original-drive-3f40b4b8948b|FAIL|FAIL|FAIL|PASS|PASS|PASS|PASS|PASS|

각gate의기준·후보·변화율·단위·방향은원본/GUI에보존했다. 원래square/pure의cached행에새screen개수를부여하지않았다. old14의판정은과거그대로재사용하고신규full조건의실제판정을별도로표시했다.

## nativeφ40·carrierRMS·signed power·범위

Proxy최대72개/180s,source30s·최종full≤1개120s+finalization30s/전체360s·출력32MiB는등록상한이다. 실제proxy완료수/종료이유는원본을그대로기록한다. 목표proxy는고정2074/전체ROI의정확한표본mean/P10,off-target은3lambda PSD고유값upperbound최솟값을ranking에만사용하고wholeVpp정규화전proxy를raw1Vpp/full8gate와동일시하지않는다. 기존15fullalias는새spectralproxycache가아니며방문시proxy를한번평가한다. pure목표regression은원래squarecapcohort만써서과거저장값과비교하고freshsinecap이나새purefull계산으로교체하지않았다. 15catalog in/outdomain·sourceSHA·계수복원proof를보존하며전역최적/연속방향/불가능성증명은아니다.

각drive의5모드40개무부하예측은정확한sourceJSON pointer로연결한다. pure는원래cohort의probe40만사용하고과거weak는원래OUTPUTWISE정규화의rawVpp/probe를그대로재사용한다. 깊이5/10/15/20mm×중심·X/Y±5mm의5개probe중심×X/Y차동방향,tipgap5mm이며중심위치와팁간격을구분한다. rawJSON의Vpp/RMS/기본파envelope·spectrum/저장검사·SHA를확인했다. ETA5001/DSOX1202A 실제switch·팬텀portZ/부하·보정·filter응답은미검증으로loaded예측을보류한다.

저장raw carrier별RMS/balance의목표r5와wholeXY보조ROI통계는별도로표시했고다른정규화에새scale/recompute하지않았다. carrierRMS·전체fieldRMS·방향별TIS·최대표본방향TIS는별개다. weak/신규각모드의signed ideal source/metal delivered/50Ωloss 출력별합계·주파수별값·그룹총합을보존했다. pure는원본rawtop전력만제공하며정규화별signed값을추가하지않았다. 음수와비활성9000/9090Hz의0계수·전력선을제거하지않았다. GND net/localJ는신규원본필드의제공분만보존했고기존pure/weak에없는항목은미제공으로남겼다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json),SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `sine-3000-3030-beat30` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](cloud-next-frequency-20261021T104000Z/sine-3000-3030-beat30/condition.json),SHA256 `08e7053dc942975f78880887a5a27e1fa1236d558676b1e8af008da4cb753a29`
  - [rawunloaded40](cloud-next-frequency-20261021T104000Z/sine-3000-3030-beat30/probes.json),SHA256 `5b757fcb72452ba8519208292f4ae4dd8fec3e6227b00d9af5e47539d6dbdf5c`
- `coherent-weak-r0p05-p090` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](cloud-next-coherent-weak-20261021T170000Z/coherent-weak-r0p05-p090/condition.json),SHA256 `2e679dd64f2ecf34351eaf758ee75f13b589fbf81cce39899f4a9163a570d0f1`
  - [rawunloaded40](cloud-next-coherent-weak-20261021T170000Z/coherent-weak-r0p05-p090/probes.json),SHA256 `a1c82cca0c7594093a98fd14fe14b25df171839a9e2b809b225225e6d2cc080d`
- `original-drive-3f40b4b8948b` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](cloud-original-cached-drive-20261021T221000Z/original-drive-3f40b4b8948b/condition.json),SHA256 `8e855480dc2f61ef3f1ed7a87c50a7a4b8285bd59b39d04c004cd3215dbdba37`
  - [rawunloaded40](cloud-original-cached-drive-20261021T221000Z/original-drive-3f40b4b8948b/probes.json),SHA256 `993434ad0b55c075e348be2ed1461fb2684b88428fbc4dbd6bf4f1c94cd83e35`

## 실제실행·검증보류·다음준비단계

Scientificworkerstatus calculated_unadopted, wall91.72538430499844s,RSS540643328bytes,CPU1,newPDE0. Queue completed_preregistered_queue, phase/stage상태는원본영수증과구분한다. 완료publication영수증은작성시점미확인으로발행commit을추측하지않았다.

contactnormalJ와SC+dermis체적vectorJ·접촉전압·SC/contact/SC+dermis/sourcepower를구분한다. signedsource/metal/resistor의주파수·출력·그룹합계에서음수와9k비활성0을제거하지않는다. pureproducer는모드별signedoutputpower가없어새로scale하지않고rawtopoutput_power_evidence만별도로보존했다. pure8gate도원본미제공이라새판정을계산하지않았다. 기존강·약14원본fields/출력별정규화와새ONEglobal정규화를구분한다. SC/XY/bulk/edge/contact수렴·PBS피부전이·계측부하·AWG흡수/compliance·실험·활성화/C1동등성·인체안전·COMSOL5.3a·fullnativepersistentbackup은미검증이다. 본문서는docsJSON만읽고native/배열/NPZ/E/φ·계산·렌더·Git을수행하지않았다.

현재결과만기록하며다음root선정/계산을미리실행완료로표시하지않는다. 기존과신규candidate ID를분리하고재계산·반복worker·무기한백그라운드·후보채택을약속하지않는다.

native source `38f005ecefc2c432cd6424a06f599f93682cc202`,physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,scout implementation/preregistration `c5ef2a43293fff655cf1402d4521a356da18979d`를구분한다. 이번docs해시검증은시뮬레이션재현/수렴/실험검증이아니며새물리fieldmap을생성하지않았다.

- [summary](cloud-original-cached-drive-20261021T221000Z/summary.json),SHA256 `a3850a5e98227ecda7b9181d24d983c92745d82b5da765579e40223cfd7e3082`
- [decision](cloud-original-cached-drive-context-20261021T221000Z/decision.json),SHA256 `9142b1b2b308129eec5c1daa952a0ab91af447b7123890c9089ba1ae9cba4a90`
- [preregistration](cloud-original-cached-drive-context-20261021T221000Z/preregistration.json),SHA256 `2c3b34e24ab542304208189b90994dca2d8bdd759fc8e6d5b075311ee70414ea`
- [queue](cloud-original-cached-drive-context-20261021T221000Z/queue/summary.json),SHA256 `1a8409cd2f796972861d6b024d55e3f4dbcbb86539379f761b16e15ad6311b00`
- [feedback_after](cloud-original-cached-drive-context-20261021T221000Z/feedback-after.json),SHA256 `1560cc008070b7698a8a961431a23c8db1b009c2dc72ff100e2372651406306e`
- [cached_volume](cloud-adjacent-cross-20261021T164000Z/volume.json),SHA256 `5ae3c3bc95021024109e6b3c0f4985b978b8a4262c4a7cd3441aca819d6bb725`
- [proxy_search](cloud-original-cached-drive-20261021T221000Z/proxy-search.json),SHA256 `246591bc0aa3cba9aae91ced46f926a7cc755972056fa6590e95a8cdefbf74dc`

[과거strong8GUI](CLOUD_COHERENT_DRIVE_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다.

## 15개 immutable full alias catalog

5개in-domain/10개out-of-domain을원본값대로보존했다. in-domain fullgene은새full후보에서제외하고out-of-domain원본도지우지않았다. 아래는catalog이며새계산건수가아니다.

|ID|이번등록영역내|원본condition SHA256|
|---|---|---|
|coherent-r0p5-p000|False|`c1914bcaf07f9b84591540fb18b7259933c1b5027678b24acc8fa9ae8aad5d2d`|
|coherent-r0p5-p090|False|`dd6ffeafc0bbf2a5a49787d8ceab2f6941bd5f310fb7800e200aa6bae65ebf3f`|
|coherent-r0p5-p180|False|`d2c5b9fbe3dbaac2bef84fd50788b050d6c9432692b90ad9d2346085cf52424e`|
|coherent-r0p5-p270|False|`0510597ccae652d663780edc87414bce9d9f3689292d668e50e146595b4102e3`|
|coherent-r1-p000|False|`5039f078399f0662020799daa8d352d88ba5d5de14491266a158dfb8a5cb49dc`|
|coherent-r1-p090|False|`50098844553a37135f963dca6bd288ef0ccba9d5cb4e3d65a809055cbd90c9fc`|
|coherent-r1-p180|False|`28b5f0bbeefb7e287bb4ecaf70843bc2aa11d4d0cbf3897c4d2a0fec00a0f3a6`|
|coherent-r1-p270|False|`e3b9f568dda9730c4366ce9badc3cfc7afc131ca650be78c97576eda2582bd1b`|
|coherent-weak-r0p05-p090|True|`2e679dd64f2ecf34351eaf758ee75f13b589fbf81cce39899f4a9163a570d0f1`|
|coherent-weak-r0p05-p270|True|`3ba346d5b4e86c5631ff19a2fa523229117e888274c46a63d3438073a35226d2`|
|coherent-weak-r0p1-p090|True|`c5d882319a542f5cdfa9e4bf73356d83e69c60019b408909eed88d87c578b74d`|
|coherent-weak-r0p1-p270|True|`ac0439efb25b8cc705f6098b176dfd3a809be757f908e95c491a267520f216c8`|
|coherent-weak-r0p2-p090|False|`911a964fc6e7b57ea6d3d80cb42b9eedae40c5d191b09e73a1246487ec61fa72`|
|coherent-weak-r0p2-p270|False|`74a4af0efac023e1db755aa0e301cfae3017bcb54611d4f6e27b4188fdcb40d6`|
|sine-3000-3030-beat30|True|`08e7053dc942975f78880887a5a27e1fa1236d558676b1e8af008da4cb753a29`|

[과거weak6공개보고서](COHERENT_WEAK_RESULTS_20261021.md) · [weak6원본summary](cloud-next-coherent-weak-20261021T170000Z/summary.json) · [과거pure frequency GUI](CLOUD_FREQUENCY_RESULTS_20261021.html)
