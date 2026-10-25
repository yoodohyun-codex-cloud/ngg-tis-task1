작업 1의 고정 D50 mm 팬텀에서 중앙 r≤5 mm·깊이 15–20 mm 부피와 표층·전체 비표적, 피부·접촉 부담을 함께 비교하는 재현 가능한 Java/Python 연구 루프를 구축했습니다. 4패드는 전극 패드 4개/독립 출력 2개이며, common GND·50Ω·비구동 주파수 종단과 원래 1 Vpp 정의를 보존합니다.

최신 완료 결과는 [4·8·12·16 strip fine 비교](docs/GROUPED_FINE_RESULTS_20261021.md), [동일 눈금 지도](docs/cloud-grouped-fine-native-maps-20261021T162000Z/index.html), [coarse/fine gap·전류·J hotspot 감사](docs/GROUPED_GAP_DIAGNOSTIC_20261021.md), [4패드 배선 대조 원표](docs/cloud-adjacent-cross-20261021T164000Z/volume.json)입니다. 같은 원래 4square 부담에서 strip 후보의 목표 평균/P10은 모두 감소했고 격자에 따라 순위가 바뀝니다. 새 adjacent-cross도 고정8항목을 모두 통과하지 못했습니다. 후보를 채택하지 않았습니다.

[4·8·12·16 GUI](docs/CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html), [4패드 square/cross × opposite/adjacent GUI](docs/CLOUD_ADJACENT_CROSS_RESULTS_20261021.html), [기존44조건 GUI](docs/CLOUD_VOLUME_RESULTS_20261021_v8.html)에 원래4square 기준·ROI·5정규화·전원 연결·출처·실행/검증 상태를 연결했습니다. 최대 방향 기본 TIS와 고정 방향 TIS, 전체 carrier RMS, 접촉/체적 J, 무부하 nativeφ probe Vpp를 구분합니다.

원본 패키지478파일(33,360,627B)은 byte hash 검증을 통과했고 덮어쓰지 않았습니다. 계산·후처리·게시 실패 원본도 보존했습니다. [피드백 누락 정정과 적용 추적](docs/FEEDBACK_DISPOSITION_CORRECTION_20261021.md)은6319669306/6320375305 원문과 실제 결과를 연결합니다. 최신7단계 배선 큐는145.074초에 완료됐고 승인13800초 장부에 실제 시간만 정산했습니다. 한 실행 잠금·PID/startticks·체크포인트·예산·실패/재개 조건을 기록하며 무기한 daemon은 없습니다.

수치 방정식 gate·기저 회귀·공개 패키지 hash와 전체 격자/SC/전극 가장자리/접촉 수렴·실험 검증은 별개입니다. PBS 계면 surrogate, ETA5001 부하·장비 설정, 인체 활성화·안전은 검증 완료로 표시하지 않습니다. COMSOL5.3a/예정5.3.1.201 설치·실행은 미검증이며 이 환경 구축은 COMSOL에 의존하지 않습니다. Task2·유료자원 확대·main 병합은 포함하지 않습니다.

검증: 새 복구·coarse/fine·파형/전류·GUI 계약의 의미 있는 합성 테스트와 실제 원 입력 SHA, native 방정식/프로브/전력 감사를 수행했습니다. 선택 JSON/NPZ와 실행 증거를 공개하며 대용량 복소 E/φ 원시 기저는 현재 환경에 보존했습니다. 전체 과거 원시자료 이전 또는 독립 영구 백업을 완료했다고 주장하지 않습니다.
