# 인접 source 정사각형 캐시 입력 감사 — 2026-10-21

`adjacent-square15-xy80`의 fine 복소 E·φ 캐시는 현재 환경에 존재한다. 동일한 네 정사각형 패드에서 두 source 위치를 인접하게 바꾼 조건이며, `balancedcross225-adjacent-sources-xy80`와 별개다. 새 PDE 없이 후속 구동 분석에 사용할 입력은 갖췄다. 이 감사는 JSON·설정과 파일 존재·크기만 확인했으며, native E/φ/density/source/loss/grid/NPZ 바이트를 읽거나 재해시·해독하지 않았다. 기존 완료·검증 영수증과 실제 바이트 재검증을 구분한다. 후속 사용 전 root의 단일 실행 잠금 아래에서 선언된 native SHA와 실제 바이트를 확인해야 한다.

## 실제 입력과 원래 기준의 동일성

- Native run: `data-native/cloud-finite-loop-20261020T002600Z-fine`
- Case/design: `adjacent-square15-xy80` / `adjacent-square15`
- Source commit: `be724b0b314263f284fdbc5397bdaf019685fa29`
- [설정](../data-native/cloud-finite-loop-20261020T002600Z-fine/configs/adjacent-square15-xy80.properties), SHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
- [완료 summary](../data-native/cloud-finite-loop-20261020T002600Z-fine/postprocess/adjacent-square15-xy80/summary.json), SHA256 `b65cffd90dd881570de4079d898a7e790ed1983d7b4b43baaf9866a1f6a00620`
- [사전등록](../data-native/cloud-finite-loop-20261020T002600Z-fine/preregistration.json), SHA256 `9471285970bce80c18ffe95f322d2525854b7e7200da7140b41a0b8c2ec24ed6`
- [Case 영수증](../data-native/cloud-finite-loop-20261020T002600Z-fine/cases/adjacent-square15-xy80.json), SHA256 `fd2e4b0d55a4c12d5f4350f65925e0dd7a0b54afd07432aa379eef8fda79aa82`

원래 `cloud-mesh-c1-20261019T190000Z/baseline-square15-xy80`와 실제 설정 property를 전부 비교했다. 다른 키는 `mask.path`, `mask.sha256`, `pad.1.y_mm`(+10→−10), `pad.2.y_mm`(−10→+10) 네 개뿐이다. 물리 접촉 네 개의 전체 위치 집합·사각형15×15 mm·패드당225 mm²·총900 mm²는 같고, solver pad1과2의 물리 역할이 교환된다.

| Solver pad | 실제 중심 (x,y) mm | 연결 |
|---|---|---|
| 0 | (−10,−10) | out0, 3000 Hz 및 명시된9000 Hz 고조파 |
| 1 | (+10,−10) | out1, 3030 Hz 및 명시된9090 Hz 고조파 |
| 2 | (+10,+10) | 공통 GND |
| 3 | (−10,+10) | 동일 공통 GND |

D50 mm, SC/dermis/fat/muscle=0.1/5/5/15 mm·윗면, hXY0.625 mm·SC2·bulk14/14/40·351,680 cells다. 독립 출력2개·귀환 노드1개·50 Ω이며, 비구동 주파수 출력은0 V through50 Ω다. 기존 nominal source는 전체 파형 open/high-Z1 Vpp, peak0.5 V 기준이다. 네 패드나 두 carrier를 독립 전원 네 개로 해석하지 않는다.

물성·네 주파수의 specific complex Z real/imag·출력·mesh 설정은 canonical SC2 square와 문자열 수준에서 동일하다. 두 mesh JSON의 차이는 config SHA뿐이며 z_faces도 정확히 같다. 복원 정의는 `half_face_flux; top contact term averaged over full cell face h^2`, peak `+jomega_t`, lossless gzip of little-endian Float64/complex128, producer `SelectivityShapeBasis` / `selectivity_native`다. 채널 수2·source peak0.5 V·50 Ω·단열 side/bottom과 동일 staircase D50 경계를 보존한다.

| 주파수 Hz | Specific Z real Ω·m² | Specific Z imaginary Ω·m² |
|---:|---:|---:|
| 3000 | 4.4523250115054224e−05 | −9.587510512701813e−05 |
| 3030 | 4.407669448241336e−05 | −9.563561408953766e−05 |
| 9000 | 4.4451099045190295e−05 | −9.508107221709578e−05 |
| 9090 | 4.462269396972829e−05 | −9.543844896710299e−05 |

두 case의 `source_coating_nm=10`, `source_Rs_fit_window_Hz=500`이다. **500은 fit window의 Hz이며 Rs=500 Ω이라는 뜻이 아니다.** [nominal fit](../tis-java/runs/eis-rs-window-analysis-20261019T123730Z/cases/eis010-f0500.json)의 저장된 selected Rs는236.5717747232937 Ω, 실제 fit 구간573.62–10000 Hz다. [EIS profile](../tis-java/runs/explore-20261017T133224038032Z/inputs/eis-profiles.json)의 측정 면적은0.0001 m²다. 설정의 Ω·m²는 이미 `(Z_measured−Rs)×measurement_area`를 한 번 적용한 nominal PBS surrogate다. 후속 loader에서 Rs를 또 빼거나 측정·패드 면적을 또 곱하지 않는다. 이것은 실제 피부 접촉의 실험 검증이 아니다. 이번 감사는 EIS 보간·fit·임피던스를 새로 계산하지 않았다.

## Native 파일 존재와 기존 방정식 영수증

Basis 폴더는 `data-native/cloud-finite-loop-20261020T002600Z-fine/bases/adjacent-square15-xy80`다. `BASIS_COMPLETE`, 네 주파수별 `field-*.bin.gz`, `potential-*.bin.gz`, `density-*.bin`, `source-*.bin`, `loss-*.bin`, `contacts-*.csv`가 모두 존재한다. E·φ gzip8개는 각각 비어 있지 않다. `grid.csv.gz`, `mesh-metadata.json`, `validation.json`, frozen-source manifest도 존재한다. 이는 현재 파일 존재 확인이며 내용 재검증·복구 테스트의 대체가 아니다.

| 기존 native gate | 저장 값 | 기존 한도 |
|---|---:|---:|
| max_residual | 9.395707359747688e−10 | 2e−7 |
| max_power_error | 2.448259835538768e−10 | 2e−7 |
| max_current_error | 8.21556390515277e−9 | 2e−6 |
| max_area_relative_error | 1.0880185641326534e−14 | 1e−10 |
| max_interface_normal_current_relative_error | 1.585860019941293e−15 | 2e−7 |

기존 record는 `complete`, post는 `complete`/`source_inputs_unchanged=true`다. [Full-skin audit](../data-native/cloud-finite-loop-20261020T002600Z-fine/audit/finite-loop-20261020T002600Z-adjacent-square15-xy80.json)은 `computed_spatial_and_skinJ_audit`, `native_inputs_unchanged=true`이고 위 동일 post SHA와 canonical original SC2 baseline에 연결된다. 감사 SHA256은 `66832667efc2bf828a41b7182577edd2a4c726e6cc69b1f462ce6c560c9b0e66`이다. Audit의 `numerical_spatial_validation`은 `not established; native samples only`이므로 방정식 gate 통과를 mesh/edge/contact 수렴으로 승격하지 않는다.

Mesh JSON SHA256: `e5475b188e1b81e89ca1fa387e0125251a97dc72c7914e5009fdb6ed1e37fab3`.
Frozen-source manifest SHA256: `604b5170376ded1bf28ac4d55b84fcbc5dad26993af342c3f7037c394761e5ee`.

## 이미 저장된 원래8개 부담 한도 비교

[4행 volume 결과](cloud-adjacent-cross-20261021T164000Z/volume.json), SHA256 `5ae3c3bc95021024109e6b3c0f4985b978b8a4262c4a7cd3441aca819d6bb725`에서 이 square/adjacent 행을 확인했다. 다음은 저장값이며 새 gate·정규화 계산이 아니다. 단위 V/m, primary ROI r≤5 mm·depth15–20 mm, 표층0–5 mm, 전체 비표적은 primary complement다.

| 조건/모드 | 목표 mean | 목표 P10 | 표층 P95 | 전체 비표적 P95 |
|---|---:|---:|---:|---:|
| Original square/opposite skin8 | 4.061848941601601 | 3.6457357391300533 | 25.25922183168775 | 23.43571858123385 |
| Adjacent square raw1Vpp | 3.4036352217441235 | 3.1062975564164006 | 52.2987957142925 | 26.542940631785758 |
| Adjacent square skin8 | 3.2648117444301574 | 2.979601538700193 | 50.165693837214604 | 25.460338332602102 |

Skin8의 저장 A는0.9592131740713304이며 활성 제한은 `bulk_skin_J_vector_RMS_p95_A_m2`다. 원래 상한6.998260050840811 A/m²에 맞춘 값이다. 이8개 제한에는 source power와1 Vpp ceiling을 포함하지 않으며, 이를 추가하는 legacy는 별도 모드다. 원래4행 공개 결과에서 새8-gate screen을 수행한 것은 cross/adjacent 한 조건뿐이다. Cached square 행에 새 판정 건수를 부여하지 않는다.

## 기존 tau의 완전한 결과 재사용

기존 producer는 [task1_return_current_drive_scout.py](../tools/task1_return_current_drive_scout.py)다. [완료 summary](cloud-next-return-current-20261021T172000Z/summary.json)는 `task1-return-current-drive-scout-v1` / `calculated_unadopted` / `inputs_unchanged=true`, SHA256 `482146de98397f3753404aaad2355b0832ff8b64bfbc201d8e9446aa971a2ae1`이다. 아래 세 조건은 모두 같은 adjacent-square native run/case/config와 source commit에 연결되며, 저장된8항목 전체 통과는 false다. Cross 세 조건을 square 결과로 바꾸어 표시하지 않는다.

Source seed는 cosine 복소 명령 `c3000=[1,τq0]`, `c3030=[τq1,1]`이며9000/9090 계수는0이다.
`q0=−0.44406572678782397+0.05989895218486412j`, `q1=−0.44385705292081495+0.05938573051566675j`.

| tau / 저장 ID | c3000 (out0,out1) | c3030 (out0,out1) |
|---|---|---|
| 0 / return-net-square-tau0 | (0.9999999999999929, 0) | (0, 0.9999999999999929) |
| 0.5 / return-net-square-tau0p5 | (0.8169809702778016, −0.18139662416911678+0.024468152037306967j) | (−0.18131138287994647+0.024258505868672738j, 0.8169809702778016) |
| 1 / return-net-square-tau1 | (0.690586248614846, −0.3066656844008285+0.04136539268530535j) | (−0.30652157709782674+0.04101096885806648j, 0.690586248614846) |

각 condition JSON은 `task1-return-current-drive-condition-v1`이며, 계수는 `coefficient_vectors`의 real/imaginary 각2요소로 명시된다. 위 표는 실제 whole-wave Vpp 정규화 후 저장값이다. Seed 자체를1 Vpp로 부르지 않는다.

| 기존 전체 condition JSON | SHA256 |
|---|---|
| [tau0](cloud-next-return-current-20261021T172000Z/return-net-square-tau0/condition.json) | `220924f62826c6c35ba28291efa9a7bf9e66dc41db6858f2ed0be19ca7768d6c` |
| [tau0p5](cloud-next-return-current-20261021T172000Z/return-net-square-tau0p5/condition.json) | `fd2165b6a967fa79a410014965ca4ba0854c941f3aaefd1184e4f13e5edeec45` |
| [tau1](cloud-next-return-current-20261021T172000Z/return-net-square-tau1/condition.json) | `7230e59cab7a6ab272cc2a14883965a378ae00593a8f8dbd9980fb217f1b2a66` |

두 carrier를 일률적으로−j배 하면 고정 진폭의 방향 변조·RMS·주파수별 손실은 불변이다. 그러나3000/3030 Hz의 실제 복수 tone 파형에서 공통 시간 이동과 같다고 보장할 수 없다. 따라서 whole-wave source/probe Vpp와 global normalization을 자동으로 동일시하여 전체 결과의 정확한 alias로 취급하면 안 된다. 후속은 cosine canonical 계수 `[1,z0]`, `[z1,rho]`를 유지하여 세 결과를 정확히 재사용하거나, 다른 위상 조건으로 실제 파형 회귀를 검증해야 한다. 음의 zero를 수치적 zero로 처리할 수 있어도 원래 JSON과 SHA는 바꾸지 않는다.

## 후속 controller에서 필요한 구분

Frozen numerical loader의2channel·351,680cells·4frequency·complex128/gzip ABI는 기존과 일치한다. 그러나 rounded controller는 rounded ID/run·576face radial 외곽 등을 명시적으로 요구한다. 새 adjacent용 source adapter가 필요하며, square를 rounded/fixed-native-face-union으로 재분류하거나 옛 사전등록을 수정하면 안 된다.

검토할 구체적5gene 영역은 `c3000=[1,z0]`, `c3030=[z1,rho]`의 `Re/Im(z0), Re/Im(z1)∈[−1,1]`, `rho∈[0.5,1.5]`이며9000/9090 명령은0으로 고정한다. 이 영역은 동일 adjacent topology에서 두 복소 cross 비율과 양의 carrier 진폭 비율만 바꾼다. 기존 tau0/0.5/1은 정확한 저장 명령을 불러오는 cache 대조로 처리한다. 기존 tau는1차원이며 두 주파수의 상쇄를 연동하고 rho=1로 고정한다. 두 carrier의 cross 비율·위상과 진폭 비율을 독립적으로 바꾸는5gene은 다른 질문이다. 단, 공통 위상만 바꾸는 sweep이나 기존 tau 재계산을 새 연구 건수로 세지 않는다. Source/metric identity를 포함하는 cache와 기존 세 전체 결과 alias를 유지하고, 새 proxy 평가·최종 검증의 상한을 root가 사전등록한다. 신규 PDE는 필요하지 않으며 root의 실제 선정·계산은 이 감사와 별도다.

이 감사는 새 worker를 시작하지 않았고 prepare·과학 배열 계산·Git·외부 전송을 수행하지 않았다. PBS 접촉 불확실성, SC/XY/bulk/edge/contact 수렴, 계측 부하·출력 흡수/compliance, 실험·생리·안전의 미검증을 유지한다.
