# Task 1 fat층 검증 요청 — 2026-10-24

**새 fat 검증 계산은 아직 시작되지 않았다.** 이 문서는 기존 계산 담당자에게 전달하는 실행 명세와 검토 기록이다. 검토 환경에서 solver/worker를 실행하거나 계산 브랜치를 변경하지 않았다. 기존 ID **T1-F004**(수치·물성/경계 검증), **T1-F001/F002**(부피·방향·부담 정의), **T1-F006/F007/F010**(단일 소유·중복 방지·실제 실행 인계)의 `FAT-20261024` 하위 요청으로 추적한다. 새 공식 ID를 만들거나 기존 실패를 닫지 않는다.

사용자 지시: “아니 새 시뮬레이션 하라고 지시해 … fat 레이어의 전기적 특성도 제대로 세팅되었는지 다시 점검해.” 따라서 기존 그림 재색칠이나 캐시 후처리만으로 이 요청을 완료 처리할 수 없다. 다만 skin/muscle과 같은 매끄러운 기울기가 반드시 있어야 한다는 가설에 맞춰 물성·장을 바꾸지 않는다.

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

NGG의 nominal PBS-derived contact impedance는 별도 주파수별 면적 임피던스(Ω m²)이며 fat σ나 skin의 실측 근거가 아니다. Rs-fit 창과 carrier/전원50 Ω도 구분한다. 새 batch의 준비 단계에서 **실제 사용한 팬텀 제작 레퍼런스 논문과 배합**을 먼저 식별하고 현재 상수와 대조한다. 사용자는 이전 팬텀 논문을 물성 근거로 지정했다. 일반 생체 지방의 표준값을 대신 넣어 이 요구를 충족했다고 하지 않는다. 논문 제목/DOI·해당 표/그림/쪽, 실제 fat 모사층 배합·농도/단위·제작 조건, 측정 주파수와 온도·측정법/불확실성을 실행 config에 연결한다. 논문이 전도도만 보고하면 εr은 ‘미보고/별도 가정’으로 남기며 측정된 값으로 꾸미지 않는다. 보간·외삽이나 다른 배합의 값을 쓰면 그 범위와 이유를 별도 표시한다.

2026-10-24 사용자 추가 지시를 반영했다. 지정된 원 Windows 작업 폴더·기존 담당자·진행 작업·원데이터·참고 논문은 부모 작업의 별도 읽기 전용 사전확인 대상이다. 이 클라우드 검토 환경이 그 경로에 접근할 수 있다고 추정하지 않는다. **정확한 논문 및 실제 배합의 식별·대조는 아직 미완료**이며, 부모가 전달할 근거와 원 계산 담당자의 확인으로 채워야 한다. 이 추가사항 자체는 접근 승인·새 계산 시작·물성 수정의 근거가 아니다.

기존 물성 그대로의 baseline 재현은 기존 결과의 재현성 검사로 명확히 표시한다. 팬텀 논문 대조에서 차이가 확인되면 원 config를 보존하고, 근거·주파수/온도 조건·변경량을 고정한 별도 검증 config를 기존 예산 안의 유한 등록에 반영한다. 문헌값을 확인하지 않은 채 임의로 고치거나, 원하는 gradient를 만들기 위해 물성을 조정하지 않는다. 팬텀 근거 검증과 기존 수치 재현을 각각 판정한다.

전체 전류는 전도+변위 성분이다([공식 electroquasistatics 설명](https://www.comsol.com/multiphysics/electromagnetics)). 이상적 계면에서 검증할 양은 접선 E와 법선 **Jtotal=γE**이며, σE만의 법선 연속이나 서로 다른 물질의 법선 E 연속을 강제하지 않는다. COMSOL 문헌은 물리식 참고일 뿐 이 Java 계산을 COMSOL 실행으로 보고하는 근거가 아니다.

## 4. 먼저 바로잡을 기존 해석

부모 작업이 수행해 인계한 [f0749c17 compact GUI 감사](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/f0749c17b99a4d4096b9b0fdbd070a3518190651/docs/TASK1_TOP5_20261022_compact/index.html)에서 baseline XZ y=−0.3125 mm의 fat min은 Float16 표시 근사 약8 V/m이지만, 같은 데이터 XY z=9.92142857143 mm는 min4.04296875 V/m, 5024셀 중182개가8 미만이다. 따라서 **“fat 전체 부피의 최소가8 V/m” 주장은 이미 반증됐다.** 이 검토는 그 compact 배열을 다시 decode하지 않았으며, 이 수치는 새 PDE/원 Float64 전체3D 통계가 아니다. 단면 min을 부피 min으로 옮기지 않는다.

해당 maxTIS는 각 셀의2074개 표본방향 최대다. 고정방향 TIS, 각 carrier 벡터 E, carrier RMS와 다르며 연속 모든 방향의 정확한 최대라는 뜻도 아니다. 단면/방향 선택이나 색상 clipping으로 생긴 외관을 전체 fat의 물성 오류/균일장 증거로 삼지 않는다.

기존 [mesh-convergence](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-restart-20261020/mesh-convergence.json)의 coarse→XY80 square 비교는 surface_J_RMS_max +23.068646%, contactV +23.070630%로5% gate **failed**다. 목표 ROI mean/P10의 작은 변화와 [실행 보존/잔차 pass](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/docs/cloud-restart-20261020/mesh-c1-execution.json)는 이를 없애지 않는다. fat 전체 min/계면 E의 수렴은 **not-run/not-established**다. baseline 원 volume.npz가 공개 tree에 없으므로 compact 그림이 이를 대체하지 못한다.

## 5. 기존 계산 소유자에게 요청하는 유한 실행 순서

이는 실행 명령/등록 완료본이 아닌 **채택·사전등록 요청**이다. 기존 소유자가 현재 환경에서 실행 가능한 entrypoint와 정확한 명령을 확정해야 한다. 검토자가 새 worker나 옛 명령을 자동 실행하지 않는다.

1. **소유권·중복·자원 admission.** 원 Task1 task/environment 식별자, 현재 PID/startticks·자식·두 lock·현 queue/등록·최신 remote와 local source를 확인한다. centered C1 후처리/게시나 fat 관련 작업이 이미 있으면 그 소유자가 안전한 단계 경계에서 이어가며 중복 solve를 만들지 않는다. 존재하는 cache를 새로운 계산으로 세지 않는다.
2. **재료/격자/경계 준비.** 위 case/config/mask SHA와 runtime effective material 표(각 f의 실제 complex γ), 길이 단위 변환, z-face/center/layer index를 보관한다. fat는5.1≤z<10.1 mm; 부동소수점 face10.100000000000005 등의 허용 처리와 실제 mask를 검사한다. material ID와 GUI 색상 이름을 따로 확인한다.
3. **최소 새 재현 1조건.** canonical baseline h0.625/SC2/bulk14/14/40, 원4주파수×2 RHS를 고유 run에 새로 풀어 기존 정의를 재현한다. 원 코드/config/mask/계수·입력 hash를 고정하고 원본/기존 GUI/current pointer를 보존한다. 실제 새 solve가 불가능하면 `not_run`과 원인을 명시한다. cached postprocess만 수행한 경우 이 단계의 대체 성공으로 세지 않는다.
4. **첫 단계 통과 후 최대1조건 추가.** 같은 baseline h0.625/SC2에서 현재 구현이 지원하는 bulk18/18/56을 사용하여 fat 내부와 두 경계의 민감도를 비교한다. 이는 dermis/fat/muscle을 함께 세분화한 **coupled bulk 비교**이며 fat-only가 아니다. 첫 admission은 최대2개 새 native 조건이다. 원 config 재현 실패나 자원 gate 실패면 중단하여 실패를 보존한다.
5. **기존 native의 제한된 비교 및 다음 결정.** 이미 완료된 baseline coarse/XY80/bulk와 best1 f35 native가 원 환경에 있고 SHA/format이 맞으면 추가 solve 없이 새 fat 통계를 얻어 재사용으로 표시한다. 새로운 두 수준에서도 fat/경계가 미수렴이면 다음 XY h0.5 비교를 별도 유한 등록으로 제안한다. 정확한 best1 새 solve가 필요하면 남은 예산/보존 공간과 함께 다음 등록에 명시한다. 이 최초2조건 요청에는 자동 XY sweep·best1 재계산·새 물성 탐색을 붙이지 않는다. 재사용 best1만으로 best1의 새 계산/수렴을 주장하지 않는다.

기존 상한 CPU1, 동시PDE1, heap2 GiB, RSS 및 소유 tmpfs 합3 GiB,800000cells, 원2 GiB disk reserve, 총 승인13800초를 유지한다. 조건당600초 및 필요한 준비·후처리·게시·보존 peak를 실제 원장 안에서 사전 예약한다. “남은 시간 전부 새 배치 예산”으로 계산하지 않는다.

[10월24일 budget note](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/data-native/cloud-centered-c1-y0-20261025/final-verification/budget-accounting-note.json)의 free_workspace_bytes=2147680256은2 GiB reserve보다 **196608 bytes**만 많다. 이 역시 당시 관측이며 지금의 free 값은 아니다. 후처리/실패한 게시 영수증에는 잔여2733.2337/2732.7449초가 기록됐지만 최종 게시 비용 이후 live 잔여는 미확인이다. 이전 nx120/791280-cell 계획의 저장 부족587174528B는 그 특정 배치의 과거 측정이다. 새 작은 배치에 그대로 복사하지 말고 현재 native/RAM/tmpfs/압축/영속보존/원격 게시 peak를 별도로 계산한다.

centered C1의 작은1주파수/1RHS tmpfs 처리·공개 성공이4주파수/2RHS 전체 체적 저장을 자동 허용하지 않는다. tmpfs는 RSS 합산과 영속 artifact readback 전 보존을 포함해야 하며 삭제·reserve 완화·예산 확대·설치·보안 변경은 승인되지 않았다. **현재 연결/lock/자원 gate를 충족했다고 이 검토에서 주장하지 않는다.**

## 6. 독립적인 물리·재구성·메시 검사

[ShapeNet](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe/tis-java/SelectivityShapeBasis.java#L185)은 z-face conductance를 `area/(dz_a/(2γ_a)+dz_b/(2γ_b))`로 조립한다. 저장 E는 half-face-flux 재구성이며 top contact 항은 패치 면적이 아닌 전체 h²로 평균된다. 측면·바닥은 outside edge가 없는 절연, 원통은 셀 중심 mask의 계단 경계다. 다음 검사는 이 이산화의 의미를 분리한다.

- 실제 φ의 실수/허수와 complex E/J의 부호·축·SI 단위·peak/RMS를 확인한다. z5.1/10.1 mm에서 인접 **셀 중심 E**를 face의 한쪽 극한값으로 바로 비교하지 않는다.
- 평면1D layered-slab 분석해(직렬 complex impedance, 일정 Jtotal, 층별 E=Jtotal/γ)와 균질 affine potential 검사로 conductance·경계 재구성을 확인한다. 이는 원통의 전역 정확도 검증이나 실제 새 baseline solve의 대체가 아니다.
- 두 인터페이스에서 양쪽 potential 기반의 독립적인 one-sided gradient/외삽을 정의해 접선 Ex/Ey의 차이, face potential 차이, 법선 γE의 차이를 complex 값과 정규화 분모/작은 값 처리까지 기록한다. 계단 측벽 근처와 내부를 사전 정의한 거리로 분리하되 전체 결과를 숨기지 않는다.
- 기존 `interfaceContinuity`는 같은 shared face flux로 face φ와 양쪽 J를 재구성하므로 거의 기계 정밀도의 일치는 **조립식 자기 정합**이다. 이를 독립 계면 정확도/접선 E/격자 수렴으로 확대하지 않는다. shared-flux check와 위 독립 진단을 별도 행에 둔다.
- 기존 residual≤2e−7, power≤2e−7, current≤2e−6, area≤1e−10, interface-normal≤2e−7 gate를 유지하고 실제 max·threshold·pass/fail을 게시한다. 새로운 analytic/gradient/fat-stat 비교의 정확한 norm·허용치·좌표 대응은 결과를 보기 전에 계산 담당자가 사전등록한다. 독립 검사에 등록 기준이 없으면 “diagnostic/not-gated”로 남기며 pass를 사후 발명하지 않는다.
- XY 비교는 원통 mask 체적·계단 측벽과 패드 교차 면적·경계 거리의 변화를 함께 보고한다. 서로 다른 위치의 극값을 같은 점 오차처럼 쓰지 않는다. 두 수준 변화만으로 완전 수렴을 인증하지 않는다.

## 7. 필수 결과와 상태 장부

전체3D fat에 대해 volume-weighted min/P10/median/P90/max, 각 extrema의 좌표·cell ID, quantile의 ECDF/가중치/대표 cell 선택·동률 처리, 실제 체적·셀수·NaN/Inf 수를 저장한다. P10/P90 등이 단일 좌표의 고유값은 아니므로 대표 좌표와 통계 정의를 함께 둔다. 동일 정의의 깊이별 분포와 지정 XZ/XY/YZ 단면은 별도 결과다.

주파수별 complex vector E와 Jtotal 및 conduction J, carrier별 RMS, 전체 RMS, 고정방향 x/y/z TIS, 기존2074방향 maxTIS/최대방향 index를 구분한다. 같은 주파수의 두 출력은 **complex 합산 후** RMS/전력을 계산한다. 두 tone 고정방향 변조의 정의(예: peak phasor 투영의2 min 진폭), fundamental와 harmonic 포함 RMS, directional sampling 한계를 명시한다. 전원 전류·loaded/contact voltage·전력/층별/접촉/50 Ω 손실 및 표층·목표 ROI·비표적 분포도 같은 합성·정규화로 보존한다.

지도는 같은 물리량/정규화끼리 상한 clipping 없는 공통 scale와 명시적 colorbar/단위/실제 범위를 쓴다. fat 세부 확대가 필요하면 별도 scale임을 표시하고 전체 scale도 함께 둔다. 새 raw φ/E/J/grid/config/coefficients를 complex128/Float64 lossless로 보존하며 Float16 GUI export를 정량 근거로 쓰지 않는다.

| 기존 ID / 하위 요청 | 현재 판정 | 완료에 필요한 직접 근거 |
|---|---|---|
| F004/F010 FAT-20261024 인계 | requested; 계산측 채택/담당 연결 미확인 | adoption source/commit, 기존 소유 task/environment·lock 확인 |
| F004 config→γ 정적 감사 | passed, 공개 코드·바이트/hash 연결 범위 | 새 실행 effective material/config hash는 별도 필요 |
| F001/F004 전체 fat min8 주장 | failed, 인계된 compact XY 반례 | 원 Float64 전체3D extrema는 아직 미검증 |
| F004 새 fat baseline·bulk 배치 | **not_run** | 고유 run ID, 시작/종료/PID/startticks/명령/환경/exit와 직접 artifact URL |
| F004 기존 baseline 이산 보존 | 공개 기록 passed | 이 검사만으로 fat 경계/극값 수렴을 닫지 않음 |
| F004 XY surface/contact 수렴 | failed 유지 | 동일 정의·새 격자 근거; 임계값 변경 불가 |
| F004 fat extrema/독립 경계 E 수렴 | not-run/not-established | raw φ/complex fields, analytic/gradient/mesh 수치·gate |
| F010 원 계산 연결·현재 admission | 미확인; 이 검토환경에서 실행 불가 | 기존 담당자의 현재 lock/예산/공간 관측과 실행/정확한 blocker |

채택·실행·검증 상태를 독립 갱신한다. 코드/등록만 있으면 실행으로 세지 않고, 다른 C1 계산이나 “수신” 댓글은 fat 요청의 시작 근거가 아니다. GitHub 조정 뒤에도 원 담당자가 확인되지 않으면 정확한 연결 blocker를 부모에게 보고한다. 공개 결과가 도착하면 실제 JSON/원값을 대조한 범위만 닫는다. 깊이 집중·물성 실험 교정·dry NGG 피부 접촉·신경 모집·사람 설정·안전·최적점 주장은 이 요청의 결과가 아니다.
