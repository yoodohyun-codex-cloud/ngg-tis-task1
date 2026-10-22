# 중·고 carrier 완료 — 같은 beat30Hz에서도 Jmax 제한으로 미채택

[수치 GUI](CLOUD_MID_HIGH_CARRIER_RESULTS_20261021.html) · [원래4square 및 sine1/2/3/5/9kHz 공통 눈금 공간 지도](cloud-frequency-native-maps-20261021T155000Z/index.html) · [실제 큐 종료](cloud-mid-high-carrier-20261021T154000Z/queue/summary.json) · [새 원시 계산 summary](cloud-mid-high-carrier-20261021T154000Z/completed/summary.json)

`cloud-mid-high-carrier-20261021T154000Z`는15:41:01–15:42:50UTC에 계산·부피·파형·40프로브와GitHub GET 두 단계 모두exit0으로 정상 완료했다. 실제 계산·후처리105.00초, 전체큐110.30초다. 새 Java는5000/5030/9030Hz만 계산했고 **신규6RHS, 기존9000Hz2RHS 재사용,3k 회귀4RHS 재사용**을 분리했다. 기존9000Hz가 있다는 이유로 새PDE를 중복 실행하지 않았다. 회귀10개 복소배열은 원래기준과 모두byteequal이었다.

원래 D50mm/층0.1·5·5·15mm/+z깊이/상면,4square 패드 각225mm²·2출력·공통GND·활성 및비활성50Ω·High-Z1Vpp=0.5Vpeak, SC2/XY0.625mm/벌크14·14·40을 유지했다. EIS의Rs500 선택값236.5717747232937Ω를 한 번 차감하고 측정면적을 한 번 반영한 PBS 계면이며 새 주파수는 모두측정대역내다. 실제 피부 접촉 검증은 아니다. 두 sine 조건은 **5000/5030과9000/9030Hz, 모두beat30Hz**다. 초기bare2000/2010과 과거9000/9090beat90은 별도 결과로 보존한다.

목표는 r≤5mm/깊이15–20mm의 부분 셀 부피가중 ROI이고, 모든 cutoff·표층0–5mm·전체 비표적 마스크는 원래 기준과 같다. 아래는 원래4square의 같은8개 피부·접촉 한도에서 최대 방향 기본 TIS(V/m)다. 한도는 사람의 안전·활성화 역치가 아니다.

| 조건 | 출력당 Vpp | 목표mean | 목표P10 | 표층P95 | 전체 비표적P95 | 제한 |
|---|---:|---:|---:|---:|---:|---|
| 원래square3k/3030 |1.000000|4.06185|3.64574|25.25922|23.43572|기준|
| sine-5000-5030-beat30 | 0.929007 | 3.54333 | 3.17848 | 21.98482 | 20.51721 | Jmax |
| sine-9000-9030-beat30 | 0.756254 | 2.86271 | 2.56735 | 17.63530 | 16.70210 | Jmax |

두 조건 모두 목표mean/P10 두 항목에 실패했고 나머지6개 비표적 항목은 통과했다. 표층 감소가 목표 절대 세기 저하를 동반하므로 **모두 미채택**이며 정밀 격자 진단으로 자동 승격하지 않는다. 낮은 carrier1k/2k는 SC손실, 이번5k/9k는 전체 피부 벡터J RMS의 국소max가 제한 원인이다. 이번 비교만으로 모든 가능한 주파수·배선의 한계라고 일반화하지 않는다.

| 조건/비교 | 출력당 Vpp | 목표mean | 목표P10 | 표층P95 |
|---|---:|---:|---:|---:|
| sine-5000-5030-beat30 / raw_1Vpp | 1.000000 | 3.81410 | 3.42138 | 23.66485 |
| sine-5000-5030-beat30 / equal_total_source_output_RMS_sum | 1.088200 | 4.15050 | 3.72314 | 25.75210 |
| sine-5000-5030-beat30 / equal_total_power | 1.098139 | 4.18841 | 3.75715 | 25.98731 |
| sine-9000-9030-beat30 / raw_1Vpp | 1.000000 | 3.78539 | 3.39483 | 23.31928 |
| sine-9000-9030-beat30 / equal_total_source_output_RMS_sum | 1.066556 | 4.03732 | 3.62078 | 24.87132 |
| sine-9000-9030-beat30 / equal_total_power | 1.084365 | 4.10474 | 3.68124 | 25.28660 |

위 원전압·총전류·총전력 비교를 피부 부담 일치와 구분한다. 총전류는 출력별RMS 전류의 합이며 net전류가 아니다. 원자료·5정규화·cached3ksine 별도한도 cohort·전류·Jmax/J95·접촉전압·구획별 손실·총전력·ROI분포/CV/max·고정cutoff의 비표적 고변조부피는 [전체 원표](cloud-mid-high-carrier-20261021T154000Z/result-brief.json)와 GUI에 보존했다. 같은전압·전류·전력·표면부담을 동시에 맞췄다고 표시하지 않는다.

부담 일치 후 전역max는5k에서919.73,9k에서509.26V/m이며 모두SC z0.025mm에 남는다. 지도에서는fat5.1–10.1mm의 고전기장 띠도 보이며 이를 깊이 집중으로 해석하지 않는다. global_native_range와 별도 deep_ROI_display_clipped 눈금을 각각 고정해6조건/XY·XZ를 같은범위로 비교했다. deep 표시범위의 clipping은 ROI통계나판정을 바꾸지 않는다. 최대 방향TIS는2074개 표본방향의 하한이고 고정방향TIS 및전체 carrier RMS와 구분한다. Square RMS는3차 고조파를 포함하며 sine RMS는실제 두carrier다. 저장NPZ scalar와 같은 grid만읽어12PNG를 렌더했고 E/φ 투영이나PDE를 다시 계산하지 않았다.

새 native 메타데이터는 **실제3주파수/6RHS** 그대로다. 분석4주파수 조합은별도 `frequency_assembly`에 각 주파수 exporter/configSHA/maskSHA/raw파일SHA/기존9000Hz접촉Z·격자·접촉행·방정식gate와함께기록했다. 하나의새4주파수 producer라고 표시하지 않는다. source9344c23/등록d74d06f와 모델·접촉·격자는source SHA로 연결된다. 기존3k producer 회귀와native5개 방정식gate·실제합성파형RMS/envelope/spectrum·40phi프로브 검사가통과했으나독립solver·SC/XY/bulk/edge/contact수렴·실험검증은별도미완료다.

40개프로브는깊이5·10·15·20mm/중심및XY±5mm십자/X·Y방향/**팁간격5mm**의무부하 nativeφ 차이다. ETA5001 입력R/C가팬텀에주는부하까지검증한실측예측은아니며스코프입력을팬텀에직접병렬연결하지않았다. 새주파수C1도미실행이다. COMSOL5.3a/예정빌드5.3.1.201의설치·실행은계속미검증이다.

선택23파일16990478bytes를[SHA일치복사](cloud-mid-high-carrier-20261021T154000Z/publication-inventory.json)했다. 복소E/φ의원시native는현재환경원래run과cachedbaseline에보존했으며공개Git이나독립영구백업으로모두옮겼다고주장하지않는다. 기존원본·실패·과거결과는삭제·덮어쓰기하지않았다.

유도현2에게[실제낮은주파수결과와새비교검토요청6320024448](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6320024448)을게시했다.15:42GET에새검토응답은없었으며합의를추정하지않는다. 다음은기존4/8/12/16패드strip900mm²가족의XY1.25→0.625mm비교다.1mmgap이coarse격자보다작았던한계를확인하려는수치진단이며새후보채택을전제하지않는다. 원래4square fine기준은재사용하고별도4strip대조군과8/12/16을같은격자·2출력·공통귀환에서계산할계획이다. 이문서시점에는다음배치미실행이다. 기존13800초장부의잔여약6731초안에서만유한실행한다.
