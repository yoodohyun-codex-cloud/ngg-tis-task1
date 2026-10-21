# 작업1 최신 연구 결과와 실행 경로

루트 README와 PACKAGE_INDEX의478파일은 **초기 이관 패키지의 원본**이므로 그대로 보존한다. 그 문서의 “새 실행 전” 상태는 현재 실행 상태를 뜻하지 않는다. 원본 byte 검증, 새 수치 계산, 격자·접촉 수렴, 실험 검증은 별도다.

- [같은 beat30Hz 중·고 carrier 결과](MID_HIGH_CARRIER_RESULTS_20261021.md) / [수치 GUI](CLOUD_MID_HIGH_CARRIER_RESULTS_20261021.html)
- [낮은 carrier 결과 및 실패 복구](LOWER_CARRIER_RESULTS_20261021.md) / [수치 GUI](CLOUD_LOWER_CARRIER_RESULTS_20261021.html)
- [원래4square와 sine1/2/3/5/9kHz 공통 눈금 공간 지도12장](cloud-frequency-native-maps-20261021T155000Z/index.html)
- [교차형 면적 배분3조건](CROSS_ALLOCATION_RESULTS_20261021.md) / [기존44조건·4/8/12/16패드 GUI](CLOUD_VOLUME_RESULTS_20261021_v8.html)
- [4/8/12/16 strip 가족 XY fine 배치 결정](cloud-grouped-fine-20261021T160000Z/DECISION.md), [설정·마스크·해시](cloud-grouped-fine-20261021T160000Z/prepared-inputs/preregistration.json), [실제 시작 snapshot](cloud-grouped-fine-20261021T160000Z/started-live-proof.json)

새 carrier 네 조건은 모두 같은8개 피부·접촉 부담에서 목표ROI mean/P10을 개선하지 못해 미채택이다.1/2k는SC손실,5/9k는국소벡터J RMS max가제한원인이다. 전역max는SC에남으며fat층의고전기장띠를깊이집중으로해석하지않는다. 최적후보/전체수렴/실험검증/인체안전·활성화동등성은주장하지않는다.

16:00UTC에fine grouped4조건의단일실행을시작했다. 이문서의시작snapshot은실시간생존증거가아니다. 최신상태는 [PR2 진행댓글](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6314015870)과해당run의PID/startticks·잠금·heartbeat·terminalcheckpoint를함께확인한다. 큐10단계/최대4200초,기존13800초승인예산안에서실제시간만정산한다. 원래4square는재사용하고4strip기하대조군과8/12/16만새PDE로계산한다. 끝나면부담·부피·8선별·피드백·완료게시를거치며자동채택하지않는다.

복소E/φ원시파일은현재환경의data-native와원래cachedrun에있고선택JSON/NPZ·provenance는Git에있다. 역사적전체원시기저가복원됐거나독립영구백업이완료됐다고주장하지않는다. 이전환경과실패증거는폐기하지않았다. COMSOL5.3a/예정5.3.1.201의설치·실행은미검증이며현재유한계산은Java/Python으로진행한다.
