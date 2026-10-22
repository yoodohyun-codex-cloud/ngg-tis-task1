# 작업1: Rounded geometry의 bounded five-gene drive optimization (2026-10-21)

118개 unique proxy 평가 후 선택한 신규4개 full validation은 모두 미채택이다. 3개는8개판정중6개를통과했으나 surfaceP95와전체비표적complementP95가실패했고, 7cfa4be0ae65는목표mean/P10도실패했다. e7 후보의목표P10상승은0.0333873033727%에불과하므로 이를수렴·실험·깊이집중성공으로승격하지않는다. 원래square와cachedrounded square3h기준을항상함께표시한다.

[6행 오프라인GUI](CLOUD_ROUNDED_DRIVE_OPTIMIZATION_RESULTS_20261021.html) · [정확한5모드/출처brief](ROUNDED_DRIVE_OPTIMIZATION_RESULTS_20261021.result-brief.json) · [원본summary](cloud-rounded-drive-optimization-20261021T203000Z/summary.json)

## 기하·회로·실제sourceVpp

새 4조건은 fixed rounded full-face225 geometry/위치를 전혀 바꾸지 않았다. 중심(±10,±10) mm, 각225/총900 mm², pad당576 full-face stepped union이며 D4 odd u²+v²≤730에560내부+16동률 face를 모두 포함한 고정 도형이다. smooth circle이 아니며 perimeter70 mm>square60 mm, gap2.5 mm(4XYcells)/rim2.002038133782378 mm의 hold를 유지한다. D50 mm/층0.1·5·5·15 mm/윗면/XY.625·SC2·bulk14·14·40, 물리4pads/독립2outputs/공통GND/50Ω, pad0out0/pad1out1/pad2·3GND다. command rank와 패드·출력수를 혼동하지 않는다.

새4조건은두출력모두3000/3030Hz·beat30Hz를포함하고9000/9090Hz계수와전력은0이다. cachedsquare3h controls만4선을포함한다. genes=[z0real,z0imag,z1real,z1imag,rho], 행=출력(out0,out1), 열=주파수(3000,3030Hz)인 seed=-i[[1,z1],[z0,rho]]; 코드의 주파수별 벡터는 c3000=-i[1,z0], c3030=-i[z1,rho]이며개별복소source계수와하나의공통g를그대로보존했다. 새조건은ONEglobalg로raw전체source waveform Vpp upper의최댓값만1Vpp로맞췄고출력별독립column정규화를하지않았다. 각출력이정확히1Vpp가아니다. 실제sourceVpp는50Ω전전체파형max−min bracket으로raw폭≤1µV를검증했으며toneVpp나2√2RMS로대체하지않는다. cachedsquare의과거nominalscalar는새actualbracket검증이아니다.

주ROI 중심r≤5mm·깊이15–20mm,x/y수평,+z안쪽을 유지했다. 모든 E/TIS 값 V/m, CV/P10mean무차원이다. maxTIS는기본파2074표본방향최대(연속방향최대의하한), fixedTIS는기본파(X+Y)/√2, fullRMS는각행의모든활성선 전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/원래square raw cutoff와staircasegeometry를 고정했고 analytic volume 재정규화는 없다. SC 전역 최대를 목표깊이 집중으로 해석하지 않는다.

## 유한 proxy 탐색과최종검증

탐색 범위는 z0/z1의 실수·허수 각각 [−0.075,+0.075], rho [0.95,1.05]이고 step 0.02/0.01/0.005와 등록된4개 seed를 사용했다. 124는 상한이며 실제 unique proxy118개와 final4개만 완료됐다. proxy는 목표2074방향을 정확히 평가하되 off-target 3-lambda spectral upper bound를 순위 선정에만 사용하며 whole-source Vpp 정규화 결과가 아니다. 선택 final 검증240s와 finalization30s reserve를 보존한 유한 탐색이며 전역 최적화·연속방향 최대·이 family 불가능성의 증명이 아니다. Frozen 방향 행렬 SHA256은 84b7f119bd37395a95e8592d186a96fdfb59e5f73a90a4e7ef22efe429a0d0b2다.

## raw source whole-wave Vpp 기준

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached rounded square3h|cached nominal 1|4.05249095969 / 3.63880089209|0.080450718365|4.95540788828|24.9859667213 / 23.5375931838|2.30217685964 / 2.10115028133|
|rounded-opt-e7b3bf639935|[[0.9957623520247947, 0.9957630873148557], [0.9999992473306978, 1.0]]|3.68380072432 / 3.30513584541|0.0811323013159|4.50152014477|22.9919264848 / 21.4321186487|1.99200384354 / 1.81771181662|
|rounded-opt-524cc4a7bece|[[0.9961826799239166, 0.9961834154678845], [0.9999992472705617, 1.0]]|3.69929176505 / 3.3188512158|0.0811217345235|4.52079644675|23.0734529843 / 21.5275365898|2.00032361552 / 1.82533899797|
|rounded-opt-7cfa4be0ae65|[[0.9968364000027296, 0.9968371360293797], [0.9999992473335242, 1.0]]|3.68167447841 / 3.30177562082|0.0812830094345|4.50080221494|23.0194392475 / 21.482082385|1.99164504378 / 1.81678419917|
|rounded-opt-67c543b5df68|[[0.9957623520247947, 0.9957630873148557], [0.9999992473306978, 1.0]]|3.69491207373 / 3.31671123084|0.0810464431181|4.52465662768|23.0337834294 / 21.4763203857|1.99696367617 / 1.8223528377|

## 동일8개 피부·접촉부담 (skin8)

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached rounded square3h|cached nominal 0.982372542559|3.98105584777 / 3.57465808423|0.080450718365|4.86805664662|24.5455276563 / 23.1226852617|2.26159533502 / 2.06411234417|
|rounded-opt-e7b3bf639935|[[1.0987440816491798, 1.0987448929829295], [1.1034191566130627, 1.1034199871234145]]|4.0647793478 / 3.64695295198|0.0811323013159|4.96706730017|25.3697512258 / 23.6486280834|2.19801685539 / 2.00569954929|
|rounded-opt-524cc4a7bece|[[1.0946331887628966, 1.0946339969990315], [1.0988269389344067, 1.098827766054414]]|4.06488450618 / 3.64684586732|0.0811217345235|4.96757666037|25.3537507979 / 23.6550549396|2.19801112982 / 2.00573317343|
|rounded-opt-7cfa4be0ae65|[[1.0972469102313644, 1.0972477203973734], [1.1007283485709338, 1.1007291770528844]]|4.0525265188 / 3.63436076191|0.0812830094345|4.95416431813|25.3381684192 / 23.645954865|2.19226181002 / 1.99978737644|
|rounded-opt-67c543b5df68|[[1.09879760246861, 1.0987984138418803], [1.1034729051596288, 1.1034737357104354]]|4.07723842912 / 3.65990373216|0.0810464431181|4.99283975175|25.4171750484 / 23.6985554853|2.20359696782 / 2.0109184936|

5모드 raw/동일출력RMS전류합/동일총sourcepower/skin8/legacy를 보존했다. skin8는원래square의8개접촉·피부수치한도이며sourcepower/1Vpp ceiling이 없다. 신규4조건의limiter는 모두SC_power_W이며skin8의실제sourceupper1.0988–1.1035Vpp가1Vpp를넘으므로 raw동일전압gain과구분한다. cachedrounded square3h의limiter는SC+dermis vectorJ95로다르다. legacy만sourcepower/1Vpp상한을추가하고 동일전류/전력에도1Vpp상한이 없다. 이한도는인체안전한계가 아니다.

5모드의절대목표mean/P10/CV/P10mean/max·fixedTIS/fullRMS·wholeXY보조ROI·표면/전체비표적P95·원래cutoff이상체적·전역hotspot과각burden을GUI/brief에보존했다. 전역SC최대값은깊이집중이아니다.

## 신규저장8gate · 원래square raw기준 고정

|조건|mean|P10|surfaceP95|surface high@mean|surface high@P10|complementP95|complement high@mean|complement high@P10|
|---|---|---|---|---|---|---|---|---|
|rounded-opt-e7b3bf639935|PASS|PASS|FAIL|PASS|PASS|FAIL|PASS|PASS|
|rounded-opt-524cc4a7bece|PASS|PASS|FAIL|PASS|PASS|FAIL|PASS|PASS|
|rounded-opt-7cfa4be0ae65|FAIL|FAIL|FAIL|PASS|PASS|FAIL|PASS|PASS|
|rounded-opt-67c543b5df68|PASS|PASS|FAIL|PASS|PASS|FAIL|PASS|PASS|

각gate의원래값·후보값·변화율·단위·요구방향은원본condition JSON과GUI에보존했다. e7/524c/67c5는6PASS/2FAIL이며실패2개는surfaceP95와complementP95다. 7cfa는목표mean/P10도실패해4PASS/4FAIL이다. e7SC2의mean4.06477934779812V/m(+0.0721446375444%),P103.646952951981444V/m(+0.0333873033727%)의작은여유를보존한다. SC4결과를이표의SC2숫자로혼합하지않는다.

## nativeφ40·carrierRMS·signed power·범위

proxy의목표값은고정된동일2074방향/순서/전체positiveweight ROI에대한표본최대의정확한mean/P10이며pureseed기준regression은오차0이다. 2074방향matrixSHA를고정했지만연속방향최대가아니다. 비표적proxy는lambda0,0.5,1의guardedPSD최대고유값upperbound중최솟값으로ranking에만사용했다. proxy에서상한이더나쁜것은실제field실패증명이아니다. 원래8개skin/contact부담은native이산모델의정확한값이고proxy는wholeVpp정규화되지않아raw1Vpp결과가아니다. 신규4fullfinal은별도로실제wholeVpp검증/2074field통계/40nativeφ/8gate를완료했다. 기존6개의fullvalidationalias는새spectralproxycache가아니다. 모든118평가를fullvalidation으로세거나124개완료/전역최적값/family배제를주장하지않는다. volumeXYZ방향별scalararchive는미생성이고centre20XYZ만별도저장했다. 이문서는docsJSON만읽고native E/φ/grid/mask/config/NPZ를읽거나scientific계산·렌더를수행하지않았다.

신규4조건×5모드 각각40개 무부하 예측은 condition JSON normalizations/.../probe40_unloaded에 있고 raw probes JSON에는 전체파형Vpp bounds/RMS/기본파envelope/스펙트럼과저장검사가 있다. 깊이5/10/15/20mm×중심·X/Y±5mm의5개probe중심×X/Y차동방향,tipgap5mm다. probe중심위치와팁간격을 구분한다. 각rawJSON의40 records/sourceID/SHA/unloaded/저장numericalcheckspass와파형audit를확인했다. cached2행은검증된과거docs raw40영수증을 보존하고 normalizedprobe를재발급하지않았다. ETA5001/DSOX1202A 실제switch·보정·팬텀portimpedance/부하·filter응답은미검증으로loaded예측은보류다.

저장raw carrier별RMS/balance의목표r5와wholeXY보조ROI통계는별도로표시했고다른정규화에새scale/recompute하지않았다. carrierRMS·전체fieldRMS·방향별TIS·최대표본방향TIS는별개다. 각모드signed ideal source/metal delivered/50Ωloss의출력별합계·주파수별값·그룹총합을보존했다. 음수와비활성9000/9090Hz의0계수·전력선을제거하지않았다. GND net전류와localJ·patch절대전류적분은brief/원본에별도로보존했다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json),SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `rounded-fullface225-xy80` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](../data-native/cloud-rounded-fullface-20261021T200000Z/postprocess/rounded-fullface225-xy80/summary.json),SHA256 `b12cc83e82cdacf457128d950ea315abe86973b0450d1eb169a1a8f3eaedef40`
  - [rawunloaded40](../data-native/cloud-rounded-fullface-20261021T200000Z/postprocess/rounded-fullface225-xy80/probes.json),SHA256 `6b0118b3cda87d31ed712d0c9e66bbd28e6bc68ab445d735c4c6c09924efe642`
- `rounded-opt-e7b3bf639935` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-e7b3bf639935/condition.json),SHA256 `48fabf8729c4efeb7ffb39737c49fba09bab29185dbc39ddaeede7684e11374e`
  - [rawunloaded40](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-e7b3bf639935/probes.json),SHA256 `17478d4a414c965efaa6e95fab665a501b0e121bfbcd3a39675248cdfdd6d339`
- `rounded-opt-524cc4a7bece` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-524cc4a7bece/condition.json),SHA256 `fcb567682f0deea46bf605a53fe21d014cc1e8c4a09d43c6b3c6ac72341e28ae`
  - [rawunloaded40](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-524cc4a7bece/probes.json),SHA256 `834bce470a1cba16cf3a1df025cd9d4271e91aae31d0a3fb61fdb7b84e27f59b`
- `rounded-opt-7cfa4be0ae65` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-7cfa4be0ae65/condition.json),SHA256 `5eddd477a62b9a219c941d2b2aeebc283866d3fc63dc9ba16417cd7d17b7411c`
  - [rawunloaded40](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-7cfa4be0ae65/probes.json),SHA256 `88c2859ea5976c9c0782d40b0a81fead91358d95c8ee18d1f28f625a15e51fb5`
- `rounded-opt-67c543b5df68` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-67c543b5df68/condition.json),SHA256 `a1ce7c9dd1450a890bc7dd485fc0912e133a61f610a969e2fb9f4d94d2a3e70d`
  - [rawunloaded40](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-67c543b5df68/probes.json),SHA256 `707ff53b15bfe52dc7dfce63103c84b31d4fb54678d19f8e079400d114b6bf24`

## 실제실행·검증보류·별도SC4진단

계산/GET의2단계 exit0와별도완료publisher, queue completed_preregistered_queue, 과학worker wall 173.79544675200304s, peakRSS 540983296bytes, CPU1, newPDE0다. queue elapsed 180.55483403000108s와worker시간은구분한다. 발행 published_completed_batch, 2026-10-21T19:29:40.026111+00:00, commit eb2b3bdb396e90c16da772bdc0d04c8762c89552다.

각주파수·출력·그룹의signed source/metal/resistorpower를 구분하고 음수를제거하지않는다. 비구동/교차주파수에서금속단의음의전력과실제source흡수요구는 hardware sinking/compliance 검증과다르다. 물리GND net전류상쇄는localJ=0을뜻하지않고독립절연출력/귀환삭제를 주장하지 않는다. SC/XY/bulk/edge/contact·방향수렴/실험/생리활성/C1동등성/인체안전/COMSOL5.3a 설치·실행을 새로검증하지않았다. PBS계면은실제피부검증값이아니다. fullcomplex native 독립persistentbackup은미검증이고원본·실패증거는보존한다.

이후root가e7b3bf639935동일command를SC4에서실제로진단했다. 해당결과는별도SC4 addendum링크이며6행SC2최적화값을교체하지않는다. SC4 same-historical-SC2-skin8-amplitude에서mean4.064792819146645/P103.646963315557711V/m,두P95판정실패가유지됐다. 제한된SC2↔SC4민감도통과는XY/bulk/edge/contact/fullconvergence나채택을의미하지않는다. nativeSC4기하계산과이후cached재합성의newPDE0도구분한다. SC4파일에추가정규화(supplemental_SC4_rematched_modes)도있지만이문서의별도SC4표는historicalSC2진폭고정결과만사용하고6행SC2표는교체하지않는다.

native source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`,physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,scout implementation/preregistration `11e14c34f250698cff97a9db5a8e363d6fcb26d3`를구분한다. 이번docs해시검증은시뮬레이션재현/수렴/실험검증이아니며새물리fieldmap을생성하지않았다.

- [summary](cloud-rounded-drive-optimization-20261021T203000Z/summary.json),SHA256 `943a0418920f49a778f1edf21a52c1a449799ae44795b2adfcf71e6c89795732`
- [decision](cloud-rounded-drive-optimization-context-20261021T203000Z/decision.json),SHA256 `0e81b45bcc2a5fb27d6718f43826ee74d1036bbf4ce73471080ca020939eee8c`
- [queue_plan](cloud-rounded-drive-optimization-context-20261021T203000Z/queue-plan.json),SHA256 `86540a9159cb0c97fdf7458a4484b553080e9c98f62a1565d30a690f328eeb3b`
- [queue](cloud-rounded-drive-optimization-context-20261021T203000Z/queue/summary.json),SHA256 `166437e67f082454da29f68b881725f9e365a3e818ecb414624ca1130b4d3432`
- [publication](cloud-rounded-drive-optimization-context-20261021T203000Z/rounded-optimization-publication-20261021T203000Z.json),SHA256 `6dab47663e4a4ba576f8d3493e2d459fff0b8375abe2b72e08aea8cad38fcdc9`
- [feedback_after](cloud-rounded-drive-optimization-context-20261021T203000Z/feedback-after.json),SHA256 `11d5bf08dc003d8bb4573ed45d3996fdeda2b620f546a76ed38a16ff508d45e9`
- [verified_rounded_snapshot](ROUNDED_FULLFACE_RESULTS_20261021.result-brief.json),SHA256 `23643003dc3f2df01891b541a81962bc61bd419012a05a50138b522885a6048f`
- [preregistration](cloud-rounded-drive-optimization-context-20261021T203000Z/preregistration.json),SHA256 `51d3050bdd2411745c4c2a3e2c409835ffbe292e9b83173ba83854e22fe73304`
- [cached_volume](cloud-rounded-fullface-context-20261021T200000Z/volume.json),SHA256 `95b1593cf23d2a539c57007f3909b56ba59692148768514fcae9b13dc65fd590`
- [proxy_search](cloud-rounded-drive-optimization-20261021T203000Z/proxy-search.json),SHA256 `c0148775132f07952122f736965d192a919a7dd69b79399809b1dc7ceac0a168`
- [separate_SC4_summary](cloud-rounded-sc4-sensitivity-20261021T204000Z/summary.json),SHA256 `f4d99e42fb11b225b0764b2d6bc8d090405efdcee981890f3411246d2be585fb`
- [separate_SC4_condition](cloud-rounded-sc4-sensitivity-20261021T204000Z/rounded-opt-e7b3bf639935-SC4-same-command/condition.json),SHA256 `05aa7358ba050c3c753d4e8deb10f4ddcdb1b39c1d6ed40c30459dd63687dc48`

[이전rounded형상2행GUI](CLOUD_ROUNDED_FULLFACE_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다.

[이전6조건 signed-weak drive GUI](CLOUD_ROUNDED_DRIVE_RESULTS_20261021.html)는 별도 완료 snapshot으로 보존한다.
