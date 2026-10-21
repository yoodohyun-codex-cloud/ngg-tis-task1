# Coherent two-tone drive 결과 — 2026-10-21

같은 원본4-square 패드에서 두 출력 모두3000/3030 Hz를 합성한8조건을 계산했으며 **8조건 모두 고정 screen을 통과하지 못했습니다**. 위상90°/270°에서는 피부·접촉 부담을 맞춘 목표 mean/P10이 기준을 넘는 조건이 있었지만 표층·전체 비표적의6개 gate가 모두 악화됐습니다. Raw actual1 Vpp 비교와1 Vpp를 넘겨 구동한 피부 부담 비교를 분리합니다.

[새 coherent GUI](CLOUD_COHERENT_DRIVE_RESULTS_20261021.html) · [완료 summary](cloud-next-coherent-drive-20261021T165000Z/summary.json) · [등록 계획](cloud-coherent-drive-context-20261021T165000Z/preregistration.json) · [정밀값 compact brief](COHERENT_DRIVE_RESULTS_20261021.result-brief.json). GUI의 JSON 전용 렌더는 완료됐습니다([receipt](CLOUD_COHERENT_DRIVE_RESULTS_20261021.receipt.json)); 이는 수치 gate·수렴성 검증의 승격을 뜻하지 않습니다. [직전 wiring GUI](CLOUD_ADJACENT_CROSS_RESULTS_20261021.html), [fine4/8/12/16 GUI](CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html), [과거44조건 GUI](CLOUD_VOLUME_RESULTS_20261021_v8.html)를 보존합니다.

## 고정 조건과 파형 정의

팬텀 D50 mm, SC/dermis/fat/muscle0.1/5/5/15 mm, 윗면 원본4-square 패드와 XY0.625 mm/SC2/bulk14,14,40을 유지했습니다. 독립 출력은2개이며 공통 GND 귀환 및50 Ω 소스/비활성 주파수 종단을 유지합니다. 새 조건은 두 출력 각각에3000/3030 Hz를 인가하고3차 고조파를 구동하지 않습니다. 같은 주파수 성분은 복소수로 먼저 합성한 결과이며 저장된 실제 전기장·40개 복소전위 프로브 시간 파형 검증을 모두 통과했습니다. 새 PDE는0개입니다.

새8조건은 mix ratio r=0.5/1과위상0/90/180/270°입니다. Seed의 unitary 성질은 실제 출력별Vpp 정규화 전의 성질입니다. 출력별 Vpp 정규화 후 unitary라고 가정하지 않습니다. 각 raw 조건은50 Ω 앞 소스의 실제 두 톤 전체1/30 s 파형 max−min 구간을 사용하며, 보수적 상한1 Vpp와폭1 µV 이하가 저장 증거에서 확인됩니다. 이는 tone별1 Vpp나 실제 전원 보정·실측 검증을 뜻하지 않습니다. 원본 square의 역사적 명목1 Vpp 정의는 그대로 보존하고 새 actual bracket을 만들어 붙이지 않습니다.

Primary ROI는 중앙반경5 mm·피부에서 깊이15–20 mm이며 +z가 깊이 방향입니다. maxTIS는2074 표본 방향 최대의 하한, fixedTIS는(X+Y)/√2 방향입니다. 아래 전기장 단위는V/m이고CV는 무차원입니다. RMS는 새 coherent/cached sine의2개 기본파와 원본 square의기본파+3차4선을 각각 포함하는 실제 벡터RMS이며, 변조와 다른 물리량입니다.

## Raw actual1 Vpp/출력과 피부·접촉8cap 결과

원본 square 기준과 cached exclusive3k sine를 항상 함께 둡니다. Cached sine는 이번에 새로 계산·screen한 조건이 아닙니다. 숫자는 소수여섯 자리로 반올림했고 원 JSON 값만 요약했습니다.

| 조건 | Raw ROI mean / P10 | Skin8 ROI mean / P10 | Skin8 CV | Skin8 ROI max | Skin8 표층P95 | Skin8 비표적P95 | Skin8 실제source Vpp 상한 (각출력) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 원본 square3h (기준) | 4.061849 / 3.645736 | 4.061849 / 3.645736 | 0.080762 | 4.971327 | 25.259222 | 23.435719 | 명목1 (새 bracket 없음) |
| Cached exclusive sine3k | 3.829548 / 3.437233 | 4.097095 / 3.677371 | 0.080762 | 5.014465 | 25.478405 | 23.639079 | 1.069864 (저장된 sine값) |
| r=0.5, φ=0° | 1.408753 / 0.932310 | 2.022113 / 1.338230 | 0.249036 | 3.489990 | 46.896694 | 38.856927 | 1.435392 |
| r=0.5, φ=90° | 2.950042 / 2.686146 | 4.234242 / 3.855468 | 0.071241 | 5.014506 | 46.712521 | 37.613406 | 1.435316 |
| r=0.5, φ=180° | 1.408812 / 0.932490 | 2.022037 / 1.338383 | 0.248975 | 3.491404 | 46.858012 | 38.856548 | 1.435278 |
| r=0.5, φ=270° | 2.930345 / 2.665016 | 4.205970 / 3.825140 | 0.072301 | 5.014506 | 44.595385 | 35.567370 | 1.435316 |
| r=1.0, φ=0° | 0.446285 / 0.206784 | 0.675250 / 0.312874 | 0.386260 | 1.373138 | 61.370053 | 39.481248 | 1.513046 |
| r=1.0, φ=90° | 2.899346 / 2.647453 | 4.386559 / 4.005458 | 0.069410 | 5.014465 | 66.996623 | 51.540062 | 1.512948 |
| r=1.0, φ=180° | 0.446212 / 0.206751 | 0.675073 / 0.312793 | 0.386253 | 1.372751 | 61.374647 | 39.479049 | 1.512896 |
| r=1.0, φ=270° | 2.899346 / 2.647473 | 4.386559 / 4.005488 | 0.069410 | 5.014465 | 66.992107 | 51.538392 | 1.512948 |

Raw actual 1 Vpp에서는 새 8조건의 목표 mean/P10이 모두 원본 square 기준보다 낮았습니다.

**Skin8 결과는 동일 인가전압 비교가 아닙니다.** r0.5는실제source 상한약1.435 Vpp, r1은약1.513 Vpp까지 올린 값입니다. 원본 square의8개 피부·접촉 부담 이내에서 비교했으며 이모드에는source power·1 Vpp ceiling이 없습니다. `legacy_composite_full_skin`은 이 둘을 추가하는 별도 모드입니다. 모든5모드의 절대 ROI·비표적·고변조 부피·current/power·source구간은 GUI/원조건JSON에 있습니다. 수치 부담 한도는 인체 안전·활성화 기준이 아닙니다.

## 목표 증가만으로 채택하지 않은 이유

모든8조건의 피부 부담 활성 제한은 **SC_power_W**입니다. r1/90°는ROImean4.386559·P104.005458 V/m까지 증가하지만 표층P95는66.996623 V/m(기준25.259222), 전체 비표적P95는51.540062 V/m(기준23.435719)입니다. 표층·비표적의 P95 및 두 frozen-cutoff 고변조 부피가 모두 증가해6개 off-target gate를 통과하지 못했습니다. 높은 전역/층 경계 값이나중심20 mm 한 점으로 성공을 판정하지 않았습니다.

| 신규 조건 | 목표mean/P10 gate | 표층·비표적6gate | 전체8gate | source bracket최대폭,V | field/40probe 시간검증 |
|---|---|---|---|---:|---|
| coherent-r0p5-p000 | False / False | False / False / False / False / False / False | False | 7.48065142e-07 | True / True |
| coherent-r0p5-p090 | True / True | False / False / False / False / False / False | False | 7.48085405e-07 | True / True |
| coherent-r0p5-p180 | False / False | False / False / False / False / False / False | False | 7.48065142e-07 | True / True |
| coherent-r0p5-p270 | True / True | False / False / False / False / False / False | False | 7.48085405e-07 | True / True |
| coherent-r1-p000 | False / False | False / False / False / False / False / False | False | 7.45594897e-07 | True / True |
| coherent-r1-p090 | True / True | False / False / False / False / False / False | False | 7.45617728e-07 | True / True |
| coherent-r1-p180 | False / False | False / False / False / False / False / False | False | 7.45594897e-07 | True / True |
| coherent-r1-p270 | True / True | False / False / False / False / False / False | False | 7.45617728e-07 | True / True |

## 전력·프로브·실험 보류

출력별 ideal-source/metal-delivered power와50 Ω 손실은 부호를 보존한 원 수치를 사용합니다. 이8조건에서 저장된 output-absorption 및 negative per-frequency source-power flag는 모두False였지만, 실제 source sink/compliance·동기 위상·multitone 전원 구현이 검증됐다는 뜻은 아닙니다. 원 JSON과 새 GUI에는 주파수별·출력별 signed power를 그대로 남겼고 음수를0으로 바꾸지 않습니다.

40개 프로브는깊이5/10/15/20 mm ×중심 및±5 mm 십자중심5개 ×수평X/Y 차동축입니다. 팁 간격은5 mm이며 프로브중심 이동과 구분합니다. 각 정규화의probe ID·Vpp 구간·RMS·변조를 저장값 그대로 표시합니다. 이는 native complex-phi 무부하 예측이며 ETA5001/DSOX1202A의 실제 입력부하·대역폭·감쇠율 검증은 보류입니다.

독립 solver·SC/XY/bulk/전극 가장자리·접촉 모델의 전체 수렴성, 실제 피부 접촉, 실험·생리학적 동등성과 새 주파수별C1 비교가 완료됐다고 주장하지 않습니다. 새 물리 지도는 별도 작업이며 이 요약·GUI는 native 배열을 열거나 새 지도를 생성하지 않습니다.

## 실행 이력과 후속 상태

- [유한 queue](cloud-coherent-drive-context-20261021T165000Z/queue/summary.json)는2026-10-21 16:48:34–16:50:02 UTC에8조건 저장basis 합성 →피드백 확인 →공개저장의3단계를 모두exit0으로 완료했습니다. Scout77.507970 s, queue88.077568 s가 저장돼 있습니다. 이 합성은 새 PDE가아니며 root가승인한 기존basis 후처리 계산입니다.
- 결과 공개커밋은 `cc306218619a3c7d929a19ac4763d238fabfef96`입니다. 실제 source는 원본 square의 `38f005ecefc2c432cd6424a06f599f93682cc202` 및 config`f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`이고, scout 구현커밋·등록·조건JSON·프로브SHA와root선택/peer context는brief에 연결했습니다. 특정 coherent 배선을 peer가승인했다고 추론하지 않습니다.
- 후속 weak mixing(r0.05/0.1/0.2,φ90/270°)6조건은 실제 완료됐습니다. 모든조건에서목표2gate는pass,off-target6gate는fail이며미채택입니다. 공개저장만누락된metadata경로로실패한뒤계산재실행없이16:59:08 UTC metadata-only복구됐습니다(commit `9ad428cbda7bcde7d6a38604841b01a8567f87a2`). [별도 weak 보고서](COHERENT_WEAK_RESULTS_20261021.md), [완료summary](cloud-next-coherent-weak-20261021T170000Z/summary.json), [실패/복구 disposition](cloud-coherent-weak-context-20261021T170000Z/publication-failure-disposition.json)을연결합니다. 후속결과를이8조건GUI에합치지않았습니다.
- Strong8+원본square+cachedsine의 [새지도 index](cloud-coherent-drive-native-maps-20261021T170500Z/index.html)는 [worker terminal receipt](cloud-coherent-drive-context-20261021T165000Z/maps-worker-receipt.json) 기준17:04:30 UTC 완료됐습니다. 10조건·24 PNG의 `rendered_unadopted` 표시이며수렴성·실험검증의승격이아닙니다. 이요약에서는PNG/native배열을독립개봉·재검증하지않았습니다.
