# 작업1: 회전 coherent의 단일 전극쌍 RMS 비교 (2026-10-21)

회전 square/sine/coherent r1·φ90°의3개 reference를 raw/skin8로 나눈6개 기준에서 centre와 true ROI energy RMS를 각각 맞춘 **12개 C1 비교**다. reference는 모두 미채택 상태다. 같은 전기장 RMS는 TIS 변조·생리적 활성·안전성의 동등성을 뜻하지 않는다. 단일 sine는 temporal envelope variation=0이고 carrier RMS는0일 필요가 없다.

[12행 오프라인 GUI](CLOUD_ROTATION_COHERENT_SINGLE_PAIR_RESULTS_20261021.html) · [원본 summary](cloud-rotation-coherent-single-pair-20261021T183500Z/summary.json) · [TIS reference 7행 GUI](CLOUD_ROTATION_COHERENT_RESULTS_20261021.html)

## 단일 전극쌍과 footprint

C1은 귀환 전극을 포함한 물리2패드/독립1출력, 3000 Hz pure sine다. out0=(-10,−10) mm, GND=(+10,−10) mm,50 Ω 출력저항이다. 회전 TIS는 물리4패드/독립2출력/공통GND50 Ω이며 pad0→out0,pad1→out1,pad2·3→GND다. C1과 TIS의 접촉면적은 서로 다르고 같은 footprint로 정규화하지 않았다.

|cohort|물리 pad|독립 출력|귀환 node|각 pad 면적mm²|총 접촉면적mm²|
|---|---|---|---|---|---|
|C1|2|1|1|[225.0, 225.0]|450|
|rotated_TIS|4|2|1|[281.25000000000006, 281.25000000000006, 168.75, 168.75]|900|

D50 mm, 층SC/dermis/fat/muscle0.1/5/5/15 mm, XY0.625/SC2/bulk14·14·40의 같은 저장 모델이다. centre는 native 복소 전기장을(0,0,20) mm에 보간한 전체 활성선 벡터 RMS다. ROI energy RMS는 중심r≤5 mm·깊이15–20 mm에서 `sqrt(weighted mean(E_RMS²))`이며 `mean(E_RMS)`와 다르다. x/y수평·+z안쪽 깊이다. square3h reference는3000/3030/9000/9090 Hz4선, sine/coherent는3000/3030 Hz2선이다.

## reference의 실제 source와 RMS

square의 저장 Vpp interval은 과거 nominal 정의를 이어받았으며, sine/coherent는 source waveform bracket에 연결된다. skin8는 canonical 원래 square의8개 수치 피부·접촉 한도이며 source power와1 Vpp ceiling을 포함하지 않는다. 원래4pad square 기준은 위7행 GUI 첫 행에 유지했다.

|reference / mode|파형|활성Hz|source Vpp interval|output RMS mA|centre RMS V/m|ROI energy RMS V/m|
|---|---|---|---|---|---|---|
|rotation-square-control--raw|square_3h|[3000, 3030, 9000, 9090]|[[1.0, 1.0], [1.0, 1.0]]|[1.5066102716657168, 1.5676207554553605]|2.261326204|2.495546333|
|rotation-square-control--skin_contact_only|square_3h|[3000, 3030, 9000, 9090]|[[0.9894546450470344, 0.9894546450470344], [0.9894546450470344, 0.9894546450470344]]|[1.490722531575218, 1.5510896381574477]|2.237479716|2.469229911|
|rotation-sine-control--raw|sine|[3000, 3030]|[[1.0, 1.0], [1.0, 1.0]]|[1.3410207044405316, 1.3939103618578277]|2.025148635|2.234722839|
|rotation-sine-control--skin_contact_only|sine|[3000, 3030]|[[1.0735507840960077, 1.0735507840960077], [1.0735507840960077, 1.0735507840960077]]|[1.4396538287411131, 1.4964335619320208]|2.174099905|2.399088456|
|rotation-coherent-r1-p090--raw|coherent_two_tone_sine|[3000, 3030]|[[0.9999992544051025, 1.0], [0.9999992543822719, 1.0]]|[0.9485123659900654, 0.9853845728938536]|1.432073514|1.580273149|
|rotation-coherent-r1-p090--skin_contact_only|coherent_two_tone_sine|[3000, 3030]|[[1.5178242353099387, 1.5178253669927877], [1.517824235275286, 1.5178253669927877]]|[1.4396761300060683, 1.4956417009816447]|2.173637506|2.398578672|

## TIS reference의 피부·접촉·전력 (6행)

|reference / mode|surface_J_RMS_max_A_m2|surface_J_RMS_p95_A_m2|contact_voltage_RMS_max_V|SC_power_W|contact_power_W|source_power_W|bulk_skin_J_vector_RMS_max_A_m2|bulk_skin_J_vector_RMS_p95_A_m2|skin_SC_plus_dermis_power_W|
|---|---|---|---|---|---|---|---|---|---|
|rotation-square-control--raw|22.51278446|13.27304262|0.002371304393|2.151822233e-06|1.817622623e-06|0.001174127487|22.49221483|7.072845719|0.0007416381304|
|rotation-square-control--skin_contact_only|22.27537915|13.13307367|0.002346298147|2.106678067e-06|1.779489799e-06|0.001149494873|22.25502644|6.998260051|0.0007260789293|
|rotation-sine-control--raw|18.81406345|11.48879228|0.001981735802|1.879683996e-06|1.408188189e-06|0.0009328816407|18.90419497|6.291548045|0.0005889211297|
|rotation-sine-control--skin_contact_only|20.19785257|12.33380196|0.002127494024|2.16635702e-06|1.622952781e-06|0.001075156619|20.29461333|6.754296337|0.0006787382486|
|rotation-coherent-r1-p090--raw|13.27286393|8.135345053|0.001400426335|9.403432624e-07|7.042329391e-07|0.0004664578278|13.34480045|4.448655323|0.0002944686985|
|rotation-coherent-r1-p090--skin_contact_only|20.14588957|12.34803309|0.002125602616|2.16635702e-06|1.62240751e-06|0.001074622672|20.25507664|6.752281898|0.0006783951751|

reference surface_J는 접촉면, bulk_skin_J_vector는SC+dermis 체적 전체벡터 RMS다. 전류밀도A/m², 접촉전압V, 전력W이며 source_power는 두 출력의 그룹총합이다.

## C1 필요 전압·전류 및 RMS (12행)

source Vpp는50 Ω 앞 인가전압이고 metal Vpp는50 Ω 뒤 금속단 전압이다. centre와 ROI energy 일치는 각각 별도의 정의로 적용한다. 각 행이 둘을 동시에 맞췄다고 해석하지 않는다.

|reference branch / mode|일치 정의|reference centre RMS V/m|reference ROI energy RMS V/m|C1 필요 source Vpp|C1 metal Vpp|C1 달성 centre RMS V/m|C1 달성 ROI energy RMS V/m|C1 source RMS mA|C1 source peak mA|
|---|---|---|---|---|---|---|---|---|---|
|rotation-square-control--raw|centre20_E_RMS|2.261326204|2.495546333|1.777090065|1.547466984|2.261326204|2.491754171|1.663361593|2.352348523|
|rotation-square-control--raw|ROI_energy_RMS|2.261326204|2.495546333|1.77979459|1.54982205|2.264767681|2.495546333|1.665893037|2.355928526|
|rotation-square-control--skin_contact_only|centre20_E_RMS|2.237479716|2.469229911|1.758350019|1.531148395|2.237479716|2.465477739|1.645820854|2.327542173|
|rotation-square-control--skin_contact_only|ROI_energy_RMS|2.237479716|2.469229911|1.761026025|1.533478626|2.240884902|2.469229911|1.648325603|2.331084423|
|rotation-sine-control--raw|centre20_E_RMS|2.025148635|2.234722839|1.591487116|1.385846343|2.025148635|2.23151023|1.48963668|2.106664395|
|rotation-sine-control--raw|ROI_energy_RMS|2.025148635|2.234722839|1.593778311|1.387841486|2.028064153|2.234722839|1.491781245|2.109697269|
|rotation-sine-control--skin_contact_only|centre20_E_RMS|2.174099905|2.399088456|1.708542241|1.487776428|2.174099905|2.395639557|1.599200625|2.261611213|
|rotation-sine-control--skin_contact_only|ROI_energy_RMS|2.174099905|2.399088456|1.711001955|1.489918315|2.177229862|2.399088456|1.601502925|2.264867157|
|rotation-coherent-r1-p090--raw|centre20_E_RMS|1.432073514|1.580273149|1.125411985|0.9799941631|1.432073514|1.578001062|1.05338897|1.489716967|
|rotation-coherent-r1-p090--raw|ROI_energy_RMS|1.432073514|1.580273149|1.127032411|0.981405209|1.434135486|1.580273149|1.054905693|1.491861938|
|rotation-coherent-r1-p090--skin_contact_only|centre20_E_RMS|2.173637506|2.398578672|1.70817886|1.48746|2.173637506|2.395130041|1.598860499|2.261130203|
|rotation-coherent-r1-p090--skin_contact_only|ROI_energy_RMS|2.173637506|2.398578672|1.710638383|1.489601721|2.176767221|2.398578672|1.601162621|2.264385894|

## C1 피부·접촉 부담 (동일12행)

contact J는 접촉면 RMS 전류밀도, bulk skin J는SC+dermis 체적 전체벡터 RMS 전류밀도다. 수치 한도와 RMS 비교는 인체 안전 한계·실험 검증을 뜻하지 않는다.

|reference / mode|일치정의|contact Jmax A/m²|contact J95 A/m²|SC+dermis Jmax A/m²|SC+dermis J95 A/m²|contact V RMS|
|---|---|---|---|---|---|---|
|rotation-square-control--raw|centre20_E_RMS|26.60670709|19.3703491|26.51134793|7.828365941|0.002812563732|
|rotation-square-control--raw|ROI_energy_RMS|26.64719943|19.39982853|26.55169514|7.840279809|0.002816844128|
|rotation-square-control--skin_contact_only|centre20_E_RMS|26.32612992|19.16608189|26.23177636|7.745813044|0.002782904249|
|rotation-square-control--skin_contact_only|ROI_energy_RMS|26.36619525|19.19525045|26.27169809|7.757601276|0.002787139507|
|rotation-sine-control--raw|centre20_E_RMS|23.82784777|17.34726991|23.74244811|7.010755268|0.002518813779|
|rotation-sine-control--raw|ROI_energy_RMS|23.86215169|17.37224403|23.77662909|7.020848348|0.002522440006|
|rotation-sine-control--skin_contact_only|centre20_E_RMS|25.58040465|18.62317522|25.48872379|7.526401815|0.002704074507|
|rotation-sine-control--skin_contact_only|ROI_energy_RMS|25.61723165|18.6499862|25.5254188|7.537237249|0.002707967446|
|rotation-coherent-r1-p090--raw|centre20_E_RMS|16.84974085|12.26703332|16.78935092|4.957619781|0.001781166299|
|rotation-coherent-r1-p090--raw|ROI_energy_RMS|16.87400197|12.28469602|16.81352509|4.964758016|0.001783730913|
|rotation-coherent-r1-p090--skin_contact_only|centre20_E_RMS|25.57496409|18.61921435|25.48330272|7.524801063|0.002703499391|
|rotation-coherent-r1-p090--skin_contact_only|ROI_energy_RMS|25.61178823|18.64602325|25.51999489|7.535635657|0.002707392028|

## C1 손실·전력 W (동일12행)

|reference / mode|일치정의|SC W|dermis W|SC+dermis W|contact W|tissue+contact W|50Ω loss W|source W|
|---|---|---|---|---|---|---|---|---|
|rotation-square-control--raw|centre20_E_RMS|2.173746055e-06|0.0006909924769|0.000693166223|1.619704879e-06|0.0008850744945|0.0001383385894|0.001023413084|
|rotation-square-control--raw|ROI_energy_RMS|2.18036747e-06|0.0006930972986|0.0006952776661|1.624638638e-06|0.0008877705065|0.0001387599805|0.001026530487|
|rotation-square-control--skin_contact_only|centre20_E_RMS|2.128141938e-06|0.0006764957965|0.0006786239385|1.585724272e-06|0.0008665060694|0.0001354363142|0.001001942384|
|rotation-square-control--skin_contact_only|ROI_energy_RMS|2.134624439e-06|0.0006785564601|0.0006806910845|1.590554522e-06|0.0008691455204|0.0001358488647|0.001004994385|
|rotation-sine-control--raw|centre20_E_RMS|1.743396554e-06|0.0005541925655|0.0005559359621|1.299042222e-06|0.0007098510059|0.0001109508719|0.000820801878|
|rotation-sine-control--raw|ROI_energy_RMS|1.748419952e-06|0.0005557894082|0.0005575378281|1.302785264e-06|0.0007118963605|0.0001112705641|0.0008231669249|
|rotation-sine-control--skin_contact_only|centre20_E_RMS|2.009284204e-06|0.0006387131864|0.0006407224706|1.497160821e-06|0.0008181112957|0.000127872132|0.0009459834279|
|rotation-sine-control--skin_contact_only|ROI_energy_RMS|2.015073728e-06|0.0006405535656|0.0006425686393|1.50147472e-06|0.00082046859|0.000128240581|0.0009487091712|
|rotation-coherent-r1-p090--raw|centre20_E_RMS|8.717922443e-07|0.0002771261532|0.0002779979455|6.495911279e-07|0.0003549637632|5.548141607e-05|0.0004104451794|
|rotation-coherent-r1-p090--raw|ROI_energy_RMS|8.74304554e-07|0.0002779247686|0.0002787990732|6.514631039e-07|0.0003559866892|5.564130107e-05|0.0004116279904|
|rotation-coherent-r1-p090--skin_contact_only|centre20_E_RMS|2.008429606e-06|0.000638441526|0.0006404499556|1.496524042e-06|0.0008177633328|0.0001278177448|0.0009455810779|
|rotation-coherent-r1-p090--skin_contact_only|ROI_energy_RMS|2.01421745e-06|0.0006402813713|0.0006422955887|1.500836689e-06|0.0008201199433|0.0001281860869|0.0009483060305|

## source-bound 무부하40개

각 matching 행의 정확한 amplitude_scale을 적용한40개 무부하 native-phi 예측은 원본 summary의 `targets[].matches.{centre20_E_RMS,ROI_energy_RMS}.unloaded_probe40`에 저장돼 있다. 깊이5/10/15/20 mm × 중심·X/Y±5 mm의5개 probe 중심 × X/Y 차동 방향이며 tip gap5 mm다. probe 중심 위치와 팁 간격은 다르다. Vpp bounds/RMS/기본파 envelope를 보존하며 원형 waveform/spectrum은 raw probe JSON에 연결한다. loaded metal Vpp는 회로의 금속단 전압이며 측정기 부하 반영 예측이 아니다. ETA5001/DSOX1202A 실제 switch·팬텀port impedance/부하·보정은 미검증이다.

- [C1 raw probe40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-C1pair0-xy80/probes.json), SHA256 `7ac08215db1ec71a6880d8eded01fcec203e2992e191f91d42ebf780484da83b`
- `rotation-square-control--raw`: [reference raw probe](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/probes.json), SHA256 `24c7b539964ab0a24e18ea3c999758650aa898c40684cf186dd6aab131e46932`; source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
- `rotation-square-control--skin_contact_only`: [reference raw probe](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/probes.json), SHA256 `24c7b539964ab0a24e18ea3c999758650aa898c40684cf186dd6aab131e46932`; source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
- `rotation-sine-control--raw`: [reference raw probe](cloud-rotation-coherent-20261021T182000Z/rotation-sine-control/probes.json), SHA256 `872ca98c4ba07db2a49280ca36290f743cb8af1454ff3d45b795b014b41cbdca`; source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
- `rotation-sine-control--skin_contact_only`: [reference raw probe](cloud-rotation-coherent-20261021T182000Z/rotation-sine-control/probes.json), SHA256 `872ca98c4ba07db2a49280ca36290f743cb8af1454ff3d45b795b014b41cbdca`; source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
- `rotation-coherent-r1-p090--raw`: [reference raw probe](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r1-p090/probes.json), SHA256 `fe39043daf8048c46619f1c3819d34a08ce668be190d64de33a672a24a2e882d`; source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
- `rotation-coherent-r1-p090--skin_contact_only`: [reference raw probe](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r1-p090/probes.json), SHA256 `fe39043daf8048c46619f1c3819d34a08ce668be190d64de33a672a24a2e882d`; source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`

C1 case `baseline-square15-C1pair0-xy80`, run `cloud-mesh-c1-20261019T190000Z`, implementation source `1b901cbf501e6deabe736fd3d9e75a7f6313b268`. C1 config SHA256 `326ca4c1bb380de90f1d794c6d0acca0d61a90a54c0f95e2168f6e55ae1706e3`다. reference summary SHA256 `abe8f354a53ea7a58abeb62743c5a206b4ecd435056b45deda8b87d45c8bdf43`에 연결했다. 로컬 native 링크는 공개 GitHub에서 파일 제공을 보장하지 않는다.

## 실행·발행·검증 범위

실제 wall `1.1767712049986585 s`, CPU1, peakRSS `252346368 bytes`. 새PDE/nativeRHS/reference recomposition은 모두0이다. 큐는`completed_preregistered_queue`, C1/GET/발행3단계 exit0이다. 발행`published_completed_batch`, `2026-10-21T18:03:47.370371+00:00`, commit `61cbbfeaed9459cf68270f4972b61f6a3ab6d540`다.

문서 작성은 완료 JSON/설정 해시 일치 확인과 저장값 복사만 수행했다. native E/phi/NPZ를 읽거나 재계산하지 않았다. 파일 해시 확인과 시뮬레이션 재현·mesh/SC/XY/bulk/edge/contact·연속방향 수렴·실험 검증을 구분한다. source footprint·단일주파수 envelope·TIS 변조가 서로 달라 같은 RMS만으로 생리적 활성화가 같다고 결론 내리지 않는다. 기존 실패와 과거 결과를 보존한다.

- [C1 결과](cloud-rotation-coherent-single-pair-20261021T183500Z/summary.json), SHA256 `ca3fe19e82f201c447083fa456a2332960bea8b6c5ea6d70f515195a85d41fec`
- [사전등록](cloud-rotation-coherent-single-pair-context-20261021T183500Z/preregistration.json), SHA256 `982557229e9c527ca93daf28b1d21c5ec250b9b83d621d74be81353a315c6e21`
- [선정 decision](cloud-rotation-coherent-single-pair-context-20261021T183500Z/decision.json), SHA256 `267f316135f6e6537532a629e1aca3890f8a7196bfd96aa2c91a12754e09f6ee`
- [큐 summary](cloud-rotation-coherent-single-pair-context-20261021T183500Z/queue/summary.json), SHA256 `d7851379f09869e8bef1736a342c8887d8424eb02ec3d02a4087170b377bf91f`
- [GET feedback](cloud-rotation-coherent-single-pair-context-20261021T183500Z/feedback-after.json), SHA256 `b8666c8969e265465560fb3edb241a9e2986d0f65b2071528b581d105faaa48f`
- [발행 영수증](cloud-rotation-coherent-single-pair-context-20261021T183500Z/single-pair-publication-20261021T183500Z.json), SHA256 `32bc0f4c69a034105534cb7abd0c409ef3207a346912f2feb238cab7113e8f30`
