# 작업1: Original opposite compact drive refinement (2026-10-21)

원래 opposite 4-square의 compact 후속 구동 탐색이다. 첫 4행은 original square3h / 과거 pure3k sine(original square caps) / exact weak-r.05-φ90 / 직전 original3f40의 실제 저장 결과를 그대로 재사용한다. 신규 compact full 1개는 목표 평균·P10 두 항목 FAIL, 비표적 여섯 항목 PASS(6/8)여서 미채택이다. 기존 72 proxy + 신규 72 = 144이며 신규 평가 상한에 따른 partial 종료다. 이전 4행의 source/Vpp/probe/정규화는 불변이다.

신규 original-refine-3e018f8a317a: genes [0.03,0.0025,0.005,-0.01,0.985]. skin8 mean4.011539371036533/P10 3.595322017410421 V/m, surfaceP95 25.247853310590045/complementP95 23.395707456631655 V/m. skin8 A=1.0934817703564808, source whole-wave upper out0/out1=1.089258573660034/1.0934817703564808 Vpp이므로 동일1Vpp 성능 향상이 아니다. limiter=SC_power_W. 직전 original3f40의 5/8에서 신규6/8로 비표적 판정은 개선됐지만 목표 mean/P10는 모두 기준 미달이고 성공/채택이 아니다.

[5행 오프라인GUI](CLOUD_ORIGINAL_DRIVE_REFINEMENT_RESULTS_20261021.html) · [정확한5모드/출처brief](ORIGINAL_DRIVE_REFINEMENT_RESULTS_20261021.result-brief.json) · [원본summary](cloud-original-drive-refinement-20261021T222000Z/summary.json)

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
|cached last original3f40|[[0.9901499323661015, 0.990150577389212], [0.9999992474453329, 1.0]]|3.66895502112 / 3.28820635157|0.0818417226832|4.4793266739|23.1175521189 / 21.4067261208|1.98518797709 / 1.80970102987|
|original-refine-3e018f8a317a|[[0.9961371089748255, 0.9961378444424639], [0.9999992474456438, 1.0]]|3.66859281955 / 3.28795789274|0.0818473705306|4.47888961743|23.0894140122 / 21.3956081307|1.98504322416 / 1.80946408588|

## 동일8개 피부·접촉부담 (skin8)

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래4-square/opposite square3h|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cachedpure3ksine (originalsquarecaps)|{"stored_pure_sine_analytic_Vpp_by_output": [1.0698639023477048, 1.0698639023477048]}|4.09709506874 / 3.67737110205|0.0807616216391|5.01446518633|25.4784052028 / 23.6390787575|2.2099078345 / 2.01626865546|
|cached exactweak-r.05-φ90|[[1.1219461167451346, 1.121946945711673], [1.1219461016794787, 1.121946945711673]]|4.10039354075 / 3.68228366564|0.0804434346243|5.0144792578|25.6156308326 / 23.9025552644|2.20990788348 / 2.01626461934|
|cached last original3f40|[[1.0826306113661086, 1.0826313166348176], [1.093399859191319, 1.0934006820351052]]|4.01163792245 / 3.59532706748|0.0818417226832|4.8976988403|25.2767472538 / 23.4061289406|2.17060588811 / 1.97872834034|
|original-refine-3e018f8a317a|[[1.0892577694395789, 1.089258573660034], [1.093480947452011, 1.0934817703564808]]|4.01153937104 / 3.59532201741|0.0818473705306|4.89758414809|25.2478533106 / 23.3957074566|2.17060857898 / 1.97861599203|

5모드공통표의raw표시만producer key map으로연결한다. pure는cohorts.cached_original_square_3000_3030_caps.normalizations와raw_sine_1Vpp원형키를그대로유지하며fresh_sine_3000_3030_caps는사용하지않는다. pure의skin8A1.0698639023477048/ROImean4.097095068740712/P103.677371102045917V/m를검증했다. skin8는원래square8개피부·접촉수치한도이고sourcepower/1Vpp상한없음,legacy만이둘을추가하며동일전류/전력에도1Vpp상한없음이다. sourceVpp>1인모드의결과를raw동일전압gain으로표현하지않는다. 수치제한은인체안전한계가아니다.

5모드의절대목표mean/P10/CV/P10mean/max·fixedTIS/fullRMS·wholeXY보조ROI·표면/전체비표적P95·원래cutoff이상체적·전역hotspot과각burden을GUI/brief에보존했다. 전역SC최대값은깊이집중이아니다.

## 원본제공 weak/신규8gate (pure N/A) · 원래square raw기준 고정

|조건|mean|P10|surfaceP95|surface high@mean|surface high@P10|complementP95|complement high@mean|complement high@P10|
|---|---|---|---|---|---|---|---|---|
|coherent-weak-r0p05-p090|PASS|PASS|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|
|original-drive-3f40b4b8948b|FAIL|FAIL|FAIL|PASS|PASS|PASS|PASS|PASS|
|original-refine-3e018f8a317a|FAIL|FAIL|PASS|PASS|PASS|PASS|PASS|PASS|

각gate의기준·후보·변화율·단위·방향은원본/GUI에보존했다. 원래square/pure의cached행에새screen개수를부여하지않았다. old14의판정은과거그대로재사용하고신규full조건의실제판정을별도로표시했다.

## nativeφ40·carrierRMS·signed power·범위

등록 범위는 신규 proxy 최대72개/180s, 최종 full≤1개120s+finalization30s, 전체360s/출력8MiB다. 실제 기존72 SHA고정 proxy를 수치 변경 없이 재사용하고 신규72개를 계산해 총144개다. stop_reason=new_evaluation_cap, proxy_budget_exhausted_partial이므로 모든 수준 완료나 시간초과가 아니다. 목표 proxy는 SHA고정2074 방향/전체 목표 ROI의 정확한 표본 mean/P10이고, 비표적은 3lambda PSD고유값 upperbound를 ranking에만 사용했다. 실제 최종 full2074/전체체적 지표와 8gate를 별도로 보존했다. 과거16 full alias는 실제 저장 결과이며 이번 신규 full로 세지 않는다. 캐시 원본72 record와 기존 pure error0 target regression을 그대로 확인했으며 이번에 pure regression을 다시 계산한 것은 아니다. 전역 최적/연속 방향 최대/불가능성 증명이 아니다.

각drive의5모드40개무부하예측은정확한sourceJSON pointer로연결한다. pure는원래cohort의probe40만사용하고과거weak는원래OUTPUTWISE정규화의rawVpp/probe를그대로재사용한다. 깊이5/10/15/20mm×중심·X/Y±5mm의5개probe중심×X/Y차동방향,tipgap5mm이며중심위치와팁간격을구분한다. rawJSON의Vpp/RMS/기본파envelope·spectrum/저장검사·SHA를확인했다. ETA5001/DSOX1202A 실제switch·팬텀portZ/부하·보정·filter응답은미검증으로loaded예측을보류한다.

저장raw carrier별RMS/balance의목표r5와wholeXY보조ROI통계는별도로표시했고다른정규화에새scale/recompute하지않았다. carrierRMS·전체fieldRMS·방향별TIS·최대표본방향TIS는별개다. 각모드signed ideal source/metal delivered/50Ωloss의출력별합계·주파수별값·그룹총합을보존했다. 음수와비활성9000/9090Hz의0계수·전력선을제거하지않았다. GND net전류와localJ·patch절대전류적분은brief/원본에별도로보존했다.

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
- `original-refine-3e018f8a317a` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](cloud-original-drive-refinement-20261021T222000Z/original-refine-3e018f8a317a/condition.json),SHA256 `1e6b9dc90d1032d76d247567f71c62cf2d3fe4d6b28ad746e3b2cc102b61f366`
  - [rawunloaded40](cloud-original-drive-refinement-20261021T222000Z/original-refine-3e018f8a317a/probes.json),SHA256 `1a4c7eac1a2ab497388d71b1384e569babbb544efe283b4f577191994922798b`

## 실제실행·검증보류·다음준비단계

Scientificworkerstatus calculated_unadopted, wall90.51734821499849s,RSS541499392bytes,CPU1,newPDE0. Queue completed_preregistered_queue, phase/stage상태는원본영수증과구분한다. 완료publication영수증은작성시점미확인으로발행commit을추측하지않았다.

contactnormalJ와SC+dermis체적vectorJ·접촉전압·SC/contact/SC+dermis/sourcepower를구분한다. signedsource/metal/resistor의주파수·출력·그룹합계에서음수와9k비활성0을제거하지않는다. pureproducer는모드별signedoutputpower가없어새로scale하지않고rawtopoutput_power_evidence만별도로보존했다. pure8gate도원본미제공이라새판정을계산하지않았다. 기존강·약14원본fields/출력별정규화와새ONEglobal정규화를구분한다. SC/XY/bulk/edge/contact수렴·PBS피부전이·계측부하·AWG흡수/compliance·실험·활성화/C1동등성·인체안전·COMSOL5.3a·fullnativepersistentbackup은미검증이다. 본문서는docsJSON만읽고native/배열/NPZ/E/φ·계산·렌더·Git을수행하지않았다.

신규 compact full은 float64 전체 체적 maxTIS/fixedTIS/fullRMS 지표를 실제 계산했지만 RAM에만 유지하고 신규 volume.npz/scalar map을 저장하지 않았다. 새 산출물은 condition.json / probes.json / native-volume-metrics.json 세 JSON뿐이다. 원래 E/φ·가중치·계수 SHA와 source_complete_reconstruction_recipe_not_executed 복원 절차를 보존했으나 실행 가능한 scalar export CLI는 등록되지 않았고 독립 replay/새 물리맵/백업 완료가 아니다. 기존 네 행의 원본 scalar archive는 보존하며 삭제·대체하지 않았다.

다음 연구는 root가 호환 가능한 cached mesh gate 등을 검토할 단계이며 이 보고서에서 시작·완료를 미리 주장하지 않는다. 후보 채택, 추가 유전자 범위 탐색, 무기한 worker를 약속하지 않는다.

native source `38f005ecefc2c432cd6424a06f599f93682cc202`,physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,scout implementation/preregistration `a610b68b746276ec1e38e06acfb66fd880be41e3`를구분한다. 이번docs해시검증은시뮬레이션재현/수렴/실험검증이아니며새물리fieldmap을생성하지않았다.

- [summary](cloud-original-drive-refinement-20261021T222000Z/summary.json),SHA256 `a7d89ab643aa5be6cb476685b13cd99228d890a1125b6c4856849e79ff68349b`
- [decision](cloud-original-drive-refinement-context-20261021T222000Z/decision.json),SHA256 `94a32af5c4a8b6d4cd8d8ab72321ab0caca7d7b00deebf290a31b2c190e5e720`
- [preregistration](cloud-original-drive-refinement-context-20261021T222000Z/preregistration.json),SHA256 `fd975d7e9852adec7728fde4d8ebac17f3d89d245c40babc78fff13f76905be0`
- [queue](cloud-original-drive-refinement-context-20261021T222000Z/queue/summary.json),SHA256 `19dce714c21f9c6641654c2450fe5cfb7d54d0fd670c09639203410428e2ebed`
- [feedback_after](cloud-original-drive-refinement-context-20261021T222000Z/feedback-after.json),SHA256 `9bc6919482b5120022ea94f0af626389c97277a4db71bc5bb4629c00e5d2b300`
- [cached_volume](cloud-adjacent-cross-20261021T164000Z/volume.json),SHA256 `5ae3c3bc95021024109e6b3c0f4985b978b8a4262c4a7cd3441aca819d6bb725`
- [proxy_search](cloud-original-drive-refinement-20261021T222000Z/proxy-search.json),SHA256 `3dca3c101b9f344a7fdee0746829c6617588749f5644dada0772f515f353b062`
- [old_proxy_cache](cloud-original-cached-drive-20261021T221000Z/proxy-search.json),SHA256 `246591bc0aa3cba9aae91ced46f926a7cc755972056fa6590e95a8cdefbf74dc`
- [old_summary](cloud-original-cached-drive-20261021T221000Z/summary.json),SHA256 `a3850a5e98227ecda7b9181d24d983c92745d82b5da765579e40223cfd7e3082`

[과거strong8GUI](CLOUD_COHERENT_DRIVE_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다.
