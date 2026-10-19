# 패키지 검증 범위

전체 로컬 inventory465개를 해시/크기로 검증하고, 공개 사본은 **463개 source 파일**을 원 바이트 그대로 보존한다.
재배포 권한이 확인되지 않은 Elsevier PDF2개는 공개하지 않고 DOI·서지·원 해시를 남겼다. 원본 전체 로컬 사본은 보존한다.
세부 결과는 `PACKAGE_VALIDATION.json`, source/생성물 구분은 `MIGRATION_MANIFEST.json`·`GENERATED_FILES.json`에 있다.

- 원 EIS XLSX17개: ZIP CRC·workbook/sheet XML 구조 및 원 해시 확인.
- 원 CV PCFFGRA4 binary461,883B·두 경로 사본 동일, 조건문서 source hash 일치. paired CSV 각각1476행 구조 확인. 새 적분/fit 없음.
- Python40개: AST 문법 및 정적 local import 연결 확인. 연구 모듈 import/테스트/solver 실행 없음.
- source/loss192개: byte hash, little-endian Float64 길이·유한값 확인. 전체 공간 E/φ 배열 복구 아님.
- credentials 패턴, 자격증명 디렉터리·개인 chat archive·작업2 전용 모델/환경 미포함. 스캔은 모든 형태의 비밀 부재에 대한 수학적 보증은 아님.
- 최신33f0d6ab 보고서·4실험패드/기존2출력·최대16패드·15–20mm 깊이 집중·지속 유한 연구 계약 반영.

**실행 가능한 완전 복구 패키지는 아니다.** 정적 reference에서 같은 상대 경로로 포함171, 원 Git에 있으나 이 최소 패키지에서 제외53,
대응 경로가 없는 원 로컬 경로466개를 구분했다. 이것은 textual path inventory이며 모든 workflow의 필수파일 수는 아니다.
과거 source 문서의 상대 링크97개는 원 저장소/생략 자료를 가리키므로 `DEPENDENCY_GAPS.json`의 고정 원문 URL로 확인한다.
작성한 새 root 문서의 local 링크는 존재를 확인했다. 고정 source를 링크 수정을 위해 덮어쓰지 않았다.

전체 native E/φ/volume·이전 raw기저·CV원설정 사진/시간벡터 등은 미이관이다. Java/runtime·COMSOL·16패드구현·실측도 미검증이다.
archive의 압축해제/해시와 fresh clone 검증은 배포 파일의 복원 가능성만 확인하며 수치 재현·원 환경 폐기 가능성을 뜻하지 않는다.
원 환경은 전체 보존자료의 실제 복구·decode·대표 수치 재현과 누락 해결 전까지 보존한다.
