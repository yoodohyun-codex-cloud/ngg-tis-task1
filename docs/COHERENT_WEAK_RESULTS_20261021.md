# Weak coherent drive 결과 — 2026-10-21

약한 혼합 r=0.05/0.1/0.2와위상90°/270°의6조건도 모두 미채택입니다. 피부·접촉8cap에서 목표mean/P10 두 gate는 모든조건에서 통과했지만 표층·전체 비표적6gate가 모두실패했습니다. 과학 계산은 완료됐고, 공개 저장 단계만 metadata 경로 오류로 실패한 뒤 **계산 재실행 없이 복구**됐습니다.

[완료 summary](cloud-next-coherent-weak-20261021T170000Z/summary.json) · [등록](cloud-coherent-weak-context-20261021T170000Z/preregistration.json) · [small brief](COHERENT_WEAK_RESULTS_20261021.result-brief.json) · [Strong8 보고서](COHERENT_DRIVE_RESULTS_20261021.md) · [Strong GUI](CLOUD_COHERENT_DRIVE_RESULTS_20261021.html). Strong GUI에는 weak6을합치지 않았습니다. Strong 지도는 [index](cloud-coherent-drive-native-maps-20261021T170500Z/index.html)와 [worker terminal receipt](cloud-coherent-drive-context-20261021T165000Z/maps-worker-receipt.json)에따라17:04:30 UTC 렌더완료입니다. 원본square+cachedsine+strong8의10조건·24 PNG이며weak6의물리지도는포함하지않습니다. 수렴성·실험검증완료를뜻하지않습니다.

## 같은 기준에서 남은 절대 결과

원본4-square·독립출력2개·공통GND1개·50 Ω, 팬텀D50 mm와고정층/격자/접촉조건을 유지했습니다. 두 출력모두3000/3030 Hz를 구동하며 beat30 Hz, 새PDE는0개입니다. Primary ROI는중앙반경5 mm·피부에서깊이15–20 mm입니다. maxTIS는동일주파수 복소합성을거친2074표본방향최대의하한이고 RMS와구분합니다. 아래단위는V/m(CV무차원), Vpp는50 Ω 앞 실제두톤전체source파형max−min 상한입니다.

| 조건 | Raw1Vpp mean / P10 | Skin8 mean / P10 | Skin8 CV | Skin8 max | Skin8 표층P95 | Skin8 전체비표적P95 | Skin8 actual Vpp 상한/출력 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 원본 square 기준 | 4.061849 / 3.645736 | 4.061849 / 3.645736 | 0.080762 | 4.971327 | 25.259222 | 23.435719 | 명목1; 새 bracket 없음 |
| r=0.05,φ=90° | 3.654713 / 3.282048 | 4.100394 / 3.682284 | 0.080443 | 5.014479 | 25.615631 | 23.902555 | 1.121947 |
| r=0.05,φ=270° | 3.651569 / 3.277455 | 4.096867 / 3.677131 | 0.080771 | 5.014479 | 25.587877 | 23.634436 | 1.121947 |
| r=0.1,φ=90° | 3.507013 / 3.152640 | 4.106688 / 3.691720 | 0.079837 | 5.014489 | 26.344971 | 24.423208 | 1.170993 |
| r=0.1,φ=270° | 3.501035 / 3.143922 | 4.099688 / 3.681510 | 0.080474 | 5.014489 | 26.220908 | 23.899744 | 1.170993 |
| r=0.2,φ=90° | 3.278768 / 2.957698 | 4.127557 / 3.723371 | 0.077939 | 5.014503 | 29.817672 | 26.318291 | 1.258874 |
| r=0.2,φ=270° | 3.267968 / 2.941611 | 4.113961 / 3.703118 | 0.079064 | 5.014503 | 28.740624 | 25.362879 | 1.258874 |

모든raw 실제1 Vpp 조건은목표mean/P10이 원본square보다낮습니다. Skin8에서는약1.122/1.171/1.259 Vpp까지올린값이므로 동일전압결과가아닙니다. 모든6조건의활성부담은 `SC_power_W`이며source power·1 Vpp ceiling은이모드에없습니다. Frozen 원본수치cap/cutoff를유지했고 인체안전·활성화한계로표현하지않습니다.

표층·전체비표적의P95와원본primary mean/P10 cutoff이상고변조부피를각각검사하는6gate가모두실패했습니다. 작은목표이득만으로깊이집중성공을판정하지않았습니다. 원8gate 값/상대변화율은각 `condition.json → canonical_skin_cap_screen`과brief에그대로보존했습니다.

## 5개 모드와 실제 파형 증거

각 조건JSON의 `normalizations`에는 `raw_1Vpp`, `equal_total_source_output_RMS_sum`, `equal_total_power`, `skin_contact_only`, `legacy_composite_full_skin`이별도로저장돼 있습니다. Brief는각조건JSON의SHA와5개JSON pointer를제공하며raw/skin8수치·부담·전류·signed power·40probe ID를발췌했습니다. 나머지모드를재계산하거나대체하지않았습니다.

모든조건의actualsource raw bracket은보수적상한1 Vpp, 폭1 µV이하입니다. 실제전기장시간파형과40개native complex-phi 프로브시간파형의저장검증은모두pass입니다. 프로브는깊이5/10/15/20 mm의십자중심5점×X/Y차동축, 팁간격5 mm이며무부하예측입니다. 실제입력부하·대역폭·감쇠율, hardware phase/sink/compliance는미검증입니다. 양출력signedpower는음수를0으로자르지않고sourceJSON에보존합니다. 새C1·전체mesh/contact수렴성·생리적동등성·실험검증을주장하지않습니다.

## 게시 실패와 metadata-only 복구

- [원 queue](cloud-coherent-weak-context-20261021T170000Z/queue/summary.json)는16:54:58 UTC에시작해6조건과feedback확인을exit0으로끝냈고,16:56:04 UTC에publication단계exit1로 `failed_preserved`가됐습니다. 과학summary의 `calculated_unadopted`와구분합니다. 저장된scout wall time은60.14141673400445 s입니다.
- [실패 receipt](cloud-coherent-weak-context-20261021T170000Z/coherent-weak-publication-20261021T170000Z.json)는존재하지않는weak-context `feedback-before.json`을publisher whitelist가요구했다고기록합니다. 실제과학등록은재사용한strong-end `feedback-after.json`을pin하고있었습니다. 계산이나GET이누락된실패가아닙니다.
- [실패 disposition](cloud-coherent-weak-context-20261021T170000Z/publication-failure-disposition.json)과원spec/결과/실패receipt를보존했습니다. `new_PDE=0`, `new_resynthesis=0`, `source_reexecution=false`인metadata-onlypublication복구를선정했습니다.
- [복구 receipt](cloud-coherent-weak-context-20261021T170000Z/coherent-weak-recovery-publication-20261021T170000Z.json)는16:59:08 UTC `published_completed_batch`, commit `9ad428cbda7bcde7d6a38604841b01a8567f87a2`입니다. 새6조건계산을다시실행하지않았습니다.

이문서/brief는저장된JSON metadata만읽었습니다. 배열분석·새score/gate·렌더·커밋·GitHub 작업을수행하지않았습니다. 모든6조건은미채택이며다음계산은이요약에서자동시작하지않습니다.
