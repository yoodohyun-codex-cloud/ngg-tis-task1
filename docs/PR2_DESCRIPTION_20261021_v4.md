고정 D50 mm 팬텀에서 목표 깊이15–20 mm의 부피 전체와 표면·비표적 부담을 비교하는 작업1 연구 환경과 유한 계산 루프를 구축합니다. 과거 패키지의 byte 보존, 새 FVM 계산, 수치 수렴, 실험 검증을 분리합니다. 현재 후보는 모두 미채택이며 깊이 집중·인체 안전·활성화 성공을 주장하지 않습니다.

현재 결과·실제 실행 상태·재현 명령은 [연구 인덱스](docs/CURRENT_RESEARCH_INDEX_20261021.md)에 연결합니다. 원본 문서·478파일·실패 증거는 보존하며 main 병합/설치/보안 변경/삭제/외부 유료 자원/예산 확대를 수행하지 않습니다.

- 팬텀은 D50/SC0.1·dermis5·fat5·muscle15 mm, 윗면 부착입니다. 기본4개는 물리 패드 수이며 실제 전원2출력/common GND/50Ω입니다. 8·12·16패드에서도 출력 수를 자동 증가시키지 않습니다. 초기2/2.01kHz와 후속3/3.03kHz 및 square3h의9/9.09kHz를 구별하고 전체 파형1Vpp를50Ω 앞 source에서 정의합니다. 다른 주파수의0V/50Ω 종단을 보존합니다.
- 기본 ROI는 표면을깊이0으로 하는 +z15–20mm, 중앙r≤5mm입니다. native fractional 체적 가중·마스크·고정cutoff를 공개하고 mean/P10/CV·비표적P95/max·고변조 부피·전역 hotspot을 함께 평가합니다. 전체XY 같은 깊이는 보조입니다. fat층 경계의 높은 E를 깊이 집중으로 해석하지 않습니다.
- raw 전압, 출력RMS전류 합 일치, 총 전력 일치,8개 피부·접촉 부담 일치,legacy composite는 별도 모드입니다. 전류·전력·부담을 동시에 같게 만들었다고 하지 않습니다. 원래 수치 cap/cutoff는 생리적 역치·안전 한계가 아닙니다. 기본 차이주파수 변조, 전체 carrier RMS, 피부 국소J, nativeφ 프로브Vpp를 분리합니다.

최신 완료 결과는 [외곽4패드 배치](docs/PERIMETER_SHELL_RESULTS_20261021.md), [sine/negativecross6조건·GUI](docs/PERIMETER_ANTIPHASE_RESULTS_20261021.md), [XYZ 및 연속 방향 경계8조건](docs/DIRECTION_BOUNDS_RESULTS_20261021.md), [5형상 출력별·주파수별 signed 전력 감사](docs/CACHED_GEOMETRY_OUTPUT_POWER_20261021.md)입니다. 외곽 배치는 각225mm²/총900mm²의 실제576full-face 합집합이고 smooth arc/convex hull이 아닙니다. rim여유0.02345mm·edge/SC/XY/bulk/contact 보류를 유지하며 미래 격자는 같은 물리 윤곽을 표현해야 합니다.

외곽 negativecross r=.05/.1은 피부8cap에서 목표mean/P10 및 표층P95를 개선했지만 전체 비표적P95와 고변조 부피4항목이 실패했습니다. 원4square 대비7개 후보의 연속 방향 경계를 실제54.908초에 후처리해 모든 후보에서 최소 한 필요 조건의 조건부 실패가 남는 것을 확인했습니다. 기존2074 방향 maxTIS는 하한L로 보존하고,9개λ PSD 혼합 최대고유값의 상한U를 추가했습니다. 이는 해당 고정 native 장·정규화에 대한 방향 범위 진단이며 정확한 연속 최적값·IEEE/solver/continuum 인증·모든 설계의 불가능 증명이 아닙니다.

[4·8·12·16패드 fine 비교](docs/GROUPED_FINE_RESULTS_20261021.md)와 [gap 진단](docs/GROUPED_GAP_DIAGNOSTIC_20261021.md)은 같은 ROI·단위·표시 범위로 보존합니다. coarse/fine 순위 반전과 접촉전압 제한을 숨기지 않습니다. [회전 구동 기준의 C1 비교12매칭](docs/ROTATION_COHERENT_SINGLE_PAIR_RESULTS_20261021.md)은 귀환을 포함한2패드/1출력/450mm²와4패드/2출력/900mm² footprint 차이를 명시하고 중심 E RMS·ROI sqrt(weighted E_RMS²) 매칭을 별도로 계산합니다. 같은 RMS가 TIS 변조나 생리적 활성화 동등성을 뜻하지 않습니다.

40개 무부하 차동 예측은 깊이5/10/15/20mm×중심/±5mm X/Y×두 수평축, 팁 간격5mm입니다. 복소φ 두 점 차이로 실제 파형·Vpp/RMS/변조/스펙트럼을 계산합니다. ETA5001의 팬텀 입력 R/C와 버퍼 뒤 Keysight DSOX1202A 입력을 구별하며 이 결과는 실제 장비 부하/대역폭/표시 설정까지 검증된 실측 예측이 아닙니다. PBS EIS의 Rs는 실제236.5717747Ω를 한 번 차감하고1cm² 정규화를 한 번 적용합니다. Rs500 표기는 fit창500Hz이며500Ω가 아닙니다. 실제 피부 접촉·CV/EIS 측정 불확실성은 별도입니다.

검증 범위: 패키지 원본478파일/33,360,627B 해시, 새 Java selftest/방정식·회로·보존 gate, source/config/접촉·물성/격자/원시 장 SHA, actual waveform·nativeφ40검사와 코드 합성시험을 결과별로 연결했습니다. 역사적 source4/loss2 불일치와 누락된 과거 복소 원자료의 정확 재현은 보류입니다. 새 PDE 재계산은 원자료 복원이라고 하지 않습니다. 생성된 full E/φ는 로컬에 보존하며 독립적인 영속 backup은 미검증입니다. COMSOL5.3a/예정5.3.1.201 설치·라이선스·실행도 미검증이고 초기 환경은 COMSOL에 의존하지 않습니다.

단일 실행자/이중 잠금·live PID/startticks·heartbeat·checkpoint·실제 ledger·실패 근거로 유한 배치를 운영합니다. 승인13800초/CPU1/RSS3GiB/Javaheap2GiB/저장여유2GiB를 유지합니다. 이 설명 작성 시5실수gene 제한 구동 탐색이 실제 실행 중이며 최대124proxy/300초 뒤 새개선최대4개만2074방향·5정규화·40nativeφ로 평가합니다. proxy26방향LB/GershgorinUB는 순위만 정하며 실제 전체 검증으로 표시하지 않습니다. 이어서 같은 패드 윤곽의 안쪽.625mm 이동1조건은 별도 결정·등록 후 실행합니다. 무기한 daemon이나 예산 초과 지속을 약속하지 않습니다.

유도현2의 stable 댓글ID별 적용·보류와 actual GET/게시를 보존했습니다. [6323875064](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6323875064)에 완료 결과와 다음 질문을 전달했으며 수신/GET을 peer 승인으로 해석하지 않습니다. 작업2 모델은 제외합니다.
