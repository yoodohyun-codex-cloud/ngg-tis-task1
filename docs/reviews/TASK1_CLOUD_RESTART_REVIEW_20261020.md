# Task 1 클라우드 재시작 검토 — 2026-10-20 KST

## 연속 실행 피드백 — 계산 PR #2 `be724b0`까지 재검토

**계산 담당자에게 요청: 완료한 6조건을 재실행하거나 별도 워커를 시작하지 말고, 현재 실행기·자식·잠금 상태를 확인한 뒤 승인된 남은 예산 안에서 기존 유한 후속 큐를 이어간다. 각 배치는 검증·보고·다음 배치 결정과 실제 진입 기록까지 마친다.** 계획 문서 작성 또는 `completed_finite_queue`만으로 연구 지속 업무를 끝내지 않는다. 조건을 충족하지 못하면 정확한 차단 사유와 재개에 필요한 행동을 남긴다.

이 추가 검토의 공개 근거는 계산 [PR #2](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2) head `be724b0b314263f284fdbc5397bdaf019685fa29`다. 요청 시점 `f84abb8` 뒤 `c8e8fd3`에 6조건 완료·유한 실행기·F004 채택 delta가, `be724b0`에 GitHub CLI 호환성 수정·중단 증거가 게시됐다. 아래 요청은 기존 구현을 인정한 후속 피드백이다. 이 검토에서는 계산·프로세스 조작·설치·삭제를 하지 않았다.

추가로 전달받은 00:28 UTC 계산 보고는 호환성 수정 후 **현재 미세 격자 유한 큐가 실행 중**이며 checkpoint는 계산 환경의 `/workspace/ngg-tis-task1/runtime/finite-loop-20261020T002600Z/checkpoint.json`이라고 한다. 이는 검토자가 해당 runtime을 직접 읽은 증거가 아니므로 live PID/자식/잠금·새 결과 게시로 확인해야 한다. 이 피드백은 **현재 큐의 검증·후속 선택·게시 조건을 보완**하며 새 큐 생성이나 재시작을 요청하지 않는다. 대화 턴의 종료, Git 게시 시각, 과거 중단 checkpoint만으로 현재 워커 종료를 단정하지 않는다.

공개 PR2 본문에도 **00:24 UTC snapshot**으로 같은 큐, coordinator PID8017·PDE controller PID8105·source `be724b0`, 최대2개 xy80+3개 확인 조건이 게시돼 있음을 재확인했다. 따라서 후속 시작의 공개 보고는 존재한다. 그 timestamp 이후의 생존·완료·잔여 예산을 이 검토가 실시간 검증한 것은 아니다.

### 이미 끝난 작업과 지금 이어갈 지점

| 공개 증거 | 확인한 실제 상태 | 중복 없이 이어갈 행동 |
|---|---|---|
| [잔차 실행 summary][resume-residual] | `cloud-residual-20261020T001300Z`, 2조건 complete, 67.235153824초 | 기본 producer 대조 및 tight 잔차 진단을 다시 실행하지 않음. 아래 목적별 보류를 유지. |
| [4패드 6조건 summary][resume-six] | `cloud-fourpad-20261020T001400Z`, 6/6 complete, 217.421313564초, `not_run=[]` | 계획의 오래된 `calculation_completed=false`를 현재 상태로 읽지 않음. 기존 native·감사·baseline을 재사용. |
| [coarse 순위][resume-rank] | 6조건 모두 `numerically_promising=false`; full-skin-cap ROI mean/P10 개선 후보 없음 | `free-square10-r12p5xy`, `adjacent-square15`의 선택은 **수치 진단용**이지 개선/최적 후보 채택이 아님. |
| [첫 실행기 checkpoint][resume-checkpoint] / [중단 진단][resume-stop] | coarse 순위 단계 완료, 후속 PDE 시작0, `peer_review_required`; 원인은 설치된 `gh`의 `--slurp` 미지원 | 기존 완료 순위/감사를 보존. 이 과거 상태를 새 피드백 도착·현재 워커 종료로 오해하지 않음. |
| [실제 GET 확인][resume-get] / [실행기 코드][resume-loop-code] | `--paginate` 연속 JSON 배열 해석으로 수정; 실제 PR1 head/댓글/리뷰 GET 성공 기록 | 호환성 구현을 다시 요구하지 않음. 현재 소유자가 새 PR1 피드백을 읽고 채택 범위·고정 snapshot을 기록한 뒤 안전한 다음 단계에서 계속 진행. |

순위의 `balanced_absolute_gain_floor`는 free-square10 약0.79837, adjacent-square15 약0.74533이다. 이는 같은 전체 피부 부담에서 ROI mean/P10 두 비율 중 작은 값이며 둘 다 baseline 미만이다. 현재 무개선 분기로 처리한다. 총면적400 mm²인 free-square10과900 mm²인 대조를 같은 면적 설계로 설명하지 않는다. 나머지 형상을 새 이름으로 다시 계산하지 않는다.

### F004: 어떤 실패가 어느 목적을 막는가

[잔차 원인 감사][resume-residual-audit]는 기본 residual producer의 coarse 3000 Hz E/φ/density/source/loss 5배열 동일성과 tight fine 잔차 약3.6453e−12를 기록한다. 그러나 역사적 source 4성분·loss 2성분은 원 `abs(new-old) <= 1e−14 + 1e−8*abs(old)` 기준에서 여전히 실패다. 작은 전역 norm·잔차 감소·reciprocity 개선으로 그 판정을 바꾸지 않는다.

| 목적 | 계속/보류 판단 |
|---|---|
| 과거 Best1 성분별 재현 완료, 원 native 복구 완료 주장 | **보류.** 6성분 실패 및 과거 전체 배열 부재가 해당 주장을 막음. |
| 3000 Hz 단일 진단을 두 carrier TIS·고조파 결과에 편입 | **불가.** 진단 용도를 유지하고 TIS 순위에서 제외. |
| 같은 현재 producer·물성·접촉·소스·격자·정의의 coarse 형상 비교 | 각 조건의 native/전류·면적·전력 gate, 같은 격자 baseline, 코드/입력 hash와 예산이 유효하면 **진행 가능**. 과거 성분별 실패가 모든 탐색을 무기한 막는 전역 중단 조건은 아님. |
| coarse 차이를 개선 후보 선별에 사용 | 등록한 실용적 1% 선별 여유와 전체 피부 부담/공간 조건을 그대로 적용. 한 형상·한 주파수에서 관측한 solver 민감도를 모든 ROI P10/격자/접촉의 보장 오차로 사용하지 않음. |
| 최적 후보 채택·깊이 집중·전체 XY/가장자리/3D 수렴·실험 타당성 | **보류.** 후보별 추가 검증과 해당 근거가 필요. 제한된 결합 격자 36 gate 통과도 전역 수렴으로 확대하지 않음. |

F004는 [실제 채택 delta][resume-adoption]의 `partially_adopted_executed_residual_mesh_separation`을 인정한다. 이전 검토의 “모든 adoption 링크 null”은 당시 snapshot의 기록이며 현재 판단이 아니다. 잔차/격자 분리 구현·실행의 채택은 확인됐지만 전체 F004 보류는 유지한다.

### T1-F010 — 배치 종료부터 다음 실행까지의 책임 계약

새 ID는 **연속 실행의 인계 누락** 한 항목에만 추가한다. F001/F002는 공간·동일 부담 평가, F004는 검증 범위, F006/F007은 단일 소유·재사용·실행 계수의 기존 의미로 계속 사용한다. T1-F010의 현재 상태는 **제안/계산측 채택 미확인**이다. 검토 문서 게시나 PR2 상호참조가 자동 채택·실행을 의미하지 않는다.

**진입 조건과 현재 소유자**

1. 현재 계산 담당자가 최신 checkpoint의 PID/startticks·프로세스 상태·자식 명령·마지막 갱신과 `.task1-loop.lock`, `.task1-execution.lock`을 실제 환경에서 확인한다. 살아 있는 실행기/자식이 있으면 그 소유자가 이어간다. 다른 실행기를 띄우거나 같은 단계/조건을 병렬 수행하지 않는다. 종료 판정에는 실제 프로세스 정체성과 잠금 확인을 함께 남긴다.
2. [4패드 계획][resume-plan]의 코드·등록·마스크/config SHA, 완료 원자료와 같은 격자 baseline, 기존 캐시를 확인한다. 6조건 coarse 진입 조건은 실제 완료로 이미 충족됐다. 현재 단계는 등록된 최대2조건 xy80, 그 결과에 따른 한 설계의 xy100/SC4/bulk 최대3조건이다. 실제 이미 완료된 후속이 있다면 그 결과부터 사용한다.
3. `runtime/task1-budget.json`의 **live 잔여**를 읽는다. 옛 중단 진단의 잔여4728.904초는 이후 잔차·6조건·감사 비용 이전 관측이므로 현재 예산이 아니다. 기존 6600초 원장을 이어 쓰고 CPU1·동시PDE1·800000셀·600초/조건·heap2 GiB·RSS3 GiB·디스크 예약2 GiB를 유지한다. 새 phase는 코드가 요구하는 `600초×조건수`와 마지막 렌더120초, 준비/감사/보고 여유를 함께 확보해야 한다. 전체 phase 예약이 안 되면 현재 코드가 지원하지 않는 부분 실행 flag를 만들어내지 말고, 실행 가능한 등록 subset 또는 `not_run_budget`을 명시한다.
4. 새 피드백 확인은 기존 안전한 phase 경계에서 처리한다. `peer_gate`가 PR1 head/댓글 변경을 감지해 멈추면 계산 담당자가 변경 내용·채택/보류·관련 commit을 검토한다. 이를 새 사용자 허가 대기나 연구 완료로 바꾸지 않는다. 피드백 확인을 우회하지 않고, 이미 실행 중인 자식이나 고정 source를 임의 교체하지 않는다. 이번 PR 업데이트 때문에 또 조회가 달라졌다면 **같은 변경을 읽고 판단한 뒤** 그 snapshot을 다음 실행 근거로 고정한다.

**결과별 다음 행동 — 현재는 B 분기**

| 분기 | 완료 직후 검증·보고 | 이어갈 유한 행동 |
|---|---|---|
| A. 같은 전체 피부 부담에서 ROI mean/P10 모두 baseline 이상, 적어도 하나 >1% 개선 | 같은 격자 비교·부담 cap·표층/전체 비표적 P95·최대·전역 최대 위치를 확인. 진폭 변경 후 고정 baseline 역치의 비표적 고변조 부피가 `unavailable`이면 원 native로 재평가할 때까지 해당 조건 보류. | 이미 등록된 최대2개 xy80, 그중 한 후보의 가장자리·xy100/SC4/bulk 검증을 진행. 실패하면 C로 분기. 통과는 한정 gate 통과로 보고하며 자동 최적점·C1 채택은 하지 않음. |
| B. 개선 없음 — 현재 6조건 해당 | 동일 전압/동일 총전력/접촉 cap/전체 피부 cap을 분해해 어떤 제한 항목이 ROI 이득을 상쇄하는지 기록. free-square10의 면적/위치 변화와 adjacent의 배선·위치 효과를 구분. | 이미 선택된 최대2개를 **수치 진단**으로 xy80에서 확인하되 기존 실행/캐시를 먼저 확인. 그다음 최대3조건 확인은 어떤 격자 민감도 질문을 해결하는지 명시. 무개선이면 baseline을 유지하고, 기존 결과 분석으로 면적·위치·배선 중 한 요인만 바꾸는 미계산 소수 대조를 선정해 다음 유한 계획을 등록한다. 예: 총900 mm²·4패드/2출력·파형 고정 상태의 배치 효과를 분리하는 최대2개 새 위치 대조. 실제 형상 가능성·producer 지원·중복 signature·남은 예산이 확인된 경우에만 진행하며 이미 계산한 형상을 다시 포장하지 않음. |
| C. 수치·출처·가용 자료·실행 실패 | 최초 실패·부분파일·잔차·원소별 차이·source/config SHA·exit 상태를 보존. 수렴 실패와 실행 인프라 오류를 구분하고 다음 조건에 영향을 미치는 범위를 판단. | 무제한 retry 대신 특정 원인을 수정/검증하고 새 고유 기록으로 재개. 이미 완료된 coarse/감사/후속 PDE는 재사용. 필요한 원인 분석이 읽기 전용이면 그것부터 수행. 허용치 완화·reserve 감소·원자료 삭제로 통과시키지 않음. |

위 B의 새 위치 대조는 **다음 질문의 구체적 후보**이며 지금 등록·실행됐다는 뜻은 아니다. 현재 후속 큐의 결과로 필요성이 없어지면 그 근거와 다른 다음 질문을 기록한다. 남은 예산 안에서 타당한 준비·검증·배치를 이어가는 것이 계산 담당자의 업무이며, 제안 문서만 저장한 뒤 끝내지 않는다. 예산·자료·실행 지원이 실제로 부족하면 그 항목을 정확히 차단 사유로 남긴다. 승인 범위 밖 자원 확대·설치·삭제·보안 변경·별도 워커·상주 서비스는 계속 보류다.

**현재 실행기의 끝부분에서 보완할 실제 누락**

[실행기 코드][resume-loop-code]에는 coarse 감사/순위→fine→confirm→mesh 판정→최종 순위/화면 갱신까지의 자동 순차 처리가 이미 있다. 이를 다시 만들 필요는 없다. 다만 마지막 `next_decision`은 일반적인 root review이고 `next_command`는 `cat checkpoint.json`이다. 첫 중단 기록의 `next_command`도 이미 완료한 `rank-coarse`를 가리킨다. 이 값들은 **다음 계산 재개 명령의 확정본이 아니다**. 현재 구현에는 `--resume` 옵션도 없고 이미 존재하는 `--output` 재사용을 거절한다. 오래된 명령을 복사해 실행하거나 존재하지 않는 재개 flag를 제안하지 않는다.

각 배치/큐 마지막 기록에는 다음 필드를 채우도록 계산 담당자에게 요청한다. 이는 기존 checkpoint를 덮어써 과거 상태를 바꾸라는 요청이 아니라, 실제 단계 종료의 새 기록/후속 결정을 남기라는 요청이다.

| 필수 기록 | 실제로 담아야 할 내용 |
|---|---|
| `next_action`, `decision_basis` | A/B/C 중 선택, 관련 run/case/판정/hash, 다음 과학적 질문과 정확한 유한 범위 |
| `next_registration`, `next_command` | 실행 가능한 코드에 맞는 등록 artifact/SHA 및 완전히 해석된 명령·cwd·입력·고유 출력. 단순 `cat`은 관찰 명령으로 따로 표시. 아직 지원되지 않으면 구현/검증의 정확한 다음 명령과 차단 이유를 먼저 기록. |
| `actual_started`, `started_utc`, `owner`, `child` | 다음 단계 실제 시작 여부와 PID/startticks·소유 잠금·자식 명령·run ID. 준비 완료를 실행 시작으로 쓰지 않음. |
| `terminal_status`, `idle_reason`, `blocker`, `resume_condition` | 완료/오류/예산부족/피드백 검토/자료부족을 구분. 시작하지 않았다면 왜인지, 누가 무엇을 확인하면 재개 가능한지, 실제 재개 명령을 명시. |
| `budget_before_after`, `cache_reuse`, `remaining_limits` | 기존 원장 차감·잔여·예약, 재사용/새 PDE·주파수/RHS 계수, 실패와 수렴/물리적 보류 유지 |

현재 실행기가 살아 있으면 위 후속 판단은 그 소유자가 처리한다. 실제 종료가 확인된 경우에만 계산 담당자가 보존된 checkpoint·완료 캐시·등록/소스 snapshot을 검토하여 **기존 작업의 중복 없는 재개 절차**를 선택하고 위 필드에 정확한 명령을 남긴다. 이 검토는 별도 워커 시작을 요청하지 않는다. 추가 PDE가 이미 일부 끝난 경우, 현재 finite-loop의 처음부터 다시 실행하면 그 완료 phase를 자동 재사용하지 않을 수 있으므로 그대로 재시작하지 말고 완료 단계를 제외하는 지원 경로를 먼저 검증한다.

`completed_finite_queue` 뒤에도 계산 담당자는 결과 검증·보고를 마친 같은 작업 흐름에서 다음 유한 배치를 선택하고, 진입 조건이 충족되면 그 다음 단계를 실제로 시작한다. 자동 진행은 **승인된 유한 큐 내부의 처리와 담당자의 후속 의사결정**을 뜻하며 무기한 daemon이나 자동 과학적 채택을 뜻하지 않는다. 정당한 차단이 생기면 유휴 사유와 재개 경로를 남기는 것으로 종료 상태를 명확히 한다. 단순 수신확인 댓글/빈 commit 반복은 하지 않는다.

### 채택 상태와 이번 확인의 한계

- F001–F009의 [현재 장부][resume-ledger]는 적용 commit/실행 근거를 이미 연결했다. F004의 잔차/격자 분리는 별도 [채택 delta][resume-adoption]와 실제 2조건 결과까지 확인했다. 이 이전 피드백 채택을 새로운 T1-F010 채택으로 세지 않는다.
- T1-F010은 본 검토 commit을 source로 계산 담당자가 채택/보류, 구현 commit, 실제 계속 실행/종료 기록, 검증 artifact를 연결해야 한다. 공개 PR2 상호참조만으로 실행·채택 완료를 선언하지 않는다.
- 새 baseline의 별도 복구 검증과 다른 새 native의 로컬 archive, 과거 전체 native 미복구를 구분한다. 이 검토는 전체 데이터 이전이나 환경 폐기를 승인하지 않는다.
- 공개 JSON·코드·Git 이력과 게시 시험 로그만 확인했다. 최신 로그는 전체157개/실행기33개 시험 통과를 기록하지만 여기서 재실행하지 않았다. 현재 워커 생존·live 잔여 예산·새 후속 결과는 계산 소유자의 실제 기록이 필요하다.

## 이전 검토 이력 — `07d3dfa` 당시의 근거와 보류

아래는 이전 snapshot의 기록이다. 현재 실행·채택 상태에는 위 연속 실행 피드백과 고정 출처를 우선 적용한다. 과거 실패·null·미구현 관찰을 현재 상태로 재사용하지 않는다.

**판정: 같은 4패드 후보의 XY/접촉 가장자리 검증을 다음 과학적 우선순위로 유지한다.** 중심·ROI 지표의 작은 변화만으로 수렴을 선언할 수 없다. 접촉 부담과 선택도는 등록 기준을 넘게 변했다. F004의 전체 검증 보류를 유지하며 새 최적점이나 15–20 mm 집중 성공을 채택하지 않는다.

검토 대상은 `codex/task1-cloud-restart-20261020`의 **`07d3dfa956b6662a07ff930577240b091065f5d6`까지**다. 수치·장부 근거는 `4890d1d7f76e947b6913a48624d4c498fc6cb668`에 고정했고 이후 `07d3dfa`에서 그 파일들은 바뀌지 않았다. 요청 시점 `038ce93981adce7b707694d495d69e9b72703430` 뒤의 `4890d1d`는 grouped 사전등록과 전체 피부 부담 분석 계약 두 파일을, `07d3dfa`는 관련 구현·시험 소스 네 파일을 추가 변경했다. 이 추가분을 반영해 이미 구현·등록된 사항을 다시 요구하지 않는다. [실행 보고서][report]는 수렴 실패와 결합 3D 미검증을 이미 명시한다. 이 문서는 그 판정의 후속 의사결정 및 F001–F009 추적 근거를 보완한다.

별도 review 브랜치는 `main`의 `3b5f1861c523a207d02b1a34a5f61c67b88556eb`에서 만들었다. 이 변경에는 본 문서 하나만 포함한다. 계산 코드·설정·장부·워커·원본·GUI를 변경하지 않았고 계산 브랜치를 병합하지 않았다. Git 객체와 게시 JSON/로그의 문서·정적 검토이며, 연구 모듈 import·시험 재실행·설치·시뮬레이션·native 배열 복구는 수행하지 않았다. 저장소 `AGENTS.md`와 연구 반복 계약을 따랐으며 검토한 tree에는 추가 `.agents/skills` 또는 하위 `AGENTS.md`가 없다.

## F003/F004: 중심값 통과와 수렴 통과를 분리

[mesh-convergence.json][mesh]의 `axis=XY`, `before=coarse`, `after=xy80`, `waveform=square_3h` 행이다. 같은 4패드·후기 10 nm/Rs500 접촉·3000/3030 Hz 조건에서 XY h=1.25→0.625 mm를 비교한다. 전압/위상·영역·분석 정의를 바꾼 개선 비교가 아니다.

| 지표 | h1.25 mm | h0.625 mm | 부호 있는 변화 | 등록 허용 변화 | 판정 |
|---|---:|---:|---:|---:|---|
| 중심20 mm 기본파 변조, V/m | 3.992027833 | 3.979456242 | −0.3149% | 1% | 통과 |
| 부피 ROI 평균 TIS, V/m | 4.073969592 | 4.061848942 | −0.2975% | 1% | 통과 |
| 접촉 법선 RMS Jmax, A/m² | 20.713025579 | 25.491240127 | +23.0686% | 5% | 실패 |
| 접촉 면적 가중 RMS J95, A/m² | 12.030220790 | 13.553106045 | +12.6588% | 5% | 실패 |
| 접촉 RMS 전압 최대, mV | 2.181542799 | 2.684838457 | +23.0706% | 5% | 실패 |
| SC 손실, µW | 2.039316612 | 2.166357020 | +6.2296% | 2% | 실패 |
| 접촉 손실, µW | 1.702473179 | 1.827275482 | +7.3306% | 2% | 실패 |
| ROI 평균/표층 TIS P95 | 0.164220015 | 0.160806575 | −2.0786% | 1% | 실패 |

ROI는 r≤5 mm·z15–20 mm 부피이며 중심20 mm 한 점과 다르다. 표층은 z0–5 mm의 평가 영역이다. `surface_J_RMS_*`는 이 표에서 **접촉 patch의 법선 RMS J**를 뜻한다. SC+dermis 내부의 전체 벡터 J 통계와 동일시하지 않는다. 기본파 TIS와 고조파를 포함하는 RMS/손실도 서로 다른 지표다. 위 허용 변화는 수치 판정 기준이며 자극·안전 역치가 아니다.

게시된 108개 scalar의 before/after로 변화율과 gate를 다시 산술 대조했다. 90개 통과/18개 실패이고, 모든 지표가 통과해야 하는 파형별 비교는 6/9 통과다. 실패 3개는 XY 비교의 square_3h·sine·triangle_3h 모두다. 이것은 저장값의 내부 정합성 확인이며 원 전계에서의 독립 재계산이 아니다.

SC2→SC4와 bulk14/14/40→18/18/56은 각각 xy80을 기준으로 한 **별도 축 비교**다. 그 지정 비교의 통과는 보존하되 다음을 뜻하지 않는다.

- 실패한 XY 비교의 통과 또는 접촉 가장자리 최댓값의 확정.
- SC·XY·bulk를 함께 세분화한 결합 3D 수렴.
- 원 2 kHz 등록 조건의 통과가 이번 3 kHz 접촉·새 형상에 자동 적용됨.

[fine-spatial.json][spatial]의 xy80 전역 샘플 최대방향 기본파 TIS는 13.46400299 V/cm이며 셀 중심 (−2.8125,+2.8125,+0.025) mm, SC 안이다. 중앙 r5 깊이 곡선의 평균 극대도 0.025 mm다. 이는 표층 지배를 보여 주는 게시 증거이며 연속체 최댓값의 인증이나 15–20 mm 집중 성공이 아니다. F001의 공간 정의 구현과 실제 깊이 집중 달성 여부를 분리한다.

## 다음 단계 제안: 동일 후보의 가장자리·XY부터

F003/F004에 연결하는 **제안 상태**다. 계산 담당자의 채택·별도 사전등록 전에는 실행 또는 해결로 표시하지 않는다.

1. 기존 coarse/xy80/SC4/bulk 결과·config/mask SHA를 재사용해 같은 4패드 후보의 접촉 가장자리와 부분 접촉 셀을 먼저 진단한다. 위치·면적·소스 연결·접촉 물성·주파수·위상·ROI 정의를 고정하고, 가장자리 거리별 J/접촉 전압과 실제 면적 가중 J95·손실을 함께 비교한다. 이미 완료된 조건을 다시 계산하지 않는다.
2. 추가 검증이 필요하면 같은 후보의 **한정된 추가 XY/가장자리 조건**을 자원 상한 안에서 사전등록한다. 접촉 면적 보존, 격자와 경계의 상대 위치, 최대값 위치, Jmax/J95, 접촉 전압, SC/접촉/소스 손실, ROI mean/P10와 ROI/표층 P95를 함께 판정한다. 국소 세분화 등 현재 producer가 지원한다고 확인되지 않은 기능은 먼저 지원 여부를 검토한다.
3. 실패 항목이 남으면 이유와 표본 정의를 보존한다. Jmax를 제외하거나 사후 허용치를 완화해 통과시키지 않는다. 별도 축 검증이 충분해진 뒤 결합 SC/XY/bulk 비교를 별도 등록해야 하며, 현재 통과 기록으로 대체하지 않는다.
4. 이 단계에는 기존 1 CPU·동시1·800,000셀·조건당600초·누적6,600초·2 GiB 디스크 예약의 잔여 예산을 확인한다. 범위를 넘으면 미실행/차단 사유로 남긴다. 이 검토는 새 계산 예산·워커·삭제를 승인하거나 계산을 예약하지 않는다.

### 이미 준비된 grouped 배치와의 관계

`038ce93`에는 패드/노드 구분 exporter와 후처리 구현, [readiness 기록][ready] 및 게시 시험 로그가 있다. `4890d1d`의 [grouped 사전등록][grouped]은 원 4정사각형 producer 대조 1조건 후 4직사각형/8/12/16 분할패드 4조건, 총 5조건을 등록했다. 따라서 “16패드 구현 자체가 없다”는 이전 bootstrap 문구를 현재 상태에 그대로 적용하면 부정확하다. 반대로 이 고정 head의 `prepared`/`preregistered_not_executed`를 실제 grouped PDE 완료로 읽어서는 안 된다. 현재 워커의 생존·진척은 이 Git snapshot만으로 판단하지 않는다.

원 4정사각형의 E/φ/density/source/loss 20배열 대조를 먼저 하고 실패 시 후속을 진행하지 않는 gate는 이미 있으므로 중복 구현을 요청하지 않는다. Java의 zero-gap 합산 동일성·배선 검사와 실제 분리 패드의 공간 수렴도 구분한다. [전체 피부 부담 계약][burden] 역시 이미 등록됐고 `No candidate adopted while XY/contact-edge convergence incomplete`를 명시한다.

**권고:** 같은 후보의 가장자리/XY 검증을 다음 과학적 우선순위로 유지한다. 이미 등록한 producer 자격검사 또는 coarse 분할패드 결과가 별도로 게시되어도, 그것은 수렴 실패를 해소하거나 형상 우열을 확정하는 근거가 될 수 없다. 새 후보 선택·순위 채택 전에 동일 후보의 미해결 수렴을 평가한다. 현재 실행을 중단·교체하라는 지시나 새 배치 사전등록은 아니다.

### `07d3dfa` 후속 구현 확인과 남은 provenance 연결

최종 원격 확인 중 새 commit을 발견해 변경된 네 파일을 추가 정적 검토했다. [파형/손실 도구][wave-latest]는 `skin_power_W`의 과거 의미 SC+contact를 보존하고, `skin_SC_plus_dermis_power_W`와 `skin_and_contact_power_W`를 분리했다. pure-sine C1은 기본파 native E에서 ROI 에너지 RMS를 구하는 명시 경로를 추가했다. [비교 화면 도구][view-latest]는 전체 피부 cap과 두 summary SHA에 연결된 C1 비교를 구현하며, 필요한 피부 감사가 없으면 결과를 비워 둔다. grouped spatial loader 연결과 [시험 소스][wave-tests-latest] 변경도 확인했다. F002/F005/F009의 구현 진척으로 인정하되 이 commit에는 새 결과 JSON·갱신된 시험 로그·복구 영수증이 없어 실행/검증 완료로 승격하지 않는다.

F005/F009에는 해결해야 할 **실행 코드 출처 연결**이 남는다. 기존 [single-pair-comparison.json][c1]의 `audit_code_sha256`은 아래 게시 코드 어느 것과도 일치하지 않는다.

| 비교 대상 | `task1_waveform_check.py` SHA256 또는 기록값 |
|---|---|
| 게시 C1 보고서의 `audit_code_sha256` | `c61f1ce3639d79a51d653e6456f01cca311218357b5b3aa43a3fa08940a55022` |
| `38f005e` / `038ce93` / `4890d1d`의 파일 | `8350f140e7355ec2416610a2bb32cdf455e4678104ba797c3e5b7b4243e33b62` |
| `07d3dfa`의 파일 | `76df6e73d8c72b86b3e7249d49ebde35466bb95566d41def8df88f1b5a2bf032` |

이는 C1 수치가 틀렸다는 판정이 아니라 **이 Git 근거만으로 정확한 실행 코드를 복원할 수 없다는 제한**이다. 당시 `c61f…` frozen source의 실제 위치·바이트·commit/manifest를 연결하거나, 기존 native 입력을 보존한 새 고유 후처리 결과에 실제 실행 코드 SHA와 검증을 연결하도록 제안한다. 과거 보고서의 SHA를 현재 코드에 맞춰 고치지 않는다. 이 검토에서는 재계산하지 않았다. `4890d1d` readiness의 10개 파일 hash 대조와 59개 시험 로그를 `07d3dfa`의 변경 코드 전체에 대한 실행 검증으로 재사용하지 않는다.

## F001–F009: 제안·구현·실행·검증 연결

[기존 장부][ledger]의 9개 ID 모두에서 `adoption_commit_current_environment`, `execution_artifact_current_environment`, `validation_artifact_current_environment`가 null이다. 장부의 초기 감사 시각 이후 실제 코드와 결과가 게시됐으므로 **null이 곧 구현·실행 부재라는 뜻은 아니다**. 반대로 본 검토가 그 필드를 대신 채웠거나 피드백의 공식 채택을 확정한 것도 아니다. 장부 원본은 수정하지 않고 아래 연결을 계산 담당자의 갱신 근거로 제안한다. 기존 ID의 의미와 과거 한정 완료를 유지하며 새 번호를 만들지 않는다.

`a4636ec`는 실행 어댑터/감사 코드 게시, `38f005e`는 baseline 재현과 파형 검사 게시, `038ce93`은 mesh/C1 결과·공간 감사·grouped 구현 게시, `4890d1d`는 grouped 계획 게시, `07d3dfa`는 피부 손실/C1/표시 후속 구현 commit이다. 아래의 **게시 commit**은 그 파일이 확인되는 실제 Git 이력이며, 자동으로 공식 adoption commit이나 실행 당시 전체 코드 SHA가 되지는 않는다.

실행 기록의 `source_commit`도 따로 보존해야 한다. baseline 실행은 `a4636ec0b1f04c03696eb647307d5c53b2eef5f8`, mesh/C1 실행은 `38f005ecefc2c432cd6424a06f599f93682cc202`, grouped 사전등록은 `038ce93981adce7b707694d495d69e9b72703430`을 기록한다. 후속 게시 commit과 이 값을 합치지 말고 실제 코드/config/input SHA·run ID·검증 artifact를 함께 연결한다. 게시된 코드 hash와 테스트 로그의 일치도 실제 실행 이력 전체의 증명은 아니다.

| 기존 ID | 확인한 구현·계획 및 게시 commit | 게시 실행·검증 근거 | 현재 검토 판정 및 남길 제한 |
|---|---|---|---|
| T1-F001 | `038ce93`의 `task1_spatial_audit.py`, 중심/부피 ROI/전역·깊이 통계 분리 | [fine-spatial][spatial], `cloud-mesh-c1-20261019T190000Z` / `baseline-square15-xy80` | 정의·통계 구현과 게시 실행 확인. 표층 최대가 유지되므로 deep focus 미검증. 다음 계획은 절대 mean/P10와 공간 선택도를 함께 유지. |
| T1-F002 | `038ce93`의 C1 분석 게시; `4890d1d`의 cap 분리 계획; `07d3dfa`의 SC+dermis 손실/전체 피부 cap 구현 | [single-pair-comparison][c1], [grouped 분석 계약][burden], [후속 코드][view-latest] | 계획에서 구현으로 진행한 부분을 인정. 새 전체 피부 cap 결과/검증은 이 head에서 미게시. 과거 bare cap의 J95 제외와 새 cap의 J95 포함을 합치지 않음. |
| T1-F003 | 과거 2 kHz 독립 SC/XY 완료 범위 유지; `038ce93`의 새 축별 gate 보고 | [mesh-convergence][mesh], [mesh/C1 실행][execution] | 이번 SC/bulk 지정 비교 통과와 XY 세 파형 실패를 함께 연결. 과거 한정 완료를 취소하지 않되 새 조건/결합 3D까지 완료로 확대하지 않음. |
| T1-F004 | `038ce93`의 현 4패드 baseline 검증, `4890d1d`의 수렴 전 미채택 규칙 | 같은 [mesh][mesh]의 실패 행, 본 문서의 동일 후보 검증 제안 | **전체 보류 유지.** 접촉/Rs 물리 타당성·전체 3D·새 형상 가장자리 검증 미완료. 새 ROI 또는 exporter 구현으로 닫지 않음. |
| T1-F005 | `38f005e`의 기본파/합성파 도구; `07d3dfa`의 명시 pure-sine/실제 고조파 손실 코드 | [baseline 재현][reproduction], [C1 파형 분석][c1], [후속 코드][wave-latest] | 한정 게시 분석과 새 코드 확인. C1 보고서의 `audit_code_sha256` 대응 소스는 미연결. 단일 carrier TIS=0과 E/RMS=0을 구분하며 새 코드 검증·임의 다주파수·실측 완료로 확대하지 않음. |
| T1-F006 | `a4636ec`/`038ce93`의 `task1_cloud_batch.py`: 전역 lock, hash, 기존 operator 검사 | [baseline 실행][baseline], [mesh/C1 실행][execution], 게시 guard 시험 로그 | 구현 및 두 유한 배치의 게시 기록 확인. 모든 과거 실행의 중복0은 미증명. 새 실행 링크와 전체 중복 감사의 보류를 별도 기록. |
| T1-F007 | 현재 후보/operator 구분 및 기존 operator 검사; 전역 frequency/RHS hit/miss 계수 결과는 확인하지 못함 | baseline 1조건, mesh/C1 4조건 실행 기록; grouped 5조건은 계획 | 후보·후처리·PDE 조건·주파수/RHS를 별도 계수할 제안 유지. 조건 수를 solve/RHS 수로 바꾸지 않음. operator 최적화 완료나 삭제 후 재계산0을 주장하지 않음. |
| T1-F008 | `a4636ec` 실행 경로와 `038ce93`의 native φ/E 기반 게시 probe·공간 분석 | [mesh/C1 실행][execution]의 새 `potential-*.bin.gz` 크기/SHA 및 결과 링크 | 새 φ 생성·probe 검사 기록은 확인. 이 검토에서 native 배열을 열거나 재현하지 않음. **과거 φ 이관/복구 미완료**, 실제 장비 loading·대역폭·교정 보류. |
| T1-F009 | `038ce93`에 pure-sine C1 결과 게시; `07d3dfa`에 명시 pure-sine 계산 및 summary SHA 기반 표시 구현 | [single-pair-comparison][c1], 실행의 `baseline-square15-C1pair0-xy80`, [후속 표시 코드][view-latest] | 새 C1 게시 근거를 인정하되 정확한 실행 코드 SHA 연결 보류. 중심/ROI 에너지/local RMS 평균 맞춤은 별개. 새 표시의 실제 렌더/수치 검증·전체 후보·loaded 측정·실측 완료로 닫지 않음. |

장부 갱신 시 `decision_current_environment`와 공식 채택 commit, 실제 run/artifact, 통과·실패의 정확한 범위를 각각 기록하는 것이 필요하다. `new_execution_from_feedback`의 인과관계는 실행 담당자가 확인해야 하며, 단순히 본 문서를 읽었거나 게시했다는 이유로 true로 바꾸지 않는다. 특히 F004의 보류, F006/F007의 전체 이력 미검증, F008/F009의 장비·복구 제한은 남긴다. 이 문서는 수신 확인을 위한 새 완료 건을 만들지 않는다.

## 새 복소 전위와 과거 원시 데이터 복원은 별개

새 [baseline][baseline]과 [mesh/C1 실행][execution] manifest에는 각 run의 `potential-*.bin.gz`와 `field-*.bin.gz` 크기·SHA 및 계산 완료가 기록돼 있다. 두 기록의 `persistent_backup_verified`와 `mesh_convergence_validated`는 false다. 새로운 φ의 존재와 같은 격자 scalar/회로 재현은 각각 새로운 계산의 증거이며 과거 전체 native 데이터의 이전·복원 증거가 아니다.

원 저장소 PR3의 고정 `7a6b62a9154e2584548e48bef4717b7e666904df`에서 [FINAL_COMPLETION.json][old-final]은 `raw_transfer_complete=false`, [closure.json][old-closure]은 `transfer_destination=null`, `unstarted_contact_audit=prepared_inputs_only`를 기록한다. 원 환경은 이전을 위해 종료됐으며 원시 자료 이전은 미수행이다. 새 계산으로 누락된 과거 원시 배열을 복구했다고 표시하지 않는다. 원 종료 결정과 새 환경에서 별도로 승인된 실행도 구분한다.

[data-recovery-inventory.json][recovery]의 700개 기록은 과거 local-only 경로 698개와 추가 provenance 범주 2개다. 그중 작은 공개 회로 대응물 184개를 별도 분류한다. 이 경로 수를 모두 미복구 전계 기저 수로 세지 않는다. 남은 복구 차단은 과거 전체 E/φ/volume 접근·실제 전송 목적지와 영속 사본·독립 복구/배열 decode·대표 지표 재현 증거의 부재다. 게시 manifest나 archive 도구의 시험 통과만으로 이 조건을 충족했다고 할 수 없다.

## 이번 검토의 검증 범위

- 고정 Git 이력과 파일을 읽고 `038ce93→4890d1d`의 사전등록/분석 계약 두 파일 및 `4890d1d→07d3dfa`의 구현/시험 소스 네 파일을 확인했다. 후자의 변경에는 새 결과/장부/시험 로그가 없다.
- 게시 mesh JSON의 108개 변화율·gate·6/9 집계를 표준 라이브러리 산술로 대조했다. 새 전계 계산은 없다.
- 9개 기존 ID의 세 null 필드와 과거/현재 상태를 확인했다. `4890d1d` readiness에 열거된 코드 7개·로그/재현 기록 3개의 SHA256을 해당 snapshot과 대조했다. C1 `audit_code_sha256`은 위에 명시한 파일 버전들의 실제 SHA256과 따로 비교했다.
- producer의 [59개 시험 통과 로그][tests] 및 Java 자격검사 문구는 읽은 증거다. 이 검토자가 시험·PDE·native decode를 다시 실행했다고 주장하지 않는다.
- 문서의 고정 commit 링크·저장 수치·수정 범위를 확인한다. 계산 브랜치에 새 commit이 생기면 그 뒤 결과는 별도 근거로 평가하며 본 snapshot의 상태를 조용히 바꾸지 않는다.

[report]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/CLOUD_RESTART_EXECUTION_20261020.md
[ledger]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/feedback-ledger.json
[mesh]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/mesh-convergence.json
[spatial]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/fine-spatial.json
[ready]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/grouped-readiness.json
[grouped]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/grouped-preregistration.json
[burden]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/grouped-analysis-contract.json
[reproduction]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/baseline-reproduction.json
[baseline]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/baseline-execution.json
[execution]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/mesh-c1-execution.json
[c1]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/single-pair-comparison.json
[tests]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/final-cloud-tests.log
[recovery]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/4890d1d7f76e947b6913a48624d4c498fc6cb668/docs/cloud-restart-20261020/data-recovery-inventory.json
[old-final]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/7a6b62a9154e2584548e48bef4717b7e666904df/tis-java/runs/final-report-20261019T181935Z/FINAL_COMPLETION.json
[old-closure]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/7a6b62a9154e2584548e48bef4717b7e666904df/tis-java/runs/final-report-20261019T181935Z/closure.json
[wave-latest]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/07d3dfa956b6662a07ff930577240b091065f5d6/tools/task1_waveform_check.py
[view-latest]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/07d3dfa956b6662a07ff930577240b091065f5d6/tools/task1_results_view.py
[wave-tests-latest]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/07d3dfa956b6662a07ff930577240b091065f5d6/tests/test_task1_waveform_check.py
[resume-plan]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/fourpad-exploration-plan.md
[resume-residual]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/residual-results/summary.json
[resume-six]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/fourpad-coarse-results/summary.json
[resume-rank]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/first-loop-attempt/rank-coarse.json
[resume-checkpoint]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/first-loop-attempt/checkpoint.json
[resume-stop]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/first-loop-attempt/stop-diagnosis.json
[resume-get]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/actual-gh-pagination-check.json
[resume-loop-code]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/tools/task1_finite_loop.py
[resume-residual-audit]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-restart-20261020/RESIDUAL_3000_CAUSE_AUDIT.md
[resume-adoption]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-resume-20261020/feedback-adoption-delta.json
[resume-ledger]: https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/be724b0b314263f284fdbc5397bdaf019685fa29/docs/cloud-restart-20261020/feedback-ledger.json
