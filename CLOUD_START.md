# 작업 1 클라우드 실행 안내

현재 실행 근거는 [첫 실행 보고서](docs/CLOUD_RESTART_EXECUTION_20261020.md), [원자료·GitHub 피드백 감사](docs/CLOUD_FEEDBACK_DATA_AUDIT_20261020.md), [결과 화면](docs/CLOUD_RESULTS.html)이다. 기존 README·인계 문서는 동결 source로 보존하며 과거의 “새 환경 미연결” 상태를 현재 실행 상태로 읽지 않는다.

## 먼저 확인

```sh
cd /workspace/ngg-tis-task1
git status --short --branch
python tools/task1_cloud_batch.py --verify-originals
cat runtime/task1-budget.json
```

`PACKAGE_INDEX.json`의 원본 478개는 바이트 그대로 유지한다. 원래 `tools/verify_package.py`는 엄격한 배포 파일 집합 검사이므로 새 연구 파일을 추가한 checkout에서 추가 경로를 거절하는 것이 정상이다. 새 원본 검사기는 인덱스의 크기·SHA만 검증하며 수치 재현이나 실측 통과로 확대하지 않는다.

현재 native 결과는 `data-native/cloud-*/`에 별도 보존한다. 복원/게시 receipt가 없는 로컬 파일을 영속 백업이라고 부르지 않는다. 원 계산 환경의 전체 기저는 여전히 미복원이다. 새 재계산과 원시 자료 복구는 구분한다.

## 유한 실행 계약

`tools/task1_cloud_batch.py --prepare --output <새 data-native/cloud-ID> --case <등록된 조건>`은 실행하지 않고 새 설정·마스크·코드 해시·격자·예산과 Java 해석해 검사를 준비한다. `--execute --output <같은 새 run>`은 해당 사전등록 조건만 한 번 수행한다. 이미 시작한 run은 재시도하지 않고 새 원인/실행 ID를 만든다. 대형 과거 `pipeline_ngg.py`나 controller를 설치 점검으로 실행하지 않는다.

실제 계산은 `.task1-execution.lock`의 flock+POSIX 잠금 하나, CPU1·동시1·조건600초·누적6600초·800,000셀·heap2 GiB·RSS합계3 GiB·disk reserve2 GiB 안에서 수행한다. budget ledger는 새 run마다 초기화하지 않는다. `STOP` 등 중단 표식·partial/failure·heartbeat·실행 attempt를 보존한다. 과거 lock 파일을 복사해 worker를 재개하지 않는다.

4패드=2출력/공통 GND, 개방 High-Z 1 Vpp/50 Ω와 비구동0 V/50 Ω를 유지한다. `channels`라는 과거 Java 필드는 **출력 수**다. 물리 패드 수는 별도 `n_pads`와 pad-node 매핑으로 기록한다. D50·층0.1/5/5/15 mm와 상부 부착은 고정한다. 초기2/2.01 kHz bare와 후기3/3.03 kHz 절단 고조파 조건은 별도다. `square_3h`의1 Vpp는 합성 파형 전체 기준이며 고조파 각각1 Vpp가 아니다.

## 결과 해석

부피 ROI r≤5 mm·깊이15–20 mm의 절대 mean/P10·최대와 표층0–5 mm/전체 비표적·전역 최대 위치·깊이 곡선을 함께 확인한다. 수치 gate/공학적 burden cap을 인체 안전 한계로 읽지 않는다. 기본파 TIS·원시 복소 E·전체 고조파 RMS·실제 합성 파형의 analytic envelope는 서로 다른 지표다.

무부하 차동 프로브는 깊이4개×십자 중심5개×X/Y=40개이며 중심 pitch5 mm와 팁 간격5 mm는 독립 값이다. ETA5001/DSOX1202A의 사용자 제공 사양과 실제 스위치·교정 상태를 구분한다. ETA5001 각 입력의4MΩ/7pF 대지 부하를 사용하고 스코프1MΩ/16pF를 팬텀에 직접 병렬 연결하지 않는다. 실제 팬텀 부하 예측에는 probe-tip 포트 임피던스가 추가로 필요하다. 단일 대조는 실제2패드/1출력이며 같은 E RMS가 같은 생리 반응을 뜻하지 않는다.

COMSOL은5.3a/예정5.3.1.201만 대상이며 설치·license·실행은 미검증이다. 작업2 모델, 새 유료 자원, 무기한 background worker는 이 실행에 포함하지 않는다. 승인된 코드·설정·작은 결과/manifest만 Git에 게시하고 비밀번호·토큰·대화·권리 미확인 논문 원문을 추가하지 않는다.
