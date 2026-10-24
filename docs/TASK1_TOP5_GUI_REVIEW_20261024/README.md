# Task 1 표시 상한 구분 — GUI 검토본

[수정 HTML](index.html) · [ROI 확대 미리보기](preview.png) · [전체 범위](global-panel.png) · [수정 전](baseline-panel.png) · [모바일](mobile.png) · [검증 결과](validation.json)

기준: PR 2의 `f0749c17b99a4d4096b9b0fdbd070a3518190651`, `docs/TASK1_TOP5_20261022_compact/index.html`.
원 compact 폴더와 영수증은 덮어쓰지 않았습니다. 이 폴더가 별도 검토용 결과입니다. GitHub 파일 게시와 실제 서비스 배포는 다르며 배포하지 않았습니다.

- 6개 전기장 지도와 6개 접촉 J 지도마다 단위·최소/중간/최대 눈금 colorbar를 표시합니다. 배치 간 동일 저장 범위를 사용합니다.
- 상한 초과 셀은 노랑+빗금이며 **표시 상한 초과, 물리적 포화 아님**을 명시합니다. 실제값은 변경하지 않습니다. 전체 분포/심부 ROI 색상 확대는 공간 범위 자르기가 아닙니다.
- 현재 표시 단면 좌표와 유한 셀의 비가중 초과 비율을 표시합니다. NaN을 제외하며 체적 ROI 통계나 물리 검증 결과가 아닙니다. 단면·지표·진폭 변경에 따라 다시 계산합니다.
- hover/클릭은 색상 상한 적용 전 Float16 근사값·좌표·초과 여부를 표시합니다. 원 Float64 정량 통계와 구분합니다.
- 진피/지방/근육 이름과 경계 깊이, SC 0–0.1 / dermis 0.1–5.1 / fat 5.1–10.1 / muscle 10.1–25.1 mm, 목표 r≤5·z15–20 mm를 표시합니다.
- maxTIS는 기본파 2074 표본방향 최대, fixedTIS는 (X+Y)/√2 고정방향 기본파 변조, RMS는 전체 carrier 벡터 E RMS입니다. 순위와 검증 보류 상태는 유지합니다.

## 검증과 한계

`validation.json`은 기존 compact의 gzip/base64 payload 바이트 동일성과 전체 해제 JSON hash를 기록합니다. 따라서 표시 배열·정밀 통계·순위·기존 원자료 hash 문자열·mesh/contact/experiment held 상태가 그대로입니다. **원 native 파일을 새로 열어 hash를 검증한 것은 아닙니다.** 정밀 3D 원자료 복원·전체 지방 체적 최솟값·fat 경계장 수렴·실험/물리 검증은 하지 않았습니다.

회귀 검사에서 중앙 XZ y=-0.3125 mm의 fat 표시 최소 8 V/m과 별도 XY z≈9.92143 mm의 최소 4.04296875 V/m을 함께 확인합니다. 후자는 유효 5024셀 중 182셀이 8 미만입니다. 둘 다 특정 Float16 단면 통계이며 전체 지방 최소가 아닙니다. 이런 값은 GUI에 고정 사실로 하드코딩하지 않습니다.

설치·활성화·새 PDE·기존 worker/예산/lock/원본 계산 파일시스템 변경은 없습니다. 이 체크아웃은 원 계산 환경 접근 증거가 아닙니다.

재생성(출력은 새 파일이어야 함):

```sh
python tools/task1_top5_gui_refresh.py BASELINE_COMPACT.html NEW_OUTPUT.html
python tests/test_task1_gui_scale_review.py BASELINE_COMPACT.html docs/TASK1_TOP5_GUI_REVIEW_20261024
```

표시 재생성은 표준 라이브러리와 검토한 dashboard 모듈만 사용합니다. 과거 compact release 실행기는 worker lock/원자료/예산에 접근하므로 실행하지 않았습니다. 테스트는 이미 설치된 Playwright와 Chromium만 사용합니다. CSP는 같은 제한을 유지하며 수정한 스크립트의 hash만 갱신했습니다.

실행 결과: Chromium 154.0.8037.57에서 210개 mode/metric/plane/depth/range 조합, 12회 반복 갱신, 12개 colorbar, 후보 공통 범위, baseline 노란 띠, hover 상한 초과/정밀도 문구, 모바일 390px을 통과했습니다. JS 오류와 외부 요청은 0입니다. 미리보기 카드 캡처에서는 가리지 않도록 sticky controls/hover만 촬영 시 숨겼으며 HTML 자체는 그대로입니다.
