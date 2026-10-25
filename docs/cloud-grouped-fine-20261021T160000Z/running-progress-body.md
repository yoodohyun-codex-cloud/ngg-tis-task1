현재 실행 상태: grouped4/8/12/16 fine 배치를 **16:00:00 UTC에 실제 시작**했습니다.

워커 PID16227/startticks4488721이며, 아래 snapshot 시각에 비zombie·시작 식별값·전역/loop 양쪽 잠금·heartbeat를 확인했습니다. 계산은 하나의 실행자에서 순차로 진행합니다. [등록 abeb973](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/commit/abeb973).

총면적900mm², 독립출력2개·공통GND·50Ω와 고정 팬텀·ROI를 유지하고, 기존strip4/8/12/16패드를XY1.25→0.625mm로 비교합니다. 1mm gap이 기존 coarse격자보다 작았던 해석 한계를 확인하는 진단입니다. 원래4square fine 기준은 재사용하고 별도4strip 기하대조군을 포함합니다. 패드가 늘면 strip너비와 그룹외곽도 함께 변하므로 순수패드수 효과로 표시하지 않습니다. 새PDE4조건/32unit-outputRHS입니다.

큐10단계는 계산4조건→피부감사4건→5행부피등록/감사→고정8선별→유도현2 피드백GET→검증된완료결과 게시입니다. 총상한4200초, 각native조건의600초와CPU1/heap2GiB/RSS3GiB/저장여유2GiB는유지합니다. 기존13800초장부의 시작잔여약6718초 안에서만 실행하며 예산을 늘리지 않았습니다. 영구 상주worker를 뜻하지 않습니다.

완료 주파수 결과는 [fa39cb8](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/fa39cb8/docs/MID_HIGH_CARRIER_RESULTS_20261021.md)과 공통눈금12장·GUI에 보존했습니다. sine1/2k는SC손실,5/9k는국소Jmax 한도에서 목표mean/P10이 낮아 모두미채택입니다. 다음fine 결과도 실제8항목과부담원인을 확인하기 전에는 채택·수렴·실험완료로 표시하지 않습니다.

관측: 2026-10-21T16:01:44.343056+00:00; phase=postprocessing; current_case=grouped-strip225-gap1-p04-xy80; heartbeat=2026-10-21T16:01:41.046015+00:00.
