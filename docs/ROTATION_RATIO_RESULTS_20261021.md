# 작업 1: 회전 형상의 출력 진폭 비율 4조건 (2026-10-21)

4개 조건 모두 **채택하지 않는다**. 원래 square의 canonical skin8에서 목표 ROI 평균·P10과 표면 P95는 전부 실패했다. 그 외 고변조 체적 조건은 각각 통과/실패가 다르므로 개별 저장 판정을 보존했다. cached 회전1:1을 이전 비대칭 부모보다 개선된 형상으로 취급하지 않는다.

[오프라인6행 GUI](CLOUD_ROTATION_RATIO_RESULTS_20261021.html) · [정확한 값/5모드/해시 brief](ROTATION_RATIO_RESULTS_20261021.result-brief.json) · [원본 summary](cloud-rotation-ratio-20261021T180500Z/summary.json)

## 고정 조건과 raw 정의

이미 계산한 `asym-return2-rot90-xy80`의 형상·mask·물성·접촉·배선·위상을 유지하고 두 출력 진폭만 변경했다. D50 mm, SC/dermis/fat/muscle0.1/5/5/15 mm, 윗면 총900 mm², XY0.625/SC2/bulk14·14·40이다. 물리4패드/독립2출력/공통GND/50 Ω, pad0→out0(3000/9000 Hz), pad1→out1(3030/9090 Hz), pad2·3→GND이다. 각 비구동 주파수는0 V through50 Ω, 위상0°이며 beat30 Hz다. 초기2/2.01 kHz 조건과 별도다. cached native basis 재합성4조건으로 **새 PDE0**이다.

선언 Vpp 벡터는 [0.5,1], [√0.5,1], [1,√0.5], [1,0.5]이다. 신규 `raw_declared_Vpp`는 동일1 Vpp 조건이 아니다. cached 원래 square·회전1:1은 `raw_1Vpp=[1,1]`이다. Vpp는50 Ω 앞 square_3h 실제 전체 파형 max−min이며 기본파 Vpp나2√2RMS가 아니다. 각 condition의 analytic source waveform 검사가 저장 PASS이고 하드웨어 보정은 미검증이다.

기본 ROI는 중심r≤5 mm·깊이15–20 mm, x/y수평·+z안쪽이다. maxTIS는 기본파만2074방향 표본 최대(연속 방향 최대의 하한), fixedTIS는 (X+Y)/√2 기본파 변조, full RMS는3000/3030/9000/9090 Hz 전체4선 전기장 RMS다. 가중 ECDF/fractional ROI/exact z overlap과 기존 staircase geometry를 유지한다. SC 경계 전역 최대를 깊이 집중으로 해석하지 않는다.

## 선언된 raw 벡터 (같은 전압 비교가 아님)

| 조건 | actual[out0,out1] Vpp | ROI mean / P10 (V/m) | CV | max (V/m) | 표면 P95 / 전체 비표적 P95 (V/m) | full RMS mean / P10 (V/m) |
|---|---|---:|---:|---:|---:|---:|
| 원래 4-square 기준 | [1.0, 1.0] | 4.06184894 / 3.64573574 | 0.0807616216 | 4.97132719 | 25.2592218 / 23.4357186 | 2.30694946 / 2.10466937 |
| 회전 cached 1:1 | [1.0, 1.0] | 4.42654541 / 3.98719667 | 0.0793127416 | 5.38131052 | 32.5014435 / 26.1632633 | 2.48930139 / 2.26800249 |
| rotation-ratio-o0-half | [0.5, 1.0] | 2.38612379 / 2.0868594 | 0.10015942 | 3.08987581 | 22.7417053 / 21.5668325 | 1.9515299 / 1.75469554 |
| rotation-ratio-o0-sqrt-half | [0.7071067811865476, 1.0] | 3.37447842 / 2.95126487 | 0.100151462 | 4.33983304 | 27.2001305 / 23.2630706 | 2.14630937 / 1.95379965 |
| rotation-ratio-o1-sqrt-half | [1.0, 0.7071067811865476] | 3.29318499 / 2.87622958 | 0.100858338 | 4.28704929 | 26.901394 / 23.664761 | 2.16405389 / 1.96835982 |
| rotation-ratio-o1-half | [1.0, 0.5] | 2.32863344 / 2.03380144 | 0.100858338 | 3.03140162 | 22.7731679 / 21.8046934 | 1.98074144 / 1.77961782 |

## 동일8개 피부·접촉 부담 (skin8)

| 조건 | actual[out0,out1] Vpp | ROI mean / P10 (V/m) | CV | max (V/m) | 표면 P95 / 전체 비표적 P95 (V/m) | full RMS mean / P10 (V/m) |
|---|---|---:|---:|---:|---:|---:|
| 원래 4-square 기준 | [1.0, 1.0] | 4.06184894 / 3.64573574 | 0.0807616216 | 4.97132719 | 25.2592218 / 23.4357186 | 2.30694946 / 2.10466937 |
| 회전 cached 1:1 | [0.9894546450470344, 0.9894546450470344] | 4.37986591 / 3.94515026 | 0.0793127416 | 5.32456269 | 32.1587042 / 25.8873624 | 2.46305082 / 2.2440856 |
| rotation-ratio-o0-half | [0.5817425912543377, 1.1634851825086754] | 2.77621967 / 2.42802999 | 0.10015942 | 3.59502473 | 26.4596371 / 25.09269 | 2.27057612 / 2.04156226 |
| rotation-ratio-o0-sqrt-half | [0.7886382095108485, 1.1153028516958763] | 3.7635654 / 3.29155412 | 0.100151462 | 4.84022816 | 30.3363831 / 25.945369 | 2.39378496 / 2.17907832 |
| rotation-ratio-o1-sqrt-half | [1.1457027360408991, 0.810134173878501] | 3.77301105 / 3.2953041 | 0.100858338 | 4.9116841 | 30.8210007 / 27.1127814 | 2.47936247 / 2.25515524 |
| rotation-ratio-o1-half | [1.2175598747637433, 0.6087799373818716] | 2.83525063 / 2.47627503 | 0.100858338 | 3.69091298 | 27.7276955 / 26.5485197 | 2.4116713 / 2.16679125 |

skin8는 원래 square의 접촉Jmax/J95·접촉전압·SC/접촉손실·SC+dermis 체적vectorJmax/J95·SC+dermis손실의8개 한도이다. source power와1 Vpp ceiling은 포함하지 않으므로 표의 실제 출력은1 Vpp를 넘을 수 있다. legacy는 이 둘을 추가한다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드, 활성 limiter, 절대목표·비표적·전류·손실·출력별signed power·40개 무부하 예측을 GUI/brief/원본condition에 연결했다. 수치 한도는 인체 안전 한계가 아니다.

## 신규4조건의 고정8개 screen

각 gate 값·변화율·판정은 원본에 저장된 것을 복사했으며 재계산하지 않았다. 기준은 원래 square이며 cached 두 control을 이번 신규 screen으로 재심사하지 않았다.

### rotation-ratio-o0-half

| gate | 단위 | 기준 | 후보 | 변화 % | 저장 판정 |
|---|---|---:|---:|---:|---|
| primary_maxTIS_mean | V/m | 4.06184894 | 2.77621967 | -31.6513315 | FAIL |
| primary_maxTIS_p10 | V/m | 3.64573574 | 2.42802999 | -33.4008232 | FAIL |
| surface_0_5_maxTIS_p95 | V/m | 25.2592218 | 26.4596371 | 4.75238426 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_mean | m3 | 7.76652902e-06 | 6.95194754e-06 | -10.4883594 | PASS |
| surface_0_5_high_volume_at_primary_r5_depth15_20_p10 | m3 | 8.20945313e-06 | 7.46392299e-06 | -9.08136173 | PASS |
| primary_complement_maxTIS_p95 | V/m | 23.4357186 | 25.09269 | 7.07028224 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_mean | m3 | 1.93996553e-05 | 1.77139914e-05 | -8.68914361 | PASS |
| primary_complement_high_volume_at_primary_r5_depth15_20_p10 | m3 | 2.11556557e-05 | 1.90391211e-05 | -10.0045803 | PASS |

활성 skin8 limiter: `bulk_skin_J_vector_RMS_max_A_m2`.

### rotation-ratio-o0-sqrt-half

| gate | 단위 | 기준 | 후보 | 변화 % | 저장 판정 |
|---|---|---:|---:|---:|---|
| primary_maxTIS_mean | V/m | 4.06184894 | 3.7635654 | -7.34354089 | FAIL |
| primary_maxTIS_p10 | V/m | 3.64573574 | 3.29155412 | -9.71495582 | FAIL |
| surface_0_5_maxTIS_p95 | V/m | 25.2592218 | 30.3363831 | 20.1002285 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_mean | m3 | 7.76652902e-06 | 7.96024833e-06 | 2.49428422 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_p10 | m3 | 8.20945313e-06 | 8.38082031e-06 | 2.08743731 | FAIL |
| primary_complement_maxTIS_p95 | V/m | 23.4357186 | 25.945369 | 10.7086557 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_mean | m3 | 1.93996553e-05 | 2.00027552e-05 | 3.10881777 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_p10 | m3 | 2.11556557e-05 | 2.18435649e-05 | 3.25165658 | FAIL |

활성 skin8 limiter: `bulk_skin_J_vector_RMS_p95_A_m2`.

### rotation-ratio-o1-sqrt-half

| gate | 단위 | 기준 | 후보 | 변화 % | 저장 판정 |
|---|---|---:|---:|---:|---|
| primary_maxTIS_mean | V/m | 4.06184894 | 3.77301105 | -7.11099541 | FAIL |
| primary_maxTIS_p10 | V/m | 3.64573574 | 3.2953041 | -9.61209642 | FAIL |
| surface_0_5_maxTIS_p95 | V/m | 25.2592218 | 30.8210007 | 22.0188052 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_mean | m3 | 7.76652902e-06 | 8.04516741e-06 | 3.58768238 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_p10 | m3 | 8.20945313e-06 | 8.44948382e-06 | 2.92383291 | FAIL |
| primary_complement_maxTIS_p95 | V/m | 23.4357186 | 27.1127814 | 15.6899939 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_mean | m3 | 1.93996553e-05 | 2.0362897e-05 | 4.96525175 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_p10 | m3 | 2.11556557e-05 | 2.23553878e-05 | 5.6709761 | FAIL |

활성 skin8 limiter: `bulk_skin_J_vector_RMS_p95_A_m2`.

### rotation-ratio-o1-half

| gate | 단위 | 기준 | 후보 | 변화 % | 저장 판정 |
|---|---|---:|---:|---:|---|
| primary_maxTIS_mean | V/m | 4.06184894 | 2.83525063 | -30.1980286 | FAIL |
| primary_maxTIS_p10 | V/m | 3.64573574 | 2.47627503 | -32.0774952 | FAIL |
| surface_0_5_maxTIS_p95 | V/m | 25.2592218 | 27.7276955 | 9.77256421 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_mean | m3 | 7.76652902e-06 | 7.18292411e-06 | -7.5143595 | PASS |
| surface_0_5_high_volume_at_primary_r5_depth15_20_p10 | m3 | 8.20945313e-06 | 7.64091518e-06 | -6.92540584 | PASS |
| primary_complement_maxTIS_p95 | V/m | 23.4357186 | 26.5485197 | 13.2822943 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_mean | m3 | 1.93996553e-05 | 1.82127734e-05 | -6.11805623 | PASS |
| primary_complement_high_volume_at_primary_r5_depth15_20_p10 | m3 | 2.11556557e-05 | 1.96876972e-05 | -6.9388465 | PASS |

활성 skin8 limiter: `bulk_skin_J_vector_RMS_p95_A_m2`.

## 전류·signed power·프로브·검증 범위

접촉 surface_J와 SC+dermis 체적 전체벡터 bulk_skin_J를 구분했다. SC/접촉/SC+dermis/source power는 별도다. signed ideal-source/metal-delivered/50 Ω loss를 출력별·주파수별 보존했다. 비구동 주파수의 음의 금속단 전달전력도 생략하지 않는다. 실제 출력단의 흡수·compliance·위상·파형 보정은 미검증이다. 출력RMS전류합은 공통GND귀환전류와 같은 양이 아니다.

신규4조건 각각 native-phi40개 검사와 field waveform audit가 저장 PASS다. raw40개는 깊이5/10/15/20 × 중심·X/Y±5 mm의5개 중심 ×X/Y차동방향이며 tip gap5 mm다. probe중심간격과 tip gap을 구분한다. 전체파형Vpp bounds/RMS/기본파envelope·스펙트럼 및5정규화별40개 unloaded 예측은 원본condition/probes에 연결한다. 실제 ETA5001/DSOX1202A switch·부하·보정과 팬텀port impedance가 미검증이므로 loaded 결과는 보류다. C1·생리적 활성 동등성을 주장하지 않는다. native5개 방정식 검사와8개 비교는 mesh/SC/XY/bulk/edge/contact 수렴 또는 실험 검증이 아니다. PBS계면을 실제피부 검증값으로 취급하지 않는다.

- `baseline-square15-xy80` / source case `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, config SHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/summary JSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json), SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [raw unloaded40 JSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `asym-return2-rot90-xy80` / source case `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary JSON](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/summary.json), SHA256 `8de92edabdcdbe5a0ec7601882ce497e7d2a6c480fa478dbb71853f281041933`
  - [raw unloaded40 JSON](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/probes.json), SHA256 `24c7b539964ab0a24e18ea3c999758650aa898c40684cf186dd6aab131e46932`
- `rotation-ratio-o0-half` / source case `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o0-half/condition.json), SHA256 `d8274dce2250f362fd431a102aefc9c01f6de0756638d9777c4db50ba557c1d8`
  - [raw unloaded40 JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o0-half/probes.json), SHA256 `102cd6b0a210ee1bf44299afacc98b4d9198e9e2cf44f14720d81fb62041fa7d`
- `rotation-ratio-o0-sqrt-half` / source case `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o0-sqrt-half/condition.json), SHA256 `1e49449b7697228484973d6aae6017e0e00732b669715ca682fa1119fb0c5ba2`
  - [raw unloaded40 JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o0-sqrt-half/probes.json), SHA256 `04c135ec839055943539e5acafc6d1bd98bdf9b22cb6717f8de36ff85e94f432`
- `rotation-ratio-o1-sqrt-half` / source case `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o1-sqrt-half/condition.json), SHA256 `8c3001ffbc24e579a2afced0081130a131b7fdff1b57e9f55cbdc6fe10cf6246`
  - [raw unloaded40 JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o1-sqrt-half/probes.json), SHA256 `a8340784e65485fb1e6b7e02fa280497e480874069ee316294a1bddaa0095e46`
- `rotation-ratio-o1-half` / source case `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o1-half/condition.json), SHA256 `c303f1fe2b16a3784526c8cceb6cf0b2dc113b3006d89e6e40121724cacf9cdb`
  - [raw unloaded40 JSON](cloud-rotation-ratio-20261021T180500Z/rotation-ratio-o1-half/probes.json), SHA256 `6393e24e399044e265557e212a5eee936599b1165acd80e5c1b466e74dd5898e`

기하 physical model `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`, native source `3381113eeee81b0925890d5d4d17496764901fd5`, scout source `3fbeb15`/preregistration source `39d9605c416ab8dc48e5a4ca2c1b0b9c896278be`를 구분한다. 로컬 native archive 링크는 GitHub에서 파일 제공을 보장하지 않는다. 문서 생성은 JSON/설정 해시 확인·저장값 복사만 수행했으며 native E/phi/NPZ를 읽거나 계산을 재현하지 않았다. 해시 검증과 시뮬레이션 재현·수렴·실험 검증을 구분한다.

## 실제 실행·발행과 후속 상태

[큐](cloud-rotation-ratio-context-20261021T180500Z/queue/summary.json)는 `completed_preregistered_queue`, 4조건과GET·발행3단계 모두exit0이다. 실제 scout wall `46.88431070200022 s`, peakRSS `534548480 bytes`, CPU1, 새PDE0이다. [발행 영수증](cloud-rotation-ratio-context-20261021T180500Z/rotation-ratio-publication-20261021T180500Z.json)은 `published_completed_batch`, `2026-10-21T17:35:55.672328+00:00`, commit `f5bf9c67952a5f29156ed7df16eb0aae9334442d`다. root선정과 동료의 특정후보 승인을 구분하며 [decision](cloud-rotation-ratio-context-20261021T180500Z/decision.json)과 summary의 실제 feedback 증거를 보존한다.

후속 amplitude interval bound 진단은 이 snapshot 작성 시 **미실행**이다. 네 표본의 실패만으로 전체 양의 진폭 계열을 배제하지 않는다. [이전 회전/부모3행 GUI](CLOUD_ONE_RETURN_ROTATION_RESULTS_20261021.html)와 [과거44조건/4·8·12·16패드 snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)은 그대로 보존한다. 이번 화면은 새 공간 맵을 생성하지 않은 JSON 표다.
