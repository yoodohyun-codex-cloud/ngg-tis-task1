# Task 1 SC·dermis·fat·muscle 재계산 검증 요청 — 2026-10-24

**현재 지시는 네 층 전체의 물성 근거를 재검토한 뒤 별도 신규 PDE로 검증하는 것이다.** 기존 미교정 baseline·원자료·실패·GUI는 보존한다. 이번 전 층 확대 요청의 계산측 채택/새 실행 근거는 아직 없으며 이 검토 환경에서는 PDE/worker를 시작하지 않았다.

기존 **T1-F004/F001/F002/F006/F007/F010 — FAT-20261024** ID와 댓글6390505397을 계속 사용한다. 추적 이름은 유지하지만 범위는 SC·dermis·fat·muscle 전체로 확대됐다. 아래 예전 fat 중심 기록은 이력이며 현재 실행 범위에는 이 절과 개정 §5가 우선한다. 공개 내용은 기존 가정값·논문 대비 불일치·서지 출처·미확인 항목·재계산 지시로 한정한다.

## 0. 전 층 물성 근거표와 현재 실행 지시

| 층 | 기존 σ (S/m) / εr (무차원) | 근거 감사와 불일치 | 새 config 전에 확정할 것 |
|---|---|---|---|
| SC | .0002 /110000 | 이전 전체 Skin 값 일부를 SC 가정에 재사용. Goyal2022는 해당 층의3kHz bulk σ/εr를 제공하지 않음 | 실제 SC 모사체·공극/수화·두께·주파수별 σ/εr 근거. 미확보 값은 sensitivity assumption으로 표시 |
| dermis 모사체 | .2 /10000 | 원 README의 가정. Goyal의 PVA 아래층은 나머지 epidermis/dermis/hypodermis를 합친 deeper-tissue 등가층이며 독립 dermis가 아님 | 5mm 독립 dermis 모사체로 대응시킬 근거와 bulk 물성. 전체 두층5mm를 dermis5mm의 근거로 쓰지 않음 |
| fat 모사체 | .04 /1000 | Anand Fig10의 제작 fat σ 전체 표시범위 약.013–.025 S/m는.04를 지지하지 않음. εr1000의 carrier 근거 없음 | 겹친 저주파 점으로2k/2010/3k/3030Hz 정확값을 만들지 않음. 원시표/재료 fit 또는 명시적 가정 필요 |
| muscle 모사체 | .3 /100000 | Anand Fig11b의 그림 근사 εr는2kHz 부근 약3.7–4×10⁵,3kHz 부근 약3.2–3.6×10⁵로 현재10⁵와 불일치. σ=.3의 carrier별 일치도 미확인 | 위 εr 범위를 정밀 입력/통계 불확도 구간으로 쓰지 않음. 실제 주파수 자료와 배합·온도·원 fit 필요 |

기존 수치의 출처는 [원 tis-java README의 가정 물성 절](https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/README.md#가정-물성-측정값으로-오해하지-말-것)과 [model-inputs의 legacy60Hz 기록](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/d6167f21e3d533952025571234f5a8751cdda557/tis-java/model-inputs.json)이다. README는 전체 Skin 값 일부의 SC 재사용과 **모든 εr의 탐색 가정**을 명시한다. legacy60Hz 전도도 이력을 현재 carrier의 실측 근거로 바꾸지 않는다. 원 파일의 null/legacy 상태도 보존한다.

[ Goyal, Borkholder, Day (2022), *A biomimetic skin phantom for characterizing wearable electrodes in the low-frequency regime*](https://doi.org/10.1016/j.sna.2022.113513), *Sensors and Actuators A: Physical*340,113513: §2.1–2.2/PDF2–4쪽과 Fig2/PDF4쪽은 SC와 deeper-tissue PVA 등가층을 구분한다. 전체 phantom 두께0.5cm는 §3.1/PDF4쪽의 **전체 두층5mm**다. 검증 주파수1–1000Hz의 측정 Z에는 전극–팬텀 계면과 phantom이 함께 포함되며 층별 σ/εr 표가 없다. 이를 SC/독립 dermis의2–3kHz bulk값으로 역지정하지 않는다. 로컬8쪽 PDF SHA256 `6d6bd13017e1674f041dccac19ec5f37bee34b50b791c11caa9b8cf09936eaf8`와 Fig2/§3.1 렌더·본문을 직접 확인했다. PDF/그림은 게시하지 않는다.

Anand2019의 전체 서지·SHA·방법·Fig10/11 근거는 §3에 있다. 개별 재료는 E4980A/coaxial1kHz–2MHz50점이고, 완성 전완만 Quadra1–349kHz15점 후 Cole fit2MHz 확장이다. 원시 주파수 물성표/개별 재료 fit 계수 없이 정확한 carrier값을 조작하지 않는다. **NGG의 PBS EIS는 전극 계면 자료이며 네 층의 bulk σ/εr가 아니다.**

현재 감사에서 단위·`γ=σ+j2πfε0εr`·mm→m·층 순서에 명백한 오류는 발견되지 않았다. 이 결과는 재료값의 검증을 뜻하지 않는다. 기존 SC 값에서3kHz의 Imγ/Reγ=`2π·3000·ε0·110000/.0002`≈**91.7936**이므로 εr 가정의 영향은 따로 검사해야 한다. 이 비율은 입력값의 산술 점검이며 새 PDE 결과가 아니다.

**물성 감사와 복소 envelope 계산식 감사는 별개 검증 행으로 제출한다.** 고정방향의 두 순수 carrier는 peak phasor 투영 후 `2 min(|n·E1|,|n·E2|)`의 max−min convention을 확인한다. 같은 주파수의 두 출력은 complex 합산한 뒤 크기/전력을 구한다. 단일 carrier·한 tone0·같은 투영 진폭·직교/위상차 벡터 등의 해석 가능한 예제와 복소 시간파형을 대조하고, 최대방향 표본2074개와 고정방향·RMS·harmonic 포함량을 분리한다. 다주파수 합성 파형에 두 tone 공식을 무조건 확장하지 않는다. 수식 검사 통과를 물성/격자 검증 통과로 쓰거나 그 반대로 쓰지 않는다.

**실행 요구:** 현재 담당자가 아래 §5의 단일 소유/자원 admission을 확인하고 네 층의 σ·εr·주파수·단위·물성 출처/미확인 가정을 모두 포함한 reset 근거표와 config diff를 작성한 후, 새 고유 run에서 네 층 PDE를 다시 푼다. 원물성이 없으면 가정 민감도 결과와 원자료 확보 과제를 나누며 “논문 재현”으로 표시하지 않는다. GUI 재생성·기존 native 재사용은 새 시뮬레이션 수행으로 인정하지 않는다.

이전 fat 요청의 담당자 수신은 별도 확인됐고 [담당자의 공개 댓글6390625143](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6390625143)도 해당 요청을 별도 미실행으로 유지한다. **이번 전 층 확대 지시의 수신·채택·실행은 별도 확인 대상**이다. 현재 검토 환경에는 원 task로 직접 전달하는 도구가 없으므로 기존 GitHub 요청을 갱신한다. credential/보안/연결 설정을 변경하거나 중복 worker를 만들지 않는다.

검토 snapshot: PR2 `b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe`; 직전 `8eb12d1` 대비 centered C1 결과 79개 경로가 추가됐다. README, AGENTS, RESEARCH_LOOP 및 기존 검토 장부를 읽었다. 이 checkout은 검토 패키지이며 원 계산 환경이 아니다.

## 1. 현재 작업과 연결 상태: 새 C1 결과와 fat 요청을 구분

[centered C1 실행 영수증](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/data-native/cloud-centered-c1-y0-20261025/execute-receipt.json)은 22:27:46–22:28:00 UTC에 새 3000 Hz/1 RHS/PDE 1조건 완료 후 `explore_tis` import 실패를 기록한다. 전체 stage 상태는 `failed_preserved`이므로 “최초 실행 전체 성공”으로 바꾸지 않는다. [후처리 복구](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/data-native/cloud-centered-c1-y0-20261025/final-verification/postprocess-receipt.json)는 22:37:58–22:38:03, 기존 native 1개 재사용/새 PDE 0이며 GUI 검증 완료다. [공개 validation](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/TASK1_CENTERED_C1_Y0_20261025/validation.json)과 [생산자 댓글6390464509](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6390464509)을 직접 읽었다. native source `2339c6b4`, 복구 source `8eb12d1`, 결과 게시 `b7ef9aae`를 구분한다. 최초 게시 영수증의 실패도 후속 원격 게시 성공 근거와 함께 보존한다.

이는 2패드/1출력 centered C1의 새 계산이다. **4패드 baseline/best1 fat 검증 배치가 아니며, fat 요청 수행 횟수로 세지 않는다.** 원 E/φ/grid 등의 공개 경로 존재와 생산자의 79파일 SHA/bytes readback 보고는 확인했지만 이 검토가 그 native 배열을 독립 decode한 것은 아니다. 과거 baseline/best1 전체 native 백업 완료도 뜻하지 않는다.

공개 PR2 설명의 “현재 worker 없음”과 10월21일 상태 문서는 과거 snapshot이다. 10월24일 새 계산·게시가 확인되므로 이를 현재 생존 판정으로 쓰지 않는다. 영수증의 `remaining_owned_children={}`는 해당 stage 종료 관측이지 전역 lock/모든 worker 확인이 아니다. **현재 계산 작업자 활동·잠금 소유는 미확인**이다.

검토 환경에는 원 계산 경로 `/workspace/ngg-tis-task1`가 없고 원 Task1 cloud task에 연결·전달·실행할 도구가 노출되지 않았다. GitHub 앱의 공개 read는 성공했다. 로컬 GitHub CLI는 이후 HTTP401로 중단했으며 자격증명 변경/재시도/권한 우회를 하지 않았다. 이 작업에는 별도 승인 대기 action이 없다. GitHub 요청 게시를 원 계산 담당자의 수신·채택·시작으로 간주하지 않는다.

## 2. 재현 대상의 정확한 식별

| 항목 | canonical 4pad baseline | 현재 GUI best1 |
|---|---|---|
| case | `baseline-square15-xy80` | `rounded-expand-f35b23a22166` (f35); native geometry `rounded-fullface225-xy80` |
| native run | `cloud-mesh-c1-20261019T190000Z` | `cloud-rounded-fullface-20261021T200000Z` |
| native source commit | `38f005ecefc2c432cd6424a06f599f93682cc202` | `10a70e9cfa19537825f2f5e829b7d1d14acbd35c` |
| effective config SHA256 | `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b` | `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0` |
| mask SHA256 | `7cfc576d31e50dcf0621567cce225df3d2cc8e55eeff4aa5d6667c59bfc401b2` | `a18c9697232e5f486acc06a16129c2e4ffb0dee45fb6ec5b0edbe34d1b9def29` |
| grid | hXY 0.625 mm, SC2, bulk14/14/40, 351680 cells | 동일 격자; 4개 rounded fullface mask |
| pads/circuit | 사각15 mm, 각225 mm², 총900 mm²; 4pad/2outputs/commonGND/각50 Ω | 각225 mm², 총900 mm²; 같은 output/return topology |
| waveform | `square_3h`, 3000/3030/9000/9090 Hz; 원 계수·위상 보존 | `optimized_two_tone_sine`, 양 출력 모두3000/3030 Hz; 9000/9090 계수0 |

baseline은 [mesh-c1 실행 기록](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-restart-20261020/mesh-c1-execution.json)과 [공개 원 config template](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/tis-java/runs/selectivity-design-20261019T155933Z/configs/baseline-square15-xy80.properties)을 연결했다. 원 template SHA256은 `578812946b79762b63931e85dc201ee673a8c370ec01f9767098f5b6476206d8`다. 그 바이트에서 `mask.path` 한 군데의
`/workspace/ngg-tis-simulation/tis-java/runs/selectivity-design-20261019T155933Z/masks/baseline-square15-h0.625.csv`를
`/workspace/ngg-tis-task1/data-native/cloud-mesh-c1-20261019T190000Z/masks/baseline-square15-h0.625.csv`로 매핑한 SHA가 기록된 runtime config SHA와 정확히 일치했다. 이는 **바이트 재구성과 기록 hash 일치**이며 원 runtime 파일에 직접 접근한 검증은 아니다. 원본은 수정하지 않았다.

best1은 [정확한 native config](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-rounded-fullface-context-20261021T200000Z/completed-native-snapshot/configs/rounded-fullface225-xy80.properties)의 공개 바이트 SHA가 위 값과 일치했다. [f35 condition](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-f35b23a22166/condition.json)의 원문 SHA256은 `b29a07e13752ef6c84893f43bbefa37a3a9aa0bdd6e1c20dfea8986ccdd835ce`다. 과거 다른 “Best1” 이름과 혼동하지 않는다. 최근 [best1/C1 GUI 설명](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/TASK1_BEST1_SINGLE_PAIR_20261025/README.md)의 게시 `ec5b30a9`/과학 후처리 source `71ffbe81`은 위 native source와 다르다.

공통 pad centers는 pad0(-10,-10), pad1(10,10), pad2(10,-10), pad3(-10,10) mm; pad0→out0, pad1→out1, pad2/3→GND다. 0.5 Vpeak/1 Vpp high-Z-before-50 Ω 기저, peak phasor `+jωt`, 비구동 출력은 해당 주파수에서0 V/50 Ω 종단이다. 실제 source/loaded metal/contact voltage를 구분한다.

f35의 signed complex coefficient vector는 3000 Hz: Re[0,−0.009669863358429174], Im[−0.9669863358429175,−0.009669863358429174]; 3030 Hz: Re[−0.009669863358429174,0], Im[−0.01933972671685835,−0.9863260625597758]다. 9000/9090은0. 원 raw global scale 0.9669863358429175와 별도 skin8 공통 배율 1.1051077374853904를 중복 적용하지 않는다. 격자 비교의 첫 기준은 **같은 명령/계수/배율**이며 새 격자에서 부담 재매칭한 결과는 별도 표다. 회로·접촉·전력도 원 복소 기저에서 같은 계수로 다시 합성한다.

## 3. fat 물성의 설정과 실제 적용

고정 원통 직경50 mm; SC/dermis/fat/muscle 두께0.1/5/5/15 mm, 총25.1 mm. 두 config의 재료값:

| layer | σ (S/m) | εr (무차원) |
|---|---:|---:|
| SC | 0.0002 | 110000 |
| dermis | 0.2 | 10000 |
| fat | 0.04 | 1000 |
| muscle | 0.3 | 100000 |

[CloudShapeBasis](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/tools/java/CloudShapeBasis.java#L89)은 config의 모든 σ/εr을 읽고, [TisSweep.Net](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/tis-java/TisSweep.java#L51)은 `γ=σ+j2πf ε0 εr`, ε0=8.8541878128e−12 F/m를 사용한다. **εr은 실제 연산에 적용된다.** 하지만 σ·εr 자체는 네 주파수에 같은 상수다. 용량성 항의 ω 의존성만 있고, 조직별 주파수 분산 모델·이방성 tensor·phantom 측정 교정은 없다. 소스 header도 물성을 “uncalibrated hypotheses, NOT measured phantom data”라고 명시한다. 이 상수의 실측/논문 추정 근거는 검토된 config/header에서 확인되지 않았다. 출처 없는 숫자를 검증된 생체 fat 특성으로 인증하지 않는다.

NGG의 nominal PBS-derived contact impedance는 별도 주파수별 면적 임피던스(Ω m²)이며 fat σ나 skin의 실측 근거가 아니다. Rs-fit 창과 carrier/전원50 Ω도 구분한다.

### 2026-10-24 원문 확인에 따른 물성 전제 정정

사용자가 지정한 논문은 Gautam Anand, Andrew Lowe, Ahmed Al-Jumaily, **Tissue phantoms to mimic the dielectric properties of human forearm section for multi-frequency bioimpedance analysis at low frequencies**, *Materials Science & Engineering C* **96** (2019),496–508, [DOI10.1016/j.msec.2018.11.080](https://doi.org/10.1016/j.msec.2018.11.080)이다. 별도 논문 검토 작업의 원문 검증을 인계받았으며, 이 검토에서도 기존 로컬 PDF의 SHA256 `dd042f66b74a5d42cf335238e6801409364fa20704520293e2971b1fe10cbe60`와13쪽을 확인하고 관련 본문·Table3 및 Fig10/11 렌더를 직접 대조했다. 아래 PDF 쪽은1부터 세며 인쇄 쪽과 구분한다. PDF 원문/그림 자체는 이 공개 문서 변경에 포함하지 않는다.

**현재 fat σ=.04 S/m·εr=1000은 이 논문의 제작 팬텀 물성으로 뒷받침되지 않는다.** config가 코드에 제대로 전달된다는 정적 검증과 물성 선택의 실험 근거는 별개다. Fig10a의 제작 fat σ는 표시 주파수 전체에 걸쳐 대략.013–.025 S/m인 그림 근사이며 .04 S/m은 그 상단보다 높다. 이 범위를2–3 kHz의 정확한 값이나 불확도 구간으로 쓰지 않는다. Fig10의0–2 MHz 선형 주파수 축에서는 저주파 점들이 겹쳐2k/2010/3k/3030 Hz별 σ·εr를 정확히 추출할 수 없고, **εr=1000도 원문의 해당 저주파 값으로 확인되지 않는다.** 범위 중간값·원하는 경향·임의 보간으로 새 수치를 만들지 않는다.

| 근거 위치 | 확인한 내용 | 적용 한계/정정 |
|---|---|---|
| §2.1.1–2.2, 인쇄498–499쪽 / PDF3–4쪽; Fig3(B,C) | Keysight E4980A LCR와 coaxial sensor, 침지 깊이를 바꾸며 fat/muscle 혼합물의 σ·εr를 산출.1 kHz–2 MHz 로그 간격50점. room temperature에서 안정화한 시료; 최소6 h 또는 overnight | 정확한 실온 °C는 미보고. 계기 자체의20 Hz 하한과 실제1 kHz 시작 sweep을 구분한다. |
| §3.2, 인쇄502쪽 / PDF7쪽 | fat 제작에0.05% NaCl 용액과5% agar를 사용 | 최종 fat 질량분율 표가 아니다. 과거 레시피 기록의 water94.95%를 논문 표값으로 확정하지 않는다. |
| Table3, 인쇄503쪽 / PDF8쪽 | muscle wt%: water75.4,NaCl.03,agar3.77,gelatine1.88,propylene glycol18.72 | 표기값의 합은99.80.100으로 임의 재정규화하지 않는다. 사용자의 실제 제조 배합 일치 여부는 별도 확인한다. |
| Fig10(a,b), 인쇄504쪽 / PDF9쪽 | fat conductivity/relative permittivity 비교. blue는 제작 simulant의 계산 물성, red는 Gabriel 모델의 목표 조직값 | red를 이번 연구의 새 사람 측정으로 쓰지 않는다. 제작 팬텀과 생체 목표값을 서로 대체하지 않는다. 그림 전체 범위와 특정 carrier 값을 구분한다. |
| Fig11(a,b), 인쇄505쪽 / PDF10쪽 | muscle 제작 simulant와 Gabriel 목표값의 비교 | Table3 배합과 주파수·측정 조건을 함께 연결한다. 그림만으로 임의의 정확한 carrier 표를 생성하지 않는다. |
| §2.3, 인쇄501쪽 / PDF6쪽; Discussion504쪽 / PDF9쪽 | **완성 전완 phantom**은 Quadra로1–349 kHz의15점을 측정하고 Cole fit으로2 MHz까지 확장 | 개별 fat/muscle 재료의 LCR1 kHz–2 MHz/50점 실험과 별개다. 과거 인계 기록의 “개별 물성도1–349 kHz 실측 후 확장” 해석은 정정한다. |

원문에는 carrier별로 바로 재사용할 제작 fat/muscle의 원시 주파수–σ–εr 표나 해당 재료의 fit 계수 집합이 제시되지 않는다. 전완 전체 임피던스의 Cole fit을 개별 fat 재료의 fit으로 대체하지 않는다. 따라서 논문 identity·배합/측정법/그림의 확인은 완료했지만 **정확한2k/2010/3k/3030 Hz 및 사용 고조파의 제작 팬텀 물성 확보는 미완료**다. 숫자 확보의 다음 단계는 적법하게 가용한 원시 측정표/재료 fit 자료와 실제 제조 조건의 확인이다. 그림에서 분해되지 않는 점을 정밀 수치로 게시하지 않는다.

원래 고정 D50/층0.1·5·5·15 mm 모델은 보존한다. 논문의 전완 형상 전체를 재현했다고 부르지 않는다. 이전 상수 그대로의 새 baseline·mesh 검사는 **기존 가정의 수치 재현/민감도 검사**로 표시하고, 팬텀 물성 근거 확보 단계와 별도 판정한다. 원물성표 없이 새 계산을 “논문 재현” 또는 “논문 검증 물성 적용”으로 표시하지 않는다. 이후 자료가 확보되면 원 config를 보존하고 적용 주파수·온도·배합·단위·보간/외삽·불확실성을 명시한 별도 config/유한 등록을 기존 예산 안에서 검토한다. 원하는 gradient를 만들기 위한 물성 조정은 금지한다.

지정된 원 Windows 작업 경로와 실제 제조 자료는 부모의 별도 읽기 전용 확인 대상이다. 부모가 전달한 최신 상태는 연결된 로컬 TIS 폴더가 비어 있고 기존 실행 담당 연결은 여전히 미확인이라는 것이다. 이 클라우드의 검토용 PDF 존재가 그 원 Windows 경로·native 결과·계산 task의 접근을 증명하지 않는다. 새 PDE/worker를 여기서 시작하지 않는다.

전체 전류는 전도+변위 성분이다([공식 electroquasistatics 설명](https://www.comsol.com/multiphysics/electromagnetics)). 이상적 계면에서 검증할 양은 접선 E와 법선 **Jtotal=γE**이며, σE만의 법선 연속이나 서로 다른 물질의 법선 E 연속을 강제하지 않는다. COMSOL 문헌은 물리식 참고일 뿐 이 Java 계산을 COMSOL 실행으로 보고하는 근거가 아니다.

## 4. 먼저 바로잡을 기존 해석

부모 작업이 수행해 인계한 [f0749c17 compact GUI 감사](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/f0749c17b99a4d4096b9b0fdbd070a3518190651/docs/TASK1_TOP5_20261022_compact/index.html)에서 baseline XZ y=−0.3125 mm의 fat min은 Float16 표시 근사 약8 V/m이지만, 같은 데이터 XY z=9.92142857143 mm는 min4.04296875 V/m, 5024셀 중182개가8 미만이다. 따라서 **“fat 전체 부피의 최소가8 V/m” 주장은 이미 반증됐다.** 이 검토는 그 compact 배열을 다시 decode하지 않았으며, 이 수치는 새 PDE/원 Float64 전체3D 통계가 아니다. 단면 min을 부피 min으로 옮기지 않는다.

해당 maxTIS는 각 셀의2074개 표본방향 최대다. 고정방향 TIS, 각 carrier 벡터 E, carrier RMS와 다르며 연속 모든 방향의 정확한 최대라는 뜻도 아니다. 단면/방향 선택이나 색상 clipping으로 생긴 외관을 전체 fat의 물성 오류/균일장 증거로 삼지 않는다.

기존 [mesh-convergence](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-restart-20261020/mesh-convergence.json)의 coarse→XY80 square 비교는 surface_J_RMS_max +23.068646%, contactV +23.070630%로5% gate **failed**다. 목표 ROI mean/P10의 작은 변화와 [실행 보존/잔차 pass](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-restart-20261020/mesh-c1-execution.json)는 이를 없애지 않는다. fat 전체 min/계면 E의 수렴은 **not-run/not-established**다. baseline 원 volume.npz가 공개 tree에 없으므로 compact 그림이 이를 대체하지 못한다.

## 5. 기존 계산 소유자에게 요청하는 유한 실행 순서 — 전 층 확대

기존 fat-only baseline→bulk 순서보다 **SC/dermis/fat/muscle 전체의 물성 재설정 근거표와 새 PDE 검증**을 우선한다. 기존 원자료·미교정 baseline은 comparator로 보존한다. 이 문서는 계산 담당자에게 주는 실행 지시이며 실제 소유 환경에서의 등록·시작 완료를 대신하지 않는다.

1. **소유권·중복·자원 admission.** 현재 담당자가 PID/startticks·자식·두 lock·진행 phase·등록/remote/local source·이미 수행 중인 전 층/물성 작업을 확인한다. 실행 중이면 같은 소유자가 안전한 단계 경계에서 이어간다. 공개 게시 또는 오래된 종료 기록을 live lock 확인으로 대체하지 않는다. 예산·영속보존 peak·RAM/tmpfs 한도를 실제 원장에서 확인한다.
2. **전 층 material reset 근거표.** 각 층/각 실제 carrier와 harmonic에 `old_sigma_S_m, old_epsilon_r, proposed_sigma_S_m, proposed_epsilon_r, frequency_Hz, source_DOI/page/figure, measured_or_fit_or_assumed, temperature, recipe, unit_conversion, interpolation_or_extrapolation, uncertainty_or_missing`를 채운다. 단순히 fat만 바꾸거나 다른 세 층을 확인 없이 검증 완료로 두지 않는다. 값이 없으면 null/필요 자료와 명시적 sensitivity assumption을 구분하고 선택 근거를 기록한다. 정확값처럼 표시할 새 숫자를 꾸미지 않는다.
3. **별도 code/config diff와 두 감사.** 형상·회로·원 출력 convention을 고정하고 새 σ/εr/frequency 적용을 기존 baseline과 비교한다. material lookup→γ·단위·층 mask와 복소 envelope 공식/합성/peak↔RMS 감사를 별도 gate로 등록한다. 주파수별 물성 지원을 바꾸어야 한다면 기존 코드 지원 범위와 새 구현·검증을 명시하며 old producer/결과를 덮어쓰지 않는다.
4. **새 native PDE, 최초1조건부터.** D50mm,SC/dermis/fat/muscle .1/5/5/15mm,4패드/2출력/commonGND/각50Ω를 고정한다. canonical baseline geometry/source와 새 등록 material config로 첫 실제 새 solve를 고유 run에 수행한다. 현재 baseline의 실제4주파수×2RHS 및 f35의 정확한 복소 계수/활성 주파수를 구분한다. 기존 native를 재색칠/합성하거나 GUI만 갱신하여 이 단계를 완료 처리하지 않는다. 실제 데이터 확보 전이라면 결과를 **네 층의 명시적 가정 민감도**로 표시하고 논문 재현/실제 팬텀 교정은 보류한다.
5. **첫 결과 후 한정 확인.** 기존 승인 원장 안에서 다음 최대1조건을 추가할 수 있다. 첫 결과가 드러낸 가장 큰 불확실성에 대해 동일격자의 한 material scenario 또는 지원되는 coupled-bulk/XY 중 하나를 사전등록하며 동시에 여러 요인을 무통제 변경하지 않는다. 최초 admission은 최대2개 새 native 조건이고 자동 sweep은 없다. 현재 best1 f35의 새 material solve가 이 조건에 선택되지 않으면 `not_run`으로 남긴다. 기존 best1 native 비교는 comparator/reuse로만 표시한다.
6. **완료/실패와 후속 전달.** 실행 run ID·소유 환경·source/config/mask/물성표 SHA·config diff·명령·시작/종료·PID/startticks·exit·예산 전후를 게시한다. raw complex φ/E/J·grid·source current·contact/층/50Ω loss와 아래 §6–7의 네 층 통계/계면/수렴 결과를 보존한다. 제출한 각 검사에 passed/failed/not-run과 이유를 붙인다. 원자료·담당 연결·자원 부족이면 정확한 blocker를 보고하며 GUI 작업으로 완료를 대신하지 않는다. 전 층 물성 확인과 새 시뮬레이션 검증의 미완료 하위단계를 그대로 남긴다.

기존 상한 CPU1, 동시PDE1, heap2 GiB, RSS 및 소유 tmpfs 합3 GiB,800000cells, 원2 GiB disk reserve, 총 승인13800초를 유지한다. 조건당600초 및 필요한 준비·후처리·게시·보존 peak를 실제 원장 안에서 사전 예약한다. “남은 시간 전부 새 배치 예산”으로 계산하지 않는다.

[10월24일 budget note](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/data-native/cloud-centered-c1-y0-20261025/final-verification/budget-accounting-note.json)의 free_workspace_bytes=2147680256은2 GiB reserve보다 **196608 bytes**만 많다. 이 역시 당시 관측이며 지금의 free 값은 아니다. 후처리/실패한 게시 영수증에는 잔여2733.2337/2732.7449초가 기록됐지만 최종 게시 비용 이후 live 잔여는 미확인이다. 이전 nx120/791280-cell 계획의 저장 부족587174528B는 그 특정 배치의 과거 측정이다. 새 작은 배치에 그대로 복사하지 말고 현재 native/RAM/tmpfs/압축/영속보존/원격 게시 peak를 별도로 계산한다.

centered C1의 작은1주파수/1RHS tmpfs 처리·공개 성공이4주파수/2RHS 전체 체적 저장을 자동 허용하지 않는다. tmpfs는 RSS 합산과 영속 artifact readback 전 보존을 포함해야 하며 삭제·reserve 완화·예산 확대·설치·보안 변경은 승인되지 않았다. **현재 연결/lock/자원 gate를 충족했다고 이 검토에서 주장하지 않는다.**

## 6. 독립적인 물리·재구성·메시 검사

[ShapeNet](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/tis-java/SelectivityShapeBasis.java#L185)은 z-face conductance를 `area/(dz_a/(2γ_a)+dz_b/(2γ_b))`로 조립한다. 저장 E는 half-face-flux 재구성이며 top contact 항은 패치 면적이 아닌 전체 h²로 평균된다. 측면·바닥은 outside edge가 없는 절연, 원통은 셀 중심 mask의 계단 경계다. 다음 검사는 이 이산화의 의미를 분리한다.

- 실제 φ의 실수/허수와 complex E/J의 부호·축·SI 단위·peak/RMS를 확인한다. z5.1/10.1 mm에서 인접 **셀 중심 E**를 face의 한쪽 극한값으로 바로 비교하지 않는다.
- 평면1D layered-slab 분석해(직렬 complex impedance, 일정 Jtotal, 층별 E=Jtotal/γ)와 균질 affine potential 검사로 conductance·경계 재구성을 확인한다. 이는 원통의 전역 정확도 검증이나 실제 새 baseline solve의 대체가 아니다.
- SC/dermis z0.1mm를 포함한 세 인터페이스에서 양쪽 potential 기반의 독립적인 one-sided gradient/외삽을 정의해 접선 Ex/Ey의 차이, face potential 차이, 법선 γE의 차이를 complex 값과 정규화 분모/작은 값 처리까지 기록한다. 계단 측벽 근처와 내부를 사전 정의한 거리로 분리하되 전체 결과를 숨기지 않는다.
- 기존 `interfaceContinuity`는 같은 shared face flux로 face φ와 양쪽 J를 재구성하므로 거의 기계 정밀도의 일치는 **조립식 자기 정합**이다. 이를 독립 계면 정확도/접선 E/격자 수렴으로 확대하지 않는다. shared-flux check와 위 독립 진단을 별도 행에 둔다.
- 기존 residual≤2e−7, power≤2e−7, current≤2e−6, area≤1e−10, interface-normal≤2e−7 gate를 유지하고 실제 max·threshold·pass/fail을 게시한다. 새로운 analytic/gradient/fat-stat 비교의 정확한 norm·허용치·좌표 대응은 결과를 보기 전에 계산 담당자가 사전등록한다. 독립 검사에 등록 기준이 없으면 “diagnostic/not-gated”로 남기며 pass를 사후 발명하지 않는다.
- XY 비교는 원통 mask 체적·계단 측벽과 패드 교차 면적·경계 거리의 변화를 함께 보고한다. 서로 다른 위치의 극값을 같은 점 오차처럼 쓰지 않는다. 두 수준 변화만으로 완전 수렴을 인증하지 않는다.

## 7. 필수 결과와 상태 장부

**SC·dermis·fat·muscle 각각의 전체3D 부피**에 대해 volume-weighted min/P10/median/P90/max, 각 extrema의 좌표·cell ID, quantile의 ECDF/가중치/대표 cell 선택·동률 처리, 실제 체적·셀수·NaN/Inf 수를 저장한다. P10/P90 등이 단일 좌표의 고유값은 아니므로 대표 좌표와 통계 정의를 함께 둔다. 동일 정의의 깊이별 분포와 지정 XZ/XY/YZ 단면은 별도 결과다.

주파수별 complex vector E와 Jtotal 및 conduction J, carrier별 RMS, 전체 RMS, 고정방향 x/y/z TIS, 기존2074방향 maxTIS/최대방향 index를 구분한다. 같은 주파수의 두 출력은 **complex 합산 후** RMS/전력을 계산한다. 두 tone 고정방향 변조의 정의(예: peak phasor 투영의2 min 진폭), fundamental와 harmonic 포함 RMS, directional sampling 한계를 명시한다. 전원 전류·loaded/contact voltage·전력/층별/접촉/50 Ω 손실 및 표층·목표 ROI·비표적 분포도 같은 합성·정규화로 보존한다.

지도는 같은 물리량/정규화끼리 상한 clipping 없는 공통 scale와 명시적 colorbar/단위/실제 범위를 쓴다. fat 세부 확대가 필요하면 별도 scale임을 표시하고 전체 scale도 함께 둔다. 새 raw φ/E/J/grid/config/coefficients를 complex128/Float64 lossless로 보존하며 Float16 GUI export를 정량 근거로 쓰지 않는다.

| 기존 ID / 하위 요청 | 현재 판정 | 완료에 필요한 직접 근거 |
|---|---|---|
| F004/F010 FAT-20261024 인계 | 이전 fat 수신 확인; 전 층 확대 requested, 채택/시작 미확인 | adoption source/commit, 기존 소유 task/environment·lock 확인 |
| F004 config→γ 정적 감사 | passed, 공개 코드·바이트/hash 연결 범위 | 새 실행 effective material/config hash는 별도 필요 |
| F004 네 층 팬텀 물성 근거 | 출처·가정·불일치 표 작성; SC/dermis 독립 bulk 근거와 fat/muscle carrier 수치 미검증 | exact σ/εr·원시표/재료 fit 미확보; 논문 재현·실험 교정 보류 |
| F001/F004 전체 fat min8 주장 | failed, 인계된 compact XY 반례 | 원 Float64 전체3D extrema는 아직 미검증 |
| F004 네 층 material reset·새 native 배치 | **not_run** | 고유 run ID, 시작/종료/PID/startticks/명령/환경/exit와 직접 artifact URL |
| F004 기존 baseline 이산 보존 | 공개 기록 passed | 이 검사만으로 fat 경계/극값 수렴을 닫지 않음 |
| F004 XY surface/contact 수렴 | failed 유지 | 동일 정의·새 격자 근거; 임계값 변경 불가 |
| F004 fat extrema/독립 경계 E 수렴 | not-run/not-established | raw φ/complex fields, analytic/gradient/mesh 수치·gate |
| F010 원 계산 연결·현재 admission | 미확인; 이 검토환경에서 실행 불가 | 기존 담당자의 현재 lock/예산/공간 관측과 실행/정확한 blocker |

채택·실행·검증 상태를 독립 갱신한다. 코드/등록만 있으면 실행으로 세지 않고, 다른 C1 계산이나 “수신” 댓글은 fat 요청의 시작 근거가 아니다. GitHub 조정 뒤에도 원 담당자가 확인되지 않으면 정확한 연결 blocker를 부모에게 보고한다. 공개 결과가 도착하면 실제 JSON/원값을 대조한 범위만 닫는다. 깊이 집중·물성 실험 교정·dry NGG 피부 접촉·신경 모집·사람 설정·안전·최적점 주장은 이 요청의 결과가 아니다.
