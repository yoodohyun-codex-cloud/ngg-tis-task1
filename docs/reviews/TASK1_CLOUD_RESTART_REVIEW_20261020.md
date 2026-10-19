# Task 1 클라우드 재시작 검토 — 2026-10-20 KST

**판정: 같은 4패드 후보의 XY/접촉 가장자리 검증을 다음 과학적 우선순위로 유지한다.** 중심·ROI 지표의 작은 변화만으로 수렴을 선언할 수 없다. 접촉 부담과 선택도는 등록 기준을 넘게 변했다. F004의 전체 검증 보류를 유지하며 새 최적점이나 15–20 mm 집중 성공을 채택하지 않는다.

검토 대상은 `codex/task1-cloud-restart-20261020`의 고정 head **`4890d1d7f76e947b6913a48624d4c498fc6cb668`**다. 요청 시점 `038ce93981adce7b707694d495d69e9b72703430` 뒤에 추가된 한 commit은 grouped 사전등록과 전체 피부 부담 분석 계약 두 파일이다. 이 추가분을 반영해 이미 구현·등록된 사항을 다시 요구하지 않는다. [실행 보고서][report]는 수렴 실패와 결합 3D 미검증을 이미 명시한다. 이 문서는 그 판정의 후속 의사결정 및 F001–F009 추적 근거를 보완한다.

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

## F001–F009: 제안·구현·실행·검증 연결

[기존 장부][ledger]의 9개 ID 모두에서 `adoption_commit_current_environment`, `execution_artifact_current_environment`, `validation_artifact_current_environment`가 null이다. 장부의 초기 감사 시각 이후 실제 코드와 결과가 게시됐으므로 **null이 곧 구현·실행 부재라는 뜻은 아니다**. 반대로 본 검토가 그 필드를 대신 채웠거나 피드백의 공식 채택을 확정한 것도 아니다. 장부 원본은 수정하지 않고 아래 연결을 계산 담당자의 갱신 근거로 제안한다. 기존 ID의 의미와 과거 한정 완료를 유지하며 새 번호를 만들지 않는다.

`a4636ec`는 실행 어댑터/감사 코드 게시, `38f005e`는 baseline 재현과 파형 검사 게시, `038ce93`은 mesh/C1 결과·공간 감사·grouped 구현 게시, `4890d1d`는 grouped 계획 게시 commit이다. 아래의 **게시 commit**은 그 파일이 확인되는 실제 Git 이력이며, 자동으로 공식 adoption commit이나 실행 당시 전체 코드 SHA가 되지는 않는다.

실행 기록의 `source_commit`도 따로 보존해야 한다. baseline 실행은 `a4636ec0b1f04c03696eb647307d5c53b2eef5f8`, mesh/C1 실행은 `38f005ecefc2c432cd6424a06f599f93682cc202`, grouped 사전등록은 `038ce93981adce7b707694d495d69e9b72703430`을 기록한다. 후속 게시 commit과 이 값을 합치지 말고 실제 코드/config/input SHA·run ID·검증 artifact를 함께 연결한다. 게시된 코드 hash와 테스트 로그의 일치도 실제 실행 이력 전체의 증명은 아니다.

| 기존 ID | 확인한 구현·계획 및 게시 commit | 게시 실행·검증 근거 | 현재 검토 판정 및 남길 제한 |
|---|---|---|---|
| T1-F001 | `038ce93`의 `task1_spatial_audit.py`, 중심/부피 ROI/전역·깊이 통계 분리 | [fine-spatial][spatial], `cloud-mesh-c1-20261019T190000Z` / `baseline-square15-xy80` | 정의·통계 구현과 게시 실행 확인. 표층 최대가 유지되므로 deep focus 미검증. 다음 계획은 절대 mean/P10와 공간 선택도를 함께 유지. |
| T1-F002 | `038ce93`의 실제 C1 맞춤 분석; `4890d1d`의 contact cap/전체 피부 cap 분리 계획 | [single-pair-comparison][c1], [grouped 분석 계약][burden] | C1 게시 분석과 grouped 계획을 구분. grouped 전체 피부 cap 결과는 이 head에서 미게시. 과거 bare cap의 J95 제외와 새 cap의 J95 포함을 합치지 않음. |
| T1-F003 | 과거 2 kHz 독립 SC/XY 완료 범위 유지; `038ce93`의 새 축별 gate 보고 | [mesh-convergence][mesh], [mesh/C1 실행][execution] | 이번 SC/bulk 지정 비교 통과와 XY 세 파형 실패를 함께 연결. 과거 한정 완료를 취소하지 않되 새 조건/결합 3D까지 완료로 확대하지 않음. |
| T1-F004 | `038ce93`의 현 4패드 baseline 검증, `4890d1d`의 수렴 전 미채택 규칙 | 같은 [mesh][mesh]의 실패 행, 본 문서의 동일 후보 검증 제안 | **전체 보류 유지.** 접촉/Rs 물리 타당성·전체 3D·새 형상 가장자리 검증 미완료. 새 ROI 또는 exporter 구현으로 닫지 않음. |
| T1-F005 | `38f005e`의 `task1_waveform_check.py`; 기본파 변조와 실제 합성 파형/RMS 구분 | [baseline 재현][reproduction], [C1 파형 분석][c1], [게시 시험 로그][tests] | 저장된 조건·파형의 한정 분석 확인. 단일 carrier의 TIS=0과 E/RMS=0을 구분. 임의 다주파수 확장이나 실험 검증으로 확대하지 않음. |
| T1-F006 | `a4636ec`/`038ce93`의 `task1_cloud_batch.py`: 전역 lock, hash, 기존 operator 검사 | [baseline 실행][baseline], [mesh/C1 실행][execution], 게시 guard 시험 로그 | 구현 및 두 유한 배치의 게시 기록 확인. 모든 과거 실행의 중복0은 미증명. 새 실행 링크와 전체 중복 감사의 보류를 별도 기록. |
| T1-F007 | 현재 후보/operator 구분 및 기존 operator 검사; 전역 frequency/RHS hit/miss 계수 결과는 확인하지 못함 | baseline 1조건, mesh/C1 4조건 실행 기록; grouped 5조건은 계획 | 후보·후처리·PDE 조건·주파수/RHS를 별도 계수할 제안 유지. 조건 수를 solve/RHS 수로 바꾸지 않음. operator 최적화 완료나 삭제 후 재계산0을 주장하지 않음. |
| T1-F008 | `a4636ec` 실행 경로와 `038ce93`의 native φ/E 기반 게시 probe·공간 분석 | [mesh/C1 실행][execution]의 새 `potential-*.bin.gz` 크기/SHA 및 결과 링크 | 새 φ 생성·probe 검사 기록은 확인. 이 검토에서 native 배열을 열거나 재현하지 않음. **과거 φ 이관/복구 미완료**, 실제 장비 loading·대역폭·교정 보류. |
| T1-F009 | `38f005e`의 파형 도구와 `038ce93`의 실제 2패드/1출력 pure-sine C1 분석 | [single-pair-comparison][c1], 실행의 `baseline-square15-C1pair0-xy80` | 두 과거 anchor만 있던 상태에서 새 C1 게시 근거가 추가됨. 중심 RMS/ROI 에너지 RMS/local RMS 평균 맞춤은 별개. 전체 후보·loaded 측정 네 표현·실측 완료로 닫지 않음. |

장부 갱신 시 `decision_current_environment`와 공식 채택 commit, 실제 run/artifact, 통과·실패의 정확한 범위를 각각 기록하는 것이 필요하다. `new_execution_from_feedback`의 인과관계는 실행 담당자가 확인해야 하며, 단순히 본 문서를 읽었거나 게시했다는 이유로 true로 바꾸지 않는다. 특히 F004의 보류, F006/F007의 전체 이력 미검증, F008/F009의 장비·복구 제한은 남긴다. 이 문서는 수신 확인을 위한 새 완료 건을 만들지 않는다.

## 새 복소 전위와 과거 원시 데이터 복원은 별개

새 [baseline][baseline]과 [mesh/C1 실행][execution] manifest에는 각 run의 `potential-*.bin.gz`와 `field-*.bin.gz` 크기·SHA 및 계산 완료가 기록돼 있다. 두 기록의 `persistent_backup_verified`와 `mesh_convergence_validated`는 false다. 새로운 φ의 존재와 같은 격자 scalar/회로 재현은 각각 새로운 계산의 증거이며 과거 전체 native 데이터의 이전·복원 증거가 아니다.

원 저장소 PR3의 고정 `7a6b62a9154e2584548e48bef4717b7e666904df`에서 [FINAL_COMPLETION.json][old-final]은 `raw_transfer_complete=false`, [closure.json][old-closure]은 `transfer_destination=null`, `unstarted_contact_audit=prepared_inputs_only`를 기록한다. 원 환경은 이전을 위해 종료됐으며 원시 자료 이전은 미수행이다. 새 계산으로 누락된 과거 원시 배열을 복구했다고 표시하지 않는다. 원 종료 결정과 새 환경에서 별도로 승인된 실행도 구분한다.

[data-recovery-inventory.json][recovery]의 700개 기록은 과거 local-only 경로 698개와 추가 provenance 범주 2개다. 그중 작은 공개 회로 대응물 184개를 별도 분류한다. 이 경로 수를 모두 미복구 전계 기저 수로 세지 않는다. 남은 복구 차단은 과거 전체 E/φ/volume 접근·실제 전송 목적지와 영속 사본·독립 복구/배열 decode·대표 지표 재현 증거의 부재다. 게시 manifest나 archive 도구의 시험 통과만으로 이 조건을 충족했다고 할 수 없다.

## 이번 검토의 검증 범위

- 고정 Git 이력과 파일을 읽고 `038ce93→4890d1d` 변경이 사전등록/분석 계약 두 파일임을 확인했다.
- 게시 mesh JSON의 108개 변화율·gate·6/9 집계를 표준 라이브러리 산술로 대조했다. 새 전계 계산은 없다.
- 9개 기존 ID의 세 null 필드와 과거/현재 상태를 확인했다. readiness에 열거된 코드 7개·로그/재현 기록 3개의 SHA256을 게시 파일과 대조했다.
- producer의 59개 시험 통과 로그 및 Java 자격검사 문구는 읽은 증거다. 이 검토자가 시험·PDE·native decode를 다시 실행했다고 주장하지 않는다.
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
