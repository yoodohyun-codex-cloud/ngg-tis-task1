# 작업 1: 회전 형상의 양의 진폭 계열 bound 진단 (2026-10-21)

고정된 저장 이산 모델에서 두 출력의 **모든 양의 진폭 조합**을 두 분기로 나누어 검사한 결과, 목표 ROI 평균 유지·표면 P95 억제·필요한 피부/접촉 전력 한도를 동시에 만족하는 계열은 배제되었다. 원본 판정은 `excluded_fixed_discrete_positive_amplitude_family`, `overall_proof_passed=true`다. 이는 아래 고정 형상·격자·물성·파형·회로·2074방향과 저장된 scalar/power 항등식에 조건부인 수치 bound이며, 연속체 또는 전역 물리 설계의 불가능성·인체 안전성을 뜻하지 않는다. 후보 채택은 없다.

[원본 결과](cloud-rotation-amplitude-bounds-20261021T181000Z/summary.json) · [사전등록](cloud-rotation-amplitude-bounds-context-20261021T181000Z/preregistration.json) · [앞선 진폭비4조건](ROTATION_RATIO_RESULTS_20261021.md) · [6행 GUI](CLOUD_ROTATION_RATIO_RESULTS_20261021.html) · [회전/부모 비교](ONE_RETURN_ROTATION_RESULTS_20261021.md)

## 적용하는 계열과 고정 조건

출력 진폭을 `[a,b]=A[t,1]` 또는 `A[1,t]`, `A>0`, `0<t≤1`로 표현한다. 각 분기에서 공통 A는 임의의 양수이며1 Vpp ceiling을 전제하지 않는다. 이는 임의의 양의 `[a,b]`를 두 분기로 나눈 표현이다. source Vpp는50 Ω 앞의 기존 square_3h 전체파형 정의다.

형상은 `asym-return2-rot90-xy80`로 고정한다. D50 mm, SC/dermis/fat/muscle0.1/5/5/15 mm, 윗면 총900 mm², 한 GND pad2의90° 회전이 이미 적용된 mask다. XY0.625 mm / SC2 / bulk14·14·40 /351680 cells, nominal tissue/contact를 유지한다. 원래 square 및 비대칭 부모에서 달라진 형상을 다시 탐색한 진단이 아니다.

물리4패드/독립2출력/공통GND/50 Ω, pad0→out0, pad1→out1, pad2·3→GND이다. 각 출력의 exclusive 기본파3000/3030 Hz와 자기3차 고조파9000/9090 Hz, 위상0°/0°를 유지한다. 다른 주파수는0 V through50 Ω로 종단한다. coherent 두주파수혼합·위상변경·새접촉/기하·SC두께·측면부착·새주파수는 이 결과 범위 밖이다. 초기2/2.01 kHz 기록과도 구분한다.

목표 T는 중심r≤5 mm, 표면에서 깊이15–20 mm의 **maxTIS 체적가중 평균**이고, S는 깊이0–5 mm의 maxTIS 가중P95다. x/y수평·+z안쪽이다. 방향 집합은26고정+2048Fibonacci=2074개로 진폭에 따라 바뀌지 않는다. 각 셀의 지표 `max_n 2 min(a|n·E3000|, b|n·E3030|)`와 고정 양의 ROI 가중치를 사용한다. 따라서 좌표별 단조성과1차 동차성이 평균 T 및 가중inverse-ECDF P95 S에 유지된다는 정의를 frozen source에서 확인했다. 기본파 변조 bound이며 전체4선 전기장 RMS·단일주파수·생리적 활성화에 대한 같은 판정이 아니다.

## 두 분기의 저장 bound

내부 구간은 `0.5≤t≤1`(양끝 포함), 외부 구간은 `0<t<0.5`다. `t=0.5`는 내부가 담당하므로 빈 구간이 남지 않는다. 아래 숫자는 원본 저장값을 복사한 것이며 새 부등식 계산이나 native 배열 재분석을 하지 않았다.

| 분기 | 내부 S/T 하한 | 허용 S/T 상한 | 외부 A 상한 | 외부 T 상한 (V/m) | 요구 T 하한 (V/m) | 저장 결과 |
|---|---:|---:|---:|---:|---:|---|
| `A*[t,1]` | 6.81051052369 | 6.21865142463 | 1.38210813165 | 3.29788117797 | 4.06184889058 | 양 구간 excluded |
| `A*[1,t]` | 6.97865147206 | 6.21865142463 | 1.42498727731 | 3.31827311051 | 4.06184889058 | 양 구간 excluded |

내부 구간에서는 저장된 단조성·동차성 bound `S/T ≥ (l/u) S(u)/T(l)`, `l=0.5,u=1`을 사용해 공통 A를 소거했다. 두 하한은 허용비보다 크므로 T를 유지하며 S를 억제할 수 없다.

외부 구간에서는 `T(t)≤T(0.5)`와 주파수가 분리된 전력의 항등식 `Pj(A,t)=A²(t²Pvariable,j+Pconstant,j)≥A²Pconstant,j`를 사용했다. SC/접촉/SC+dermis 손실3개의 필수 한도에서 얻은 A 상한을 적용한 T 상한이 요구하한에 미달한다. 목표 mean/P10·표면/비표적8개 gate를 모두 통과한다고 결론 내리려면 이 필요조건 부분집합부터 충족해야 하므로, 이 부분집합의 배제로 해당 고정계열의8gate/8cap 동시통과를 배제한다. P10이나 모든 비표적 지표를 각각 독립적으로 증명한 것은 아니다.

| 분기 | 고정 출력 | 필수 전력 cap | 고정출력 단위전력 하한 W | 기준 cap 상한 W | A 상한 |
|---|---:|---|---:|---:|---:|
| `A*[t,1]` | 1 | `SC_power_W` | 1.13233215464e-06 | 2.17635704155e-06 | 1.38636683296 |
| `A*[t,1]` | 1 | `contact_power_W` | 9.61812140275e-07 | 1.83727550058e-06 | 1.38210813165 |
| `A*[t,1]` | 1 | `skin_SC_plus_dermis_power_W` | 0.000379072630351 | 0.000736180770271 | 1.39357718482 |
| `A*[1,t]` | 0 | `SC_power_W` | 9.99490057105e-07 | 2.17635704155e-06 | 1.47562444364 |
| `A*[1,t]` | 0 | `contact_power_W` | 8.35810464295e-07 | 1.83727550058e-06 | 1.48263158271 |
| `A*[1,t]` | 0 | `skin_SC_plus_dermis_power_W` | 0.000362545492667 | 0.000736180770271 | 1.42498727731 |

6개 출력별 단위전력 항등식 검사는 저장 PASS다. 접촉 surface_Jmax/J95·접촉전압·SC/접촉손실·SC+dermis 체적vector Jmax/J95·SC+dermis 손실의 canonical8개 한도는 원래 square 기준으로 유지한다. bound는 그중3개 손실 한도만 필요한 조건으로 사용했다. source power cap 또는1 Vpp ceiling은 배제 결론에 필요하지 않다. 기준 수치 한도를 인체 안전 한계로 표현하지 않는다.

원래 square의 T=`4.061848941601601 V/m`, S=`25.25922183168775 V/m`에 저장된 outward arithmetic guard를 적용했다. guard는 상대 `1e-08`, 절대 `1e-08`이며 각 scalar/비율/전력/진폭의 단위에서 따로 적용했다. 그래서 표의 허용 S/T 및 요구 T는 raw 기준과 소폭 다르다. 이 guard는 모델 불확실성·연속체 오차·전체 격자 수렴에 대한 bound가 아니다.

한 출력의 진폭이0인 끝점은 기본 두-carrier maxTIS=0인 해석적 끝점으로 별도 처리했다. carrier RMS는0일 필요가 없으며 이 끝점에서도 생리적 추론은 하지 않는다.

## 무엇을 이어받고 무엇을 검증하지 않았는가

앞선 ratio4의 half/sqrt-half 표본에서 저장된 scalar와 출력별 전력, 회전1:1 및 원래 square의 고정 기준을 사용했다. ratio4에서는 네 표본 모두 목표mean/P10·표면P95/offP95를 실패했고 half의 고변조체적4개는 통과했다. 이번 bound는 네 표본의 실패를 그대로 무한계열로 일반화한 것이 아니라, 고정지표의 단조성·동차성 및 분리주파수 전력 항등식으로 나머지 구간을 제한한 별도 진단이다.

[ratio4 probe40·전류·signed power 증거](ROTATION_RATIO_RESULTS_20261021.result-brief.json)는 그대로 보존한다. 이번 진단은 새 전위·전기장·프로브·loaded ETA 예측을 만들지 않았다. 5정규화의 이전 결과는 원래 정의대로 남으며, 특히 skin8는 source power/1 Vpp 상한 없는8개 수치 부담이라는 의미를 바꾸지 않았다.

`native_arrays_read=false`, `independent_field_recalculation=false`, `new_PDE=0`, `global_physical_feasibility_inferred=false`, `candidate_adopted=false`다. 물성·피부접촉/PBS 불확실성, SC/XY/bulk/edge/contact 수렴, 연속방향 최대, 하드웨어·실험·활성화·안전성은 검증하지 않았다. 저장된 이산 지표·전력 항등식과 stated arithmetic tolerance가 성립한다는 조건을 벗어나면 새 증거가 필요하다. 미증명 구간은 inconclusive로 남기는 원칙을 보존한다.

## 실행·소스·발행 영수증

실제 wall `0.08177248999709263 s`, CPU `1`, peakRSS `24379392 bytes`, 진단 cap60 s다. 큐는 `completed_preregistered_queue`, bounds/GET/발행3단계 모두exit0이다. 발행 `published_completed_batch`, `2026-10-21T17:50:17.956068+00:00`, commit `428ac3ec0b1118375bb59c81597bc7b6bf94b57f`다. root선정이며 `peer_endorsed=false`를 유지한다.

- geometry native source: `3381113eeee81b0925890d5d4d17496764901fd5`
- geometry config SHA256: `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
- bounds implementation/preregistration source: `645ddca95ba8c258e86b1a91a2cdf6d4d3d454bd`
- 결과 `inputs_unchanged=true`. JSON 입력 SHA 및 사전등록 SHA 일치만 이 문서 작성 과정에서 다시 확인했다. 원시 배열 재현 검증을 수행한 것이 아니다.

- [결과 summary](cloud-rotation-amplitude-bounds-20261021T181000Z/summary.json), SHA256 `70046bad98db81e9ab1ee324d408f56dc68fd035f75dc60bd6825048ee9cc77f`
- [사전등록](cloud-rotation-amplitude-bounds-context-20261021T181000Z/preregistration.json), SHA256 `a88b55e7963f4fd39a7c9453a891bf34b2eda3855869d7dcaebcc084c3a29e86`
- [선정 decision](cloud-rotation-amplitude-bounds-context-20261021T181000Z/decision.json), SHA256 `7b329e55b6a88d1070bec372493dbc7125249531c880db3739af4709da128c82`
- [큐 summary](cloud-rotation-amplitude-bounds-context-20261021T181000Z/queue/summary.json), SHA256 `881f8394b93bc5994ca9a87420ba46a7c83318c38b659db3b8b585d0605f1b61`
- [GET 피드백 snapshot](cloud-rotation-amplitude-bounds-context-20261021T181000Z/feedback-after.json), SHA256 `2ea91c0e48cb6ec71b217c46256c045e3d8eaf233fd01fa9edc67dafd2a9d6d8`
- [발행 영수증](cloud-rotation-amplitude-bounds-context-20261021T181000Z/bounds-publication-20261021T181000Z.json), SHA256 `b5456c72d5f38a888ac4bbebb214b5261ead7a91278058075d30ba070b4bbf1a`

이전 문서의 후속 진단 `UNRUN` 표시는 해당 작성 시점의 역사적 snapshot으로 보존하며, 이번 완료 결과는 이 새 문서에 연결한다. 이 보고서에서 다음 coherent 배치가 실행 완료되었다고 주장하지 않는다.
