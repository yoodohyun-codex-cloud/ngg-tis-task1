# 작업1 최신 연구 결과와 실행 경로

루트 README와 PACKAGE_INDEX의478파일은 **초기 이관 패키지의 원본**이므로 그대로 보존한다. 그 문서의 “새 실행 전” 상태는 현재 실행 상태를 뜻하지 않는다. 원본 byte 검증, 새 수치 계산, 격자·접촉 수렴, 실험 검증은 별도다.

- [한 귀환 패드 회전3행 결과](ONE_RETURN_ROTATION_RESULTS_20261021.md) / [수치 GUI](CLOUD_ONE_RETURN_ROTATION_RESULTS_20261021.html) / [공통 눈금 지도12장](cloud-one-return-rotation-native-maps-20261021T180000Z/index.html)
- [실제 귀환 응답 rank 진단](RETURN_ROTATION_OPERATOR_DIAGNOSTIC_20261021.md)
- [귀환 net전류 조정6조건](RETURN_CURRENT_RESULTS_20261021.md) / [6행 수치 GUI](RETURN_CURRENT_RESULTS_20261021.html) / [새 피드백6321929825 적용](FEEDBACK_APPLICATION_STATUS_20261021T172000Z.md)
- [단일 전극쌍 RMS 비교6cohort](COHERENT_SINGLE_PAIR_RESULTS_20261021.md) / [별도 RMS 매칭 GUI](CLOUD_COHERENT_SINGLE_PAIR_RESULTS_20261021.html)
- [같은4패드 coherent 두 톤8조건](COHERENT_DRIVE_RESULTS_20261021.md) / [10행 수치 GUI](CLOUD_COHERENT_DRIVE_RESULTS_20261021.html) / [공통 눈금 지도24장](cloud-coherent-drive-native-maps-20261021T170500Z/index.html)
- [약한 coherent 후속6조건 완료 summary](cloud-next-coherent-weak-20261021T170000Z/summary.json) / [게시 오류의 재계산 없는 복구](cloud-coherent-weak-context-20261021T170000Z/publication-failure-disposition.json)
- [4패드 square/cross × opposite/adjacent 배선 비교](ADJACENT_CROSS_RESULTS_20261021.md) / [4행 수치 GUI](CLOUD_ADJACENT_CROSS_RESULTS_20261021.html)
- [완료된 gap·전류·접촉/피부 J 위치 진단](GROUPED_GAP_DIAGNOSTIC_20261021.md) / [피드백 적용 추적](FEEDBACK_APPLICATION_STATUS_20261021T164000Z.json)
- [4·8·12·16패드 fine 결과](GROUPED_FINE_RESULTS_20261021.md) / [5행 수치 GUI](CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html) / [공통 범위 지도12장](cloud-grouped-fine-native-maps-20261021T162000Z/index.html)
- [피드백 처리 기록 정정](FEEDBACK_DISPOSITION_CORRECTION_20261021.md): 실제 도착한6319669306 누락을 정정하고6320375305 진단 요구를 연결
- [같은 beat30Hz 중·고 carrier 결과](MID_HIGH_CARRIER_RESULTS_20261021.md) / [수치 GUI](CLOUD_MID_HIGH_CARRIER_RESULTS_20261021.html)
- [낮은 carrier 결과 및 실패 복구](LOWER_CARRIER_RESULTS_20261021.md) / [수치 GUI](CLOUD_LOWER_CARRIER_RESULTS_20261021.html)
- [원래4square와 sine1/2/3/5/9kHz 공통 눈금 공간 지도12장](cloud-frequency-native-maps-20261021T155000Z/index.html)
- [교차형 면적 배분3조건](CROSS_ALLOCATION_RESULTS_20261021.md) / [기존44조건·4/8/12/16패드 GUI](CLOUD_VOLUME_RESULTS_20261021_v8.html)
- [4/8/12/16 strip 가족 XY fine 배치 결정](cloud-grouped-fine-20261021T160000Z/DECISION.md), [설정·마스크·해시](cloud-grouped-fine-20261021T160000Z/prepared-inputs/preregistration.json), [실제 시작 snapshot](cloud-grouped-fine-20261021T160000Z/started-live-proof.json)

새 carrier 네 조건은 모두 같은8개 피부·접촉 부담에서 목표ROI mean/P10을 개선하지 못해 미채택이다.1/2k는SC손실,5/9k는국소벡터J RMS max가제한원인이다. 전역max는SC에남으며fat층의고전기장띠를깊이집중으로해석하지않는다. 최적후보/전체수렴/실험검증/인체안전·활성화동등성은주장하지않는다.

16:00 UTC에 시작한 fine grouped 네 조건은 PDE와 fullskin 감사가 모두 완료됐습니다. 기존 큐는16:08에 후처리 등록 메타데이터 불일치로 종료됐고, 원 실행·실패를 보존했습니다. 새 후처리 전용 큐는16:17에5단계를 모두 완료했고 게시 커밋은 `dc9f842`입니다. 새 PDE는 없었습니다. 원래4square의 동일8개 피부·접촉 한도에서 strip4/8/12/16의 목표ROI mean은 각각0.963/0.853/0.731/0.597 V/m이며 원래4square4.062 V/m보다 낮습니다. P10도 모두 낮고 제한항은 접촉 전압입니다. 후보를 채택하지 않았습니다.

새 GUI와 지도는 원래4square와 별도4strip 대조군을 구분하고 모든 조건의2개 독립 출력/common GND/50Ω를 유지합니다. 저장된 coarse/fine native field의 실제 면적·실효gap·복소전류 보존·J hotspot 위치·부담 제한·목표/비표적 순위 진단은23.622초에 완료됐고 `96aa1e6`에 보존했습니다. 같은 fine기준에서도 순위가 coarse16/8/4/12에서 fine4/8/12/16으로 바뀌므로 확장패드를 채택하지 않았습니다. 1mm gap당1.6셀인 XY0.625 비교만으로 가장자리 수렴을 선언하지 않습니다. 기존13800초 승인 예산,1CPU/RSS3GiB/저장여유2GiB를 유지합니다. 무기한 상주 워커는 없습니다. 최신상태는 [PR2 진행댓글](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6314015870), run의PID/startticks·잠금·heartbeat·terminalcheckpoint를 함께 확인합니다.

복소E/φ원시파일은현재환경의data-native와원래cachedrun에있고선택JSON/NPZ·provenance는Git에있다. 역사적전체원시기저가복원됐거나독립영구백업이완료됐다고주장하지않는다. 이전환경과실패증거는폐기하지않았다. COMSOL5.3a/예정5.3.1.201의설치·실행은미검증이며현재유한계산은Java/Python으로진행한다.


16:33:57–16:36:23 UTC의 새4패드 배선 큐는7단계 모두 완료됐습니다. 기존3개 대조군을 재사용하고 adjacent-cross 한 조건의8RHS만 새로 계산했습니다. 같은 피부 부담에서 목표 mean/P10은3.244504/2.963020 V/m이고 고정8항목 모두 실패해 미채택입니다. 완료 source·원표·checkpoint·선택 산출물은 위 결과 문서에 있습니다.

16:48:34–16:50:02 UTC의 coherent8조건 큐는 저장된 원본4square의 두 출력 각각에3000/3030Hz를 합성해 완료했습니다. 실제 합성 Thevenin 파형의 전체 Vpp를 구간으로 검증하고 raw 상한1Vpp로 정규화했습니다. 동일8개 피부·접촉 한도에서는 quadrature 조건이 목표를 늘렸지만 여섯 비표적 screen을 모두 실패했습니다. r1/90°의 ROI mean/P10=4.386559/4.005458 V/m, 표층P95=66.996623 V/m(원본25.259222), 비표적P95=51.540062 V/m(원본23.435719)이며 source상한은각1.512948Vpp입니다. 고정전압 개선으로 해석하지 않고 미채택했습니다. 지도24장은17:04:30 UTC에 외부120초 단일잠금 guard 아래41.664초에 완료됐습니다. 저장 scalar의 표시이며 새 PDE/새 검증은 아닙니다.

16:54:58 UTC에 시작한 weak mixing(r0.05/0.1/0.2,φ90/270°)6조건도 계산·nativeφ 프로브·피드백 GET은 완료했고, 모두 목표2항목 pass/비표적6항목 fail이었습니다. 최초 게시 단계만 존재하지 않는 feedback-before 경로 때문에 실패했습니다. 원 실패와 계산은 보존하고 실제 재사용한 feedback 경로를 고정한 새 metadata-only 게시로 `9ad428c`에서 복구했습니다. 계산 재실행은0입니다.

17:10:33–17:11:52 UTC의 다음 귀환 net전류 조정6조건 큐도3단계 모두 완료됐고 결과는 `8723508`에 공개했습니다. 실제 scout70.013초로 새 PDE는0입니다. 두 출력의 같은 주파수 전압을 복소합성한 결과이며 GND 전류를 별도 자유변수로 만들지 않았습니다. 모든6조건의 목표mean/P10과 표층P95가 기준에 실패했습니다. τ1에서 선택한 GND패드의 net전류는 상쇄돼도 국소J는 남습니다. 일부 표층 고변조 부피는 감소했으므로 모든 비표적 지표가 실패했다고 묶지 않습니다. 여전히 미채택입니다.

단일 전극쌍 비교도17:09:06 UTC에 실제 계산됐고 `121bed2`에 공개했습니다. 최신 미채택 coherent의 피부8cap 결과와 목표ROI 에너지RMS를 맞추려면 source1.579958Vpp, 중심20mm RMS를 맞추려면1.577268Vpp가 필요합니다. 225mm²패드2개(귀환포함)/독립출력1개이고, 비교TIS의4패드/2출력과footprint가 다릅니다. 총전류·전력·피부부담을 동시에 맞춘 비교나 변조·생리학적 동등성 주장이 아닙니다.

새 댓글6321929825는17:10:52 UTC에 귀환 계산 도중 작성됐고17:11:46 첫 GET로 수신했습니다. 기존 구현·등록·실행에 소급하지 않고 위 적용 문서에 고정 회로 합성/새 회로 풀이의 경계, 작은 혼합비에서 주파수별 음의metal-delivered power, C1 cohort/footprint를 명시적으로 연결했습니다. 새 peer의 후보 승인·전체 수렴 검증은 추론하지 않습니다.

단일 귀환pad2 회전 조건은17:21:42 UTC에 실제 시작해 네이티브100.395초로완료했습니다. 계산/fullskin/부피/8screen/GET은모두exit0이었고, 게시만root가report별서로다른SHA필드명을잘못연결해실패했습니다. 원실패·코드·결과를보존하고새metadata-only명세로 `312b346d`에서복구했습니다. 재계산0입니다. 같은8피부상한에서목표mean/P10=4.379866/3.945150V/m은원본4square4.061849/3.645736보다높지만, 표층P95=32.158704/비표적P95=25.887362가높고고변조부피4항목도증가해비표적총6항목모두실패했으므로미채택입니다. 원래비대칭parent4.383544/3.951942와비교하면회전이목표를개선하지않았습니다. 원본대조군과parent의형상/면적차이와parent→회전의단일인자대비를구분합니다.

회전결과의저장scalar만사용한지도12장은17:30:45 UTC에단일120초guard아래11.041초로완료했습니다. 별도작은전류응답진단도완료해원본square/회전귀환응답rank1,원래비대칭rank2를실제로확인했습니다. 독립전압출력은모두2개이며GND전류를새출력처럼만들지않았습니다. 이진단은E/φ/grid/NPZ를읽거나새PDE를수행하지않았습니다.

다음root선택은같은회전기하의원래square3h파형·위상·고정회로를유지하며두출력의Vpp비만바꾸는4조건입니다. [선택·정확한전압벡터·rank제약](cloud-rotation-ratio-context-20261021T180500Z/decision.json)을고정했고소스·합성테스트를준비중입니다. 아직이4조건의새장합성은시작하지않았습니다. 원본4square와회전1/1캐시를재사용하며새PDE0입니다. 기존누적13800초/CPU1/RSS3GiB/저장여유2GiB를유지하고후보채택·COMSOL·ETA부하·전체수렴·실험검증은미완료입니다.
