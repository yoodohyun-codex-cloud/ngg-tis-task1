# 작업1: Original command mesh sensitivity (2026-10-21)

선택된 original-refine-3e018f8a317a 구동을 기존 native SC4/XY-coarse basis에 적용한 2수준 독립 진단이다. 새 PDE/최적화/fine 재계산 없이 실제 cached 복소 E/φ로 새 두 격자 지표·40프로브를 계산했다. 첫행 original 4-square fine control과 둘째행 선택 fine 결과는 기존 저장 JSON을 불변 재사용한다. SC4 20/20 PASS, XY coarse 14/20 PASS·6개 FAIL이며 양쪽 raw/fixed-fine skin8의 16개 screen 상태는 모두 불변이다. 목표 mean/P10 두 항목은 여전히 FAIL이므로 채택하지 않는다.

[4행 오프라인 GUI](CLOUD_ORIGINAL_MESH_SENSITIVITY_RESULTS_20261021.html) · [정확한5모드·검증brief](ORIGINAL_MESH_SENSITIVITY_RESULTS_20261021.result-brief.json) · [실제summary](cloud-original-mesh-sensitivity-20261021T223000Z/summary.json)

## Fine 진폭 고정과 실제 물리 조건

새 두 조건의 fixed_fine_amplitude_modes는 fine의 계수·ONEglobal g·5개 amplitude A를 정확히 고정한다. equalI/equalP/skin8/legacy는 역사적 FINE mode ID일 뿐 새 격자에서 전류/전력/피부부담을 다시 맞췄다는 뜻이 아니다. 새 mesh에 top normalizations를 만들거나 rematch하지 않았다. 특히 frozen fine skin8 A=1.0934817703564808, actual source whole-Vpp upper out0/out1=1.089258573660034/1.0934817703564808 V로 고정되며 raw1Vpp 향상이 아니다. 모든 모드의 실제 전류·전력·8cap ratio를 따로 표시한다.

D50mm, SC/dermis/fat/muscle=0.1/5/5/15mm, 윗면 square225mm²×4=900mm², source0SW(−10,−10)/source1NE(+10,+10), GND2SE(+10,−10)/GND3NW(−10,+10), 물리4pads/독립2outputs/공통GND1/50Ω 및 다른주파수0Vthrough50Ω를 유지한다. fine XY.625 SC2 bulk14/14/40 351680cells, SC4는 validation.sc_cells만2→4(361728cells), XY coarse는 h_mm .625→1.25 및 대응 mask path/SHA만 바뀐다(88480cells). 근본 물성/접촉/기하/배선은 동일하고 물리 사각형 mask는 격자에 맞게 재표현된다.

주ROI r≤5mm·깊이15–20mm, x/y 수평·+z 팬텀 안쪽이다. maxTIS=기본파3000/3030Hz 실제 SHA고정2074방향 표본 최대(연속방향 최대의 하한), fixedTIS=(X+Y)/√2방향, fullRMS=모든 활성 주파수 벡터 RMS다. 새 drive9000/9090계수0, 첫square3h행만 고조파가 활성이다. fractional native ROI/h²dz·가중ECDF·exact z overlap 및 fine original square의 cutoff를 유지한다. 새 mesh 실제 표현 체적은 analytic volume/fine 체적으로 강제 정규화하지 않는다. SC 경계 전역 hotspot을 깊이 집중으로 해석하지 않는다.

## Raw fine 진폭 고정

|행|native mesh|fine A|sourceVpp actualbounds/cachednominal|ROImean/P10V/m|CV|surface/complementP95V/m|fullRMSmean/P10V/m|
|---|---|---:|---|---:|---:|---:|---:|
|original square3h · fine control|XY.625 / SC2 / bulk14,14,40 /351680cells|1|{"cached_nominal_Vpp_each": 1.0}|4.0618489416/3.64573573913|0.0807616216391|25.2592218317/23.4357185812|2.30694946283/2.10466937124|
|selected 3e · fine SC2|XY.625 / SC2 / bulk14,14,40 /351680cells|1|[[0.9961371089748255, 0.9961378444424639], [0.9999992474456438, 1.0]]|3.66859281955/3.28795789274|0.0818473705306|23.0894140122/21.3956081307|1.98504322416/1.80946408588|
|selected 3e · SC4 same command|XY0.625 / SC4 / bulk14,14,40 /361728cells|1|[[0.9961371089748255, 0.9961378444424639], [0.9999992474456438, 1.0]]|3.66860017908/3.28796370154|0.0818476329954|23.0925164225/21.3951687429|1.9850478285/1.80946787436|
|selected 3e · XY1.25 same command|XY1.25 / SC2 / bulk14,14,40 /88480cells|1|[[0.9961371089748255, 0.9961378444424639], [0.9999992474456438, 1.0]]|3.67875709546/3.30223421259|0.0818632068888|22.8338908565/21.257822668|1.99158216899/1.81785396305|

## Frozen fine skin8 진폭 고정 — 새 격자 burden rematch 아님

|행|native mesh|fine A|sourceVpp actualbounds/cachednominal|ROImean/P10V/m|CV|surface/complementP95V/m|fullRMSmean/P10V/m|
|---|---|---:|---|---:|---:|---:|---:|
|original square3h · fine control|XY.625 / SC2 / bulk14,14,40 /351680cells|1|{"cached_nominal_Vpp_each": 1.0}|4.0618489416/3.64573573913|0.0807616216391|25.2592218317/23.4357185812|2.30694946283/2.10466937124|
|selected 3e · fine SC2|XY.625 / SC2 / bulk14,14,40 /351680cells|1.09348177036|[[1.0892577694395789, 1.089258573660034], [1.093480947452011, 1.0934817703564808]]|4.01153937104/3.59532201741|0.0818473705306|25.2478533106/23.3957074566|2.17060857898/1.97861599203|
|selected 3e · SC4 same command|XY0.625 / SC4 / bulk14,14,40 /361728cells|1.09348177036|[[1.0892577694395789, 1.089258573660034], [1.093480947452011, 1.0934817703564808]]|4.01154741855/3.59532836923|0.0818476329954|25.2512457396/23.3952269941|2.17061361375/1.97862013466|
|selected 3e · XY1.25 same command|XY1.25 / SC2 / bulk14,14,40 /88480cells|1.09348177036|[[1.0892577694395789, 1.089258573660034], [1.093480947452011, 1.0934817703564808]]|4.02265382146/3.61093291291|0.0818632068888|24.9684433979/23.245041565|2.17775879596/1.98779016977|

5개 mode의 실제 current/power/skin·contact cap ratio, fixedTIS/fullRMS, wholeXY 보조ROI, 평균/P10/CV/max/전체hotspot·fixed cutoff 이상 체적은 GUI/brief에 보존했다. 실제 equalcurrent/equalpower/equalburden을 새 mesh에 주장하지 않는다.

## 실제 민감도 판정

등록 민감도는 raw 및 frozen fine skin8 각각10개=20개 metric과 각8개=16개 screen status다. mean/P10 relative1%, 비표적P95·J95·power relative2%, status flip허용0이며 수치 진단 기준이다. SC4 최대 상대변화0.0001827984903058971(0.01827984903058971%), 실패없음. XY 최대0.09531025411755592(9.531025411755592%); raw와fixedskin8 각각 surface_J_RMS_p95_A_m2, SC_power_W, contact_power_W가 FAIL이다. 나머지 metric은 원본 판정대로 보존한다. 양쪽 status flip0/16이 mesh metric 실패를 무효화하지 않는다.

|조건|20metrics 통과|최대 absolute relative change|16screen status flips|최종 진단|
|---|---:|---:|---:|---|
|selected 3e · SC4 same command|20/20|0.0001827984903058971|0/16|PASS|
|selected 3e · XY1.25 same command|14/20|0.09531025411755592|0/16|FAIL|

실패 metric은 두 amplitude에서 각각 `surface_J_RMS_p95_A_m2`, `SC_power_W`, `contact_power_W`이며 원본20개 비교값/허용차와16개 상태 비교를 GUI/brief에 그대로 보존했다.

|조건|mean|P10|surfaceP95|surface≥fine mean volume|surface≥fine P10 volume|complementP95|complement≥fine mean volume|complement≥fine P10 volume|
|---|---|---|---|---|---|---|---|---|
|selected 3e · fine SC2|FAIL|FAIL|PASS|PASS|PASS|PASS|PASS|PASS|
|selected 3e · SC4 same command|FAIL|FAIL|PASS|PASS|PASS|PASS|PASS|PASS|
|selected 3e · XY1.25 same command|FAIL|FAIL|PASS|PASS|PASS|PASS|PASS|PASS|

## Native 표현 체적·대수 gate·복원/계측 범위

원래 square3h/sine/triangle3h의 과거 XY FAIL은 그대로 남는다. 새 2수준 선택구동 진단은 이전 실패 종료·bulk/edge/contact/fullconvergence·수치검증 승격·실험검증·채택을 뜻하지 않는다. 각 cached native basis의 5개 대수적 검증은 source-bound producer 수치영수증으로 별도 표시하며 이번 report가 다시 판정하지 않았다. 새 bulk skinJ는 각 격자의 native 방향별 density에서 실제 재계산됐고 다른 fullskin audit 값을 혼합하지 않았다. PBS 임피던스의 실제피부전이/접촉·계측·AWG흡수·생리적 활성화·안전·COMSOL5.3a 및 fullnative 독립영구백업은 미검증이다. 수치 cap은 인체안전 한계가 아니다.

XY coarse의 total/wholeXY/surface 표현 체적은 원래 fine과 달라지며 실제값을 보존했다. 주ROI와 비표적·RMS를 analytic/fine volume으로 강제 정규화하지 않았다. SC4 체적일치 검사는 별도 저장판정이다.

새 두 조건은 float64 전체 체적 지표를 실제 RAM 계산했지만 신규 scalar NPZ/XYZ archive/field map은 저장하지 않았다. 산출물은 condition.json, probes.json, native-volume-metrics.json이다. source-bound reconstruction recipe는 있으나 독립 export replay를 실행하지 않았고 실행가능 scalar export CLI도 등록되지 않았다. 과거 raw/NPZ를 삭제·대체하지 않았다. fine native arrays를 다시 decode하거나 source를 재정규화하지 않았다.

새 조건별 raw40 및 각5모드40 nativeφ 두 점 차동 예측·field waveform audit가 통과했다. 깊이5/10/15/20mm×중심/X±5/Y±5의5개 probe 중심×X/Y방향, tipgap5mm이다. probe 중심과 팁 간격을 구분한다. 무부하 Vpp/RMS/envelope/spectrum/source·probe IDs와 SHA를 링크한다. ETA5001/DSOX의 실제 switch/portZ·부하·대역폭·감쇠 보정은 미검증이며 loaded 예측을 만들지 않았다.

실제 worker calculated_unadopted; wall 15.316130772000179s, peakRSS 496185344bytes,CPU1,newPDE0. Queue completed_preregistered_queue의 모든 두 stage exit0. Publication 완료영수증은 작성시점 별도 확인하지 않아 발행 commit을 추정하지 않았다. 다음 계산/진단/채택을 시작·완료로 미리 표시하지 않는다.

이 보고서는 docs JSON을 복사·대조하고 저장 flag/상대변화의 최대 및 실패목록만 집계했다. 새로운 필드/정규화/수치 gate를 계산하거나 native/NPZ를 읽지 않았다. 문서 해시 일치는 시뮬레이션 독립재현·전체수렴·실험·영구백업 검증이 아니다.

## 출처

- [summary](cloud-original-mesh-sensitivity-20261021T223000Z/summary.json), SHA256 `b4ec4b8d053e62256b4a3070e5da2918277e9a8cf32bc4092fefe7a678d18bbb`
- [queue](cloud-original-mesh-sensitivity-context-20261021T223000Z/queue/summary.json), SHA256 `119701f00bf134729b9ffdd639a2e6f27d47d95f458eb0c4186a5a0241df623c`
- [decision](cloud-original-mesh-sensitivity-context-20261021T223000Z/decision.json), SHA256 `9975cebecd428a30970e8c018e269d0c9e747ef64a4a3ca4f757fc8cc1d7fcaa`
- [feedback_after](cloud-original-mesh-sensitivity-context-20261021T223000Z/feedback-after.json), SHA256 `a6448bcd6540570bbcc6b15e36786f7e4a2a0820439312584445247211e57392`
- [preregistration](cloud-original-mesh-sensitivity-context-20261021T223000Z/preregistration.json), SHA256 `a6c34949235783710cfa131c4f08867a4eeba4d58d4475ec1c1b3a38f4c135b9`
- [selected_fine_condition](cloud-original-drive-refinement-20261021T222000Z/original-refine-3e018f8a317a/condition.json), SHA256 `1e6b9dc90d1032d76d247567f71c62cf2d3fe4d6b28ad746e3b2cc102b61f366`
- [selected_fine_summary](cloud-original-drive-refinement-20261021T222000Z/summary.json), SHA256 `a7d89ab643aa5be6cb476685b13cd99228d890a1125b6c4856849e79ff68349b`
- [original_mesh_failures](cloud-restart-20261020/mesh-convergence.json), SHA256 `1577604f09923f30a998608d5b65fe8bc28f1fc7817164ae06e11316672c4f69`
- [fine_report_snapshot](ORIGINAL_DRIVE_REFINEMENT_RESULTS_20261021.result-brief.json), SHA256 `6cfb0efd149b061180a29912bf62e2cb2e7b0aa21a9e41b26e786f741f71dabd`
- `baseline-square15-xy80`: sourcecase `baseline-square15-xy80`,run `cloud-mesh-c1-20261019T190000Z`,sourcecommit `38f005ecefc2c432cd6424a06f599f93682cc202`,configSHA `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`; [condition/upstream sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json),SHA `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`; [unloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),SHA `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`.
- `original-refine-3e018f8a317a`: sourcecase `baseline-square15-xy80`,run `cloud-mesh-c1-20261019T190000Z`,sourcecommit `38f005ecefc2c432cd6424a06f599f93682cc202`,configSHA `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`; [condition/upstream sourceJSON](cloud-original-drive-refinement-20261021T222000Z/original-refine-3e018f8a317a/condition.json),SHA `1e6b9dc90d1032d76d247567f71c62cf2d3fe4d6b28ad746e3b2cc102b61f366`; [unloaded40](cloud-original-drive-refinement-20261021T222000Z/original-refine-3e018f8a317a/probes.json),SHA `1a4c7eac1a2ab497388d71b1384e569babbb544efe283b4f577191994922798b`.
- `original-refine-3e018f8a317a-sc4-same-command`: sourcecase `baseline-square15-sc4`,run `cloud-mesh-c1-20261019T190000Z`,sourcecommit `38f005ecefc2c432cd6424a06f599f93682cc202`,configSHA `858132f1f2e15c35cdcfa84a05df99e7690cc760d40d9ea73497b88ae61fea5c`; [condition/upstream sourceJSON](cloud-original-mesh-sensitivity-20261021T223000Z/original-refine-3e018f8a317a-sc4-same-command/condition.json),SHA `ff0e1b5f4b9ab2ff55079c9f2cd24a8239f51087f315555e63866a4a1d9c5ecb`; [unloaded40](cloud-original-mesh-sensitivity-20261021T223000Z/original-refine-3e018f8a317a-sc4-same-command/probes.json),SHA `297f8068b9f3446e3599309b1b93b89e23ead6a2d07257897da1de63ca435b9f`.
- `original-refine-3e018f8a317a-xy_coarse-same-command`: sourcecase `baseline-square15-coarse`,run `cloud-baseline-20261019T185900Z`,sourcecommit `a4636ec0b1f04c03696eb647307d5c53b2eef5f8`,configSHA `f8d6d232a9c47364af0815874805d4ae8373be61d78523b94d04e3b1c539e111`; [condition/upstream sourceJSON](cloud-original-mesh-sensitivity-20261021T223000Z/original-refine-3e018f8a317a-xy_coarse-same-command/condition.json),SHA `0420a9cc0af1f2f19ceb9073ad831a0e79336e7232e874747d4d2017fe9c35c3`; [unloaded40](cloud-original-mesh-sensitivity-20261021T223000Z/original-refine-3e018f8a317a-xy_coarse-same-command/probes.json),SHA `91284719707c9b2a3b57bd9c87e2287acd158263d766431196774e4d17f05627`.

[이전fine refinement GUI](CLOUD_ORIGINAL_DRIVE_REFINEMENT_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을 보존한다. 새 격자맵은 생성하지 않았다.
