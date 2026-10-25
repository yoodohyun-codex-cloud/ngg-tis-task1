고정 D50 mm·층0.1/5/5/15 mm 팬텀에서 중앙 r≤5 mm·깊이15–20 mm의 절대 TIS 변조와 표층·전체 비표적, 피부·접촉 부담을 함께 비교하는 작업1 전용 유한 연구 환경입니다. 4패드는 물리 패드4개/독립 출력2개이며 common GND·50 Ω·다른 주파수 출력단 종단·실제 전체 파형1 Vpp 정의를 보존합니다. 8/12/16패드도 출력은2개입니다.

[최신 연구 인덱스](docs/CURRENT_RESEARCH_INDEX_20261021.md)에 원본4square 대조, [4/8/12/16 fine GUI](docs/CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html), [배선·형상 비교](docs/ADJACENT_CROSS_RESULTS_20261021.md), [두 톤 coherent 구동](docs/COHERENT_DRIVE_RESULTS_20261021.md), [귀환 net전류 조정](docs/RETURN_CURRENT_RESULTS_20261021.md), [단일 귀환 회전](docs/ONE_RETURN_ROTATION_RESULTS_20261021.md), [전압 비율4조건 GUI](docs/CLOUD_ROTATION_RATIO_RESULTS_20261021.html), [최신 회전 sine/coherent5조건 원결과](docs/cloud-rotation-coherent-20261021T182000Z/summary.json)를 연결했습니다. 공통 ROI·눈금·고정전압·출력RMS전류합 일치·전력 일치·피부/접촉8cap·legacy 정규화는 별도입니다.

회전 coherent r1/90°의 같은8cap 목표mean/P10은4.743313/4.326879 V/m이지만 표층P95=67.804247, 전체비표적P95=51.338308 V/m으로 비표적6항목을 모두 실패했습니다. 이때 실제 source상한은 각1.517825Vpp이고 raw1Vpp 결과와 구분합니다. 새 sine 대조군의 부피·40nativeφ probe를 계산했고 기존 nativepost 전기/복소centre 회귀는배율1/오차0입니다. 모든 새 후보는 미채택입니다. [양의 출력진폭 계열 bound](docs/ROTATION_AMPLITUDE_BOUNDS_20261021.md)는 고정 회전 기하·격자·2074방향·exclusive-square3h·위상·회로만의 조건부 배제이며 다른 기하/파형/접촉/연속체 물리의 불가능성 주장이 아닙니다.

복소 E/φ 합성, 기본 차이주파수 방향별/표본최대 TIS, 전체 carrier RMS, 접촉법선 및 피부체적 J, signed주파수별 source/metal 전력, 손실, 실제40개 무부하 전위차 probe Vpp/RMS/스펙트럼을 분리했습니다. 단일 자극은 귀환 포함 패드2개/출력1개이며 중심 fieldRMS 일치와 ROI energyRMS 일치 cohort 및 footprint를 따로 보존합니다. ETA5001의 R/C 부하, 실제 장비 설정·전력흡수·phase동기화는 미검증입니다.

478개 원본 패키지(33,360,627 B)는 byte hash 검증을 통과했고 수정·삭제하지 않았습니다. 패키지 해시 검증과 역사적 시뮬레이션 재현·새 PDE·전체 수렴·실험 검증을 구분하며 전체 역사적 raw기저 이전/독립 영구백업 완료는 주장하지 않습니다. 계산·게시/메타데이터 실패 원본, 복구 이유와 재계산0 증거도 보존했습니다. [피드백 누락 정정](docs/FEEDBACK_DISPOSITION_CORRECTION_20261021.md), [6321929825 명시 적용](docs/FEEDBACK_APPLICATION_STATUS_20261021T172000Z.md), PR의 실제 검토/결과 댓글은 채택commit·수치검증·peer승인을 각각 구분합니다.

실행은 단일 수치 워커, loop/execution 각각 FLOCK+POSIX, livePID/startticks, checkpoint·실패·정확한 다음 명령과 기존13,800초 장부로 관리합니다. CPU1/RSS3GiB/저장여유2GiB, 수치조건600초 및 사전등록 유한 큐를 유지합니다. 다음 물리적 기하 질문은 소스 패드·총면적·회로를 고정하고 두 GND패드를 접선 이동하는1조건이며, 코드/검토 준비와 실제 시작은 실행 증거로 구분합니다. 무기한 daemon·자동 재시도는 없습니다.

검증은 새 coherent 소스 합성12개, 실행 제어25개 테스트와 입력해시·기존 native5방정식 gate·실제 전류/전력/파형/프로브 감사를 포함합니다. SC/XY/bulk/전극 가장자리 및 PBS→피부 접촉 불확실성 gate는 별도로 유지하며 전체 수렴이나 활성화·인체안전의 증명으로 표시하지 않습니다. COMSOL5.3a/예정5.3.1.201 설치·실행은 미검증이고 현재 Java/Python 계산은 COMSOL에 의존하지 않습니다. Task2·설치·유료자원/예산 확대·main 병합·자료 폐기는 포함하지 않습니다.
