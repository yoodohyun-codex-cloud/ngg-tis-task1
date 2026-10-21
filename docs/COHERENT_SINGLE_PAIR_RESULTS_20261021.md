# Coherent reference와 단일 전극쌍의 RMS matching — 2026-10-21

귀환을 포함한 한 전극쌍(물리2패드·출력1개)의3000Hz 정현파가 세 TIS reference의 중심점 또는 true ROI energy RMS를 맞추는 데 필요한 전압·전류·부담·전력을 비교했습니다. 비교는6행이며 기존 저장 basis를 재사용했습니다. 새 PDE·native RHS는0개입니다.

[오프라인 HTML 표](CLOUD_COHERENT_SINGLE_PAIR_RESULTS_20261021.html) · [원 summary](cloud-coherent-single-pair-20261021T172000Z/summary.json) · [정밀값 brief](COHERENT_SINGLE_PAIR_RESULTS_20261021.result-brief.json). 최신 reference `coherent-r1-p090`는 미채택 진단이며 목표2개통과·비표적6개실패 상태가 유지됩니다.

## 두 matching 정의

- 중심점: native complex E를(0,0,20mm)에서 보간한 full-vector electric-field RMS를 맞춥니다.
- True ROI energy RMS: 중앙반경5mm·깊이15–20mm의 `sqrt(부피가중 평균(native E_RMS²))`입니다. `평균(E_RMS)`와 다릅니다. 다른 matching 값은 달라질 수 있습니다.
- 별도 무부하 phi-gradient 중심 RMS `1.2732196327813072 V/m`은 기록만 보존하고 matching에 사용하지 않았습니다(`phi_gradient_used_for_matching=false`).

원본 TIS는4패드·출력2개·공통GND/50Ω입니다. Coherent 두 branch는양출력에3000/3030Hz가 함께 있으며, 원본 square branch는4개선 기본파/3차를포함합니다. C1은 source/return 중심(-10,-10)/(10,-10)mm의윗면2패드·출력1개/50Ω입니다. 단일주파수 자극은 TIS 변조와같은 물리량이 아니며 RMS 일치로활성화·생리효과의동등성을결론내리지않습니다.

## 6행의 필요 source Vpp와 reference 구동

필요 source Vpp와reference interval vector는 저장JSON의정밀도그대로입니다. 전기장표시값은9자리유효숫자로반올림했고brief에는원값을보존합니다.

| Reference | Matching | 목표 centre RMS,V/m | 목표 ROI energy RMS,V/m | 필요 C1 source Vpp | Reference TIS Vpp intervals [out0,out1] |
|---|---|---:|---:|---:|---|
| Coherent r1/90° raw actual1Vpp | 중심(0,0,20mm) E RMS | 1.32658551 | 1.46425758 | 1.0425129841463132 | `[[0.9999992544051025,1.0],[0.9999992543822719,1.0]]` |
| Coherent r1/90° raw actual1Vpp | True ROI energy RMS | 1.32658551 | 1.46425758 | 1.044291456594175 | `[[0.9999992544051025,1.0],[0.9999992543822719,1.0]]` |
| Coherent r1/90° original skin8 | 중심(0,0,20mm) E RMS | 2.00705446 | 2.2153451 | 1.5772675970590195 | `[[1.5129465484287756,1.5129476764748433],[1.512946548394234,1.5129476764748433]]` |
| Coherent r1/90° original skin8 | True ROI energy RMS | 2.00705446 | 2.2153451 | 1.5799583328166869 | `[[1.5129465484287756,1.5129476764748433],[1.512946548394234,1.5129476764748433]]` |
| 원본4-line square 명목1Vpp | 중심(0,0,20mm) E RMS | 2.09503782 | 2.31263459 | 1.6464103626295805 | `[[1.0,1.0],[1.0,1.0]]` |
| 원본4-line square 명목1Vpp | True ROI energy RMS | 2.09503782 | 2.31263459 | 1.6493440663383405 | `[[1.0,1.0],[1.0,1.0]]` |

Canonical square의[1,1]vector는원래명목source정의이며새waveform bracket을만들어붙이지않았습니다. Skin8 coherent source는실제약1.513Vpp인reference입니다. 이값을명목1Vpp결과로바꿔쓰지않습니다.

이 6행은 전기장 RMS를 맞춘 비교이며 같은 피부·접촉 부담을 맞춘 조건은 아닙니다. 전류·표면 부담·전력은 각 행의 별도 결과이고 reference와 같다고 가정하지 않습니다.

## C1 필요 전류·표면/체적 부담·전력

각행의최대/P95 J는RMS기반이며bulk skin은SC+dermis입니다. SC·dermis·contact·source 손실과전력은분리합니다.

| Reference / Matching | source RMS mA | source peak mA | Contact Jmax / J95,A/m² | Bulk Jmax / J95,A/m² | Contact RMS V | SC+dermis W | Contact W | Source W |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Coherent r1/90° raw actual1Vpp / 중심(0,0,20mm) E RMS | 0.975795258 | 1.37998289 | 15.6085717 / 11.3634311 | 15.5526301 / 4.59243642 | 0.00164996376 | 0.00023855112 | 5.57416677e-07 | 0.000352204607 |
| Coherent r1/90° raw actual1Vpp / True ROI energy RMS | 0.977459913 | 1.38233707 | 15.6351991 / 11.3828165 | 15.5791621 / 4.60027088 | 0.00165277851 | 0.000239365725 | 5.59320147e-07 | 0.000353407317 |
| Coherent r1/90° original skin8 / 중심(0,0,20mm) E RMS | 1.47632717 | 2.0878419 | 23.6149522 / 17.1922766 | 23.5303156 / 6.94811601 | 0.00249630884 | 0.000546046059 | 1.27593272e-06 | 0.000806200105 |
| Coherent r1/90° original skin8 / True ROI energy RMS | 1.4788457 | 2.09140365 | 23.6552381 / 17.2216057 | 23.5704571 / 6.95996914 | 0.00250056741 | 0.0005479107 | 1.28028978e-06 | 0.000808953121 |
| 원본4-line square 명목1Vpp / 중심(0,0,20mm) E RMS | 1.541045 | 2.17936674 | 24.6501622 / 17.9459354 | 24.5618153 / 7.25270095 | 0.00260573967 | 0.000594969491 | 1.39025093e-06 | 0.000878432245 |
| 원본4-line square 명목1Vpp / True ROI energy RMS | 1.54379096 | 2.18325011 | 24.6940858 / 17.9779129 | 24.6055815 / 7.26562439 | 0.00261038278 | 0.000597091707 | 1.39520986e-06 | 0.000881565554 |

HTML과brief에는SC/dermis각손실·source50Ω저항손실·전극금속Vpp와각matching에서실제달성한centre/ROI RMS를추가했습니다. `loaded_metal_Vpp`는50Ω회로의전극금속단자값이지측정기의입력부하를적용한프로브예측이아닙니다. Reference TIS 출력별전류·접촉부담·전력도HTML에서별도표로제시합니다.

## 프로브·검증·실행

- [기존 C1 native-phi 프로브](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-C1pair0-xy80/probes.json)의 `baseline-square15-C1pair0-xy80-C1-3000Hz-sine`를연결합니다. 깊이5/10/15/20mm ×십자중심5점 ×X/Y차동축=40행, 팁간격5mm의무부하예측입니다. 각matching의저장된amplitude_scale를기존sine Vpp/RMS에곱하는참조이며이요약은새파형·프로브·장비부하계산을하지않았습니다.
- PBS계면·SC/XY/bulk/edge/contact전체수렴성,source phase/sink/compliance,ETA5001/DSOX실제입력부하·대역폭·감쇠율·실험·생리검증은보류입니다. 부담수치도인체안전한계로판정하지않습니다.
- [Queue](cloud-coherent-single-pair-context-20261021T172000Z/queue/summary.json)는17:09:05–17:09:12 UTC에matching→feedback GET→publication을모두exit0으로완료했습니다. [게시receipt](cloud-coherent-single-pair-context-20261021T172000Z/single-pair-publication-20261021T172000Z.json)는 `published_completed_batch`, commit `121bed2da204e99237f1d3e1876140703c2595a3`입니다. 저장된분석wall time은1.2423021560025518s입니다.
- 후보source commit은 `38f005ecefc2c432cd6424a06f599f93682cc202`, matching분석source commit은 `a1724f684ade02a76741a762ebccb1dd6c054061`입니다. 원summary·등록·후보조건·C1프로브·queue·publication SHA는brief와HTML에연결했습니다.

이문서와HTML은저장된JSON만표시합니다. 새matching·score/gate·변조공식·수치배열계산·JavaScript·외부요청·커밋을수행하지않았습니다.
