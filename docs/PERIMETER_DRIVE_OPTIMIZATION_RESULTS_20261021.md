# 작업1: Perimeter 5-gene 유한 drive 최적화 (2026-10-21)

4개 full final 후보는 **모두미채택**이다. 원래square skin8에서목표ROI mean/P10이전부실패했다. 076후보는complementP95와고변조체적2개를통과했지만목표미달을해소하지못한다.124개proxy ranking을full2074검증·전계열global최적화증명으로표현하지않는다.

[6행 오프라인GUI](CLOUD_PERIMETER_DRIVE_OPTIMIZATION_RESULTS_20261021.html) · [정확한5모드/출처brief](PERIMETER_DRIVE_OPTIMIZATION_RESULTS_20261021.result-brief.json) · [원본summary](cloud-perimeter-drive-optimization-20261021T192000Z/summary.json) · [proxy-search](cloud-perimeter-drive-optimization-20261021T192000Z/proxy-search.json)

## proxy124와full2074 final4의구분

proxy는26개고정실수방향targetmean/P10 하한과9개λ의Gershgorin off-target 상한을사용한다. λ=0,1/8,…,1이며고유값계산이아니다. exact8skin/contactburden은cachednative이산모델에서평가했지만proxy는whole-sourceVpp정규화를하지않았고raw1Vpp를주장하지않는다. 보수적인상한이나빠도실패증명은아니다. 이실행에서124개proxy를완료했고4개만전체native scalar/2074방향·40phi로평가했다. 과거6개full2074 alias를새proxycache또는새full계산6개로세지않았다.

유한탐색genes는 `[z0_real,z0_imag,z1_real,z1_imag,rho]`, 앞4개범위[-1,1],rho∈[0.5,2],steps0.25/0.125/0.0625,4개seed·최대124평가다. 전공간전수탐색/전역최적/전체family의불가능성을주장하지않는다. 아래gene실수값은JSON에저장된그대로보존한다.

|final|proxy평가index|exactgenes|final공통g|저장proxyobjective(ranking전용)|
|---|---:|---|---:|---|
|perimeter-opt-3b8b3153d641|102|[0.2, 0.0, -0.05, 0.0, 0.8125]|0.9523855946281081|[0.1494792803054322, 0.8584481068880778, -3.1007737842955265]|
|perimeter-opt-076db2f87da8|85|[0.1875, 0.0, 0.0, 0.0, 0.75]|0.9999999999999929|[0.1561383622187943, 0.7138731126527816, -3.104908712793425]|
|perimeter-opt-0cc5736e7eb4|105|[0.1875, 0.05, 0.0, 0.05, 0.75]|0.9523855946281081|[0.17164213411534762, 0.8460132810611204, -3.1140285079250076]|
|perimeter-opt-81b82881db5c|99|[0.2, 0.0, 0.012499999999999997, 0.0, 0.875]|0.930249041618202|[0.1730364471974879, 0.8658397810763614, -3.0148905790445077]|


## 고정기하·source·지표

물리4pads/독립2outputs/공통GND50Ω, pad0→out0,pad1→out1,pad2·3→동일GND다. 각225mm²/총900mm². perimeter는576full-face고정steppedunion/각pad로원래square와형상·위치가함께다르다. smootharc/convexhull아님,동일fixedoutline의후속grid reranking금지,bboxcentre±13.125mm≠centroid±13.638237847222221mm,rim0.02344849663989379mm/gap3.75mm6cells의edge/contacthold를유지한다. D50mm/층SC·dermis·fat·muscle0.1·5·5·15mm/윗면/XY0.625SC2bulk14·14·40이다.

cachedsquare는3000/3030/9000/9090Hz4선,새final은3000/3030Hz2선·beat30Hz·고조파0이다. sourcecomplexseed와정규화후vector는brief/condition에보존했다. 다른주파수는0Vthrough50Ω,초기2/2.01kHz기록과별도다. final은하나의공통g로전체source파형Vpp upper최대만1Vpp로정규화하고출력별독립column정규화를하지않았다. 각출력이정확히1Vpp인것은아니며rawbracket폭≤1µV/sourcepeakbasis0.5V/50Ω앞wholewave정의를보존했다. cached2행은과거nominalscalar·upstream영수증으로새bracket검증이아니다.

기본ROI중심r≤5mm·깊이15–20mm,+z안쪽,x/y수평이다. 전기장V/m,CV/P10mean은무차원이다. 주표는full2074표본maxTIS(연속방향최대의하한),fixedTIS는(X+Y)/√2 기본파변조,RMS는각행의활성선전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/staircasegeometry와원래square cutoff를유지하며SC전역최대를깊이집중으로해석하지않는다. **새4개final의native volume XYZ modulation archive는미생성**이다. fixeddiagonal/2074maximum archive만제공되며과거8조건direction audit를새4개후보의XYZ로재명명하지않는다.

## raw: max whole-source Vpp upper≤1

|조건|source Vpp: 신규actual bounds / cached nominal|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1 Vpp/output|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached perimeter square3h|cached nominal 1 Vpp/output|3.683420745 / 3.373850513|0.06437681876|4.308663569|17.00506951 / 23.33228047|2.085126023 / 1.950512172|
|perimeter-opt-3b8b3153d641|[[0.9999992611357055, 1.0], [0.9642716843431327, 0.9642724076191167]]|2.705886252 / 2.366586411|0.08736253765|3.239143675|18.75879699 / 19.08657928|1.482568163 / 1.383856107|
|perimeter-opt-076db2f87da8|[[0.9999999999999929, 1.0], [0.9374815978281292, 0.9374823009753414]]|2.654713996 / 2.407536614|0.07058229809|3.141231716|18.92357453 / 17.87828708|1.464273227 / 1.359943232|
|perimeter-opt-0cc5736e7eb4|[[0.9999992611357055, 1.0], [0.8990734368992274, 0.8990741111727367]]|2.536287573 / 2.302836963|0.06994476457|2.996968852|18.29948223 / 17.06237825|1.397386473 / 1.298066824|
|perimeter-opt-81b82881db5c|[[0.9418754543496629, 0.9418761497727413], [0.9999992497559866, 1.0]]|2.630221297 / 2.31157921|0.08608126991|3.155160134|18.84067263 / 18.87679136|1.449525 / 1.354528082|

## 원래square의동일8개피부·접촉부담 (skin8)

|조건|source Vpp: 신규actual bounds / cached nominal|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1 Vpp/output|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached perimeter square3h|cached nominal 1.030042389 Vpp/output|3.794079503 / 3.475209043|0.06437681876|4.438106116|17.51594243 / 24.03323792|2.14776819 / 2.009110218|
|perimeter-opt-3b8b3153d641|[[1.3238826254303797, 1.3238836036007045], [1.2765834723183076, 1.2765844298515236]]|3.582278442 / 3.133084946|0.08736253765|4.288249201|24.83446376 / 25.26840936|1.962747682 / 1.83206441|
|perimeter-opt-076db2f87da8|[[1.3003550583063985, 1.3003550583064079], [1.2190589378049814, 1.2190598521460154]]|3.452070773 / 3.130652414|0.07058229809|4.084716551|24.60736586 / 23.24812104|1.904075097 / 1.76840906|
|perimeter-opt-0cc5736e7eb4|[[1.3638517423697933, 1.3638527500718933], [1.2262037794316, 1.2262046990413802]]|3.459122782 / 3.140730525|0.06994476457|4.087424211|24.95779917 / 23.2705715|1.905829384 / 1.770372007|
|perimeter-opt-81b82881db5c|[[1.2412473669331723, 1.241248283394113], [1.3178456131992633, 1.3178466019057868]]|3.466228198 / 3.046306807|0.08608126991|4.158017061|24.82911641 / 24.87671535|1.910251596 / 1.785060229|

4개final의활성limiter는`bulk_skin_J_vector_RMS_p95_A_m2`다. finalskin8sourceupper약1.22–1.36Vpp를raw동일전압gain으로서술하지않는다. skin8는접촉Jmax/J95·접촉전압·SC/접촉손실·SC+dermis체적vectorJmax/J95·SC+dermis손실의8개수치한도이며sourcepower/1Vpp상한은없다. legacy만이둘을추가하고동일전류/전력도1Vpp상한없음이다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드에서절대mean/P10/CV/P10mean/max·wholeXY보조ROI·표면/전체비표적P95·고변조체적·전역hotspot을보존했다. 수치한도는인체안전한계가아니다.

## final4의개별8gate (원래square skin8)

### perimeter-opt-3b8b3153d641

|gate|단위|기준|final|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.582278442|-11.80670444|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.133084946|-14.06165532|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|24.83446376|-1.681596024|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|8.685262277e-06|11.82939324|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|8.763716518e-06|6.751526374|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|25.26840936|7.820075023|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|1.953119423e-05|0.678047997|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.092517003e-05|-1.089475249|PASS|

### perimeter-opt-076db2f87da8

|gate|단위|기준|final|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.452070773|-15.01233004|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.130652414|-14.12837797|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|24.60736586|-2.580665301|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|8.685722656e-06|11.83532098|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|8.764042969e-06|6.755502898|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|23.24812104|-0.8004770203|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|1.919371094e-05|-1.061587511|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.025221706e-05|-4.270435356|PASS|

### perimeter-opt-0cc5736e7eb4

|gate|단위|기준|final|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.459122782|-14.8387143|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.140730525|-13.8519424|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|24.95779917|-1.193317309|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|8.951071429e-06|15.25188933|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.118777902e-06|11.07655727|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|23.2705715|-0.704681093|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|1.947024135e-05|0.3638523191|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.062397939e-05|-2.513163755|PASS|

### perimeter-opt-81b82881db5c

|gate|단위|기준|final|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.466228198|-14.66378371|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.046306807|-16.44191941|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|24.82911641|-1.702765939|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|8.667388393e-06|11.59925332|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|8.746517857e-06|6.542028123|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|24.87671535|6.148720216|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|1.933853097e-05|-0.3150792276|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.053710107e-05|-2.923826147|PASS|

## 40phi·signedpower·공개범위

새4final×5모드각40개무부하nativephi예측은condition JSON의`normalizations/.../probe40_unloaded`에보존했다. 깊이5/10/15/20mm ×중심·X/Y±5mm의5개중심 ×X/Y차동방향,tipgap5mm다. probe중심간격과팁간격은다르다. rawJSON은전체파형Vpp bounds/RMS/기본파envelope·스펙트럼·저장검사에연결된다. cached2행은upstreamraw40영수증이며이번에nativeprobe를열거나정규화영수증을재발급하지않았다. ETA5001/DSOX1202Aactualswitch·팬텀portimpedance/부하·보정은미검증으로loaded예측은보류다.

접촉surfaceJ·SC+dermis체적vectorJ·접촉전압·SC/contact/SC+dermis/sourcepower를구분했다. signedpower는주파수/출력/그룹총합을구분하고음수및비활성9000/9090Hz의0전력선을생략하지않았다. returnnet/local current는peak양으로condition/brief에보존하며net상쇄=localJ0을주장하지않는다. 실제AWG두tone·위상동기·흡수/sink/compliance는미검증이다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`,configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json),SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `perimeter-shell225-notch-xy80` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`,configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](../data-native/cloud-perimeter-shell-20261021T185000Z/postprocess/perimeter-shell225-notch-xy80/summary.json),SHA256 `fbbe40074b2219d09607a588ca8b31b35337449459b2eeb19cbb0d74b7c35252`
  - [rawunloaded40](../data-native/cloud-perimeter-shell-20261021T185000Z/postprocess/perimeter-shell225-notch-xy80/probes.json),SHA256 `da6ff0f59e36827fce26f3e418fb52a0073d44f0df488cfa576a8e67254b31ed`
- `perimeter-opt-3b8b3153d641` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`,configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-3b8b3153d641/condition.json),SHA256 `7860608898111ac26067ec82ee5ae122bf687dbdc7b3331b3b56362c9ec31a23`
  - [rawunloaded40](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-3b8b3153d641/probes.json),SHA256 `69179808276b28f245df0d68a9c9a00d357124f1d4568cf9a596784137df508f`
- `perimeter-opt-076db2f87da8` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`,configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-076db2f87da8/condition.json),SHA256 `89d655f217699c1bc56a50897dc8ba895280e989c01efb446bfce666baed6ac6`
  - [rawunloaded40](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-076db2f87da8/probes.json),SHA256 `86c8344e13deaeb2f101220a91ff722d840676ac08c9e3e3269d9e7bcd5ef1ae`
- `perimeter-opt-0cc5736e7eb4` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`,configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-0cc5736e7eb4/condition.json),SHA256 `fac94f39c939b2646bdb4f32b47894cc78a0821423121c5a312cc5f3beebf886`
  - [rawunloaded40](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-0cc5736e7eb4/probes.json),SHA256 `6eddfa210a319f582c671660f99189f314ad1e99828c5441213903988395b1a1`
- `perimeter-opt-81b82881db5c` / sourcecase `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`,configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [sourceJSON](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-81b82881db5c/condition.json),SHA256 `d4564f299b645d92e197d4ab1e60bc034cc1837d31b6f9de83d70cc91478b1d6`
  - [rawunloaded40](cloud-perimeter-drive-optimization-20261021T192000Z/perimeter-opt-81b82881db5c/probes.json),SHA256 `e6e7b883676bd3d9e36b06375b10d7b9f89d30137727456d040d2c2c793c1ee4`

physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`, native source `257d56bc7300efaf691d2f017369b29065a7edf0`, optimizer implementation/preregistration `103de32abd47a0aedbe7559b5614dcbb7c2ce128`를구분한다. 이문서는docs JSON만읽고data-native내용·E/phi/NPZ를열거나재해시하지않았다. cachednative SHA는upstream영수증으로현재독립재검증을주장하지않고모든raw데이터가공개archive됐다고가정하지않는다. 해시검증과시뮬레이션재현·수렴·실험검증은별도다.

## 과학계산완료와발행댓글복구

과학summary는`calculated_unadopted`,124proxy+4fullfinal,wall `141.85920428499958s`,CPU1,peakRSS `540139520bytes`,새PDE0이다. 큐`completed_preregistered_queue`는계산/GET2단계exit0이다. 과학계산이실패한것이아니다.

원래publisher는commit/push `0de09e4dd954c7f92fb6b706207089927fdb759a` 성공뒤고정댓글확인에서`failed_preserved`로끝났다. generic `publication.json`이이전direction audit runtime body이름과충돌했고원실패영수증은보존됐다. [원발행실패](cloud-perimeter-drive-optimization-context-20261021T192000Z/publication.json)와[댓글전용수동복구](cloud-perimeter-drive-optimization-context-20261021T192000Z/comment-publication-recovery.json)를분리한다. 복구는`published_existing_results_comment_recovered`, `2026-10-21T18:55:03.761306+00:00`,기존원격commit을확인하고댓글만복구했다. `comment_only_recovery=true, simulation_repeated=false, scientific_arrays_reread=false, new_PDE=0`이다. 시뮬레이션재시도로표현하지않는다.

native방정식/파형/8gate는SC/XY/bulk/edge/contact·방향수렴·실험검증이아니고PBSnominal계면도실제피부검증이아니다. C1/활성화/인체안전/COMSOL검증을새로주장하지않는다.

다음[inward decision](cloud-perimeter-inward-context-20261021T194000Z/decision.json)은`selected_not_executed`의planned1PDE등록자료만연결한다. 이등록파일만으로현재실제worker시작/완료를가정하지않는다.

- [summary](cloud-perimeter-drive-optimization-20261021T192000Z/summary.json),SHA256 `759a4184903751a8f2ba01a79e60eb43d55df2ed9299fa6c85b26009872346c5`
- [proxy_search](cloud-perimeter-drive-optimization-20261021T192000Z/proxy-search.json),SHA256 `cdbe6d83f8c563139e574b3bdf429c65fda487fe1ba7903b6f3c2690debf6dc0`
- [preregistration](cloud-perimeter-drive-optimization-context-20261021T192000Z/preregistration.json),SHA256 `2a3173e33f64aff860a61ebed95a539e215dbe0db2653184b8b310d750af8a95`
- [queue](cloud-perimeter-drive-optimization-context-20261021T192000Z/queue/summary.json),SHA256 `42d61a5c349283125ff877afc3e32eb8c3ca68b6c648b38b941bd89e8e24c4c0`
- [original_publication_failure](cloud-perimeter-drive-optimization-context-20261021T192000Z/publication.json),SHA256 `c0f80c64eaa45e3d660de8c9b06d8940dea7682152d6c7847a1a60ab985b3812`
- [comment_only_recovery](cloud-perimeter-drive-optimization-context-20261021T192000Z/comment-publication-recovery.json),SHA256 `607a0887c304b3c96d85d858c8d6d6e603f8e6e961176f456821542a29aa8333`
- [decision](cloud-perimeter-drive-optimization-context-20261021T192000Z/decision.json),SHA256 `33b957fc08959cfe9a35abc12d9a501579ced7be7e631306e459707637d80d54`
- [feedback_after](cloud-perimeter-drive-optimization-context-20261021T192000Z/feedback-after.json),SHA256 `42a7879cfe0c0922c6ec72eabac32f42a74977df8b305b12278620cc5f3e02d3`
- [verified_perimeter_snapshot](PERIMETER_SHELL_RESULTS_20261021.result-brief.json),SHA256 `3c09e2121db7d44387f6c4a2561ec0498207e9c12acda9ceda034f034fb57c5b`
- [next_inward_decision_only](cloud-perimeter-inward-context-20261021T194000Z/decision.json),SHA256 `a42a99c19facb6decc110792610254d82dc775e016abd73b9f1e3b26dbbebb4f`
- [cached_control_volume](cloud-perimeter-shell-context-20261021T185000Z/volume.json),SHA256 `60e19c019800cd3b958dda4f183254dcc3687743314ea6016e1fcc0f28987564`

[과거8행antiphaseGUI](CLOUD_PERIMETER_ANTIPHASE_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다. 이번화면은새물리공간맵을생성하지않은정적오프라인JSON표다.
