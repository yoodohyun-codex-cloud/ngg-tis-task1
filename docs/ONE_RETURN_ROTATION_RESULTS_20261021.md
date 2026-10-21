# 작업 1: 귀환 패드 하나의 90° 회전 결과 (2026-10-21)

신규 `asym-return2-rot90-xy80`는 **채택하지 않는다**. 동일 skin8 부담에서 목표 ROI 평균·P10은 원래 square 기준보다 높지만, 표면·전체 비표적의 6개 고정 조건을 모두 실패했다. 저장된 8개 판정 중 목표 2개만 통과했으며, 계산 완료를 깊이 집중·수렴·실험 검증 완료로 승격하지 않는다.

[오프라인 3행 GUI](CLOUD_ONE_RETURN_ROTATION_RESULTS_20261021.html) · [정확한 값/5모드/해시 brief](ONE_RETURN_ROTATION_RESULTS_20261021.result-brief.json) · [원본 volume](cloud-one-return-rotation-context-20261021T174000Z/volume.json) · [신규 조건 8개 screen](cloud-one-return-rotation-context-20261021T174000Z/screen.json)

## 조건과 한 번의 물리적 회전

D50 mm, SC/dermis/fat/muscle 0.1/5/5/15 mm, 윗면 부착을 유지했다. 4개 물리 패드, 2개 독립 출력, 공통 GND, 출력저항 50 Ω이다. pad0→out0, pad1→out1, pad2·3→GND이며 다른 주파수의 출력단은 0 V through 50 Ω다. 이 결과는 3/3.03 kHz square_3h 및 9/9.09 kHz 고조파이고, 초기 2/2.01 kHz 조건과 별도로 추적한다. raw nominal1 Vpp 정의를 보존했다.

원래 square→cached 비대칭 부모는 형상·면적 배분이 함께 달라진 비교다. 부모→신규에서는 (+10,−10) mm의 **GND pad2만 +90° 한 번 회전**했다. 15×11.25→11.25×15 mm이며 operative rotation은 0°로 기록하여 이중 회전하지 않는다. pad0·1·3과 배선·물성·구동은 그대로다. 부모/신규 면적은 281.25/281.25/168.75/168.75 mm², 총900 mm²; face 수720/720/432/432, partial faces0, clipping·재정규화 없음이다. full faces는 가장자리·접촉 수렴의 증거가 아니다.

XY0.625 mm / SC2 / bulk14·14·40 / 351680 cells의 같은 격자다. [회전 mask proof](cloud-one-return-rotation-context-20261021T174000Z/prepared-inputs/rotation-mask-proof.json)를 보존했다.

## 원시 동일 전압

| 조건 | 각 출력 nominal Vpp | ROI mean / P10 (V/m) | CV | max (V/m) | 표면 P95 / 비표적 P95 (V/m) | ROI full RMS mean / P10 (V/m) |
|---|---:|---:|---:|---:|---:|---:|
| 원래 4-square 기준 | 1 | 4.06184894 / 3.64573574 | 0.0807616216 | 4.97132719 | 25.2592218 / 23.4357186 | 2.30694946 / 2.10466937 |
| 비대칭 부모 (cached) | 1 | 4.42904483 / 3.992963 | 0.0787701521 | 5.37867676 | 32.5182928 / 26.1477161 | 2.48887298 / 2.26782513 |
| 귀환 pad2 +90° (신규) | 1 | 4.42654541 / 3.98719667 | 0.0793127416 | 5.38131052 | 32.5014435 / 26.1632633 | 2.48930139 / 2.26800249 |

## 동일 8개 피부·접촉 부담 (skin_contact_only)

| 조건 | 각 출력 nominal Vpp | ROI mean / P10 (V/m) | CV | max (V/m) | 표면 P95 / 비표적 P95 (V/m) | ROI full RMS mean / P10 (V/m) |
|---|---:|---:|---:|---:|---:|---:|
| 원래 4-square 기준 | 1 | 4.06184894 / 3.64573574 | 0.0807616216 | 4.97132719 | 25.2592218 / 23.4357186 | 2.30694946 / 2.10466937 |
| 비대칭 부모 (cached) | 0.989726667 | 4.38354378 / 3.95194196 | 0.0787701521 | 5.32341982 | 32.1842216 / 25.8790919 | 2.46330396 / 2.24452701 |
| 귀환 pad2 +90° (신규) | 0.989454645 | 4.37986591 / 3.94515026 | 0.0793127416 | 5.32456269 | 32.1587042 / 25.8873624 | 2.46305082 / 2.2440856 |

skin8는 접촉 Jmax/J95·접촉전압·SC/접촉 손실·SC+dermis 체적 벡터 Jmax/J95·SC+dermis 손실의 8개 기준 한도다. 신규 활성 한도는 `bulk_skin_J_vector_RMS_p95_A_m2`다. source power 및1 Vpp ceiling은 포함하지 않는다. legacy는 이 둘을 추가한다. 원시 동일전압/동일 출력 RMS 전류합/동일 source power/skin8/legacy 5모드의 절대 목표값, 전류·접촉·피부·전력은 GUI와 brief에 모두 보존했다. 수치 한도를 인체 안전 한계로 해석하지 않는다.

기본 ROI는 중심 r≤5 mm, 깊이15–20 mm이고 x/y 수평, +z가 안쪽 깊이다. maxTIS는 기본파2074방향 표본 최대(연속 방향 최대의 하한), fixedTIS는 (X+Y)/√2 방향 기본파 변조, RMS는 전체4개 선의 전기장 RMS다. 단일 주파수·활성화와 동등한 양으로 취급하지 않는다. weighted ECDF와 fractional ROI/exact z overlap을 유지하며 이상 원기둥 체적으로 재정규화하지 않았다. wholeXY15–20 및 표면0–5/전체 비표적/전역 최대·고변조 체적을 GUI에 별도로 표시했다. SC 경계의 높은 전기장은 깊이 집중의 증거가 아니다.

## 고정 8개 비교 결과 (신규만)

| 저장 screen | 단위 | square 기준 | 신규 | 변화 % | 저장 판정 |
|---|---|---:|---:|---:|---|
| primary_maxTIS_mean | V/m | 4.06184894 | 4.37986591 | 7.82936485 | PASS |
| primary_maxTIS_p10 | V/m | 3.64573574 | 3.94515026 | 8.21273246 | PASS |
| surface_0_5_maxTIS_p95 | V/m | 25.2592218 | 32.1587042 | 27.3147068 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_mean | m3 | 7.76652902e-06 | 8.27178013e-06 | 6.50549447 | FAIL |
| surface_0_5_high_volume_at_primary_r5_depth15_20_p10 | m3 | 8.20945313e-06 | 8.62833705e-06 | 5.10245838 | FAIL |
| primary_complement_maxTIS_p95 | V/m | 23.4357186 | 25.8873624 | 10.461142 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_mean | m3 | 1.93996553e-05 | 2.09851725e-05 | 8.1729147 | FAIL |
| primary_complement_high_volume_at_primary_r5_depth15_20_p10 | m3 | 2.11556557e-05 | 2.352137e-05 | 11.1824206 | FAIL |

기준은 원래 동일 격자 square의 원시 절대 cutoff다. cached 부모·기준에 이번 신규 screen 판정을 덧씌우지 않았다. 신규 native5개 이산 방정식 검증은 통과했지만 SC/XY/bulk/edge/contact 수렴과 실험 검증은 보류다. PBS 계면 모델의 실제 피부 접촉 검증도 보류다.

## 무부하 측정 예측과 출처

세 조건 모두 같은 후보 ID/run ID의 raw square_3h native-phi 프로브 JSON을 연결했다. 각 40파형은 깊이5/10/15/20 mm × 십자5개 중심(0 및 X/Y ±5 mm) × X/Y 차동 방향이며 tip gap5 mm다. 중심 위치와 팁 간격은 서로 다른 정의다. 복소 전위 차이의 전체 파형/Vpp/RMS/변조·스펙트럼과 저장된 수치 검사는 원본 프로브 JSON에 있다. ETA5001/DSOX1202A 실제 스위치·부하·보정 및 팬텀 port impedance가 미검증이므로 loaded 결과를 새로 만들지 않았다. 이번 보고서에는 신규 C1·생리적 동등성 주장이 없다.

- `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, config SHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [raw unloaded40 JSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `asym-cross281p25-return168p75-xy80` / run `cloud-asymmetric-20261021T051000Z`
  - source `713c35c95114f7e478e04f5ada35d7efbfe49156`, config SHA256 `12afd425530b37dc0e7ab4f941d279277d00e23d3d3dd6acf81cc8fbdb98c584`
  - [raw unloaded40 JSON](../data-native/cloud-asymmetric-20261021T051000Z/postprocess/asym-cross281p25-return168p75-xy80/probes.json), SHA256 `2de7724b4bb29d9d91bfaa0291d3da3f1a25832f1d8abd7abf81bf77cf9eee12`
- `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [raw unloaded40 JSON](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/probes.json), SHA256 `24c7b539964ab0a24e18ea3c999758650aa898c40684cf186dd6aab131e46932`

모든 physical model 버전은 `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`이다. 로컬 native 링크는 GitHub에서 파일 제공을 보장하지 않는다. report·summary·probe JSON 및 설정 해시를 확인했으며, native E/phi/NPZ를 읽거나 계산을 재현한 것은 아니다. 파일 해시 검증과 시뮬레이션 재현·수렴·실험 검증을 구분한다.

## 실행·발행·피드백 상태

원래 [큐 summary](cloud-one-return-rotation-context-20261021T174000Z/queue/summary.json)는 `failed_preserved`로 유지한다. native/fullskin/register/volume/screen/GET 6단계는 exit0, 발행만 exit1이었다. root publisher spec에서 volume의 `inputs_sha256`와 screen의 report proof 키를 잘못 지정했다. [실패 disposition](cloud-one-return-rotation-context-20261021T174000Z/publication-failure-disposition.json), 원래 실패 영수증 및 spec을 보존했다.

별도 [metadata-only 복구 영수증](cloud-one-return-rotation-context-20261021T174000Z/one-return-rotation-recovery-publication-20261021T174000Z.json)은 `published_completed_batch`, `2026-10-21T17:24:37.730956+00:00` 완료, 발행 commit `312b346d9a65f467ed9467f2aaf7ab5a27a46f6c`이다. 새 PDE0, 과학 계산 재실행0이다. 원래 큐 성공으로 덮어쓰지 않는다.

피드백 `6321929825`의 보고 요구사항은 [적용 영수증](cloud-one-return-rotation-context-20261021T174000Z/feedback-application-commit.json)과 실제 적용 commit `48a7d5200ebd2bd199c1711b1f5c9eeb5d717e6a`에 연결했다. 특정 회전 설계의 동료 승인 또는 과거 구현의 인과적 공로를 주장하지 않는다. native source `3381113eeee81b0925890d5d4d17496764901fd5`, preregistration source `08228976abb68041dd53af2988a53ebd5ff4eb80`를 구분한다.

[과거44조건/4·8·12·16패드 GUI](CLOUD_VOLUME_RESULTS_20261021_v8.html) 및 [과거 fine grouped GUI](CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html)는 해당 과거 snapshot으로 보존한다. 이번 화면은 새 공간 맵을 생성하지 않은 JSON 표다. 이 보고서에서 다음 후보나 추가 수렴 계산이 시작되었다고 주장하지 않는다.
