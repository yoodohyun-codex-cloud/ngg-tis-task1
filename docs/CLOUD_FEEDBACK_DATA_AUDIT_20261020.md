# 새 클라우드의 피드백·원자료 감사 — 2026-10-20 KST

새 저장소의 동결 연구 파일은 변경하지 않았다. 이번 범위는 필수 인계 문서, 실제 입력 파일과 처리 코드의 정적 검토, 공개 GitHub GET 조회, 원 EIS/CV 바이트 대조다. 연구 Python import, fit/CV 적분, solver, 기존 수치 시험, 새 PDE와 원격 쓰기는 수행하지 않았다. 이 감사의 원시 조회·파일 해시·분류는 `runtime/audits/feedback-data-20261020/`에 보존한다. 해시 일치는 입력 바이트의 동일성만 확인하며 시뮬레이션 재현이나 실측 검증을 의미하지 않는다.

## GitHub의 실제 상태

조회 시각은 `github-discovery.json`, `feedback-requests.json`, `producer-latest-requests.json`의 UTC timestamp에 고정했다. 사용자 표시는 KST 기준이다.

| 항목 | 조회한 고정 commit / 상태 |
|---|---|
| 새 저장소 main | `3b5f1861c523a207d02b1a34a5f61c67b88556eb`; branch 1개, issue/PR 0개 |
| 원 저장소 main | `3feb66b4015fea968c4775e65ac176366853cc2e` |
| 원 PR #2 / 검토 문서 | `33f0d6ab106ad4fa54d8fd35672092296c615f87` |
| 원 PR #3 / 생산자 응답 | `7a6b62a9154e2584548e48bef4717b7e666904df` |
| 패키지의 동결 계산 코드 | `8c3a30a778cc9bf19ccb52ca523598bff0a84650` |

원 PR #3은 패키지 source보다 두 commit 앞선다. `33db27bd8cac54322cca284b63333d0875082ce3`의 최종 보고서/이전 인계와 `7a6b62a…`의 게시 영수증 추가다. 비교 응답의 전체 파일 목록을 `upstream-pr3-delta.json`에 보존했다. 기존 `tis-java` 핵심 solver 수정은 이 두 commit의 변경 목록에 없다. 원격 branch를 병합하거나 동결 파일을 덮어쓰지 않고 새 근거로만 연결한다. 작업 2 전용 추가 자료는 적용 대상에서 제외한다.

유도현2/dot 협업의 지정 피드백 문서 `docs/TASK1_FEEDBACK.md`를 원 PR #2 head에서 읽었다. SHA256은 `2f277a9e868879c89687bd040ea4d0bb22adca33596dd3bac6b75aa1322fc384`이며 기존 고정 `f4b6d5fa…` 바이트와 같다. 원 main·PR #3에서 같은 경로는 404이므로 main만 검사하면 피드백을 놓친다. 원 PR #2/#3의 issue comments, review comments, reviews는 각 0개다. GitHub 계정명으로 실제 사람의 별도 신원을 추정하지 않으며, 자동 dot 통신이나 상대의 이번 감사 수신을 주장하지 않는다.

원 PR #3의 `FINAL_COMPLETION.json`은 **원 환경이 사용자 지시로 이전을 위해 종료되었으며 원시 자료 이전은 미수행**이라고 기록한다. 접촉 가장자리 후속은 입력/형식 검토까지만 수행했고 새 PDE 0이다. 이 상태는 원 환경의 과거 실행 권한에 관한 기록이며 현재 사용자가 별도로 승인한 새 작업 1 유한 배치를 취소하는 지시로 해석하지 않는다. 원 worker를 재시작하지 않는다. 문서에 남은 과거 실행 중/미완료 문구는 이 최신 종료 기록과 구분한다.

## 안정적 피드백 ID

`feedback-ledger.json`은 기존 T1-F001–T1-F009를 재번호화하지 않고 피드백 source, 생산자 응답 source, 과거 채택·실행·검증과 현재 환경 상태를 분리한다. 아래 완료는 원 저장 근거의 한정된 과거 완료이며 이번 재실행 결과가 아니다. 원 최초 응답 게시 commit은 `ccb05c9680368be79ac734fa50f386907c0c38a2`다. 최신 응답 파일 안의 미확정 자기 commit 필드는 새 hash로 꾸미지 않았다. 현재 환경의 적용 commit/실행 artifact는 실제 생성 전까지 null이다.

| ID | 이번에 유지한 판단 | 남은 검증 또는 적용 조건 |
|---|---|---|
| T1-F001 | 중심점·부피 ROI·공간 집중 구분 채택 | 표면 최대 유지; 절대 ROI·선택도·같은 부담 동시 개선 미확보 |
| T1-F002 | 같은 Vpp/전력/복합 부담 cap 분리 채택 | 과거 bare cap의 J95 제외와 새 코팅 square cap의 J95 포함을 혼합하지 않음 |
| T1-F003 | 기존 2 kHz 독립 SC/XY 10조건 통과 유지 | 고정 bulk-z 범위; 새 형상·접촉·전체 3D로 전이 불가 |
| T1-F004 | 전체 항목 보류 유지 | Rs-window 결과 확보는 완료; 새 형상 18비교 중 7실패와 타원 SC Jmax +73.1508%는 미해결 |
| T1-F005 | 기본파 TIS와 고조파 포함 RMS/손실 분리 채택 | 새 복수 주파수는 실제 합성 파형으로 검증 필요 |
| T1-F006 | 기존 lock/hash/reuse guard 부분 채택 | 과거 전체 실행 중복 0은 미증명 |
| T1-F007 | 읽기 전용 계수 검토의 한정 완료 유지 | operator 최적화·과거 hit/miss·삭제 후 재계산 미계측 |
| T1-F008 | native φ 차동과 probe 정의 채택 | 전체 φ 미이관; loading/대역폭/감쇠/잡음/교정은 별도 미검증 |
| T1-F009 | 두 과거 anchor의 네 표현 한정 완료 유지 | 새 TIS/C1 후보 전체 파형 및 실측 완료 아님 |

현재 환경이 F004를 해결했다고 표시하거나 과거 통과 suite를 이번에 재실행했다고 표시하지 않는다. 새 결과가 생기면 이 ID에 실제 적용 commit·run·검증 경로를 추가한다. 단순 수신 확인을 반복 계산 진척으로 세지 않는다.

## 원 EIS와 CV

원 EIS XLSX **17개**, 원 CV PCFFGRA4 바이너리의 **두 경로 사본** 총 19경로의 크기와 SHA256을 manifest에 대조해 모두 일치했다. `electrode-original-inventory.json`에 원 commit/URL과 관찰 hash를 남겼다. 이는 새 전기화학 fit나 수치 검증이 아니다. CV 바이너리는 461,883 bytes, SHA256 `d1c6c74591a810dbb569f663bfc67e5b13256f13d4a50f826c96d8934614c369`다.

정적 처리 경로는 다음과 같다.

- `update_ngg_eis.py`는 XLSX의 실제 XML 행을 읽고 원 `−Z″/−Phase`를 `Im(Z)<0` 규약으로 변환한다. Re/Im을 log(f)에 대해 보간하며 측정 1–10 kHz 밖으로 외삽하지 않는다.
- 노출 면적은 1 cm² = 1e−4 m², 3전극 PBS 측정이다. PBS1×:DI=8:72는 명목 0.1× PBS이며 비율의 부피 근거는 기존 기록상 가정이다. 온도, AC 진폭, DC bias/OCP, 반복 수, 동일 시편 여부, EIS 기준·상대전극은 null/미확인이다.
- 초기 `NggSweep.java`는 properties의 **측정 총 Z**에서 Rs를 한 번 빼고 측정 면적을 한 번 곱한다. JSON에 저장된 면적 정규화 값을 다시 넣어 차감하는 구조가 아니다. 초기 bare 선택 Rs는 **213.27997221512513 Ω**이며 유효 직렬항이다.
- 후속 `explore_tis.py:contact_rows`는 측정점에서 Rs를 한 번 차감하고 면적을 한 번 곱해 `z.<f>.re/im`에 쓴다. `ExploreBasis.Boundary`는 이미 Ω·m²인 값을 그대로 사용하고 cell 접촉 전도도 계산에서 실제 접촉 면적으로 나눈다. 검토한 두 경로에서 Rs/면적 중복 적용은 찾지 못했다. 정적 코드 확인을 모든 과거 runtime 경로의 독립 검증으로 확대하지 않는다.
- `full_measured`는 Rs=0을 쓰는 별도 구조적 스트레스 조건이며 실제 피부 접촉의 검증값이나 통계적 신뢰구간이 아니다. 명목 Rs500/1000/2000은 fit의 하한 주파수 Hz이며 고정 저항값 Ω가 아니다. 측정 접촉과 별개의 발생기 출력저항 50 Ω를 Rs로 차감하면 안 된다.
- 50 nm의 무제약 fit 차감 비수동성과 constrained fallback을 유지한다. 선택 Rs **214.13262432777125 Ω**, n=0.2 하한이며 100 nm도 n≈0.2다. Rs-window 세 결과의 일치는 bound 영향으로 식별성 개선을 증명하지 않는다. PBS→실제 건식/팬텀 접촉은 계속 불확실성 조건이다.
- CV paired CSV는 각 1476 유효행, 전압 V/전류 A/면적 1 cm²다. 공통 명목 scan rate **0.1 V/s**는 사용자 확인 문서와 연결한다. 동결 profile의 null을 덮어쓰지 않는다. 원 데이터 약 −0.80078~+1.000977 V/1476점과 설정사진의 ±1 V/1640점은 미일치다. 서로 다른 bare 곡선을 같은 반복 실험으로 합치지 않는다. 기존 ∫|I||dV|의 단위 A·V를 CIC나 CSC/안전창으로 바꾸지 않는다.

## 실제로 없는 자료와 복원 우선순위

`data-recovery-inventory.json`은 manifest의 **700기록 = 생산자 local-only 698경로 + 추가 미이관 범주 2개**를 현재 checkout과 대조한다. 역사적 `bases/...` 등 **같은 상대 경로로 존재하는 것은 0개**다. 이 중 **184 source/loss 행렬은 `released-circuits/...`의 별도 사본이 존재**하며 그 경로·크기·hash를 연결했다. 따라서 700개 전부가 원시 기저이거나 700개가 서로 다른 계산인 것은 아니다. 전체 공개 행렬 192개 중 나머지 8개는 별도 reference 회로 파일이다. 이 작은 행렬만으로 공간 E/φ를 복구할 수 없다.

184 별도 회로 사본을 제외한 516기록에는 전계 92, 전위 92, 접촉 전류밀도 92, grid 23, volume NPZ 28, contacts CSV 92, metadata/완료표식 69, class 16, 감사 patch 7, 역사적 lock 3, 추가 범주 2개가 포함된다. metadata/class/lock은 독립 기저 수가 아니다. 전체 원 run과 과거 기저는 이 선택도 경로 목록보다 넓으며 추가 복구 필요량의 정확한 byte 총량은 현재 자료로 알 수 없다.

| 우선순위 | 복원할 항목 | 필요한 이유 / 대체 가능 범위 |
|---|---|---|
| 1 | 원 계산 storage identity, 원 inventory와 영속 backup 위치, baseline/best1 원 config/code/data hash | 원 환경과 새 환경의 같은 이름 경로를 동일 storage로 오인하지 않고 복원 가능성을 먼저 판단 |
| 2 | representative bare, Best1, 부분 접촉 타원, genuine 2-pad C1의 grid/mesh/contacts/validation·전체 complex E/φ·density | 같은 격자 baseline 재현, ROI/전역최대/J95, 팁 두점 Δφ, 회로·전력·수렴 재현; E-only 옛 export에 존재하지 않는 φ를 요구하지 않음 |
| 3 | 전체 선택도 23개 local basis 및 reference 의존 run, 28 volume/관련 분석 revision | 비교 대상의 완전한 원시 복구와 누락 없는 재사용; 작은 released 회로는 source/loss만 대체 |
| 4 | omitted but pinned Git artifact 53개 중 해당 workflow에 필요한 항목 | completion·과거 validation·C1·probe·registry 의존성 회수. 53개를 모두 실행 필수라고 단정하지 않고 의존별 선택 |
| 5 | CV 설정 원본 이미지/hash, timestamps, 기기 method, 원 export/record flag 해석, EIS 미확인 조건 | 명목 설정과 실제 취득 프로토콜 대조; 실제 dV/dt·CSC branch 해석과 접촉 조건 검증 |
| 6 | 과거 MPH/LFS 실제 객체와 원 historical runs의 inventory | 원본 보존·독립 복원. COMSOL 5.3a/예정 5.3.1.201 실행 가능 여부는 별도 gate |
| 7 | 측정기의 입력 R/C/대역폭/감쇠 설정과 교정 근거 | 무부하 예측과 실제 부하 예측 분리. 불명 장비값을 실제 측정값으로 채우지 않음 |

역사적 lock은 복원한 계산을 자동 재개하는 실행 lock으로 가져오지 않는다. frozen source의 절대 경로는 증거로 보존하고 새 path mapping·새 run ID에서 해결한다. 원본이 복구되지 않으면 현재 사용자 승인 범위의 새 계산을 **원시 계산 복구와 구분되는 신규 재계산**으로 기록하고 실제 CPU/시간/저장 비용을 남겨야 한다. 이번 감사에서는 신규 재계산을 하지 않았다.

## 다음 실행 연결

원 데이터 전달 비용/전체 byte 총량은 미확인이다. 원 환경·원본과 실패 증거는 삭제할 수 있는 상태가 아니다. 원 자료가 없더라도 현재 환경의 최소 해석해/회로 검사와 새 고유 baseline을 유한 예산 안에서 준비하는 것은 구분된 경로다. 실행 담당은 원자료 복구 가능 여부, 새 계산임을 밝힌 사전등록, 동일 격자/물성/접촉/회로/측정 정의, 결과별 source/config SHA를 먼저 확정해야 한다. 본 감사가 제공하는 것은 실제 누락 목록과 최신 피드백 연결이며 solver 실행 승인·수렴 통과·인체 안전 한계가 아니다.

두 Elsevier PDF는 권리 미확인으로 계속 DOI/서지/hash만 연결한다. 이번 원격 조회는 공개 task1 코드/피드백/연구 인계 근거에 한정했고 비밀번호·토큰·개인 대화·논문 원문을 수집하거나 게시하지 않았다.

## 후속 피드백 소비·실행 연결 — 2026-10-20 04:32 KST 조회

공개 GitHub를 다시 GET으로 조회했다. 원 PR #2/#3 head와 피드백/응답 바이트는 앞의 고정 근거에서 바뀌지 않았고 comments/reviews는 모두 0개다. 새 main도 `3b5f1861…`다. 새 저장소에는 **다른 검토자의 PR #1**, `review/task1-mesh-feedback-20261020` / `8053270779400652da95bd2bca01b7f276b64b8e`가 있다. 이것은 계산 담당자의 구현 PR이 아니다. diff는 `docs/reviews/TASK1_CLOUD_RESTART_REVIEW_20261020.md` 한 파일 추가이며 직접 읽은 SHA256은 `762898c0df92b35decf1aa1db36ce231caa6306120a1e6fa5b64796fc2d2b8e3`다. PR #1 comments/reviews도 0개이며 실제 피드백은 이 문서에 있다. 이 PR을 병합하거나 원본 파일·계산 코드를 덮어쓰지 않았고 메시지를 보내지 않았다. 조회 근거는 `docs/cloud-restart-20261020/feedback-refresh.json`에 연결했다.

검토 문서는 기존 F001–F009를 그대로 사용한다. 같은 4패드 후보의 접촉 가장자리/XY를 다음 과학적 우선순위로 유지하고, SC·bulk의 별도 통과를 결합 3D 수렴으로 해석하지 말라는 제안을 채택했다. 이미 완료한 grouped 구현을 다시 요구하지 않으며, coarse 분할패드 결과를 형상 채택·수렴 통과로 올리지 않는다. 적용·실행·검증 링크는 실제 `a4636ec…`, `38f005e…`, `038ce93…`, `07d3dfa…`, `66901b7…`의 구현/게시 근거와 각 run의 실제 `source_commit`을 구분해 `feedback-ledger.json` v2에 갱신했다. 이번 피드백 읽기를 새 실행의 원인으로 꾸미지 않았으며, 이번 정식 결정 갱신의 미래 commit SHA는 null로 남겼다.

검토자의 F005/F009 지적은 과거 `single-pair-comparison.json`의 코드 SHA `c61f1c…`가 확인한 Git 코드와 맞지 않는다는 출처 문제다. 해당 과거 결과/해시는 그대로 보존한다. 계산 담당자가 이미 별도로 실행한 **새 PDE 0의 후속 분석** `waveform-C1-full-skin.json`을 확인했으며, 그 코드 SHA `76df6e73d8c72b86b3e7249d49ebde35466bb95566d41def8df88f1b5a2bf032`는 실제 `07d3dfa…`/현재 코드 바이트와 일치했다. 이 후속의 별도 사본을 `single-pair-full-skin-comparison.json`으로, 같은 코드가 연결된 공간 후속을 `fine-spatial-full-skin.json`으로 저장했다. 이번 감사에서 후처리나 PDE를 실행하지 않았다. 이 연결은 **새 후속 결과의 정확한 코드 출처**를 해결하며, 사라진 옛 `c61f…` 소스를 복원했다는 뜻이 아니다. 실제 2패드 C1의 두 주파수 각각에 대한 중심·ROI 에너지 RMS·local RMS 평균의 6개 비교라는 한정 범위와 실험 미검증을 유지한다.

현재 결과 상태도 분리했다. A `cloud-baseline-20261019T185900Z`는 같은 격자의 39 scalar/8행렬 재현 통과, B `cloud-mesh-c1-20261019T190000Z`는 4조건 계산 완료이나 격자 gate 9개 파형 비교 중 3개 XY 실패, C `cloud-grouped-20261019T191500Z`는 5조건 계산 완료이며 공간 수렴/실측 미검증이다. B의 108 scalar 판정은 90통과/18실패이며, square_3h XY Jmax/J95/contactV는 각각 +23.0686/+12.6588/+23.0706%다. F004 전체 보류를 유지한다.

**D `cloud-reference-20261019T192000Z`는 `error`이며 전체 완료가 아니다.** h0.5 baseline은 case ledger까지 완료했고 명목 Best1의 native·후처리 자체도 3파형 완료했다. 그러나 정확 참조 대조는 39 scalar 통과, 행렬 8파일 중 3000 Hz source/loss 2파일이 사전등록 entrywise gate에서 실패해 중단했다. 최대 normwise 상대차 2.3477601938991445e−9라는 수치와 near-zero entrywise 실패는 다른 판정이므로 원 gate를 사후 변경하지 않는다. 원 실패·부분 결과를 유지하고 계산 담당자가 원인을 조사 중이다. `best1-square15-C1pair0-xy120`은 **not_run**이다. 기존 h0.625 C1을 이 최신 격자의 대조 완료로 전용하지 않는다.

별도 등록된 `cloud-coupled-20261019T193200Z`는 이 감사의 마지막 읽기에서 결합 격자 조건을 실행 중이었다. 이 관측은 완료·수렴 통과를 뜻하지 않고 D의 실패를 해소하지 않는다. 실행 담당이 그 run의 다음 판정을 관리한다. 모든 새 run의 실험 검증은 false이며 새 φ 생성, 패키지 해시 검증, 과거 raw 복구, 같은 격자 재현, 공간 수렴과 영속 백업을 계속 별도 상태로 둔다.
