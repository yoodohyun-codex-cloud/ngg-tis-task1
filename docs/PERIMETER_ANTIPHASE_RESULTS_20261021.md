# 작업1: Perimeter sine와negative-cross antiphase5조건 (2026-10-21)

새6조건은 **모두미채택**이다. sine는목표P10·표면P95만PASS, r0.05/0.1은목표mean/P10·표면P95만PASS, r0.2/0.5/1은목표mean/P10만PASS다. 모든신규조건에서표면고변조체적2개와전체비표적3개가실패했다. 단일지표증가나낮은CV만으로깊이집중성공을판정하지않는다.

[8행 오프라인GUI](CLOUD_PERIMETER_ANTIPHASE_RESULTS_20261021.html) · [정확한5모드/출처brief](PERIMETER_ANTIPHASE_RESULTS_20261021.result-brief.json) · [원본summary](cloud-perimeter-antiphase-20261021T190500Z/summary.json)

## 고정기하·회로와공통g

원래square와cachedperimetersquare는각225mm²×4=900mm²이나형상·위치가함께다르다. perimeter는576full-face steppedunion/각pad이며smootharc/convexhull/strictoutermost576아님, bboxcentre각축±13.125mm≠areacentroid±13.638237847222221mm, rim여유0.02344849663989379mm/gap3.75mm6cells·fixedphysicaloutline의미래grid reranking금지를유지한다. D50mm, SC/dermis/fat/muscle0.1/5/5/15mm·윗면, XY0.625/SC2/bulk14·14·40이다.

모든행은물리4pads/독립2outputs/공통GND50Ω, pad0→out0,pad1→out1,pad2·3→동일GND다. cachedsquare는3000/3030/9000/9090Hz4선, 신규sine/mix는3000/3030Hz2선·beat30Hz·고조파0이다. sine는각출력자기tone만, mix는두출력모두두tone을포함한다. 비구동주파수는0V through50Ω이며초기2/2.01kHz기록과별도다.

seedcommandmatrix는`-i[[1,-r],[-r,1]]`이며하나의공통g만사용해raw실제전체source파형Vpp upper의최대만1Vpp로맞췄다. 각출력이정확히1Vpp인것은아니며출력별독립column정규화를하지않았다. raw검증은신규6행의전체파형max−min bracket폭≤1µV이며단일toneVpp나2√2RMS로대체하지않는다. cached2행은과거nominalscalar와upstream영수증으로새파형bracket검증이아니다. pure sine는exact1Vpp별도대조군이다.

seed common/differential weights는1−r/1+r, 새K=+r²·이전unitaryfamily K=−r²다. r<1은difference-mode enriched이며r=1만rank1 pure differential command다. commandrank1이어도독립물리출력2개·물리패드4개·공통GND는그대로다. r1의netGND전류상쇄는localGND J/절대patch전류적분=0을뜻하지않는다. 관련저장값은5모드마다peak양으로GUI에표시했고RMS전류와구분했다.

## raw: max source full-Vpp upper1Vpp

|조건|source Vpp: 신규actual bounds / cached nominal|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1 Vpp/output|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached perimeter square3h|cached nominal 1 Vpp/output|3.683420745 / 3.373850513|0.06437681876|4.308663569|17.00506951 / 23.33228047|2.085126023 / 1.950512172|
|perimeter-sine-control|[[1.0, 1.0], [1.0, 1.0]]|3.472762382 / 3.180896769|0.06437681876|4.06224697|16.03253329 / 21.99788499|1.866462474 / 1.746058681|
|perimeter-antiphase-r0p05|[[0.9999992611357055, 1.0], [0.9999991154390689, 0.9999998677272894]]|3.494336012 / 3.21526989|0.06153425598|4.062266771|15.07878331 / 23.23202349|1.86442221 / 1.744492227|
|perimeter-antiphase-r0p1|[[0.9999992604899567, 0.9999999999999999], [0.9999989819642251, 0.9999997336136647]]|3.514123084 / 3.244145665|0.05917535379|4.062285754|15.57076847 / 23.44634417|1.862743402 / 1.742551655|
|perimeter-antiphase-r0p2|[[0.999998736645279, 0.9999994772842005], [0.9999992494696535, 1.0]]|3.54915797 / 3.292801242|0.05561256986|4.06231241|19.20728427 / 25.82203903|1.860206614 / 1.740799479|
|perimeter-antiphase-r0p5|[[0.9999989361569032, 0.9999996792762822], [0.9999992519348577, 1.0]]|3.628078588 / 3.394379512|0.05063183619|4.062353965|31.11725999 / 33.14083668|1.856440148 / 1.737911799|
|perimeter-antiphase-r1|[[0.9999992544051027, 1.0], [0.9999992544051027, 1.0]]|3.709382192 / 3.472763969|0.04989131179|4.063373812|44.83864382 / 41.61197273|1.855182539 / 1.737281555|

## 동일8개피부·접촉부담 (skin8)

|조건|source Vpp: 신규actual bounds / cached nominal|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1 Vpp/output|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached perimeter square3h|cached nominal 1.030042389 Vpp/output|3.794079503 / 3.475209043|0.06437681876|4.438106116|17.51594243 / 24.03323792|2.14776819 / 2.009110218|
|perimeter-sine-control|[[1.1596127942731396, 1.1596127942731396], [1.1596127942731396, 1.1596127942731396]]|4.027059689 / 3.688608591|0.06437681876|4.71063356|18.59153073 / 25.50902888|2.164373765 / 2.024751986|
|perimeter-antiphase-r0p05|[[1.216646512544186, 1.2166474114815176], [1.2166463352827506, 1.2166472505522667]]|4.251374864 / 3.911849789|0.06153425598|4.942346352|18.34556269 / 28.26518124|2.268344455 / 2.122431952|
|perimeter-antiphase-r0p1|[[1.2732040350381923, 1.2732049765860596], [1.2732036804178448, 1.273204637421652]]|4.474198999 / 4.130462406|0.05917535379|5.172122438|19.82477991 / 29.85200209|2.371654169 / 2.218625439|
|perimeter-antiphase-r0p2|[[1.3631088317484095, 1.3631098413211398], [1.3631095307847265, 1.3631105538405628]]|4.837894687 / 4.488452125|0.05561256986|5.53738092|26.18165191 / 35.19829392|2.535667268 / 2.372902142|
|perimeter-antiphase-r0p5|[[1.538472684061462, 1.538473827331544], [1.538473169877736, 1.5384743207567477]]|5.581705742 / 5.222165714|0.05063183619|6.249827257|47.87310543 / 50.98632621|2.856085496 / 2.673732674|
|perimeter-antiphase-r1|[[1.616087167504658, 1.616088372451902], [1.616087167504658, 1.616088372451902]]|5.994689429 / 5.612293471|0.04989131179|6.566771171|72.46321092 / 67.24862529|2.998138929 / 2.807600521|

신규6조건의skin8활성limiter는`bulk_skin_J_vector_RMS_p95_A_m2`다. actualsourceupper가1.16~1.62Vpp로1Vpp를넘으므로skin8의목표증가를raw동일전압gain으로표현하지않는다. skin8는 원래 square의 접촉Jmax/J95·접촉전압·SC/접촉손실·SC+dermis체적vectorJmax/J95·SC+dermis손실의8개수치한도이며 sourcepower/1Vppceiling은 없다. legacy만이둘을추가하고동일전류/전력에도1Vpp상한은없다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드에서절대mean/P10/CV/P10mean/max·wholeXY보조ROI·표면/전체비표적P95·고변조체적·전역hotspot을보존했다. 수치한도는인체안전한계가아니다.

ROI는중심r≤5mm·깊이15–20mm,+z안쪽,x/y수평이다. 모든전기장V/m,CV/P10mean은무차원이다. maxTIS는기본파2074방향표본최대(연속방향최대의하한), fixedTIS는(X+Y)/√2기본파변조, fullRMS는 각 행의활성선전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/기존staircasegeometry와원래square rawcutoff를유지했다. SC전역최고값을깊이집중으로해석하지않는다.

## 개별저장8gate (원래square기준)

### perimeter-sine-control

|gate|단위|기준|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|4.027059689|-0.8564880822|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.688608591|1.175972547|PASS|
|surface_0_5_maxTIS_p95|V/m|25.25922183|18.59153073|-26.39705668|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.764207589e-06|25.72163919|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.778191964e-06|19.10893229|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|25.50902888|8.846796372|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|2.144272822e-05|10.53149108|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.359968862e-05|11.55262213|FAIL|

### perimeter-antiphase-r0p05

|gate|단위|기준|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|4.251374864|4.666001245|PASS|
|primary_maxTIS_p10|V/m|3.645735739|3.911849789|7.299323607|PASS|
|surface_0_5_maxTIS_p95|V/m|25.25922183|18.34556269|-27.37083189|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.770066964e-06|25.79708312|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.785044643e-06|19.19240531|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|28.26518124|20.60727364|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|2.239003931e-05|15.41462471|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.567750026e-05|21.3741643|FAIL|

### perimeter-antiphase-r0p1

|gate|단위|기준|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|4.474198999|10.15178218|PASS|
|primary_maxTIS_p10|V/m|3.645735739|4.130462406|13.29571592|PASS|
|surface_0_5_maxTIS_p95|V/m|25.25922183|19.82477991|-21.51468464|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.79578683e-06|26.12824607|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.801741071e-06|19.39578584|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|29.85200209|27.3782239|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|2.432409014e-05|25.38413607|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.824243954e-05|33.49829471|FAIL|

### perimeter-antiphase-r0p2

|gate|단위|기준|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|4.837894687|19.10572639|PASS|
|primary_maxTIS_p10|V/m|3.645735739|4.488452125|23.11512535|PASS|
|surface_0_5_maxTIS_p95|V/m|25.25922183|26.18165191|3.651854678|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.749280134e-06|25.52943679|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.781305804e-06|19.14686222|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|35.19829392|50.19080297|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|2.818748837e-05|45.29891382|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|3.217093006e-05|52.06775234|FAIL|

### perimeter-antiphase-r0p5

|gate|단위|기준|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|5.581705742|37.4178563|PASS|
|primary_maxTIS_p10|V/m|3.645735739|5.222165714|43.24037965|PASS|
|surface_0_5_maxTIS_p95|V/m|25.25922183|47.87310543|89.52723781|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.179916295e-06|18.19844197|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.340742188e-06|13.78032185|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|50.98632621|117.5581945|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|3.492149367e-05|80.0108982|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|3.867059105e-05|82.79079443|FAIL|

### perimeter-antiphase-r1

|gate|단위|기준|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|5.994689429|47.58523803|PASS|
|primary_maxTIS_p10|V/m|3.645735739|5.612293471|53.94131314|PASS|
|surface_0_5_maxTIS_p95|V/m|25.25922183|72.46321092|186.8782396|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.312751116e-06|19.90879188|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.382734375e-06|14.29183202|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|67.24862529|186.9492781|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|3.931802408e-05|102.6738288|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|4.260450148e-05|101.3858713|FAIL|

## nativephi40·signedpower·검증범위

새sine fullROI/volumeNPZ·40phi는이번worker에서계산했고, cachednativepost sine electrical/contact/centre-field regression만별도로PASS/error0이다. 과거sine fullROI NPZ복원검증으로표현하지않는다. 신규6조건×5모드각40개의nativephi무부하예측은condition JSON의`normalizations/.../probe40_unloaded`에보존했다. 깊이5/10/15/20mm ×중심·X/Y±5mm의5개중심 ×X/Y차동방향이며tipgap5mm다. probe중심간격과팁간격은다르다. rawJSON은전체파형Vpp bounds/RMS/기본파envelope·스펙트럼·저장검사와연결된다. cached2행은upstreamraw40영수증이며이번에nativeprobe를열거나정규화영수증을재발급하지않았다.

접촉surfaceJ와SC+dermis 체적 vectorJ, 접촉전압, SC/contact/SC+dermis/sourcepower를구분했다. signedpower는주파수·출력별합계·그룹총전력을별도로보존하고음수및9000/9090Hz비활성0계수/0전력선을제거하지않았다. sourceRMS합과netGND전류·localJ를혼동하지않는다. 실제AWG두tone·위상동기·흡수/sink/compliance는미검증이다. ETA5001/DSOX1202Aactualswitch·팬텀portimpedance/부하·보정이미검증이므로loaded예측은보류다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json), SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `perimeter-shell225-notch-xy80` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](../data-native/cloud-perimeter-shell-20261021T185000Z/postprocess/perimeter-shell225-notch-xy80/summary.json), SHA256 `fbbe40074b2219d09607a588ca8b31b35337449459b2eeb19cbb0d74b7c35252`
  - [rawunloaded40](../data-native/cloud-perimeter-shell-20261021T185000Z/postprocess/perimeter-shell225-notch-xy80/probes.json), SHA256 `da6ff0f59e36827fce26f3e418fb52a0073d44f0df488cfa576a8e67254b31ed`
- `perimeter-sine-control` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-antiphase-20261021T190500Z/perimeter-sine-control/condition.json), SHA256 `3dede22f87154634dd375471d75597021298c73677b8923b323ee6aab9d95bda`
  - [rawunloaded40](cloud-perimeter-antiphase-20261021T190500Z/perimeter-sine-control/probes.json), SHA256 `c72a344898d5e6ef28908cf6b30c6a01d20b656690477dabdb4dd5803ec44d58`
- `perimeter-antiphase-r0p05` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p05/condition.json), SHA256 `25ce95c8be3cfd7aca84295c0a3698a694574f72824cc0bd3d88afe9fe4f022a`
  - [rawunloaded40](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p05/probes.json), SHA256 `2aaf4a3c10c2375261e1dadcfefc304c870f999b8f0eea1bc3c8a7f50f9c32d5`
- `perimeter-antiphase-r0p1` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p1/condition.json), SHA256 `5ee213287e1e714889cdc764ddc3f0de44f1e3ff8f4aa2a38785e05dec3f92c9`
  - [rawunloaded40](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p1/probes.json), SHA256 `7eaf23e925d4e2a6d0de68f52ca2afb67f2a91fa72a6e22511d3b445554f8f4e`
- `perimeter-antiphase-r0p2` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p2/condition.json), SHA256 `75bb3a0ecf924ced08ba437d2db5b54e9070bcb69f68a6137739cec6275114f5`
  - [rawunloaded40](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p2/probes.json), SHA256 `43440e7cbe7064aea41869a0b352ee7630f6dd66cf830bd62be9792a69d6f8b2`
- `perimeter-antiphase-r0p5` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p5/condition.json), SHA256 `3e3a0551cc085666d078b34acec11257e795adb2527a05d6f16af332541257af`
  - [rawunloaded40](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r0p5/probes.json), SHA256 `4aae4dab2cb9af646c5446fba34481e26308f921716ce6fecbae021e2f9fcd0e`
- `perimeter-antiphase-r1` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r1/condition.json), SHA256 `b1418edc13ff7fd8f452467ea23fc75322607be47acb23162021e4db75c27363`
  - [rawunloaded40](cloud-perimeter-antiphase-20261021T190500Z/perimeter-antiphase-r1/probes.json), SHA256 `1e248705ced7a762906e6f7f31a8888cddd5af4cbffee138737d4b7f8826e1f0`

physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`, native source `257d56bc7300efaf691d2f017369b29065a7edf0`, scout implementation/preregistration `8890790d8c0e06119e87ddefe3cf6482cfcec97b`를구분한다. 이번문서생성은docs JSON만읽었고data-native파일·E/phi/NPZ를열거나재해시하지않았다. cachedsource/probe/config SHA는검증된과거docs snapshot의upstream영수증으로현재native재검증을주장하지않는다. localnative링크는공개archive완료를보장하지않는다. JSON해시검증과시뮬레이션재현·수렴·실험검증을구분한다.

## 실제실행·발행과 완료된 direction supplement

actualwall `62.80328225899575s`, CPU1, peakRSS `541495296bytes`, 새PDE0이다. 큐`completed_preregistered_queue`의계산/GET/발행3단계exit0, 발행`published_completed_batch`, `2026-10-21T18:31:16.143668+00:00`, commit `0cdcb85d28af3f6d0b6bc991f4e6db616a60c511`다.

native방정식·파형검사와8gate는SC/XY/bulk/edge/contact·방향수렴·실험검증이아니다. PBSnominal계면을실제피부검증값으로취급하지않는다. C1/생리적활성동등성/인체안전/COMSOL5.3a검증을새로주장하지않는다. 이전exclusive-square amplitude bound도다른perimeter/negative-cross family를배제하지않는다.

방향 보조 audit는 [실제 완료 summary](cloud-direction-bounds-20261021T191000Z/summary.json)의 `calculated_supplemental_unadopted`이다. 8조건, wall `54.90790198100149s`, [발행 영수증](cloud-direction-bounds-context-20261021T191000Z/publication.json) `2026-10-21T18:45:36.943473+00:00`, commit `7a8341f07cc686d250f5fad65b8c1331843eaa05`에 연결한다. 등록 decision의 `selected_not_executed`는 당시의 역사적 상태다. 이 문서의 주 표에 있는2074방향 값·기존8gate·5정규화·40probe는 그대로 두었고, 보조 audit 수치를 재계산하거나 병합하지 않았다. 링크 연결만으로 연속방향 최적값·전체 격자/접촉 수렴·채택을 주장하지 않는다.

- [summary](cloud-perimeter-antiphase-20261021T190500Z/summary.json), SHA256 `8348af42e9ebd1b77fc48f3d7b0b6fc5c91f37e86929b73dfef99c6015746e93`
- [preregistration](cloud-perimeter-antiphase-context-20261021T190500Z/preregistration.json), SHA256 `33c5a3a5b65d53ab734e36da50b99af136593f0e479798dbb5759fd176673fe2`
- [queue](cloud-perimeter-antiphase-context-20261021T190500Z/queue/summary.json), SHA256 `7555556e2db8d22b31b13d1ea99e549b6c3998d8652b4b252d9db5ba320166fa`
- [publication](cloud-perimeter-antiphase-context-20261021T190500Z/antiphase-publication-20261021T190500Z.json), SHA256 `8037cc3d497fc6586b093a7cc8f1f5ad8fe94bf5d744357a1a40d6cec726cf80`
- [decision](cloud-perimeter-antiphase-context-20261021T190500Z/decision.json), SHA256 `60f71ded12c7a391909bd3537b01e9810d6bd4f1da6ae95f0bc19ff8a7b58adb`
- [feedback_after](cloud-perimeter-antiphase-context-20261021T190500Z/feedback-after.json), SHA256 `8767b13837245237bbf0e7722b4bd5729523a730f3ce06ddcda9fc6e3b330987`
- [cached_volume](cloud-perimeter-shell-context-20261021T185000Z/volume.json), SHA256 `60e19c019800cd3b958dda4f183254dcc3687743314ea6016e1fcc0f28987564`
- [verified_perimeter_snapshot](PERIMETER_SHELL_RESULTS_20261021.result-brief.json), SHA256 `3c09e2121db7d44387f6c4a2561ec0498207e9c12acda9ceda034f034fb57c5b`
- [direction_registration_history](cloud-direction-bounds-context-20261021T191000Z/decision.json), SHA256 `1153be594145db6aa57fb4b337817d5b139a503c9ad95d01d3923d5bbe3ccffd`

[이전perimeter square2행GUI](CLOUD_PERIMETER_SHELL_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다. 이번화면은새물리공간맵을생성하지않은정적오프라인JSON표다.

- [direction_supplemental_summary](cloud-direction-bounds-20261021T191000Z/summary.json), SHA256 `130def5cf8035fdfbf5b157b5322448ee3027be9a08afe94fb83f37fd76b882e`
- [direction_supplemental_publication](cloud-direction-bounds-context-20261021T191000Z/publication.json), SHA256 `0c70fe157904cd66c1afc9661e1dc34272f19759bd7d8cd351520d1898101dc9`
