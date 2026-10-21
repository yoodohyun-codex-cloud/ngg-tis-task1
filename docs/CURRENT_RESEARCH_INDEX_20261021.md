# 작업1 최신 연구 결과와 실행 경로

루트 README와 PACKAGE_INDEX의478파일은 **초기 이관 패키지의 원본**이므로 그대로 보존한다. 그 문서의 “새 실행 전” 상태는 현재 실행 상태를 뜻하지 않는다. 원본 byte 검증, 새 수치 계산, 격자·접촉 수렴, 실험 검증은 별도다.

- [4·8·12·16패드 fine 결과](GROUPED_FINE_RESULTS_20261021.md) / [5행 수치 GUI](CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html) / [공통 범위 지도12장](cloud-grouped-fine-native-maps-20261021T162000Z/index.html)
- [피드백 처리 기록 정정](FEEDBACK_DISPOSITION_CORRECTION_20261021.md): 실제 도착한6319669306 누락을 정정하고6320375305 진단 요구를 연결
- [같은 beat30Hz 중·고 carrier 결과](MID_HIGH_CARRIER_RESULTS_20261021.md) / [수치 GUI](CLOUD_MID_HIGH_CARRIER_RESULTS_20261021.html)
- [낮은 carrier 결과 및 실패 복구](LOWER_CARRIER_RESULTS_20261021.md) / [수치 GUI](CLOUD_LOWER_CARRIER_RESULTS_20261021.html)
- [원래4square와 sine1/2/3/5/9kHz 공통 눈금 공간 지도12장](cloud-frequency-native-maps-20261021T155000Z/index.html)
- [교차형 면적 배분3조건](CROSS_ALLOCATION_RESULTS_20261021.md) / [기존44조건·4/8/12/16패드 GUI](CLOUD_VOLUME_RESULTS_20261021_v8.html)
- [4/8/12/16 strip 가족 XY fine 배치 결정](cloud-grouped-fine-20261021T160000Z/DECISION.md), [설정·마스크·해시](cloud-grouped-fine-20261021T160000Z/prepared-inputs/preregistration.json), [실제 시작 snapshot](cloud-grouped-fine-20261021T160000Z/started-live-proof.json)

새 carrier 네 조건은 모두 같은8개 피부·접촉 부담에서 목표ROI mean/P10을 개선하지 못해 미채택이다.1/2k는SC손실,5/9k는국소벡터J RMS max가제한원인이다. 전역max는SC에남으며fat층의고전기장띠를깊이집중으로해석하지않는다. 최적후보/전체수렴/실험검증/인체안전·활성화동등성은주장하지않는다.

16:00 UTC에 시작한 fine grouped 네 조건은 PDE와 fullskin 감사가 모두 완료됐습니다. 기존 큐는16:08에 후처리 등록 메타데이터 불일치로 종료됐고, 원 실행·실패를 보존했습니다. 새 후처리 전용 큐는16:17에5단계를 모두 완료했고 게시 커밋은 `dc9f842`입니다. 새 PDE는 없었습니다. 원래4square의 동일8개 피부·접촉 한도에서 strip4/8/12/16의 목표ROI mean은 각각0.963/0.853/0.731/0.597 V/m이며 원래4square4.062 V/m보다 낮습니다. P10도 모두 낮고 제한항은 접촉 전압입니다. 후보를 채택하지 않았습니다.

새 GUI와 지도는 원래4square와 별도4strip 대조군을 구분하고 모든 조건의2개 독립 출력/common GND/50Ω를 유지합니다. 다음 단계는 저장된 coarse/fine native field로 실제 면적·실효gap·복소전류 보존·J hotspot 위치·부담 제한·목표/비표적 순위 변화를 진단하는 유한 배치입니다. 현재 이 진단의 소스와 테스트를 준비 중이며 계산 시작은 별도 실행 영수증으로 기록합니다. 1mm gap당1.6셀인 XY0.625 비교만으로 가장자리 수렴을 선언하지 않습니다. 기존13800초 승인 예산,1CPU/RSS3GiB/저장여유2GiB를 유지합니다. 무기한 상주 워커는 없습니다. 최신상태는 [PR2 진행댓글](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6314015870), run의PID/startticks·잠금·heartbeat·terminalcheckpoint를 함께 확인합니다.

복소E/φ원시파일은현재환경의data-native와원래cachedrun에있고선택JSON/NPZ·provenance는Git에있다. 역사적전체원시기저가복원됐거나독립영구백업이완료됐다고주장하지않는다. 이전환경과실패증거는폐기하지않았다. COMSOL5.3a/예정5.3.1.201의설치·실행은미검증이며현재유한계산은Java/Python으로진행한다.
