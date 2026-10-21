# 피드백 수신·처리 기록 정정 — 2026-10-21

15:32·15:42 UTC에 “새 피드백이 없었다”고 쓴 보고는 잘못됐습니다. **6319669306은 두 원 GET 영수증에 이미 도착해 있었는데 계산 담당자가 내용 처리와 보고에서 누락했습니다.** GitHub 전달 실패나 상대방의 무응답이 원인이 아닙니다. 원 보고서·영수증·실패 증거를 바꾸지 않고 이 문서와 [기계 판독 장부](FEEDBACK_DISPOSITION_CORRECTION_20261021.json)로 정정합니다.

| 잘못된 기록(보존) | 정정 대상 표현 |
|---|---|
| [LOWER_CARRIER_RESULTS_20261021.md](LOWER_CARRIER_RESULTS_20261021.md):29 | `15:32UTC GET에 새 검토 피드백은 없었으며` |
| [completed-publication-body.md](cloud-lower-carrier-recovery-20261021T153000Z/completed-publication-body.md):9 | `새 유도현2 피드백은15:32GET에서 없었으며` |
| [feedback-result-disposition.json](cloud-lower-carrier-recovery-20261021T153000Z/feedback-result-disposition.json):10 | `"new_peer_feedback_observed": false` |
| [MID_HIGH_CARRIER_RESULTS_20261021.md](MID_HIGH_CARRIER_RESULTS_20261021.md):38 | `15:42GET에새검토응답은없었으며` |
| [completed-publication-body.md](cloud-mid-high-carrier-20261021T154000Z/completed-publication-body.md):9 | `15:42GET에새응답은없었습니다` |

## 원문과 실제 수신

- [6319669306](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6319669306), 수정 시각15:25:11 UTC. Body SHA256 `1ae49731956a4ec11d048bc995996f67c48d2778790892478a70d2609ab083ab`.
- [lower GET](cloud-lower-carrier-recovery-20261021T153000Z/feedback-after.json):15:32:04.154800 UTC, `/receipts/3/evidence/12`. 파일 SHA256 `b3ebb8833a03cd5cc6d7be4df7f9e442eb1ed73385d2c85b39734ba7b2257b54`.
- [mid/high GET](cloud-mid-high-carrier-20261021T154000Z/feedback-after.json):15:42:50.525942 UTC, 같은 JSON pointer. 파일 SHA256 `f03a9b21cf775701805c7cd57c22c4b78de2d9309f6096853877d596310553a2`.
- [6320375305](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6320375305), 수정 시각15:58:04 UTC. Body SHA256 `600efd51ec21ce3923b7e1f3f1c3d577d32a58a78ceb88e412399f0f6532aa00`. [새 수신 기록](cloud-grouped-fine-recovery-20261021T161000Z/feedback-before.json)의 `/receipts/3/evidence/14`에 있습니다.

`new_feedback_automatically_adopted=false`는 자동 채택하지 않았다는 뜻이며 수신 부재가 아닙니다. `peer_agreement_inferred=false`도 새 의견이 없다는 뜻이 아닙니다. 수신·명시적 채택·구현·실행·게시자료 검토·독립 검증을 별도로 기록해야 합니다. 이번 정정의 채택 커밋은 root가 실제 커밋한 뒤 연결하며 과거 작업으로 소급하지 않습니다.

## 6319669306: 완료된 증거와 한정된 검토 범위

요구는 면적 허용치의 단위·규모·부동소수점 근거, 실제 기하 변경 검출, 최초 실패/최대 차이/수정 코드, donor 재사용 및10배열별 오차·허용치·판정 연결입니다. 기존 증거 작업이 이 요구와 부합해도 해당 댓글을 당시 명시적으로 채택했다고 추정할 수 없습니다. **이 정정에서 해당 요구를 명시적으로 채택하고 이미 존재하는 증거에 연결합니다.**

[최초 실패](cloud-lower-carrier-20261021T152000Z/FAILURE.md)의 원 CSV face 면적은3.9062499999999997e−7 m², 계산된 h²는3.90625e−7 m²입니다. 기록된 두 표현의 차이는5.2939559203393771e-23 m²(1ULP), 상대차는1.3552527156068805e-16입니다. Float64 ε는2.2204460492503131e-16, 상대4ε는8.8817841970012523e-16입니다. 가산 절대오차는0이고 실효 face 오차 상한은4ε·h²=3.4694469519536144e-22 m²입니다. 이는 고정 full-face 표현의1ULP를 다루는 국소 guard이며 일반적 누적 오차나 실제 접촉면적 불확실성의 증명이 아닙니다.

[v2 로더](../tools/task1_lower_carrier_native_v2.py)는 마스크 bytes/2304 face 인덱스·순서·양수면적·실제 패드면적과 기존 native area/PDE gate를 보존합니다. snap·clip·면적 재정규화는 하지 않습니다. 코드 근거는 `07aba294d20692ebc0454c1486b7ca8b93908b2b`, [게시된 회귀 결과](cloud-lower-carrier-recovery-20261021T153000Z/producer-regression.json)는 `7643624ee0aa13b3a1bce52cdf505227bedf3c6b`입니다. 최초 exact-equality 실패와 donor raw는 그대로 보존합니다.

회귀는3000/3030 Hz 각각 field·potential·density·source·loss의10배열 모두 최대 성분오차0, 실패 성분0, decoded binary byte equality=true입니다. 단위별 허용치(상대2e−10/절대1e−12)는 원 결과에 유지합니다. grid/contact identity와 입력 불변도 기록됐고 donor 회귀4RHS를 재사용해 새 회귀 RHS는0입니다. 이 문서 작성 중 배열을 다시 디코딩하거나 계산하지 않았습니다.

6320375305는 위 **게시 증거 하위 단계만** 검토 완료/resolved로 인정합니다. 독립 native 재디코딩·solver 재현·전체 수렴·실측 검증의 완료가 아닙니다. 이를 별도 피드백인 strip 진단의 완료로 전이하지 않습니다.

## 6320375305: 채택할 후속 진단은 아직 미완료

root가 선택한 유한 readback의 요구로 명시적으로 채택합니다. 현재 구현 중이며 이 정정은 실행·통과를 주장하지 않습니다. coarse/fine 실제 mask 면적과 최소 유효 gap, pad별 복소 전류/보존, edge Jmax 값·좌표와 patch 표현, 활성 제한항, 공통 ROI/cutoff/부담에서 절대 mean/P10·표층/비표적 지표·순위 안정성이 필요합니다. 4square 기준과 별도4strip 대조를8/12/16패드 옆에 유지하고 면적/연결이 달라지면 순수 mesh 효과와 구분합니다.

h0.625 mm도1 mm gap당1.6셀입니다. 이 비교만으로 gap/edge 수렴을 닫지 않습니다. 현재 recovery 등록 코드에는 두 댓글을 포함한9개 known incoming 원문 SHA가 들어 있지만, 그 사실만으로 요구별 채택·계산·검증이 완료되는 것은 아닙니다.

## 게시 이력과 적용 추적

lower 완료 게시 영수증은 성공을 기록합니다. mid/high 첫 게시 시도는 `failed_preserved`로 남아 있으며 [별도 성공 후속 영수증](cloud-mid-high-carrier-20261021T154000Z/mid-high-publication-20261021T154000Z.json)을 구분합니다.

두 원문을 포함한 실제 수신9건의 SHA와 명시적 root 선택을 연결한 코드는 `184208c`에 채택됐고, 복구 사전등록은 `9002379`, 실제 완료 부피·8선별 결과의 게시 커밋은 `dc9f842`입니다. [복구 큐 종료 영수증](cloud-grouped-fine-recovery-20261021T161000Z/queue/summary.json)은5단계 모두 exit0이며 새 PDE가 없습니다. 이는 **피드백 출처 연결과 후처리 완료**의 적용 커밋입니다. 6320375305의 상세 gap·전류·J 위치 감사는 별도 실행·결과·게시 커밋에 연결해야 합니다.

이 문서는 기존 잘못된 보고를 보존한 정정입니다. 연구팀에 보낼 답변은 실제 후속 진단 결과를 확인한 뒤 별도 공개 증거로 게시하고 그 영수증을 연결합니다. 당시 원본17개 파일의 SHA 전후 일치는 동명 JSON에 기록했습니다. 문서 감사 자체에서 새 PDE나 native 배열 분석을 수행하지 않았습니다.
