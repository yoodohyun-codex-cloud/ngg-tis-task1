# Grouped strip gap 진단 — 2026-10-21

**원래 fine 4square의 동일 8개 피부·접촉 상한을 적용하면 8조건 모두 목표 mean/P10을 통과하지 못했습니다.** pad 수 순위도 coarse의16·8·4·12에서 fine의4·8·12·16으로 바뀌어, coarse 결과만으로 우열이나 깊이 집중을 채택할 수 없습니다. 새 후보 채택·gap/edge 수렴·실험 검증은 모두 false입니다.

[원 결과](cloud-grouped-gap-diagnostic-20261021T162000Z/summary.json)와 [간결 장부](GROUPED_GAP_DIAGNOSTIC_20261021.json)를 함께 보존합니다. 원 결과 SHA256은 `3de44841a85c73b5bb3e15e435c5e55479619962c6f33a6bea426b7323f2695d`, 실행 소스는 `1d1cd9ce41e4a40a2e42b54847f69c7bb6443e69`, 사전등록 게시 커밋은 `7045c954fd8bbcc53ae9b3e81a4529b436362124`입니다. 계산은 23.621846초/CPU1/peak RSS 348348416bytes, 새PDE0입니다. 이 보고서는 저장 JSON만 읽었으며 원 배열·전위·장·후처리를 다시 계산하지 않았습니다.

## 공통 비교와 목표 잔존값

두 격자에 원래 fine 4square의 같은 수치 부담과 물리 cutoff를 고정했습니다. 기본 ROI는 r≤5mm·표면 기준 깊이15–20mm, 보조 ROI는 같은 깊이의 전체 modeled XY입니다. native 부분 체적 가중과 고정 cutoff를 유지합니다. 기준 목표 mean/P10은 각각 4.0618489/3.6457357 V/m입니다. 아래 목표 전기장·변조 값은 원 JSON의 V/m 단위를 그대로 사용합니다. 이 기준은 인체 안전·생리적 활성화 한계가 아닙니다.

| pads | 격자 h mm | 상한 scale | 목표 mean V/m | P10 V/m | 활성 제한 | 원전압 contact Vmax mV | 원전압 contact Jmax A/m² |
|---:|---:|---:|---:|---:|---|---:|---:|
| 4 | 1.25 | 0.327062 | 1.25214 | 1.12012 | contact_voltage_RMS_max_V | 8.20897 | 77.9391 |
| 8 | 1.25 | 0.368081 | 1.40732 | 1.25861 | surface_J_RMS_max_A_m2 | 7.29383 | 69.2544 |
| 12 | 1.25 | 0.214136 | 0.81839 | 0.731787 | contact_voltage_RMS_max_V | 12.538 | 119.036 |
| 16 | 1.25 | 0.380022 | 1.43843 | 1.28597 | contact_voltage_RMS_max_V | 7.06495 | 67.0759 |
| 4 | 0.625 | 0.251917 | 0.963174 | 0.861257 | contact_voltage_RMS_max_V | 10.6576 | 101.186 |
| 8 | 0.625 | 0.222771 | 0.853353 | 0.76275 | contact_voltage_RMS_max_V | 12.052 | 114.424 |
| 12 | 0.625 | 0.191275 | 0.730929 | 0.653191 | contact_voltage_RMS_max_V | 14.0366 | 133.263 |
| 16 | 0.625 | 0.156843 | 0.597005 | 0.533441 | contact_voltage_RMS_max_V | 17.118 | 162.517 |

위 순위 변화는 `skin_contact_only` 및 기존 복합 상한에서 mean/P10 모두에 해당합니다. raw 순위는 coarse4·8·12·16→fine8·4·12·16이며, 동일 전류 합/동일 전력 순위는 두 격자에서4·8·12·16입니다. 정규화별 결과를 섞어 pad 수 효과로 해석하지 않습니다.

## 실제 면적·gap·공유 조직 면

| pads | h mm | 표현 면적 mm² | 물리 최소 gap mm | 공유 tissue top face | 같은 node pad 쌍 | 다른 node pad 쌍 |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1.25 | 900 | 1 | 0 | 0 | 0 |
| 8 | 1.25 | 900 | 1 | 44 | 4 | 0 |
| 12 | 1.25 | 900 | 1 | 0 | 0 | 0 |
| 16 | 1.25 | 900 | 1 | 44 | 4 | 0 |
| 4 | 0.625 | 900 | 1 | 0 | 0 | 0 |
| 8 | 0.625 | 900 | 1 | 0 | 0 | 0 |
| 12 | 0.625 | 900 | 1 | 0 | 0 | 0 |
| 16 | 0.625 | 900 | 1 | 0 | 0 | 0 |

각 coarse/fine 쌍의 물리 패드 외곽·면적과 metal-node 연결은 같습니다. 총면적은 부동소수점 표현 범위에서900mm²이고 별도 면적 재정규화는 없습니다. 모든 조건은 물리4/8/12/16패드에 독립출력2개·공통귀환1node·50Ω이며 출력 수가 늘지 않습니다.

coarse8/16의 공유44면은 각각 같은 전기 node의4개 물리 패드 쌍에 속하며 다른 node 쌍 공유는0입니다. fine에서는 모두0입니다. 이는 서로 다른 금속 전극을 합치거나 금속 단락이 있다는 뜻이 아니라 별도 접촉 edge가 같은 tissue DOF를 사용하는 표현입니다. 물리 최소 gap 약1mm와 contacted-cell bounding box 간격/중심 거리는 서로 다른 정의입니다. h0.625mm도1mm당1.6셀이므로 수렴 완료가 아닙니다.

## 접촉·피부 J의 위치와 보존

원전압 contact Vmax는4/8/12/16패드에서 coarse 8.2090/7.2938/12.5380/7.0650mV에서 fine 10.6576/12.0520/14.0366/17.1180mV로 변했습니다. 정확한 원수치와 위치는 아래 장부에 보존합니다. fine16의 최대 패치 면적은 native face의0.02523076923이고, contact Jmax/voltage max는 physical pad4의 작은 overlap에 있습니다. 이는 격자/fragment 민감도이며 비물리적 artifact를 입증하거나 edge 최대가 수렴했다고 판정하는 근거가 아닙니다.

| pads/h mm | SC total Jmax A/m² · xyz mm | dermis total Jmax A/m² · xyz mm | 최대 주파수별 전류보존 상대오차 |
|---|---|---|---:|
| 4/1.25 | 21.6089 · [3.125, 0.625, 0.025] | 24.44 · [3.125, 0.625, 0.278571428571] | 1.4852919e-09 |
| 8/1.25 | 22.7793 · [1.875, 0.625, 0.025] | 25.0673 · [1.875, 0.625, 0.278571428571] | 3.295202e-09 |
| 12/1.25 | 23.4064 · [1.875, 0.625, 0.025] | 25.6062 · [1.875, 0.625, 0.278571428571] | 1.4080505e-09 |
| 16/1.25 | 22.8446 · [0.625, 0.625, 0.025] | 25.8941 · [0.625, 0.625, 0.278571428571] | 1.7304656e-09 |
| 4/0.625 | 26.5818 · [2.1875, 0.9375, 0.025] | 26.5264 · [2.1875, 0.9375, 0.278571428571] | 4.2180624e-09 |
| 8/0.625 | 25.9012 · [2.1875, 0.9375, 0.025] | 26.0703 · [1.5625, 0.9375, 0.278571428571] | 3.0805159e-09 |
| 12/0.625 | 27.4218 · [1.5625, 0.9375, 0.025] | 26.9655 · [1.5625, 0.9375, 0.278571428571] | 1.1334765e-09 |
| 16/0.625 | 30.032 · [0.9375, 0.9375, 0.025] | 29.2849 · [0.9375, 0.9375, 0.278571428571] | 4.5093217e-09 |

전류보존 한도는2e−6이고 각 주파수의 실제 값/한도, 출력별·패드별 RMS 및 복소 전류 원표 위치를 JSON에 연결했습니다. SC/dermis total vector J는 변위전류를 포함하며 접촉 법선 J와 다릅니다. 피부 최대 위치는 native cell 중심, contact 최대 위치는 물리 overlap patch/tissue face 중심을 각각 구분합니다. 접촉 Jmax와 contact Vmax도 자동으로 같은 위치라고 가정하지 않습니다.

## 피드백 처리와 다음 질문

[6319669306](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6319669306) 및 [6320375305](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6320375305)는 [명시적 정정 장부](FEEDBACK_DISPOSITION_CORRECTION_20261021.md), 커밋 `40b8bd39904b63c0f269000b6f8de00c2f979f78`에 연결했습니다. 앞선 회귀 증거의 peer 검토 범위와 별개로, **이번 상세 gap 진단은 구현·계산 완료지만 아직 독립 peer 검토·전체 수렴 검증이 아닙니다.**

root가 선택한 다음 질문은 동일900mm²의 square/cross × opposite/adjacent source 배선2×2를 완성하는 **aligned full-face 4pad cross의 adjacent source 조건 하나**입니다. 원래 square/opposite, square/adjacent, balanced cross/opposite의 완료3대조를 재사용합니다. 예정 run은 `cloud-adjacent-cross-20261021T164000Z`, case는 `balancedcross225-adjacent-sources-xy80`입니다. [새 결정](cloud-adjacent-cross-20261021T164000Z/decision.json)에 따라 native 준비는 완료됐으나 **이 보고서에서 actual_started=false**, 새 PDE 시작이나 결과를 주장하지 않습니다. 준비 소스는 `7045c954fd8bbcc53ae9b3e81a4529b436362124`입니다. 실제 allocation 원표는 [보존된 결과](cloud-autonomous-20261021T144000Z/volume-cross-allocation.json)이며, 앞선 잘못된 경로 조회는 [별도 실패 기록](cloud-adjacent-cross-20261021T164000Z/decision-path-failure-preserved.json)에 보존합니다. 그 경로 오류 시점에는 새 수치 run/PDE가 만들어지지 않았습니다. Partial-face/edge 불확실성이 해결되기 전 rounded-pad PDE는 선택하지 않습니다.

원래 E/φ·마스크·실패·이전 결과는 보존합니다. 본 문서와 요약 JSON만 새로 작성했으며 Git 커밋·GitHub 게시·배열 읽기·추가 계산은 수행하지 않았습니다.
