# 작업1: Rounded geometry의 bounded expansion drive search (2026-10-21)

확장 탐색의 신규2full조건은 모두 미채택이다. f35b는4/8PASS,2254는5/8PASS이며 둘다목표P10과surface/complementP95가실패했다. 기존narrowe7의6/8PASS는원래값그대로보존하며새개선후보로대체하지않는다. Strict lexicographic proxy objective의개선은실제8개screen의우위·목표영역집중성공과다르다.

[5행 오프라인GUI](CLOUD_ROUNDED_DRIVE_EXPANSION_RESULTS_20261021.html) · [정확한5모드/출처brief](ROUNDED_DRIVE_EXPANSION_RESULTS_20261021.result-brief.json) · [원본summary](cloud-rounded-drive-expansion-20261021T214000Z/summary.json)

## 기하·회로·실제sourceVpp

신규2조건과재사용e7은 fixed rounded full-face225 geometry/위치를 전혀 바꾸지 않았다. 중심(±10,±10) mm, 각225/총900 mm², pad당576 full-face stepped union이며 D4 odd u²+v²≤730에560내부+16동률 face를 모두 포함한 고정 도형이다. smooth circle이 아니며 perimeter70 mm>square60 mm, gap2.5 mm(4XYcells)/rim2.002038133782378 mm의 hold를 유지한다. D50 mm/층0.1·5·5·15 mm/윗면/XY.625·SC2·bulk14·14·40, 물리4pads/독립2outputs/공통GND/50Ω, pad0out0/pad1out1/pad2·3GND다. command rank와 패드·출력수를 혼동하지 않는다.

원래square/roundedsquare3h controls만3000/3030/9000/9090Hz4선을포함하고재사용e7·신규2조건은3000/3030Hz·beat30Hz만활성이며9k고조파는0이다. genes=[Re(z0),Im(z0),Re(z1),Im(z1),rho]의주파수별벡터순서는명시적으로 f3000:(out0=−i,out1=−i·z0), f3030:(out0=−i·z1,out1=−i·rho)다. 따라서 frequency-rows/output-columns 행렬은−i[[1,z0],[z1,rho]]이며output-rows/frequency-columns로쓸때만그전치다. basis source peak0.5V에하나의공통g를곱한실제복소계수를원본그대로보존했다. raw 전체sourcewaveformVpp upper의최댓값만1Vpp이고각출력이exact1Vpp가아니다. 출력별독립정규화없이50Ω전전체파형max−min의raw bracket폭≤1µV를검증했다. cachedsquare의nominalscalar와실제sourceinterval을구분하고toneVpp/2√2RMS로대체하지않는다.

주ROI 중심r≤5mm·깊이15–20mm,x/y수평,+z안쪽을 유지했다. 모든 E/TIS 값 V/m, CV/P10mean무차원이다. maxTIS는기본파2074표본방향최대(연속방향최대의하한), fixedTIS는기본파(X+Y)/√2, fullRMS는각행의모든활성선 전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/원래square raw cutoff와staircasegeometry를 고정했고 analytic volume 재정규화는 없다. SC 전역 최대를 목표깊이 집중으로 해석하지 않는다.

## 확장범위·실제cache재사용·종료이유

확장범위는z0/z1실수·허수각각[−0.25,+0.25],rho[0.8,1.2],steps0.05/0.02/0.01/0.005와등록4seeds다. oldnarrow118행의source/metric identity와현재cachemap을SHA로묶어재사용했고sourcehelper의record/genes/objective수치는일치한다. origin은previous_completed_cache로표시되고new_evaluation=false인118행이며새124행과구분한다. 6cache hits는다시방정식을푼횟수가아니다. new_evaluation_cap에닿아일부탐색수준은미완료이므로전체level완료/전역최적값을주장하지않는다. final240s+finalization30s reserve를보존한유한batch다.

## raw source whole-wave Vpp 기준

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached rounded square3h|cached nominal 1|4.05249095969 / 3.63880089209|0.080450718365|4.95540788828|24.9859667213 / 23.5375931838|2.30217685964 / 2.10115028133|
|cached narrow e7|[[0.9957623520247947, 0.9957630873148557], [0.9999992473306978, 1.0]]|3.68380072432 / 3.30513584541|0.0811323013159|4.50152014477|22.9919264848 / 21.4321186487|1.99200384354 / 1.81771181662|
|rounded-expand-f35b23a22166|[[0.988605383369711, 0.9886061134362394], [0.9999992472108359, 1.0]]|3.66771688836 / 3.28887166201|0.0812210338062|4.47293935953|22.9194653917 / 21.3857112585|1.98425715854 / 1.80994406832|
|rounded-expand-22540f728bf9|[[0.9844158524147059, 0.9844165793262936], [0.9999992472108359, 1.0]]|3.67772158885 / 3.29670695439|0.0811601180762|4.47293935953|22.899801656 / 21.4148023176|1.98913343527 / 1.8143406256|

## 동일8개 피부·접촉부담 (skin8)

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached rounded square3h|cached nominal 0.982372542559|3.98105584777 / 3.57465808423|0.080450718365|4.86805664662|24.5455276563 / 23.1226852617|2.26159533502 / 2.06411234417|
|cached narrow e7|[[1.0987440816491798, 1.0987448929829295], [1.1034191566130627, 1.1034199871234145]]|4.0647793478 / 3.64695295198|0.0811323013159|4.96706730017|25.3697512258 / 23.6486280834|2.19801685539 / 2.00569954929|
|rounded-expand-f35b23a22166|[[1.0925154584815784, 1.0925162652837477], [1.1051069055722604, 1.1051077374853904]]|4.05322231223 / 3.63455752128|0.0812210338062|4.94307989552|25.3284785434 / 23.6335149834|2.19281793906 / 2.00018319432|
|rounded-expand-22540f728bf9|[[1.0879848200030962, 1.0879856233920004], [1.105207721219809, 1.105208553208832]]|4.06464935632 / 3.64354872342|0.0811601180762|4.94353083814|25.309056657 / 23.6678226867|2.19840728613 / 2.00522477785|

5모드 raw/동일출력RMS전류합/동일총sourcepower/skin8/legacy를 보존했다. skin8는원래square의8개접촉·피부수치한도이며sourcepower/1Vpp ceiling이 없다. 재사용e7·신규2조건의limiter는모두SC_power_W이며skin8의실제sourceupper는표와같이1Vpp를넘으므로 raw동일전압gain과구분한다. cachedrounded square3h의limiter는SC+dermis vectorJ95로다르다. legacy만sourcepower/1Vpp상한을추가하고 동일전류/전력에도1Vpp상한이 없다. 이한도는인체안전한계가 아니다.

5모드의절대목표mean/P10/CV/P10mean/max·fixedTIS/fullRMS·wholeXY보조ROI·표면/전체비표적P95·원래cutoff이상체적·전역hotspot과각burden을GUI/brief에보존했다. 전역SC최대값은깊이집중이아니다.

## 재사용e7 및 신규2조건의8gate · 원래square raw기준 고정

|조건|mean|P10|surfaceP95|surface high@mean|surface high@P10|complementP95|complement high@mean|complement high@P10|
|---|---|---|---|---|---|---|---|---|
|rounded-opt-e7b3bf639935|PASS|PASS|FAIL|PASS|PASS|FAIL|PASS|PASS|
|rounded-expand-f35b23a22166|FAIL|FAIL|FAIL|PASS|PASS|FAIL|PASS|PASS|
|rounded-expand-22540f728bf9|PASS|FAIL|FAIL|PASS|PASS|FAIL|PASS|PASS|

각gate의원래값·후보값·변화율·단위·요구방향은원본condition JSON과GUI에보존했다. 재사용e7은6PASS/2P95FAIL을유지하고f35b는4PASS/4FAIL,2254는5PASS/3FAIL이다. 신규두조건모두P10·surfaceP95·complementP95가실패하며f35b의mean도실패한다. 신규proxyobjective개선은기존e7을8gate에서우위로대체한다는뜻이아니다.

## nativeφ40·carrierRMS·signed power·범위

old118개same-definition proxy cache를실제로재사용하고new124개를계산해총242개가저장됐다. 상태proxy_budget_exhausted_partial/stop_reason=new_evaluation_cap은신규평가개수상한종료이며시간timeout이나모든level/전역탐색완료가아니다. 목표proxy는고정2074방향/순서/전체positiveweightROI의정확한표본mean/P10이고cachedpureseedregression(error0)도실제로oldcache에서재사용했다. 2074는연속방향최대가아니다. off-targetproxy는lambda0,.5,1의guardedPSD최대고유값upperbound중최솟값을ranking에만쓴것이며나쁜상한은실제field실패증명이아니다. 과거26direction/Gershgorin9proxy와도별개다. exactnative8burden은그대로지만proxy는wholeVpp정규화되지않아raw1Vpp결과가아니다. 최종새2개만실제wholeVpp/2074field/40nativeφ/8gate를별도로검증했고old10개fullvalidation은다시계산하지않았다. old10alias중legacy6레코드의proxy2074_three_lambda_spectral_cache_available:false필드는당시역사기록으로불변보존했다. 현재cache유무는SHA-bound118rowcachemap/실제reuse기록이근거이고역사필드를현재cache없음으로해석하거나원본을고쳐쓰지않는다. 모든242개를fullvalidation으로세거나전역최적/불가능성을주장하지않는다. volumeXYZscalararchive는미생성이고centre20XYZ만별도저장됐다. 본문서는docsJSON만읽고native/E/φ/grid/mask/config/NPZ를읽거나scientific계산·렌더를수행하지않았다.

신규2조건×5모드각40개와재사용e7의기존5모드각40개 무부하 예측은 condition JSON normalizations/.../probe40_unloaded에 있고 raw probes JSON에는 전체파형Vpp bounds/RMS/기본파envelope/스펙트럼과저장검사가 있다. 깊이5/10/15/20mm×중심·X/Y±5mm의5개probe중심×X/Y차동방향,tipgap5mm다. probe중심위치와팁간격을 구분한다. 각rawJSON의40 records/sourceID/SHA/unloaded/저장numericalcheckspass와파형audit를확인했다. cached2행은검증된과거docs raw40영수증을 보존하고 normalizedprobe를재발급하지않았다. ETA5001/DSOX1202A 실제switch·보정·팬텀portimpedance/부하·filter응답은미검증으로loaded예측은보류다.

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
- `rounded-expand-f35b23a22166` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-f35b23a22166/condition.json),SHA256 `b29a07e13752ef6c84893f43bbefa37a3a9aa0bdd6e1c20dfea8986ccdd835ce`
  - [rawunloaded40](cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-f35b23a22166/probes.json),SHA256 `78e04cfee766f8d159fe8ad8c9a8cc4404b400b8761e85277e978c46b16268f2`
- `rounded-expand-22540f728bf9` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-22540f728bf9/condition.json),SHA256 `539410b1542d46a2e723c9b0e68d7009f8c8c8ef969de605d8843bd66fd4d28e`
  - [rawunloaded40](cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-22540f728bf9/probes.json),SHA256 `6783b0f574b72ac712f1175ff016951d8b2a928c4ca4d7a269500c78bea3310f`

## 실제실행·검증보류·다음준비단계

계산/GET의2단계가exit0이고 queue completed_preregistered_queue다. 과학worker wall165.51844380799594s,peakRSS540389376bytes,CPU1,newPDE0이며 queue elapsed173.16241982000065s와구분한다. 보고서작성시점에이배치의완료publication영수증은확인되지않아완료발행·commit을추측하지않았다. 시작댓글이나GET완료는결과발행완료와다르다.

각주파수·출력·그룹의signed source/metal/resistorpower를 구분하고 음수를제거하지않는다. 비구동/교차주파수에서금속단의음의전력과실제source흡수요구는 hardware sinking/compliance 검증과다르다. 물리GND net전류상쇄는localJ=0을뜻하지않고독립절연출력/귀환삭제를 주장하지 않는다. SC/XY/bulk/edge/contact·방향수렴/실험/생리활성/C1동등성/인체안전/COMSOL5.3a 설치·실행을 새로검증하지않았다. PBS계면은실제피부검증값이아니다. fullcomplex native 독립persistentbackup은미검증이고원본·실패증거는보존한다.

신규2조건은등록된strict lexicographic proxy objective 개선으로선택됐지만actual8screen에서기존e7을대체하지못했다. f35b는목표mean/P10모두실패,2254는mean만통과하고P10실패다. 기존e7은6/8이라도두P95실패로미채택이며본확장이승격하지않는다. Root는다음유한질문을별도등록할수있지만자동재시도/무기한worker/새후보채택을약속하지않는다. 완료된contact×.5/2/SC4진단은별도불확실성근거이며이번검색은nominalPBS·SC2조건을유지했다.

native source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`,physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,scout implementation/preregistration `6bbccf2c6970bb0c6a1e15b9f62eaa07bbd72da1`를구분한다. 이번docs해시검증은시뮬레이션재현/수렴/실험검증이아니며새물리fieldmap을생성하지않았다.

- [summary](cloud-rounded-drive-expansion-20261021T214000Z/summary.json),SHA256 `1f18ca8d2b2799cd46229ec9950b58f2312d33b72321de2aeedac4c398316b37`
- [decision](cloud-rounded-drive-expansion-context-20261021T214000Z/decision.json),SHA256 `2de0152a7cb653c180f1f8cc096a235dc328fc14cd08cf331fdd03b49ff79207`
- [queue_plan](cloud-rounded-drive-expansion-context-20261021T214000Z/queue-plan.json),SHA256 `0f9c6eb3cc00743bb3b8c67bbd5d2ea01073c87402fbe730ffb3423d611e819a`
- [queue](cloud-rounded-drive-expansion-context-20261021T214000Z/queue/summary.json),SHA256 `4d02760c2368970595ab18a28c8b3e7545cbd36ea141ed7b653fe079b61c753c`
- [feedback_after](cloud-rounded-drive-expansion-context-20261021T214000Z/feedback-after.json),SHA256 `2ea4e0f93efb7650e2cd0741a839b433ba971ca0cda7409fda67f1b4ef3340f2`
- [verified_rounded_snapshot](ROUNDED_FULLFACE_RESULTS_20261021.result-brief.json),SHA256 `23643003dc3f2df01891b541a81962bc61bd419012a05a50138b522885a6048f`
- [preregistration](cloud-rounded-drive-expansion-context-20261021T214000Z/preregistration.json),SHA256 `d2da3f5eb59b65bd46d97020d70f9aa2fc2441553dfc7349329b3967da48c60c`
- [cached_volume](cloud-rounded-fullface-context-20261021T200000Z/volume.json),SHA256 `95b1593cf23d2a539c57007f3909b56ba59692148768514fcae9b13dc65fd590`
- [previous_narrow_summary](cloud-rounded-drive-optimization-20261021T203000Z/summary.json),SHA256 `943a0418920f49a778f1edf21a52c1a449799ae44795b2adfcf71e6c89795732`
- [proxy_search](cloud-rounded-drive-expansion-20261021T214000Z/proxy-search.json),SHA256 `aa151f1a056d9559a905ef4ae86fb99ecacfdefbb45d0a1483023853323f8cb8`
- [previous_proxy_cache](cloud-rounded-drive-optimization-20261021T203000Z/proxy-search.json),SHA256 `c0148775132f07952122f736965d192a919a7dd69b79399809b1dc7ceac0a168`

[이전rounded형상2행GUI](CLOUD_ROUNDED_FULLFACE_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다.

[이전 narrow 최적화GUI](CLOUD_ROUNDED_DRIVE_OPTIMIZATION_RESULTS_20261021.html)와 [이전6조건 signed-weak GUI](CLOUD_ROUNDED_DRIVE_RESULTS_20261021.html)는완료된별도snapshot으로보존한다.
