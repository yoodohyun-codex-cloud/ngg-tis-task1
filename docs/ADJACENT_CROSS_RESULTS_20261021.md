# 4-pad square/cross × source-assignment 결과 — 2026-10-21

새 cross/adjacent 조건은 원본 square/opposite 기준보다 목표 변조 평균·P10이 낮고 표층·전체 비표적 지표가 높아 고정 8개 screen을 모두 통과하지 못했습니다. 피부·접촉 8개 부담을 맞춘 목표 mean/P10은 **3.244504 / 2.963020 V/m**이며 기준은 **4.061849 / 3.645736 V/m**입니다. 새 후보는 미채택입니다.

[새 4행 GUI](CLOUD_ADJACENT_CROSS_RESULTS_20261021.html) · [원 volume JSON](cloud-adjacent-cross-20261021T164000Z/volume.json) · [신규 1조건 screen](cloud-adjacent-cross-20261021T164000Z/screen.json) · [정밀값 compact brief](ADJACENT_CROSS_RESULTS_20261021.result-brief.json). GUI의 JSON 전용 렌더는 완료됐습니다([receipt](CLOUD_ADJACENT_CROSS_RESULTS_20261021.receipt.json)); 이는 수치 gate·수렴성 검증의 승격을 뜻하지 않습니다.

## 비교 범위

네 행은 원본 square/opposite, 기존 square/adjacent, 기존 cross/opposite 및 신규 cross/adjacent입니다. **새 PDE는 마지막 한 조건**이며, 다른 세 조건의 native 결과를 재사용했습니다. 이번 새 8-gate screen은 신규 cross/adjacent 한 조건에만 수행했습니다. Cached 행을 새 계산·새 판정으로 재표시하지 않습니다.

조건당 물리 패드 4개·독립 출력 2개·공통 GND 귀환 노드 1개, 총 접촉면적 900 mm²(패드당225 mm²)를 유지합니다. 50 Ω 출력저항과 타 주파수의 0 V/50 Ω 종단, 기본파3000/3030 Hz 및 명시적3차9000/9090 Hz를 유지했습니다. 실제 source pad를 opposite diagonal에서 adjacent bottom row로 바꾸며, 같은 shape 내에서 물리 접촉·형상·좌표·면적은 유지합니다. 새 cross의 solver pad 순서는 기존 physical `[0,2,1,3]`입니다. 독립 귀환 쌍으로 바꾸지 않았습니다.

팬텀 D50 mm와 0.1/5/5/15 mm 층, 윗면 부착, XY0.625 mm /SC2 /bulk14,14,40 /351,680 cells를 유지했습니다. Primary ROI는 중앙 반경5 mm·깊이15–20 mm이고 +z는 피부에서 안쪽 깊이입니다. 정규화·cutoff는 항상 원본 square/opposite에서 가져옵니다. PBS 접촉 surrogate는 실제 피부 검증값이 아닙니다.

## 저장된 절대 결과

maxTIS는 기본파의2074 표본 방향 최대값으로 연속 방향 최대의 하한입니다. RMS는 네 스펙트럼 선 전체 벡터 전기장 RMS이며 변조와 구분합니다. 아래 단위는 V/m(CV는 무차원), 숫자는 소수 여섯 자리로 반올림했습니다. 원 JSON 수치로부터 새 필드·정규화·gate를 계산하지 않았습니다.

### 동일 명목1 Vpp/출력

| 조건 | Vpp/출력 | ROI mean | ROI P10 | CV | ROI max | 0–5mm P95 | 비표적 P95 | ROI 전체 RMS mean / P10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Square / opposite 기준 | 1.000000 | 4.061849 | 3.645736 | 0.080762 | 4.971327 | 25.259222 | 23.435719 | 2.306949 / 2.104669 |
| Square / adjacent (cached) | 1.000000 | 3.403635 | 3.106298 | 0.070862 | 4.112651 | 52.298796 | 26.542941 | 2.390600 / 2.143209 |
| Cross / opposite (cached) | 1.000000 | 4.056640 | 3.642473 | 0.080468 | 4.960590 | 25.146861 | 23.573498 | 2.304339 / 2.103124 |
| Cross / adjacent (NEW) | 1.000000 | 3.398583 | 3.103731 | 0.070545 | 4.108175 | 49.736978 | 26.542618 | 2.387055 / 2.140205 |

### skin_contact_only: 원본 8개 피부·접촉 부담 이내

| 조건 | Vpp/출력 | ROI mean | ROI P10 | CV | ROI max | 0–5mm P95 | 비표적 P95 | ROI 전체 RMS mean / P10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Square / opposite 기준 | 1.000000 | 4.061849 | 3.645736 | 0.080762 | 4.971327 | 25.259222 | 23.435719 | 2.306949 / 2.104669 |
| Square / adjacent (cached) | 0.959213 | 3.264812 | 2.979602 | 0.070862 | 3.944909 | 50.165694 | 25.460338 | 2.293095 / 2.055794 |
| Cross / opposite (cached) | 0.969885 | 3.934474 | 3.532780 | 0.080468 | 4.811202 | 24.389566 | 22.863585 | 2.234945 / 2.039788 |
| Cross / adjacent (NEW) | 0.954664 | 3.244504 | 2.963020 | 0.070545 | 3.921926 | 47.482091 | 25.339276 | 2.278835 / 2.043176 |

새 조건의 활성 제한은 **SC+dermis 체적 전류벡터 RMS P95**입니다. Vpp/출력은0.9546637712914466이며, 이8개 제한에는 source power나1 Vpp ceiling이 포함되지 않습니다. CV가 더 작거나 RMS가 기준과 가깝더라도 목표 변조의 절대 mean/P10과 비표적 gate를 대신하지 못합니다. 모든 제한은 수치 비교 기준이며 인체 안전·활성화 한계가 아닙니다.

## 신규 조건의 고정 8-gate 결과

아래 값과 상대 변화는 screen JSON에 저장된 값입니다. 다른 세 행에 이번 새 판정을 부여하지 않습니다.

| Gate | 단위 | 원본 기준 | 신규 조건 | 변화 % | 통과 |
|---|---|---:|---:|---:|---|
| primary_maxTIS_mean | V/m | 4.06184894 | 3.24450447 | -20.122473 | False |
| primary_maxTIS_p10 | V/m | 3.64573574 | 2.96301984 | -18.726423 | False |
| surface_0_5_maxTIS_p95 | V/m | 25.2592218 | 47.4820905 | 87.979229 | False |
| surface_0_5_high_volume_at_primary_r5_depth15_20_mean | m3 | 7.76652902e-06 | 8.44018973e-06 | 8.673897 | False |
| surface_0_5_high_volume_at_primary_r5_depth15_20_p10 | m3 | 8.20945313e-06 | 8.75473214e-06 | 6.642087 | False |
| primary_complement_maxTIS_p95 | V/m | 23.4357186 | 25.3392758 | 8.122461 | False |
| primary_complement_high_volume_at_primary_r5_depth15_20_mean | m3 | 1.93996553e-05 | 2.09696638e-05 | 8.092971 | False |
| primary_complement_high_volume_at_primary_r5_depth15_20_p10 | m3 | 2.11556557e-05 | 2.27775512e-05 | 7.666487 | False |

## 피부·접촉 부담과 소스

| 저장된 부담/구동 (skin8) | 원본 square/opposite 한도 또는 값 | 신규 cross/adjacent |
|---|---:|---:|
| surface_J_RMS_max_A_m2 | 25.4912401 | 23.2285699 |
| surface_J_RMS_p95_A_m2 | 13.553106 | 13.3313532 |
| contact_voltage_RMS_max_V | 0.00268483846 | 0.0024473586 |
| SC_power_W | 2.16635702e-06 | 1.89213814e-06 |
| contact_power_W | 1.82727548e-06 | 1.59984705e-06 |
| source_power_W (W; skin8 cap 아님) | 0.00113591556 | 0.00101087181 |
| bulk_skin_J_vector_RMS_max_A_m2 | 25.4642838 | 23.2068219 |
| bulk_skin_J_vector_RMS_p95_A_m2 | 6.99826005 | 6.99826005 |
| skin_SC_plus_dermis_power_W | 0.000736170763 | 0.000635754861 |

신규 출력별 RMS 전류는 1.44774956 / 1.44861415 mA입니다. 출력 RMS 합은 장부상 합이며 공통 GND 귀환 전류와 같은 값이 아닙니다. 접촉 J, 체적 J, 접촉 전압, SC·SC+dermis·접촉 손실 및 source power를 별도로 보존했습니다.

## 실행·피드백·보류

- Queue는2026-10-21 16:33:57–16:36:23 UTC에 신규PDE → full-skin → 4행 volume 등록 → volume audit → 신규조건 screen → feedback 확인 → 공개 저장의7단계를 모두 exit0으로 완료했습니다. [실행 receipt](cloud-adjacent-cross-20261021T164000Z/queue/summary.json). 결과 공개 커밋은 `5c1ebd01995828a2e2438c8915bacb8c742f94e5`입니다.
- 신규 native source commit은 `7045c954fd8bbcc53ae9b3e81a4529b436362124`, 설정 SHA256은 `b16fa7dc7d341d0a1e85c5353e23f06a4e942e345acd417e2e67aa117885f0d8`입니다. 각 cached source commit·설정 hash·모델 버전·프로브 원본·보고서 SHA는 compact brief에 있습니다.
- [feedback-after snapshot](cloud-adjacent-cross-20261021T164000Z/feedback-after.json)은16:36:18.132240 UTC 관측입니다. 기존 incoming peer6320375305/bodySHA600efd…는 변하지 않았고, 이후 보이는6321162181/bodySHA3bef6d…는 root가 dot 검토자에게 보낸 진행 보고입니다. 이 snapshot에서는6320375305 뒤의 새 incoming peer를 찾지 못했습니다. 같은 GitHub author명이나 발신 진행 댓글을 새 peer 피드백으로 세지 않았습니다. 이 문서 작성은 새 GET·메시지 발신을 수행하지 않았습니다.
- [과거 fine grouped 지도](cloud-grouped-fine-native-maps-20261021T162000Z/index.html)와 [이전44조건 GUI](CLOUD_VOLUME_RESULTS_20261021_v8.html)는 다른 조건의 historical artifact입니다. 새 cross/adjacent 물리 지도라고 표시하지 않습니다.
- [피드백 처리 정정](FEEDBACK_DISPOSITION_CORRECTION_20261021.md)과 이전 실패 증거를 보존합니다. 이번 wiring은 root가 선택한 과학적 대비이며6320375305가 이 구체적 배선을 승인했다는 뜻은 아닙니다.
- 방정식/native gate와 고정 screen은 전체 mesh/SC/XY/bulk/edge/contact 수렴성, 독립 solver, 실험 또는 생리적 동등성 검증을 뜻하지 않습니다. 층 경계 hotspot을 깊이 집중으로 판정하지 않습니다. 프로브는40개 native complex-phi 무부하 예측이며 ETA5001/DSOX1202A의 실제 부하·대역폭·감쇠 검증과 새 주파수별 C1은 보류입니다.
- 다음 PDE나 후보 채택은 자동으로 시작하지 않았습니다. 남은 geometry/contact/mesh 질문과 자원 예산을 root가 검토해 다음 유한 배치를 선정합니다.
