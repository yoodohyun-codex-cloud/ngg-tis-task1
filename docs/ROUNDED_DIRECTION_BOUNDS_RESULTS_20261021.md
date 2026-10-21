# Rounded 방향 상·하한 결과 — 2026-10-21

선택된 rounded 구동 opt-e7은 SC2와 같은 명령·진폭의 SC4 모두에서 전체 비표적 P95의 **조건부 방향 강건 실패**가 남았다. `skin_contact_only`에서 목표 평균은 방향 강건 통과이고 목표 P10과 표층 P95는 미결정이다. 두 조건 모두 8항목 중 **5통과·1실패·2미결정**이며 채택하지 않았다. Rounded square3h도 같은 skin8에서 목표 평균·P10의 방향 강건 실패와 비표적 6항목의 방향 강건 통과를 보였다. 이 결과는 고정 모델에 한정하며 전체 수렴이나 모든 물리 설계의 불가능성을 뜻하지 않는다.

근거: [완료 JSON](cloud-rounded-direction-bounds-20261021T205000Z/summary.json), [사전등록 v2](cloud-rounded-direction-bounds-context-20261021T205000Z/bounds-plan-v2.json), [root 결정](cloud-rounded-direction-bounds-context-20261021T205000Z/decision.json), [기계 판독 요약](ROUNDED_DIRECTION_BOUNDS_RESULTS_20261021.result-brief.json), [결과 GUI](CLOUD_ROUNDED_DIRECTION_BOUNDS_RESULTS_20261021.html). 이 문서는 완료된 집계·개별 JSON만 읽었다. 개별 JSON 4개를 집계 내용과 대조하고 JSON SHA256을 계산했다. NPZ·native E·grid·φ는 읽거나 재해시하지 않았다. 아래 아카이브 SHA256은 완료 JSON에 기록된 선언값이며 별도 복구·재해시 검증과 구분한다.

실행은 `calculated_supplemental_unadopted`, 구현 커밋은 `f1b17a8d1f0cc8d40339a5827edce755877822e8`이다. 실제 계산 30.491987초, 최대 RSS 470,929,408바이트, CPU1을 사용했다. 한도는 전체600초·조건120초·RSS3GiB·디스크 여유2GiB이며 승인된 누적13,800초를 확대하지 않았다. 신규 PDE·프로브는 0회, 입력 보존과 기존 판정 불변이 확인되었다. 유한 큐의 계산·피드백 GET 두 단계는 모두 exit0으로 종료했다.

팬텀 D50 mm와 SC/dermis/fat/muscle 0.1/5/5/15 mm, 위쪽 부착, 물리 패드4개·독립 출력2개·공통 GND·출력50 Ω을 유지했다. hXY=0.625 mm, bulk14/14/40이며 SC2는351,680셀, SC4는361,728셀이다. Rounded SC2/SC4는 동일 mask 바이트·고정 물리 윤곽을 사용한다. Rounded는 패드당225 mm²·576개 full-face의 고정 합집합, 총900 mm², 실제 계단형 둘레70 mm이다. 매끄러운 원형·둘레 축소·모서리 수렴으로 해석하지 않는다.

기본 목표 ROI는 중앙 r≤5 mm·깊이15–20 mm의 전체 부피, 표층 비표적은 깊이0–5 mm, 전체 비표적은 primary ROI의 전체 complement이다. z=0은 윗면, +z는 깊이이며 X/Y는 수평 로컬 축이다. 저장된 fractional native ROI 부피와 h²dz 가중치를 유지하고 분석적 부피로 재정규화하지 않았다.

`L`은 기존2,074방향 maxTIS 하한, `U`는 9λ PSD 상한이다. 모든 표의 전기장 단위는 기본파3000/3030 Hz 투영 변조 폭 V/m이다. Carrier RMS·전체 square 파형의 envelope·원시 E·native φ 프로브 Vpp와 다르다. Square3h의 고조파 부담은 기존 모드에 보존했지만 이번 방향 감사는 두 기본파 E만 읽었다.

아래 P/F/I는 각각 조건부 방향 강건 통과/실패/미결정이다. 순서는 **목표mean, 목표P10, 표층P95, 표층V≥c_mean, 표층V≥c_P10, 전체비표적P95, 전체비표적V≥c_mean, 전체비표적V≥c_P10**이다. 고변조 부피 cutoff는 원래 SC2 square의 저장된 mean/P10을 유지하며 생리적 역치가 아니다. 기존8선별 결과를 교체하지 않는다.

각 모드의 A는 저장된 공통 진폭 배율이다. Equal I는 출력별 RMS 전류의 합, equal P는 총 공급전력만 각각 맞춘다. Skin8은 원래 SC2 square의 피부·접촉8상한을 사용하며 전력 상한과1 Vpp ceiling을 포함하지 않는다. Legacy는 전력과1 Vpp ceiling을 추가한다. 이들을 동시에 일치한다고 가정하지 않는다. SC4의 모드명과 A는 **역사적 SC2 진폭**을 그대로 뜻하며 SC4에서 전류·전력·피부부담을 다시 맞췄다는 뜻이 아니다. 실제 복소 계수와 whole-wave Vpp는 동일하게 보존했고 supplemental SC4 rematch는 제외했다. A를 모든 출력의 Vpp와 혼동하지 않는다.

## raw — 고정 원자료

| 조건 | A | 목표 mean L–U | 목표 P10 L–U | 표층 P95 L–U | 전체비표적 P95 L–U | 8항목 P/F/I | 통과/실패/미결정 |
|---|---:|---:|---:|---:|---:|---|---:|
| [원래 사각 SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/summary.json) | 1.000000000 | 4.061849–4.063236 | 3.645736–3.648477 | 25.259222–25.371916 | 23.435719–23.500215 | 기준 | 기준 |
| [rounded SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/summary.json) | 1.000000000 | 4.052491–4.053876 | 3.638801–3.641481 | 24.985967–25.099469 | 23.537593–23.585487 | F F P P P F P P | 5/3/0 |
| [선택 opt-e7 SC2](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/summary.json) | 1.000000000 | 3.683801–3.685289 | 3.305136–3.305577 | 22.991926–23.102527 | 21.432119–21.511189 | F F P P P P P P | 6/2/0 |
| [선택 opt-e7 SC4 · 같은 명령/A](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/summary.json) | 1.000000000 | 3.683813–3.685301 | 3.305145–3.305587 | 22.992494–23.102022 | 21.431909–21.510550 | F F P P P P P P | 6/2/0 |

## equal I — SC2 출력 RMS 합 일치

| 조건 | A | 목표 mean L–U | 목표 P10 L–U | 표층 P95 L–U | 전체비표적 P95 L–U | 8항목 P/F/I | 통과/실패/미결정 |
|---|---:|---:|---:|---:|---:|---|---:|
| [원래 사각 SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/summary.json) | 1.000000000 | 4.061849–4.063236 | 3.645736–3.648477 | 25.259222–25.371916 | 23.435719–23.500215 | 기준 | 기준 |
| [rounded SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/summary.json) | 1.011223983 | 4.097976–4.099377 | 3.679643–3.682353 | 25.266409–25.381185 | 23.801779–23.850210 | P P I P P F F F | 4/3/1 |
| [선택 opt-e7 SC2](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/summary.json) | 1.165946282 | 4.295114–4.296849 | 3.853611–3.854126 | 26.807351–26.936306 | 24.988699–25.080891 | P P F F F F F F | 2/6/0 |
| [선택 opt-e7 SC4 · 같은 명령/A](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/summary.json) | 1.165946282 | 4.295128–4.296863 | 3.853622–3.854137 | 26.808013–26.935717 | 24.988454–25.080146 | P P F F F F F F | 2/6/0 |

## equal P — SC2 총전력 일치

| 조건 | A | 목표 mean L–U | 목표 P10 L–U | 표층 P95 L–U | 전체비표적 P95 L–U | 8항목 P/F/I | 통과/실패/미결정 |
|---|---:|---:|---:|---:|---:|---|---:|
| [원래 사각 SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/summary.json) | 1.000000000 | 4.061849–4.063236 | 3.645736–3.648477 | 25.259222–25.371916 | 23.435719–23.500215 | 기준 | 기준 |
| [rounded SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/summary.json) | 1.005477351 | 4.074688–4.076081 | 3.658732–3.661426 | 25.122824–25.236948 | 23.666517–23.714673 | P P P P P F P I | 6/1/1 |
| [선택 opt-e7 SC2](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/summary.json) | 1.155136770 | 4.255294–4.257012 | 3.817884–3.818394 | 26.558820–26.686579 | 24.757028–24.848365 | P P F F F F F F | 2/6/0 |
| [선택 opt-e7 SC4 · 같은 명령/A](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/summary.json) | 1.155136770 | 4.255308–4.257027 | 3.817895–3.818405 | 26.559476–26.685995 | 24.756786–24.847627 | P P F F F F F F | 2/6/0 |

## skin8 — 원래 SC2 피부·접촉 8상한

| 조건 | A | 목표 mean L–U | 목표 P10 L–U | 표층 P95 L–U | 전체비표적 P95 L–U | 8항목 P/F/I | 통과/실패/미결정 |
|---|---:|---:|---:|---:|---:|---|---:|
| [원래 사각 SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/summary.json) | 1.000000000 | 4.061849–4.063236 | 3.645736–3.648477 | 25.259222–25.371916 | 23.435719–23.500215 | 기준 | 기준 |
| [rounded SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/summary.json) | 0.982372543 | 3.981056–3.982417 | 3.574658–3.577291 | 24.545528–24.657029 | 23.122685–23.169735 | F F P P P P P P | 6/2/0 |
| [선택 opt-e7 SC2](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/summary.json) | 1.103419987 | 4.064779–4.066421 | 3.646953–3.647440 | 25.369751–25.491791 | 23.648628–23.735876 | P I I P P F P P | 5/1/2 |
| [선택 opt-e7 SC4 · 같은 명령/A](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/summary.json) | 1.103419987 | 4.064793–4.066435 | 3.646963–3.647451 | 25.370378–25.491233 | 23.648396–23.735171 | P I I P P F P P | 5/1/2 |

## legacy — 피부8+전력+1 Vpp ceiling

| 조건 | A | 목표 mean L–U | 목표 P10 L–U | 표층 P95 L–U | 전체비표적 P95 L–U | 8항목 P/F/I | 통과/실패/미결정 |
|---|---:|---:|---:|---:|---:|---|---:|
| [원래 사각 SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/summary.json) | 1.000000000 | 4.061849–4.063236 | 3.645736–3.648477 | 25.259222–25.371916 | 23.435719–23.500215 | 기준 | 기준 |
| [rounded SC2 square3h](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/summary.json) | 0.982372543 | 3.981056–3.982417 | 3.574658–3.577291 | 24.545528–24.657029 | 23.122685–23.169735 | F F P P P P P P | 6/2/0 |
| [선택 opt-e7 SC2](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/summary.json) | 1.000000000 | 3.683801–3.685289 | 3.305136–3.305577 | 22.991926–23.102527 | 21.432119–21.511189 | F F P P P P P P | 6/2/0 |
| [선택 opt-e7 SC4 · 같은 명령/A](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/summary.json) | 1.000000000 | 3.683813–3.685301 | 3.305145–3.305587 | 22.992494–23.102022 | 21.431909–21.510550 | F F P P P P P P | 6/2/0 |

## Skin8 결론과 실제 고정 방향

원래 SC2 square 평균 U=4.063235935889318 V/m보다 선택 SC2 평균 L=4.064779347798120 V/m와 SC4 평균 L=4.064792819146645 V/m가 높아 평균은 조건부 방향 강건 통과이다. P10은 각 구간이 기준 구간과 겹치므로 미결정이며 기존 sampled2074 P10 통과를 연속 방향 강건 통과로 승격하지 않는다. 표층 P95도 미결정이다.

전체 비표적 P95는 선택 SC2 L=23.648628083416750 V/m, SC4 L=23.648396397750115 V/m로 기준 U=23.500215379531570 V/m보다 높다. 방향 상한을 고려해도 이 고정 모델·명령·진폭의 비표적 P95 실패는 남는다. 반면 표층·전체 비표적의 고변조 부피4항목은 조건부 방향 강건 통과이다. 서로 다른 비표적 지표를 하나의 비율로 합쳐 실패를 숨기지 않는다.

XYZ는 실제 각 고정 축의 별도 투영 변조이다. 합해서 maxTIS를 만들지 않으며, Z는 생리학적 근섬유 방향으로 등록된 축이 아니다. 아래는 저장된 skin8 A를 적용한 목표 ROI 평균 V/m이다.

| 조건 | X 평균 | Y 평균 | Z 평균 |
|---|---:|---:|---:|
| 원래 사각 SC2 square3h | 2.759812022 | 2.759812022 | 0.373723147 |
| rounded SC2 square3h | 2.704802436 | 2.704802436 | 0.364013116 |
| 선택 opt-e7 SC2 | 2.759065455 | 2.759065455 | 0.371125103 |
| 선택 opt-e7 SC4 · 같은 명령/A | 2.759074004 | 2.759074004 | 0.371127184 |

연속 방향 상한은 `Ai=Re(Ei)Re(Ei)^T+Im(Ei)Im(Ei)^T`, `U=2√minλ eigmax(λA0+(1−λ)A1)`이고 λ=0,1/8,…,1의 고정9개를 사용한다. 고유값 여유는 `64·eps·max(||A0||F,||A1||F)+1e−24`이며 raw U·guarded U를 구분해 저장했다. 정확한 최적λ·연속 최댓값·minimax 등호·정식 IEEE 인증을 주장하지 않는다. L≤U 상대1e−10/절대1e−12 V/m 검사와 XYZ 평균·P10 회귀는4개 코호트 모두 통과했고 상한을 L까지 넓힌 셀은 모두0개였다.

각 gate는 후보와 기준의 반대쪽 구간 끝을 비교한다. 목표 통과에는 후보L≥기준U, 비표적 통과에는 후보U≤기준L이 필요하며 실패는 반대쪽 끝으로 확인한다. 기존 산술 허용오차와 추가 outward guard를 유지한다. 미결정은 통과도 실패도 확정하지 못했다는 뜻이다. 이 bound는 PDE·격자·물성·접촉 오차를 덮는 오차막대가 아니다.

## 최초 등록 오류와 보존

최초 구현 `811614689243509505c3d36a2f1258f205541189`의 metadata-first 등록은 `KeyError: n_outputs`로 실패했다. [원 실패](cloud-rounded-direction-bounds-context-20261021T205000Z/bounds-plan.json.failure.json)와 [원인·수정 기록](cloud-rounded-direction-bounds-context-20261021T205000Z/registration-failure-disposition.json)을 보존했다. Native mesh JSON에는 `channels`가 있고 독립 출력 수는 등록된 `case.circuit.n_outputs`에 있다는 ABI 차이였다. 당시 native 배열은 해독하지 않았다. 실제 mesh channels와 circuit 출력2개를 각각 검사하도록 수정했고 기존13개 테스트와 actual-schema 회귀1개, 총14개 테스트를 통과시킨 뒤 새 v2 등록으로 실제 실행했다. 원 실패·원 소스·원 결과를 덮어쓰지 않았다.

## 재현 근거와 보류 조건

개별 JSON 바이트 해시와 아래 선언된 아카이브 해시는 기계 판독 요약에 함께 보존했다. Bounds/LB와 실제 XYZ는 서로 다른 NPZ이다. 문서 작성 단계에서 이 NPZ들의 바이트나 native E·φ를 읽지 않았다.

| 조건 | Bounds/LB 아카이브 SHA256 | 실제 XYZ 아카이브 SHA256 |
|---|---|---|
| 원래 사각 SC2 square3h | [`b9a20cdd28d77577b8c20fc9be28d24cb015e5a353a22bef0e128973ef2dcfbf`](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/direction-bounds.npz) | [`9ebea3d9be1cc26d1fa7e7211e359d02c76ce7e1f8e0d22a063d6c602b3456fa`](cloud-rounded-direction-bounds-20261021T205000Z/baseline-square15-xy80-square_3h/directional-XYZ.npz) |
| rounded SC2 square3h | [`4fdd42dd0d6ec982c8e720c6fa789d1081462a2fdb7d31c52811d67b35b1b55f`](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/direction-bounds.npz) | [`bf744fec89c22783e954b7357fdadfabc1add557f2a56b969ea1cc38a0e7d01e`](cloud-rounded-direction-bounds-20261021T205000Z/rounded-fullface225-xy80-square_3h/directional-XYZ.npz) |
| 선택 opt-e7 SC2 | [`f4394579c70c404d234f00d844f5a12c7321ae10712f93d0f91ca4f51846b707`](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/direction-bounds.npz) | [`10ba012ed98cbcbfb5fb6499bc1e7ae83f30b3a1d6c8e8c910e73d6698744179`](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935/directional-XYZ.npz) |
| 선택 opt-e7 SC4 · 같은 명령/A | [`c56f6a3a4a2e429f9f96533d8c2c6d6e7e26c82fb9a3e2473ff314634010d326`](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/direction-bounds.npz) | [`72fd32fa81b5a0a2e4affeb28ef882023401d6ea767316e78e3e21eb7d303e96`](cloud-rounded-direction-bounds-20261021T205000Z/rounded-opt-e7b3bf639935-SC4-same-command/directional-XYZ.npz) |

완료 집계 JSON SHA256: `17fe81a53b41e553ed1d8b00705d73847459c88ade2551f48123c7c364a1db2e`. 소스/config/mask/native grid 및 입력 SHA, 고정SC2 amplitude·실제 source whole-Vpp, source commit은 개별 JSON과 사전등록에 연결된다. [피드백6324462120 원문 근거](cloud-rounded-sc4-context-20261021T204000Z/feedback-after-sensitivity.json)의 상태와 root 채택·실제 실행은 구분하며 peer 합의를 추정하지 않는다.

이 결과는 선택된 고정 native 모델의 네 코호트·다섯 진폭 조건에 한정된다. SC2→SC4 두 수준에서 유사한 결과가 나와도 전체 SC/XY/bulk/edge/contact 수렴, PBS 계면의 실제 피부 검증, 전원 동기화·흡수 전력 처리, ETA5001 계측 부하, 실험·생리학적 활성화·인체 안전 또는 COMSOL 5.3a 설치·실행을 입증하지 않는다. 기존 nominal 후보는 미채택으로 유지한다. 후속 접촉 불확실성 배치는 root의 별도 등록·실제 실행 증거로 보고하며 이 문서에 미완료 결과를 포함하지 않는다.
