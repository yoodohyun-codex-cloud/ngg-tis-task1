# 새 실행기·백업 경로 독립 검토 — 2026-10-20 KST

`tools/task1_cloud_batch.py`, `tools/java/CloudShapeBasis.java`, `tools/task1_compare_baseline.py`, 실행 경계 시험과 첫 baseline 영수증을 읽었다. 이 검토 중 실제 원시 배열 후처리·PDE·추가 worker를 실행하지 않았다. 과거 파일이나 실행 중인 코드의 pin을 수정하지 않았다.

새 실행 어댑터의 numerical main body는 동결 `SelectivityShapeBasis`와 같고 wrapper 영수증만 추가한다. PID/startticks·controller/config SHA·두 Linux lock namespace·새 경로 검증을 유지한다. source/input 바이트를 검증한 다음 연구 모듈을 import한다. 첫 재현 대조는 동일 condition ID·raw 1 Vpp·같은 격자 기준의 39 scalar와 8 source/loss를 확인하며 독립 solver·격자 수렴·실험 검증을 명시적으로 false로 둔다. 이번 검토에서 이 경로의 높은 영향도 수치 오류는 찾지 못했다.

실패 원인 기록에는 수정할 항목이 하나 있다. 실행기의 `child.wait(timeout=...)`에서 나오는 `subprocess.TimeoutExpired`는 `TimeoutError`의 하위형이 아니다. 0.2초 monitor보다 wait가 먼저 timeout을 발생시키면 현재 except 분류는 자원 한도 종료를 `error`로 기록할 수 있다. 실행 중 pin을 건드리지 말고 해당 배치 종료 후 `(TimeoutError, subprocess.TimeoutExpired)` 분류와 작은 가짜 child timeout 시험을 추가한다. 이미 완료한 수치 결과에는 영향이 없다.

## 새 raw 보존 도구

`tools/task1_native_archive.py`는 stdlib만 사용하며 원격 쓰기·연구 import·solver·삭제가 없다. CLI는 계산 실행기와 같은 전역 잠금을 요구하므로 활성 배치 중 중복 읽기·복사를 시작하지 않는다. 새 `data-native/cloud-*`의 완료 run만 받으며 원 과거 자료에는 적용하지 않는다.

- 전체 새 run의 설정·마스크·native E/φ/density·grid/contacts·source/loss·메타데이터·완료/진행 영수증·후처리·로그·classes를 함께 보존한다. run 외부의 자격증명·환경 디렉터리를 따라가지 않는다.
- 파일별 상대 경로·바이트·SHA256, 소스 commit, preregistration SHA, terminal summary SHA를 내장 manifest에 기록한다. tar는 이미 압축된 native 파일을 다시 압축하지 않는다. 원본 timestamp/사용자명은 tar header로 전파하지 않는다.
- symlink·special·hardlink tar 항목, 경로 탈출/절대경로·중복 이름, manifest와 실제 파일집합 불일치를 거부한다. 출력은 모두 배타적으로 생성한다. 실패 도중 생성된 부분 파일도 삭제하지 않는다.
- pack은 archive를 새로 읽어 hash를 검사하며 `.manifest.json`/`.receipt.json`을 별도로 쓴다. `verify`/`restore`는 외부에서 고정한 archive SHA256을 필수로 요구한다. 로컬 pack의 SHA를 외부 사본 검증의 대체로 쓰지 않는다.
- clean restore는 실행용 `data-native` 바깥의 새 검사 디렉터리만 허용한다. 파일별 byte hash를 다시 검사하고 native little-endian complex128 길이·shape·finite·좌표/층 단위·고정 D50·출력 정규화·주파수 순서를 decode한다. 공간장/ROI/probe 수치를 새로 계산하지 않는다.
- pack/restore 전에 추가 사본의 산술 상계와 기존 2 GiB reserve를 확인한다. 독립 영속 백업·과학적 재현·실측·원 환경 폐기 허용은 자동으로 true가 되지 않는다.

13개 synthetic 저장 fixture 시험이 통과했다. byte roundtrip과 native decode의 별도 상태, externally pinned hash 불일치, overwrite 방지, partial/symlink 거절, 잘못된 shape·NaN, traversal/absolute/symlink/hardlink/중복 tar 거절을 검사했다. 실제 연구 배열은 이 시험에서 읽지 않았다.

GroupedPadBasis의 최종 `grouped_native` 메타데이터도 지원한다. 물리 패드는 4/8/12/16개, 독립 출력은 `n_outputs=channels=2`로 고정한다. metadata·등록 case·config의 pad→0/1/−1 매핑, 공통 귀환 노드, 패드별 양의 면적과 원 접촉 행의 면적 합(상대1e−10), 주파수 간 물리 접촉 순서를 검사한다. 기존 4패드 exporter를 사칭하는 메타데이터를 허용하지 않는다. 12/16패드 fixture에서 field/potential/density의 basis 차원 및 source 2×2·loss 6×2×2를 검사하고, 누락 mapping·추가 출력·물리 패드 수를 source 행렬 차원에 잘못 쓴 자료를 거부했다. 이 검사도 저장 형식 검증이며 grouped 설계의 PDE·수렴 검증이 아니다.

실행 담당의 권장 순서는 **배치 종료 → archive 도구 commit 고정 → 완료 run pack → 승인된 외부 저장소에 asset 보존 → 새 경로에 실제 download → 원 archive SHA 대조 → clean restore → 대표 수치·probe 재현 결과를 별도 연결**이다. 외부 업로드 자체는 이 도구가 수행하지 않는다. GitHub release asset URL·asset ID·서버 크기와 download SHA·clean restore receipt·검사 source commit을 작은 Git manifest에 기록한다. 원 과거 raw 누락 상태와 새 계산 백업 상태를 분리한다.

예를 들어 첫 baseline을 보존할 때, 실행 담당은 새 archive 디렉터리를 만든 다음 다음 명령을 사용할 수 있다. 이미 존재하는 archive/restore 경로는 재사용하지 않는다.

```bash
python tools/task1_native_archive.py pack \
  --run /workspace/ngg-tis-task1/data-native/cloud-baseline-20261019T185900Z \
  --archive /workspace/ngg-tis-task1/runtime/backups/cloud-baseline-20261019T185900Z.tar

python tools/task1_native_archive.py restore \
  --archive /workspace/ngg-tis-task1/runtime/downloaded/cloud-baseline-20261019T185900Z.tar \
  --expected-sha256 <게시 전 고정한 원 archive SHA256> \
  --destination /workspace/ngg-tis-task1/scratch/github-baseline-restore-20261020
```

## 현재 피드백 대장의 구체적 갱신 제안

`docs/cloud-restart-20261020/feedback-ledger.json`을 작성한 초기 시점에는 실제 적용 commit과 실행 artifact가 null이었다. 현재 존재하는 실제 commit만 다음과 같이 연결할 수 있다. 이 제안은 대장 자체를 아직 수정하지 않으며 미래 commit을 추측하지 않는다.

| ID | 현재 적용 commit/실행 근거에 추가할 값 | 상태의 한계 |
|---|---|---|
| F001 | `a4636ec0b1f04c03696eb647307d5c53b2eef5f8`의 same-ROI 후처리 경로; `38f005ecefc2c432cd6424a06f599f93682cc202`의 baseline execution/reproduction | 새 raw 계산·동일 ROI scalar 재현 완료; 깊이 집중/공간 수렴 미검증 |
| F002 | 같은 두 commit의 실제 Jmax/J95·contactV·SC/contact/source power | raw 1 Vpp 부담 계산만 실행 완료. 새 같은 총전력/복합부담 cap 비교는 해당 artifact 생성 전까지 pending |
| F003 | 초기 보존/범위 명시 commit `a4636ec…`만 연결 | 2 kHz의 새 실행 artifact는 null 유지. 현재 baseline은 3 kHz 후기 조건 |
| F004 | baseline execution/reproduction에 연결해 `same_grid_electrical_reproduction_passed` 하위 단계 추가 | 전체 decision은 held 유지. 실행 중 SC/bulk 및 변경 접촉 검증은 결과 전 승격 불가 |
| F005 | `38f005ecefc2c432cd6424a06f599f93682cc202`의 실제 spectrum 재구성 코드 | 실행 중 변경/시험 중 코드의 새 검증은 별도 commit·receipt를 기다림 |
| F006 | `a4636ec…`의 새 단일 lock·source/config guard, baseline의 단일 실행 영수증 | 새 환경 guard 적용 확인. 과거 전체 중복 0이나 재사용 이력 완료 아님 |
| F007 | baseline의 `new_PDE_conditions=1`, retained frequency 4개·source RHS 2개를 별도 계수로 연결 | 구조적 기저 조건 1개와 실제 주파수/RHS 8개는 다른 분모; 과거 cache 감사/최적화 완료 아님 |
| F008 | baseline의 새 native φ와 `postprocess/baseline-square15-coarse/{summary,probes}.json`에 연결 | 3파형×40 trace의 이번 저장 범위. 장비 loading/교정·전체 과거 φ 복구 미검증 |
| F009 | 기존 두 anchor 완료 유지; 새 baseline trace는 F008의 별도 근거로 연결 | 진짜 2-pad C1·loaded source/단자/팁/포락선 묶음이 생성되기 전 전체 확장은 pending |

실제 대장 갱신에서는 `execution_artifact_current_environment`를 native run 안의 경로와 Git에 보존한 작은 `baseline-execution.json` 양쪽으로 연결하고 hash를 함께 둔다. `validation_artifact_current_environment`는 `baseline-reproduction.json`으로 기록하되 numerical reproduction/mesh convergence/experimental validation을 한 상태로 합치지 않는다. `new_execution_from_feedback`는 단순 문서 수신 여부가 아니라 현재 사용자 승인과 지정 F ID를 반영한 실제 실행 범위를 설명하는 객체로 보완하는 편이 정확하다.
