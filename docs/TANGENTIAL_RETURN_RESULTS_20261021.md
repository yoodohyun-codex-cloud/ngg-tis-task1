# 작업1: 두 공통GND 귀환 패드의 접선 이동 (2026-10-21)

신규 `asym-return-tangent4p375-xy80`는 **채택하지 않는다**. raw 목표 평균만 보면 원래 square보다 높지만, 동일8개 피부·접촉 부담(skin8)에서는 contact power 한도로 source를 줄여 목표 평균·P10이 원래 기준에 미달했다. 저장된8개 gate가 전부 FAIL이다. raw 한 점·한 평균의 증가를 깊이 집중 성공으로 판정하지 않는다.

[3행 오프라인GUI](CLOUD_TANGENTIAL_RETURN_RESULTS_20261021.html) · [정확한5모드/출처brief](TANGENTIAL_RETURN_RESULTS_20261021.result-brief.json) · [volume](cloud-tangential-return-context-20261021T183000Z/volume.json) · [신규8gate](cloud-tangential-return-context-20261021T183000Z/screen.json)

## 변경 변수와 고정 조건

원래 square는225 mm²×4의 별도 기하다. cached 비대칭 부모→신규에서는 source pad0·1, 모든 패드 면적·형상·방향, 물성·접촉·회로·구동을 유지하고 GND pad2·3의 위치만 바꿨다. GND2(+10,−10)→(+14.375,−5.625) mm, GND3(−10,+10)→(−14.375,+5.625) mm다. 각 x/y성분±4.375 mm, 격자 index±7/±7이며 물리적 회전0°다. 두차원 이동 길이를4.375 mm로 혼동하지 않는다.

부모/신규 총900 mm², 면적281.25/281.25/168.75/168.75 mm², fullfaces720/720/432/432이다. partialfaces0, clipping·재정규화 없음이다. 최소 간격1.25 mm는XY2셀뿐으로 가장자리·접촉 수렴이 확인되지 않았다. [translation mask proof](../data-native/cloud-tangential-return-20261021T183000Z/geometry-audit/translation-mask-proof.json)를 보존한다.

D50 mm, SC/dermis/fat/muscle0.1/5/5/15 mm·윗면 부착, XY0.625/SC2/bulk14·14·40/351680 cells이다. 물리4패드/독립2출력/공통GND/50 Ω, pad0→out0(3000/9000Hz), pad1→out1(3030/9090Hz), pad2·3→동일GND다. private isolated return pair가 아니다. 다른 주파수 출력단은0V through50Ω, sourcephase0°/0°, 기존square_3h nominal1Vpp/fullwave before50Ω 정의를 유지했다. 표의sourceVpp는 기존 정의의nominal scalar이며 새하드웨어파형bracket 검증이 아니다. 초기2/2.01kHz 기록과 별도로 추적한다.

기본ROI는 중심r≤5mm·깊이15–20mm, x/y수평·+z안쪽이다. maxTIS는 기본파2074방향 표본 최대(연속방향 최대의하한), fixedTIS는(X+Y)/√2 기본파변조, RMS는4개선 전체벡터전기장 RMS다. fractional ROI/exactzoverlap·가중ECDF·기존staircase geometry를 유지하고 이상원기둥체적으로 재정규화하지 않았다. SC경계의 전역최대를 깊이집중으로 해석하지 않는다.

## 원시 동일 nominal1Vpp

|조건|각출력 nominal Vpp|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached 비대칭 부모|1|4.429044834 / 3.992962997|0.07877015215|5.37867676|32.51829281 / 26.14771614|2.488872983 / 2.267825135|
|GND2·3 접선 이동 (신규)|1|4.329672014 / 3.903911826|0.07821389998|5.232478229|34.2349448 / 27.09121427|2.424152724 / 2.208395351|

## 원래square의 동일8개 피부·접촉부담 (skin8)

|조건|각출력 nominal Vpp|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached 비대칭 부모|0.9897266671|4.383543782 / 3.951941959|0.07877015215|5.323419823|32.18422156 / 25.87909195|2.463303962 / 2.244527012|
|GND2·3 접선 이동 (신규)|0.9211900933|3.988450966 / 3.596244899|0.07821389998|4.820107108|31.53689199 / 24.9561582|2.233105474 / 2.03435192|

신규 skin8의활성limiter는 `contact_power_W`다. 원래 square 기준은 평균4.0618489416/P103.64573573913V/m인데, 신규의절대목표값은 source0.9211900933nominalVpp에서 mean3.98845096637/P103.59624489933V/m로 낮아진다. 부모대비전압/부담이달라지는점을 분리하고, raw평균4.32967201393만보고 개선이라하지않는다.

skin8는 접촉Jmax/J95·접촉전압·SC/접촉손실·SC+dermis체적vectorJmax/J95·SC+dermis손실의8개수치한도이며sourcepower/1Vppceiling을포함하지않는다. legacy만이둘을추가한다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드에서절대ROImean/P10/CV/P10mean/max, wholeXY보조ROI, surface/complementP95, 고변조체적·전역hotspot을GUI/brief/원본에보존했다. 모든전기장단위V/m, CV·P10mean은무차원이다. 수치한도는인체안전한계가아니다.

## 신규후보의8개 저장판정

|gate|단위|원래square|신규|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.988450966|-1.807008983|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.596244899|-1.357499373|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|31.53689199|24.8529832|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|8.094313616e-06|4.220477352|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|8.417254464e-06|2.531244605|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|24.9561582|6.487702137|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|1.983564771e-05|2.247423737|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.145794132e-05|1.428864505|FAIL|

기준cutoff는 원래square raw ROI mean/P10으로 고정했다. cached부모·기준을이번에새로심사한것으로표시하지않았고gate를재계산하지않았다.

## 전류·손실·프로브와검증범위

접촉surfaceJ와SC+dermis체적전체vectorJ는별도다. 접촉전압/SC/contact/SC+dermis/sourcepower와출력별RMS전류를5모드모두보존했다. sourcepower는그룹총합이며출력RMS전류합은공통GND귀환전류와동일하지않다. 기존PBS Rs500fit/500Hzwindow의Rs236.5717747232937Ω1회차감·1cm²면적1회정규화를유지했다. 실제피부접촉으로검증된값은아니다.

각조건의raw square_3h nativephi무부하40개를연결했다. 깊이5/10/15/20mm ×중심·X/Y±5mm의5개probe중심 ×X/Y차동방향이며tipgap5mm다. probe중심위치·중심간격과팁간격을구분한다. 복소전위두점차의전체파형Vpp/RMS/변조·스펙트럼및저장수치검사는원본JSON에있다. 이volume audit는5모드별새probe영수증을발급하지않았다. ETA5001/DSOX1202Aactualswitch·팬텀portimpedance/부하·보정이미검증이므로loaded예측은보류다. 최신별도C1은이전회전coherent reference의비교이며새접선후보의C1로재명명하지않는다.

- `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, config SHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `asym-cross281p25-return168p75-xy80` / run `cloud-asymmetric-20261021T051000Z`
  - source `713c35c95114f7e478e04f5ada35d7efbfe49156`, config SHA256 `12afd425530b37dc0e7ab4f941d279277d00e23d3d3dd6acf81cc8fbdb98c584`
  - [rawunloaded40](../data-native/cloud-asymmetric-20261021T051000Z/postprocess/asym-cross281p25-return168p75-xy80/probes.json), SHA256 `2de7724b4bb29d9d91bfaa0291d3da3f1a25832f1d8abd7abf81bf77cf9eee12`
- `asym-return-tangent4p375-xy80` / run `cloud-tangential-return-20261021T183000Z`
  - source `83b03e2b5b85a0a4a78738579ad2fa8cf2b5d7fb`, config SHA256 `d6685d10e32df4bc399440c68018744bca5e86b9fd4c128be18d7924b0ef5ab8`
  - [rawunloaded40](../data-native/cloud-tangential-return-20261021T183000Z/postprocess/asym-return-tangent4p375-xy80/probes.json), SHA256 `6b63c9fd9384146938278efb1ed45581889594c6cda4e19471d0bd9230e8ea3b`

physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`이며native source `83b03e2b5b85a0a4a78738579ad2fa8cf2b5d7fb`, volume implementation/preregistration `57a939480d684e775351a452c5bac475a32b03f8`를구분한다. native5개이산방정식검증은통과했지만SC/XY/bulk/edge/contact·방향수렴과실험검증을승격하지않는다. 최소2셀간격은별도edgehold다. 원시native/probe snapshots는현재로컬보관이며모두공개됐다고가정하지않는다. 문서작성은JSON/설정해시확인과저장값복사만했고E/phi/NPZ배열을읽거나재계산하지않았다. 파일해시검증과시뮬레이션재현·수렴·실험검증을구분한다.

## 실제실행·발행

새native조건1개·4주파수×2출력=8RHS의완료영수증이있다. native실행summary wall `119.5676372720045 s`,7단계큐elapsed `140.34181137300038 s`, `completed_preregistered_queue`,전단계exit0이다. volume audit의`new_PDE_solves=0`은앞선새native조건1개와다른단계의통계다. 발행 `published_completed_batch`, `2026-10-21T18:08:35.646838+00:00`, commit `84fe05ecab1ddb2a7efff01cb349637fa57d5691`다. COMSOL5.3a/예정5.3.1.201설치·실행가능성은미검증상태를유지한다.

- [volume](cloud-tangential-return-context-20261021T183000Z/volume.json), SHA256 `628d317157a0acd2d002a72221fa4c64ea3357889255b42727405e0f1b981d93`
- [screen](cloud-tangential-return-context-20261021T183000Z/screen.json), SHA256 `3bd6bd621f12db41f46347abf8dd7a7fd9f884cbf67ae808d545f0c529a5d8c2`
- [volume_plan](cloud-tangential-return-context-20261021T183000Z/volume-plan.json), SHA256 `59c95cc8bc9ce97fa4625dabb1869a6f80006acd284f9d3c4a44fdb829634955`
- [screen_plan](cloud-tangential-return-context-20261021T183000Z/screen-plan.json), SHA256 `3457b86dc8ca72d2e9757e70e06393d9deb37032259ef4cb8448822e62c18fe6`
- [decision](cloud-tangential-return-context-20261021T183000Z/decision.json), SHA256 `8dcf40425e7f80557582203862162fdb33f3a1265a4b8ebc5360ebfadc7f835f`
- [queue](cloud-tangential-return-context-20261021T183000Z/queue/summary.json), SHA256 `115bb995442d9fc92ac7e4fc6adb2162d19ae0e16f4a82a592001ede66e563f9`
- [publication](cloud-tangential-return-context-20261021T183000Z/tangential-return-publication-20261021T183000Z.json), SHA256 `896a81675a50051a1b09746398ea6c8a112a115f118c6f0ba59420df8159e383`
- [feedback_after](cloud-tangential-return-context-20261021T183000Z/feedback-after.json), SHA256 `dcebae851b5d06ba34270c82cabe52bed25cff177f4240fd541594fc2c032a18`
- [native_summary](../data-native/cloud-tangential-return-20261021T183000Z/summary.json), SHA256 `8d2278944ee6051604c2fb4f031fa60ae8725edf126c5878690dcd8daf63a9ec`
- [native_preregistration](../data-native/cloud-tangential-return-20261021T183000Z/preregistration.json), SHA256 `a302a5be4a241106dcbcbd33c3e8eeb8c095dbf6ad974ee7d5e9682fada8d8b6`
- [geometry_translation_proof](../data-native/cloud-tangential-return-20261021T183000Z/geometry-audit/translation-mask-proof.json), SHA256 `fdfeb4076ea38c07244ea019e9a3738bbebbc2002432331316e642fd56eba1a8`

[이전한귀환회전GUI](CLOUD_ONE_RETURN_ROTATION_RESULTS_20261021.html), [과거회전coherent C1](CLOUD_ROTATION_COHERENT_SINGLE_PAIR_RESULTS_20261021.html), [과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다. 이번화면은새물리공간맵을만들지않은오프라인JSON표다. 다음후보가실행됐다고이보고서에서주장하지않는다.
