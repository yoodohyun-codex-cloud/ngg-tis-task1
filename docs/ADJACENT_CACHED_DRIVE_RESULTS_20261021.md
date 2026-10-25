# 작업1: Adjacent square cached cosine drive (2026-10-21)

실제 신규full validation 2조건과기존cosine tau0/0.5/1 세조건을분리했다. 모든후보는미채택이며기존세조건은정확히재사용한결과로신규건수에포함하지않는다. 원래4-square/opposite기준을첫행으로유지하고adjacent square3h와같은5정규화/ROI/단위에서비교한다. 저장8gate통과가있더라도SC/XY/bulk/edge/contact/fullconvergence나실험채택으로승격하지않는다.

[7행 오프라인GUI](CLOUD_ADJACENT_CACHED_DRIVE_RESULTS_20261021.html) · [정확한5모드/출처brief](ADJACENT_CACHED_DRIVE_RESULTS_20261021.result-brief.json) · [원본summary](cloud-adjacent-cached-drive-20261021T220000Z/summary.json)

## 실제핵심결과

새2조건은둘다목표mean/P10만PASS,비표적6개모두FAIL로각2/8PASS이며미채택이다. adjacent-drive-ad5a53c9fbf0의skin8 mean/P10은4.19071428009/3.81646893616V/m,기준대비3.17257830968/4.68309305028%다. surfaceP95=44.3207719998,complementP95=29.5838771329V/m로상승했고활성limiter는SC+dermis체적vectorRMSJ95다. adjacent-drive-3c257930f5bd의skin8 mean/P10은4.78487859979/4.3731228944V/m,기준대비17.8005058432/19.9517246263%다. surfaceP95=44.666515688,complementP95=35.3631296449V/m로상승했고활성limiter는SC+dermis체적vectorRMSJ95다. 높아진절대목표값을보존하되피부부담정규화에서sourceupper가1Vpp를넘는결과이며raw동일전압gain이나깊이집중성공으로해석하지않는다.

## 실제proxy완료상태

등록범위z0/z1실수·허수[−1,+1],rho[0.5,1.5],steps0.25/0.1/0.05와3seeds다. 실제proxy93개가계획된모든level을완료했고상태proxy_search_complete_ranked_only/stop_reason=null이다. 96은상한이며cap종료·시간timeout·부분종료가아니다. 새fullvalidation은2개,기존tau3full결과는정확한별도재사용이다. tau0-targetregression은실제동일2074ROI평가와과거저장값비교PASS,mean/P10절대오차8.881784197001252e−16/4.440892098500626e−16V/m로0이라고반올림해주장하지않았다. 2074방향행렬SHA256 84b7f119bd37395a95e8592d186a96fdfb59e5f73a90a4e7ef22efe429a0d0b2를고정했지만연속방향/전역최적검증은아니다.

## 기하·회로·실제sourceVpp

D50mm/층SC·dermis·fat·muscle0.1·5·5·15mm/윗면/hXY.625SC2bulk14·14·40/351680cells다. 모든패드는15×15mm square/225mm²,총900mm²이며원래four-contact물리위치집합을유지하고source/return역할만다르다. adjacent는pad0SW(−10,−10)out0,pad1SE(+10,−10)out1,pad2NE(+10,+10)GND,pad3NW(−10,+10)동일GND다. 원래opposite는out1이NE다. 물리4pads/독립2outputs/공통GND노드1/50Ω,비구동주파수0Vthrough50Ω를유지했다. balancedcross225와별개square기하이며팬텀·형상·격자를늘리거나절연전원으로바꾸지않았다.

Cosine canonical command는frequency-row/output-column으로 c3000=[1,z0],c3030=[z1,rho]이며peak0.5V·+jωt basis다. 새actualg를한번공통적용한복소벡터와전체sourcewaveformVpp bounds를저장값대로보존한다. −j를곱한sine gauge를정확한wholewaveVpp/time-shift alias로취급하지않는다. 기존tau3도원본cosine계수·globalg를그대로재사용한다. 원래두square3h controls는3000/3030/9000/9090Hz4선,모든cosine drive는3000/3030Hz만활성이며9000/9090명령은0이다. 각outputmax−min의rawbracket폭≤1µV,출력전체최대upper만1Vpp인공통g와각출력exact1Vpp를구분한다. cachedsquare는과거nominalscalar이며새actualbracket영수증이아니다.

주ROI중심r≤5mm/깊이15–20mm,x/y수평,+z안쪽이다. E/TIS V/m,CV/P10mean무차원. maxTIS는기본파2074표본방향최대(연속최대하한),fixedTIS는(X+Y)/√2기본파변조,fullRMS는모든활성선전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/staircasegeometry와원래opposite-square rawcutoff를고정했고analytic volume재정규화는없다. SC전역최대를깊이집중으로해석하지않는다.

## raw source whole-wave Vpp 기준

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square/opposite 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached 4-square/adjacent square3h|cached nominal 1|3.40363522174 / 3.10629755642|0.07086183411|4.11265143593|52.2987957143 / 26.5429406318|2.39060030531 / 2.14320853698|
|cached return-net-square-tau0|[[0.9999999999999929, 1.0], [0.9999999999999929, 1.0]]|3.20897806131 / 2.92864542203|0.07086183411|3.87744495867|49.3077774633 / 25.0249244178|2.14021208758 / 1.91881954896|
|cached return-net-square-tau0p5|[[0.9998842675041715, 0.9998850083044936], [0.9999992497093182, 1.0]]|2.76560708023 / 2.3204830036|0.130090043148|3.87352256289|50.7621270921 / 28.2360530583|1.73618088445 / 1.52103634249|
|cached return-net-square-tau1|[[0.999805526465753, 0.999806269089573], [0.9999992515781166, 1.0]]|2.766908021 / 2.32168811518|0.130004896582|3.87215586412|52.6135869756 / 33.3888778837|1.52977169343 / 1.31132958852|
|adjacent-drive-ad5a53c9fbf0|[[0.7143177589654415, 0.7143177589654466], [0.9999992506845373, 1.0]]|2.76533619878 / 2.51838206933|0.0727360749536|3.23751346617|29.2460489972 / 19.5215805393|1.64820838878 / 1.49474260106|
|adjacent-drive-3c257930f5bd|[[0.9259321025407692, 0.9259327887960308], [0.9999992508210327, 1.0]]|3.08068910315 / 2.81558492375|0.0696663918179|3.55897444894|28.7580228602 / 22.7681446621|1.7204912261 / 1.56952649511|

## 동일8개 피부·접촉부담 (skin8)

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square/opposite 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached 4-square/adjacent square3h|cached nominal 0.959213174071|3.26481174443 / 2.9796015387|0.07086183411|3.94490943771|50.1656938372 / 25.4603383326|2.29309530679 / 2.05579386345|
|cached return-net-square-tau0|[[1.078092494625656, 1.0780924946256636], [1.078092494625656, 1.0780924946256636]]|3.45957516331 / 3.15735064891|0.07086183411|4.18024430827|53.1583448098 / 26.9791831934|2.30734658852 / 2.06866495428|
|cached return-net-square-tau0p5|[[1.1787971125783285, 1.1787979859326847], [1.1789326689580315, 1.1789335535008911]]|3.26046698268 / 2.73569527327|0.130090043148|4.56662571964|59.845174876 / 33.2884303689|2.04684189962 / 1.79320078026|
|cached return-net-square-tau1|[[1.2223484883513627, 1.2223493962730332], [1.2225853340098283, 1.2225862490201314]]|3.38278369877 / 2.83846396414|0.130004896582|4.73404451354|64.324647948 / 40.8207829708|1.87027783653 / 1.60321352286|
|adjacent-drive-ad5a53c9fbf0|[[1.0825091120350117, 1.0825091120350194], [1.5154436345835929, 1.515444770129792]]|4.19071428009 / 3.81646893616|0.0727360749536|4.90627285053|44.3207719998 / 29.5838771329|2.49776878285 / 2.26519985747|
|adjacent-drive-3c257930f5bd|[[1.438143400375188, 1.4381444662562313], [1.553183347895726, 1.5531845115088942]]|4.78487859979 / 4.3731228944|0.0696663918179|5.52774399096|44.666515688 / 35.3631296449|2.67224032457 / 2.43776424261|

raw/동일출력RMS전류합/동일총sourcepower/skin8/legacy의5모드를보존했다. skin8는원래opposite-square의8개피부·접촉수치한도이며sourcepower/1Vpp상한없음,legacy만이둘을추가하고동일전류/전력에도1Vpp상한은없다. actualsourceVpp가1을넘는모드의목표증가를raw동일전압gain으로표현하지않는다. contactnormalJ와SC+dermis체적vectorJ·접촉전압·SC/contact/실제피부SC+dermis/sourcepower를구분하고수치한도를인체안전한계라고부르지않는다.

5모드의절대목표mean/P10/CV/P10mean/max·fixedTIS/fullRMS·wholeXY보조ROI·표면/전체비표적P95·원래cutoff이상체적·전역hotspot과각burden을GUI/brief에보존했다. 전역SC최대값은깊이집중이아니다.

## 재사용tau3 및 신규2조건의저장8gate · 원래square raw기준 고정

|조건|mean|P10|surfaceP95|surface high@mean|surface high@P10|complementP95|complement high@mean|complement high@P10|
|---|---|---|---|---|---|---|---|---|
|return-net-square-tau0|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|
|return-net-square-tau0p5|FAIL|FAIL|FAIL|PASS|FAIL|FAIL|FAIL|FAIL|
|return-net-square-tau1|FAIL|FAIL|FAIL|PASS|PASS|FAIL|FAIL|FAIL|
|adjacent-drive-ad5a53c9fbf0|PASS|PASS|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|
|adjacent-drive-3c257930f5bd|PASS|PASS|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|

각gate의기준·후보·변화율·단위·방향은원본/GUI에보존했다. 원래square/adjacent square의cached행에새screen개수를부여하지않았다. oldtau3의판정은과거그대로재사용하고신규full조건의실제판정을별도로표시했다.

## nativeφ40·carrierRMS·signed power·범위

계산은cachednative adjacent-square basis를재사용한newPDE0이다. 등록proxy상한96개에대해실제완료개수/종료상태는아래원본그대로보존한다. proxy목표는동일SHA2074방향/전체ROI의정확한표본mean/P10이고off-target은lambda0,.5,1의PSD최대고유값upperbound최솟값을ranking에만사용한다. wholeVpp정규화전proxy를raw1Vpp/full8gate결과와동일시하지않는다. 기존tau3의fullvalidation은immutable exactreuse이고새spectralproxycache는별개로visited시한번평가한다. oldalias proxy2074_three_lambda_spectral_cache_available:false는full결과부재를뜻하지않는다. 실제tau0-targetregression상태·오차는원본필드를그대로보존한다. 연속방향최대/전역최적값/oldtau재계산/새PDE를주장하지않는다.

각drive의5모드40개무부하예측과rawJSON fullwaveVpp bounds/RMS/기본파envelope·스펙트럼/검사영수증을원본candidateID/runID/SHA로연결했다. 깊이5/10/15/20mm×중심·X/Y±5mm의5개probe중심×X/Y차동방향,tipgap5mm를유지하고probe중심과팁간격을구분한다. 기존tau3는정확한원본40/5모드결과를재사용해새계산으로세지않는다. cachedsquare2행은upstreamraw40영수증으로정규화probe를새로발급하지않았다. ETA5001/DSOX1202Aactualswitch·팬텀portZ/부하·보정·filter응답은미검증으로loaded예측은보류다.

저장raw carrier별RMS/balance의목표r5와wholeXY보조ROI통계는별도로표시했고다른정규화에새scale/recompute하지않았다. carrierRMS·전체fieldRMS·방향별TIS·최대표본방향TIS는별개다. 각모드signed ideal source/metal delivered/50Ωloss의출력별합계·주파수별값·그룹총합을보존했다. 음수와비활성9000/9090Hz의0계수·전력선을제거하지않았다. 신규2조건의GND net전류와localJ·patch절대전류적분은brief/원본에보존했다. oldtau3원본에없는localJ/familyproof는미제공으로남겼다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json),SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `adjacent-square15-xy80` / sourcecase `adjacent-square15-xy80` / run `cloud-finite-loop-20261020T002600Z-fine`
  - source `be724b0b314263f284fdbc5397bdaf019685fa29`, configSHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
  - [condition/upstream sourceJSON](../data-native/cloud-finite-loop-20261020T002600Z-fine/postprocess/adjacent-square15-xy80/summary.json),SHA256 `b65cffd90dd881570de4079d898a7e790ed1983d7b4b43baaf9866a1f6a00620`
  - [rawunloaded40](../data-native/cloud-finite-loop-20261020T002600Z-fine/postprocess/adjacent-square15-xy80/probes.json),SHA256 `e3754b36902d1efe63e54f9e4bd4f424eae4f7306dc410c9ae4006d6f73ecf61`
- `return-net-square-tau0` / sourcecase `adjacent-square15-xy80` / run `cloud-finite-loop-20261020T002600Z-fine`
  - source `be724b0b314263f284fdbc5397bdaf019685fa29`, configSHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
  - [condition/upstream sourceJSON](cloud-next-return-current-20261021T172000Z/return-net-square-tau0/condition.json),SHA256 `220924f62826c6c35ba28291efa9a7bf9e66dc41db6858f2ed0be19ca7768d6c`
  - [rawunloaded40](cloud-next-return-current-20261021T172000Z/return-net-square-tau0/probes.json),SHA256 `00eb2bd63a73101b570160f69091894082a29f02f029ddd48970f52ee47b9142`
- `return-net-square-tau0p5` / sourcecase `adjacent-square15-xy80` / run `cloud-finite-loop-20261020T002600Z-fine`
  - source `be724b0b314263f284fdbc5397bdaf019685fa29`, configSHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
  - [condition/upstream sourceJSON](cloud-next-return-current-20261021T172000Z/return-net-square-tau0p5/condition.json),SHA256 `fd2165b6a967fa79a410014965ca4ba0854c941f3aaefd1184e4f13e5edeec45`
  - [rawunloaded40](cloud-next-return-current-20261021T172000Z/return-net-square-tau0p5/probes.json),SHA256 `f4d9d0a6c3457616199d669c00c13b74c96c7c9ff5a6f895a7ee07ef15982e89`
- `return-net-square-tau1` / sourcecase `adjacent-square15-xy80` / run `cloud-finite-loop-20261020T002600Z-fine`
  - source `be724b0b314263f284fdbc5397bdaf019685fa29`, configSHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
  - [condition/upstream sourceJSON](cloud-next-return-current-20261021T172000Z/return-net-square-tau1/condition.json),SHA256 `7230e59cab7a6ab272cc2a14883965a378ae00593a8f8dbd9980fb217f1b2a66`
  - [rawunloaded40](cloud-next-return-current-20261021T172000Z/return-net-square-tau1/probes.json),SHA256 `4091ea4c2edc5221651a91d996302cc77e2132982365c9c84981a4e4709198b0`
- `adjacent-drive-ad5a53c9fbf0` / sourcecase `adjacent-square15-xy80` / run `cloud-finite-loop-20261020T002600Z-fine`
  - source `be724b0b314263f284fdbc5397bdaf019685fa29`, configSHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
  - [condition/upstream sourceJSON](cloud-adjacent-cached-drive-20261021T220000Z/adjacent-drive-ad5a53c9fbf0/condition.json),SHA256 `2e1aa3c43e84af703ce328a4cbf51be4664706b040c8a3d93643297e01c363f2`
  - [rawunloaded40](cloud-adjacent-cached-drive-20261021T220000Z/adjacent-drive-ad5a53c9fbf0/probes.json),SHA256 `055534efea05e892e722930bd45fc54778ce30c7221869fa179b0c5ffa6f22ee`
- `adjacent-drive-3c257930f5bd` / sourcecase `adjacent-square15-xy80` / run `cloud-finite-loop-20261020T002600Z-fine`
  - source `be724b0b314263f284fdbc5397bdaf019685fa29`, configSHA256 `021bd4486d756aedb7a1bd9e5b70d27970fe3efd0eda84e622952dc44ffc243e`
  - [condition/upstream sourceJSON](cloud-adjacent-cached-drive-20261021T220000Z/adjacent-drive-3c257930f5bd/condition.json),SHA256 `6b3916f4c31e8de9c7f3b25ddb856f3089c452c054ab1da910683a11bc6d6883`
  - [rawunloaded40](cloud-adjacent-cached-drive-20261021T220000Z/adjacent-drive-3c257930f5bd/probes.json),SHA256 `d8dce8def5a277d811f5d99662e5ea1ea135ea312e9aa9cb56ad15fa92636218`

## 실제실행·검증보류·다음준비단계

Scientificworkerstatus calculated_unadopted, wall125.43468138100434s,RSS542560256bytes,CPU1,newPDE0. Queue completed_preregistered_queue, phase/stage상태는원본영수증과구분한다. 완료publication영수증은작성시점미확인으로발행commit을추측하지않았다.

signedsource/metal/resistorpower의주파수별·출력별·그룹총합을구분하고음수와비활성0계수를제거하지않는다. 실제AWG흡수/sink/compliance·동기위상은미검증이다. oldtaucondition에familyproof/returnlocal필드가없으면미제공으로표시하고새proof를옛원본필드처럼만들지않는다. source_Rs_fit_window_Hz500은500Hz이지Rs500Ω가아니다. nominalselectedRs236.5717747232937Ω·measurementarea.0001m²에서(Zmeasured−Rs)×area를한번적용한PBSΩm²를유지하고Rs/면적을중복차감·스케일링하지않는다. PBS피부전이·SC/XY/bulk/edge/contact수렴·실험·생리활성/C1동등성·안전·COMSOL5.3a설치실행·fullnativepersistentbackup은미검증이며원본/실패증거는보존한다. 이번보고서는docsJSON만읽고native/배열/NPZ/E/φ를읽거나계산·렌더하지않았다.

현재저장결과만보고하며root의다음유한선정은별도등록한다. proxyobjective와저장8gate결과를구분하고신규final이0개면기존결과를신규로대체하거나없는값을발명하지않는다. 자동재시도/추가워커/무기한백그라운드실행을약속하지않는다.

native source `be724b0b314263f284fdbc5397bdaf019685fa29`,physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,scout implementation/preregistration `f17d38516aef44b074fb2bd9796253efa1166fe7`를구분한다. 이번docs해시검증은시뮬레이션재현/수렴/실험검증이아니며새물리fieldmap을생성하지않았다.

- [summary](cloud-adjacent-cached-drive-20261021T220000Z/summary.json),SHA256 `8745f8b2c37baae6b8ad106d8bac3789123561866224148e0ffc6acd25ee286f`
- [decision](cloud-adjacent-cached-drive-context-20261021T220000Z/decision.json),SHA256 `d9b6f92670130fac597b41aa20dca91632d07bba8bca41337e789c07880c2261`
- [queue_plan](cloud-adjacent-cached-drive-context-20261021T220000Z/queue-plan.json),SHA256 `9a3aad1ee9f686a1ffdd06290b763e18515b42e7e26f05f5201d22cf829e3e64`
- [preregistration](cloud-adjacent-cached-drive-context-20261021T220000Z/preregistration.json),SHA256 `01ce7fb7d0dcd4b47f5a0e93331bbeaed79fe8ec1b8a3b955062b73a10be40ec`
- [input_audit](ADJACENT_CACHED_INPUT_AUDIT_20261021.md),SHA256 `cf16f8831b22f0bcf52f5ba3ca7d16a42195a6d99a9e839b1ebed695eadb35f6`
- [queue](cloud-adjacent-cached-drive-context-20261021T220000Z/queue/summary.json),SHA256 `e29e4bd351976f46988d8faa9ecc5a6d31a7dd8e7b780293ddfe908d0deb8e4b`
- [feedback_after](cloud-adjacent-cached-drive-context-20261021T220000Z/feedback-after.json),SHA256 `54e11b063e96a2c5e73cdcbdf30caa9efbca489570b2fe391a408e47b848c4e0`
- [cached_volume](cloud-adjacent-cross-20261021T164000Z/volume.json),SHA256 `5ae3c3bc95021024109e6b3c0f4985b978b8a4262c4a7cd3441aca819d6bb725`
- [proxy_search](cloud-adjacent-cached-drive-20261021T220000Z/proxy-search.json),SHA256 `be69f73faa54c2ff64f150cecf539189211324d0eecdffa068f83e9828afb79b`

[이전adjacent2×2factorialGUI](CLOUD_ADJACENT_CROSS_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다.
