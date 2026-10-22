현재까지 완료된 결과로 **기준 4패드 + 서로 다른 전극 배치 5개를 비교하는 오프라인 GUI**를 완성했습니다.

[GUI HTML 내려받기](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/raw/__GUI_COMMIT__/docs/TASK1_TOP5_20261022_compact/index.html) · [미리보기](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/__GUI_COMMIT__/docs/TASK1_TOP5_20261022_compact/preview.png) · [선정 기준·사용법·제한](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/__GUI_COMMIT__/docs/TASK1_TOP5_20261022_compact/README.md) · [실제 GUI 검증](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/__GUI_COMMIT__/docs/TASK1_TOP5_20261022_compact/final_validation.json)

전극 실제 윤곽·면적·배선, XY/XZ/YZ 전기장, 접촉 normal J RMS 지도, 피부 bulk J 최대/P95, 목표 ROI mean/P10/분포, 표층·비표적·전역 hotspot, 접촉 전압·손실·전력과 기존 4/8/12/16패드 대조표를 보존했습니다. 고정 전압·출력 RMS 전류 합·전력·피부접촉 부담 일치는 별도 비교입니다. 지도와 통계는 같은 색상 범위·ROI를 사용하며, 전체 carrier RMS와 기본파 TIS 지표를 구분합니다.

적격 완료 53조건/비기준 배치 21종에서 8개 공간 평가 항목의 최대 상대 위반율 → 합계 → 목표 P10 → 평균 순으로 대표 5개를 선별했습니다. 1위 rounded-fullface225/rounded-expand-f35b23a22166도 4/8만 통과하며, 부담 제한 후 목표 mean/P10=4.053222/3.634558 V/m로 기준4.061849/3.645736 V/m보다 약간 낮습니다. 표층 hotspot도 남습니다. 성공·전체 수렴·실험 검증·활성화·안전·후보 채택을 뜻하지 않습니다. PBS 접촉 불확실성과 무부하 probe 제한을 유지합니다.

저장 결과와 접촉 72개 비교·ROI scalar 18종이 일치했고, 실제 Chromium 표시 45조합/6개 패널/모바일390px/오류·외부 요청0 검사를 통과했습니다. 최종 검증 실행은 19.512초, aggregate RSS 최대1,042,038,784B로 CPU1/RSS3GiB/여유2GiB 내에서 완료했습니다. 새 PDE0이며 원본·이전 실패 기록은 보존했습니다. 지도만 Float16 표시 근사이고 정량 표·색상 범위·선정은 원 Float64입니다.

2GiB reserve 위의 남은 공간이 약1MiB여서 로컬 Git blob을 복제하지 않는 원격 child commit으로 GUI를 게시했습니다. 원격 GUI commit은 __GUI_COMMIT__, 로컬 source HEAD는 __LOCAL_COMMIT__로 의도적으로1commit 뒤에 있습니다. 원본 삭제·reserve 완화·forcepush·큰blob fetch·main 병합은 수행하지 않았습니다. 다음 새 field/mesh 계산은 저장 공간 때문에 보류이며, 추가 계산의 peak 저장량과2GiB reserve가 함께 확보되기 전에는 시작하지 않습니다. 사용 가능한 기존 승인 시간은 게시 후 약 __REMAINING_SECONDS__초이며 예산 확대는 없습니다.
