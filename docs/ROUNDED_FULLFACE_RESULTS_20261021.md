# 작업1: Rounded-looking fixed full-face union (2026-10-21)

신규 후보는 미채택이다. skin8에서는 비표적 6개 지표가 모두 통과했지만 목표 ROI mean/P10이 약 2% 낮아 목표 2개 지표에 실패했다. 동일 nominal 1 Vpp에서도 목표 mean/P10은 기준보다 낮고 complement P95는 더 높다. skin8의 비표적 감소에는 공통 진폭 0.9823725425587069로 낮아진 영향이 포함되므로 깊이 집중 재분포 성공으로 판정하지 않는다.

[2행 오프라인GUI](CLOUD_ROUNDED_FULLFACE_RESULTS_20261021.html) · [정확한5모드/출처brief](ROUNDED_FULLFACE_RESULTS_20261021.result-brief.json) · [volume](cloud-rounded-fullface-context-20261021T200000Z/volume.json) · [8gate](cloud-rounded-fullface-context-20261021T200000Z/screen.json)

## 고정 면적·중심의 새 물리 도형

고정 중심 (−10,−10),(+10,+10),(+10,−10),(−10,+10) mm, 각 225 mm²/총 900 mm²를 유지한 shape contrast다. hXY=0.625 mm에서 local odd u²+v²≤730의 560개 내부 face와 경계 동률 16개 모두를 포함해 pad당 576 full faces를 고정했다. D4 대칭의 실제 비볼록 stepped face-union이며 smooth circle이 아니다. bbox 17.5×17.5 mm는 실제 접촉 도형과 다르다. outline perimeter 70 mm는 원래 square 60 mm보다 길어 둘레 감소를 주장하지 않는다. min gap 2.5 mm(4 XY cells), rim clearance 2.002038133782378 mm다. 면적·중심은 같지만 축방향 폭·gap·perimeter가 함께 달라져 특정 edge 메커니즘을 분리 입증하지 않는다. 후속 격자는 같은 물리 경계와 교차시키며 radial face 재선정 금지다.

D50 mm, SC/dermis/fat/muscle 0.1/5/5/15 mm, 윗면, XY0.625/SC2/bulk14·14·40, 351680 cells를 유지했다. 물리 4 pads / 독립 2 outputs / 공통 GND / 각 출력 50 Ω다. pad0→out0, pad1→out1, pad2·3→동일 GND이고 다른 주파수의 비구동 출력은 0 V through 50 Ω다. square_3h 기본파 3000/3030 Hz와 3차 9000/9090 Hz, phase0°/0°다. 기존 nominal 1 Vpp whole waveform before50Ω 정의를 유지하며 새로운 hardware waveform bracket 검증으로 승격하지 않는다. 초기2/2.01 kHz 기록은 별도다.

주 목표 ROI는 중심 r≤5 mm, 깊이15–20 mm이며 x/y 수평, +z가 표면에서 안쪽 깊이다. 모든 전기장 표는 V/m, CV와P10/mean은 무차원이다. maxTIS는 기본파의 2074 표본 방향 최대(연속 방향 최대의 하한), fixedTIS는 기본파 (X+Y)/√2 방향 변조, RMS는 저장된 네 주파수선 전체 벡터 RMS다. 가중 inverse-ECDF, fractional ROI, exact z overlap, full-cell staircase cylinder geometry와 원래 square raw cutoff를 보존하며 analytic volume 재정규화를 하지 않는다. 전역 최대가 SC 층 경계에 있다는 사실을 깊이 집중으로 해석하지 않는다.

## raw 동일 nominal1Vpp

|조건|각output nominal Vpp|ROI mean / P10 V/m|CV|P10/mean|ROI max V/m|surfaceP95 / complementP95 V/m|fullRMS mean / P10 V/m|
|---|---:|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.0618489416 / 3.64573573913|0.0807616216391|0.897555717001|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|신규 rounded-looking full-face union|1|4.05249095969 / 3.63880089209|0.080450718365|0.897917090571|4.95540788828|24.9859667213 / 23.5375931838|2.30217685964 / 2.10115028133|

## 원래 square의 동일8개 피부·접촉부담 (skin8)

|조건|각output nominal Vpp|ROI mean / P10 V/m|CV|P10/mean|ROI max V/m|surfaceP95 / complementP95 V/m|fullRMS mean / P10 V/m|
|---|---:|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.0618489416 / 3.64573573913|0.0807616216391|0.897555717001|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|신규 rounded-looking full-face union|0.982372542559|3.98105584777 / 3.57465808423|0.080450718365|0.897917090571|4.86805664662|24.5455276563 / 23.1226852617|2.26159533502 / 2.06411234417|

5개 모드는 raw 동일 nominal1Vpp, 동일 출력 RMS전류합, 동일 총 sourcepower, skin8, legacy다. skin8는 접촉 Jmax/J95·접촉전압·SC/접촉손실·SC+dermis 체적 vector Jmax/J95·SC+dermis 손실의 8개 수치 한도를 원래 square 기준으로 고정하고 sourcepower/1Vpp ceiling은 포함하지 않는다. legacy만 이 둘을 추가하고 동일 전류/전력도 1Vpp ceiling이 없다. 신규 skin8의 활성 limiter는 bulk_skin_J_vector_RMS_p95_A_m2(SC+dermis 체적 전체벡터 RMS P95)다. 접촉면 normalJ95와 다르다. 수치 제한은 인체 안전한계가 아니다.

각 모드에서 절대 ROImean/P10/CV/P10mean/max와 fixedTIS/RMS, wholeXY보조ROI, 표면·전체비표적P95, 고정 cutoff이상체적 및 전역 hotspot을 GUI/brief에 보존했다. SC층 전역최대를 목표 깊이로 오인하지 않는다.

## 신규8개 저장판정 (skin8)

|gate|단위|원래square|신규|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.0618489416|3.98105584777|-1.98907184867|FAIL|
|primary_maxTIS_p10|V/m|3.64573573913|3.57465808423|-1.94961072298|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.2592218317|24.5455276563|-2.82547966094|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.76652901786e-06|7.57938616071e-06|-2.40960738977|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|8.07932756696e-06|-1.58506974891|PASS|
|primary_complement_maxTIS_p95|V/m|23.4357185812|23.1226852617|-1.33571035367|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.93996552549e-05|1.9044910121e-05|-1.82861565983|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.11556556606e-05|2.07101582644e-05|-2.1058075599|PASS|

## 전류·접촉·전력·무부하 측정

접촉면 normalJ와 SC+dermis체적 전체 vectorJ, 접촉전압, SC/dermis/접촉/source50Ω/그룹sourcepower를 구분했다. legacy skin_power_W는SC+contact로 실제 modeled skin loss가 아니다. raw 각주파수의 저장된 signed group sourcepower와 손실을 그대로 보존했으며 개별 output signed source/metalpower는 이 volume/fullskin bundle에 없어 새로 계산하지 않았다. source sink/흡수 hardware 검증을 주장하지 않는다. 출력RMS전류합은 GND귀환전류가 아니다.

신규 raw square_3h의 공개 docs 복사 probe JSON은 source SHA와 일치하고 complete 40개 및 저장된 numerical checks all_passed를 확인했다. 깊이5/10/15/20 mm ×중심 및 X/Y±5 mm의5개 probe중심 ×X/Y 차동방향이며 tip gap은5 mm다. probe중심 위치와 tip gap은 구분한다. Vpp/RMS/방향별 기본파 envelope/스펙트럼/시간 파형은 원본 probe JSON에 보존돼 있다. 이 volume audit는 정규화별 새 probe40 계산 영수증을 발급하지 않았다. 원래 baseline은 과거 docs 검증 영수증을 재사용했고 native probe를 재개방하지 않았다. 모두 unloaded prediction이며 ETA5001/DSOX1202A 실제 attenuation switch·보정·팬텀 port impedance/부하·15MHz filter 검증이 없어 loaded 예측을 보류한다.

- `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, config SHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [raw unloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), source SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, config SHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [raw unloaded40](cloud-rounded-fullface-context-20261021T200000Z/completed-native-snapshot/postprocess/rounded-fullface225-xy80/probes.json), source SHA256 `6b0118b3cda87d31ed712d0c9e66bbd28e6bc68ab445d735c4c6c09924efe642`

## 실제 실행·보존·해석 범위

native/fullskin/register/volume/screen/GET/publish의 원래 7단계 모두 exit0이고 queue는 completed_preregistered_queue다. 새 native1조건/8RHS의 실제 wall 100.38368314599938 s, queue elapsed 117.05196724199777 s다. volume 단계 newPDE0은 새 solve가 없다는 의미이며 앞서 완료된 native1조건을 부정하지 않는다. publisher published_completed_batch, 2026-10-21T19:08:33.070468+00:00, commit 7c821016f7435844168c06e7de564b552ac942a5다.

완료 compact snapshot은 38파일/14747951 bytes의 producer inventory로 연결했다. 선택한 docs JSON/config/probe SHA만 검증했고 NPZ/grid/mask/binary/E/φ/native 디렉터리 내용은 열거나 다시 계산하지 않았다. full_complex_native_backup_verified=false이며 fullcomplex E/φ는 로컬에 남아 있다. compact checksum은 fullraw clean restore나 독립 persistentbackup 검증이 아니다. 로컬 배열 유실시 동일 source/config8RHS 재계산이 필요하며 원 native100.38368314599938s는 참고 비용이다. 원본·실패증거를 삭제하지 않았다.

과거 equal-circle225-coarse는 별개 hXY1.25 mm analytic-circle/partial-contact 후보다. 보존된 skin8 A=0.2022126402958491, ROImean=0.829581316283475 V/m, contact_voltage_RMS_max_V limiter를 역사 참조로만 연결한다. equal-rounded18-r3-coarse는 또 다른 geometry이므로 혼동하지 않는다. 새 fixed576-fullface union은 이 두 과거 도형과 동일하지 않으며 coarse-circle grid refinement 또는 partial-contact artifact 제거 입증이 아니다.

native5개 이산 방정식 gate와 저장된 primary-stat reproduction은 완료됐지만 SC/XY/bulk/전극 edge/contact/방향 수렴·실험·생리 활성화·인체 안전 검증으로 승격하지 않는다. PBS nominal 계면은 실제 피부 접촉 검증값이 아니다. COMSOL5.3a/예정5.3.1.201 설치·실행은 미검증이다. 새 물리 맵은 아직 완료 영수증이 없는 코드 준비 단계로 표시하며 과거 맵을 현재 형상 맵으로 부르지 않는다. 다음 c=0,+.01,+.025,+.05,−.01,−.025의 여섯 signed-weak drive는 root가 선택한 코드 준비 계획이고 실행 결과는 아직 없다. pure-sine fullROI 재현을 가정하지 않는다.

native source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`, volume implementation/preregistration `1b4db3c91128a3e8cd75dfe5c0203f3ae0f350b8`를 구분한다.

- [volume](cloud-rounded-fullface-context-20261021T200000Z/volume.json), SHA256 `95b1593cf23d2a539c57007f3909b56ba59692148768514fcae9b13dc65fd590`
- [screen](cloud-rounded-fullface-context-20261021T200000Z/screen.json), SHA256 `9fef9cc219d97f2c63fca8af4d02394983d0869b07e6b8183bf4b7cf52f49df9`
- [volume_plan](cloud-rounded-fullface-context-20261021T200000Z/volume-plan.json), SHA256 `4ee6fa1bce8ff4dee0534b95a879c30bdc147b95fce1df597b62c564f2c65398`
- [screen_plan](cloud-rounded-fullface-context-20261021T200000Z/screen-plan.json), SHA256 `1e3ed9c7a2e689c29b271a74a513775c03d52af6dbb79714f9681e376e373c6d`
- [decision](cloud-rounded-fullface-context-20261021T200000Z/decision.json), SHA256 `1802dd3c6a2b9b1b95741d1ce0cc4ad591ecf826e0e8edf9152e439d8c94181f`
- [queue_plan](cloud-rounded-fullface-context-20261021T200000Z/queue-plan.json), SHA256 `6e92db3bd25155e06f37141b3fa675f9bd233f4b5e6d190bc0002f02a7a24920`
- [completed_queue](cloud-rounded-fullface-context-20261021T200000Z/queue/summary.json), SHA256 `8017a98668cf2cacc513b48a45f02754aca9983d8575b1490c25ca1819582964`
- [publication](cloud-rounded-fullface-context-20261021T200000Z/rounded-fullface-publication-20261021T200000Z.json), SHA256 `96d7f839599c170f0a2251bd428629395f75a533187be1d508fc26f65ec549cc`
- [feedback_after](cloud-rounded-fullface-context-20261021T200000Z/feedback-after.json), SHA256 `93074ddd60fbbe81783b121866c31f141a573493e8b08a088b879d2b1cf609c5`
- [completed_snapshot_inventory](cloud-rounded-fullface-context-20261021T200000Z/completed-snapshot-inventory.json), SHA256 `5aff648ef397f41cbc624e4c41d6eb21f46140257fad7da668a0de2e4eb2a8e0`
- [geometry_proof](cloud-rounded-fullface-context-20261021T200000Z/completed-native-snapshot/geometry-audit/rounded-mask-proof.json), SHA256 `2dfb1256320fb88ebb6b580001281c66fd12d4546baf15e07c006772f8ece8ea`
- [physical_design](cloud-rounded-fullface-context-20261021T200000Z/completed-native-snapshot/geometry-audit/rounded-design.json), SHA256 `a2a210cb90eb58ff7df9c155fae1263a571ec50288c1927354746e2d7caa185c`
- [native_summary_snapshot](cloud-rounded-fullface-context-20261021T200000Z/completed-native-snapshot/summary.json), SHA256 `de1d24d40c673120d270368bcf3cb55e53c6e983b11809945b3c2787bb6f3c9e`
- [verified_baseline_snapshot](PERIMETER_SHELL_RESULTS_20261021.result-brief.json), SHA256 `3c09e2121db7d44387f6c4a2561ec0498207e9c12acda9ceda034f034fb57c5b`
- [historical_coarse_circle_volume](cloud-continuation-20261021/volume-remaining-coarse.json), SHA256 `c0512fc1b68a88bb2210221fadcf5d471c2362b491fbe19942b2c2c0771b90c9`
- [historical_coarse_circle_summary](cloud-resume-20261020/fourpad-coarse-results/equal-circle225-coarse-summary.json), SHA256 `dea658b3b34c0d6f130d14dac487c96617ec523f616b3f546127fa1650ee0680`

[이전 inward결과](CLOUD_PERIMETER_INWARD_RESULTS_20261021.html)와 [과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을 보존한다. 새 화면은2행 저장 JSON표이며 새 물리 fieldmap을 생성하지 않았다.
