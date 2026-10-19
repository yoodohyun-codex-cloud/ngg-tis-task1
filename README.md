# NGG–TIS 작업 1 재시작 패키지

승인 대상은 사용자 소유의 **공개 `yoodohyun-codex-cloud/ngg-tis-task1`**다. 원 EIS·CV와 연구 자료 공개에 대한 사용자 승인을 반영했다.
이 패키지는 계산 환경이 아니라 작업1의 읽기 전용 재시작·이관 준비 자료다. 저장소는 사용자가 생성했으며,
기존 integration의 생성 요청403은 이전 경로의 실패 이력이다. 새 환경 연결·설치·시뮬레이션은 시작하지 않았다.
포함 파일의 byte/형식·정적 의존성 검사는 완료했지만 전체 native 기저 이관·수치 복구는 미완료다.

목표는 고정 D50 mm 팬텀의 **15–20 mm 깊이에 실제로 집중된 TIS 전계**다. 표면 최대가 남은 상대 개선과 깊이 집중 성공을 구분한다.
작업 2 설정/활성화 모델/사람 자극 설정은 범위 밖이다.

먼저 다음 문서를 읽는다.

1. [CODEX_START_PROMPT.md](CODEX_START_PROMPT.md): 새 계산 Codex에 전달할 한국어 프롬프트.
2. [RESEARCH_LOOP.md](RESEARCH_LOOP.md): 계산 담당–dot의 유한 연구 반복·GitHub 검토 계약.
3. [MIGRATION.md](MIGRATION.md)와 [MIGRATION_MANIFEST.json](MIGRATION_MANIFEST.json): 실제 포함 파일과 미이관 자료.
4. [ELECTRODE_DATA_PROVENANCE.md](ELECTRODE_DATA_PROVENANCE.md): 원본 EIS·CV·reference와 조건/권리의 구분.
5. [연구 보고서](docs/TASK1_NEW_CLOUD_RESTART_REPORT_20261019.md): 단계별 결과·기준값·실패·재시작 gate.

`tis-java/`의 코드/설정/테스트는 원 PR #3 `8c3a30a778cc9bf19ccb52ca523598bff0a84650`의 바이트를 보존한 검토 자료다.
정적 Python import 의존성을 수집했으나 실제 실행 가능한 완전한 복구 bundle이라고 인증하지 않았다.
과거 경로·run 참조는 그대로 남아 있으므로 자동 재개하지 않는다. `pipeline_ngg.py` 같은 재계산 명령을 bootstrap 검사로 실행하지 않는다.
기존 보고서의 과거 “미상” 또는 “실행 중” 문구는 원시 이력이며 최신 조건/완료 문서와 구분한다.

전체 native E/φ/volume 기저는 원 계산 저장소에만 남아 있고 이 패키지에는 없다.
선택도 698 local-only 경로 목록은 lock 등도 포함하며 698개 기저라는 뜻이 아니다.
GitHub 결과와 작은 source/loss 행렬이 전체 원시 자료의 백업을 대신하지 않는다.

계산을 시작하기 전에 원 저장소 inventory와 실제 복구·decode·대표 결과 재현을 확인한다.
설치·시뮬레이션·원자료 삭제는 이 패키지를 만드는 과정에서 하지 않았다. 원 환경을 폐기하지 않는다.
새 데이터는 계산 인스턴스와 독립적인 불변 영속 저장소에 보관하고 Git에는 코드/설정/manifest/보고서를 둔다.

제공된 원본 데이터·사용자 코드에 포괄적인 새 라이선스를 부여하지 않는다. 참고 PDF2개는 all-rights-reserved 표시 때문에 본문을 공개하지 않고 DOI·서지·해시만 남겼다.
원 데이터와 reference의 출처/권리 상태를 유지하며 자격증명·개인 채팅 보관본·작업 2 환경은 포함하지 않는다.

추가 확정 요구: 실험4패드/기존2출력, 시뮬레이션 최대16패드. [패드 수 비교 계약](PAD_COUNT_DESIGN_CONTRACT.md)은 회로·총예산·공통눈금 비교와 미구현 상태를 명시한다.

## 패키지 검증과 실행 범위

[PACKAGE_VALIDATION.md](PACKAGE_VALIDATION.md)와 [DEPENDENCY_GAPS.json](DEPENDENCY_GAPS.json)에 검증/누락 범위를 기록했다.
검증 명령 `python tools/verify_package.py`는 표준 라이브러리로 패키지 파일의 크기·SHA만 확인하며 계산 코드를 import하지 않는다.
이는 native 전계 재현·16패드 지원·COMSOL 실행 검사가 아니다. 연구 코드의 고정 과거 절대경로와 누락 run을 먼저 검토한다.
원 source 문서의 일부 상대 링크는 최소 패키지에서 제외한 자료를 가리킨다. 링크 감사의 고정 source URL을 이용하며
이 링크를 채우기 위해 예전 worker나 계산을 자동 재시작하지 않는다.
