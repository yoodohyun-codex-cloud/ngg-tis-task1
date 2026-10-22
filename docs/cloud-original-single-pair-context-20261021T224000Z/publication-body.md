최신 fine 원래4square 구동 original-refine-3e018f8a317a의 단일 전극쌍 비교를 완료했습니다. 실제 계산0.100548초/peakRSS39075840B, 새JSON매칭4개와 기존 원래square 기준매칭4개의 불변 재사용으로 총8개입니다. 계산·후속GitHub GET 큐는 모두 exit0입니다. 새PDE/RHS/원시배열해독은0이고 기존 원본과 실패 기록을 보존했습니다.

C1은 귀환 포함 225mm²×2/총450mm²/독립출력1개/3000Hz 순수sine입니다. TIS는225mm²×4/총900mm²/독립출력2개/common GND/50Ω입니다. 같은 명목PBS·SC2 native 격자의 비교이며 SC4/coarse/접촉0.5·2배 자료를 섞지 않았습니다. 모든 Vpp는 50Ω 전의 whole high-Z source 값이며 loaded metal/contact 전압은 별도입니다.

최신 TIS skin8 조건의 중심 깊이20mm E_RMS=1.970406628V/m에 C1을 맞추려면1.548467460Vpp,1.449370153mA_RMS,source0.777027258mW가 필요합니다. primary ROI(r≤5mm,깊이15–20mm)의 energyRMS=2.175961540V/m에 맞추려면1.551870436Vpp,1.452555350mA_RMS,source0.780446266mW가 필요합니다. ROIenergyRMS는 sqrt(volume-weighted mean(E_RMS²))이며 mean(E_RMS)나 TIS변조와 다릅니다. 같은C1전압으로 두 기준을 동시에 맞췄다고 하지 않습니다. raw1Vpp TIS의 두 매칭은 각각1.416088957/1.419201013Vpp입니다. 기존 원래square 기준의1.646410363/1.649344066Vpp 매칭은 재계산하지 않았습니다.

낮은 전력이 같은 접촉 부담을 뜻하지 않습니다. 위 ROIenergyRMS 매칭의 C1접촉J95=16.915446606A/m²로 TIS12.466047323보다 높고, 원래 수치 비교cap13.553106045의1.248086배입니다. 실제 전류·접촉전압·국소Jmax/J95·층별/접촉/저항 손실·signed 주파수별 출력전력을 함께 보존했습니다. 이cap은 인체 안전한계가 아닙니다. RMS가 같아도 단일sine의 envelope변화0과 TIS차이주파수변조는 같은 물리량이 아니며 활성화 동등성을 주장하지 않습니다.

각 매칭은 깊이5/10/15/20mm × centre/±5X/±5Y × X/Y 두 방향의40개 nativeφ 프로브를 연결합니다. 팁간격5mm와 프로브중심위치를 구분합니다. ETA5001의 두 tip–GND 4MΩ∥7pF가 차동8MΩ/3.5pF를 이루므로 추가 병렬차동 branch를 더하지 않습니다. 스코프1MΩ·16pF는 프로브 출력 뒤에 있으며 팬텀에 병렬로 붙이지 않습니다. 실제 finite-tip port응답·접지·대역/감쇠/메뉴 설정이 미확인이어서 부하검증 예측은 보류하고 무부하 및 명목 감쇠/표시 변환과 구분했습니다.

native기저 실행 cloud-mesh-c1-20261019T190000Z, TIS 계산실행 cloud-original-drive-refinement-20261021T222000Z, 이번 비교실행 cloud-original-single-pair-20261021T224000Z를 별도로 저장했습니다. 27개 입력SHA가 실행 후 일치하고 기준aliases4개도 그대로입니다. 이전 최신구동 목표mean/P10=4.011539371/3.595322017V/m은 원래4square4.061848942/3.645735739보다 낮아6/8·미채택입니다. SC4두수준20/20통과와 XY진단6/20실패를 유지하며 전체SC/XY/bulk/edge/contact 수렴·실험·인체안전/활성화·COMSOL5.3a 실행을 완료했다고 하지 않습니다.

이 유한 큐는 완료됐고 현재 numerical worker는 없습니다. 다음 필수 finerXY는 기존800000셀/Java nx120내의791280셀(h≈.4167mm)을 검토하지만 새native설정·실행은 아직 등록하지 않았습니다. native보수상한+post128MiB+원래disk2GiB에 총2756469376B여유가 필요합니다. 최종 전용preflight에서 실제 가용량·잔여13800초 예산·PID/startticks/두잠금을 갱신해 정확한 blocker/resume_condition을 게시합니다. 과거원본/실패삭제·자원/예산확대·설치·main병합·무기한백그라운드는 없습니다.

[8개 C1 비교 GUI](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/CLOUD_ORIGINAL_SINGLE_PAIR_RESULTS_20261021.html), [보고서](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/ORIGINAL_SINGLE_PAIR_RESULTS_20261021.md), [실제 summary](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/cloud-original-single-pair-20261021T224000Z/summary.json), [SC/XY GUI](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/CLOUD_ORIGINAL_MESH_SENSITIVITY_RESULTS_20261021.html).
