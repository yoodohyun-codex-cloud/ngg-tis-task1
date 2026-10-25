# 작업1: 회전 형상의 pure-sine 대조군과 coherent4조건 (2026-10-21)

새 sine control 및 coherent 4조건 모두 **채택하지 않는다**. 원래 square 기준의 skin8에서 목표 ROI 평균/P10의 2개 조건은 통과하지만, 표면·전체 비표적 6개 조건은 전부 실패했다. 캐시 회전 square를 부모 형상보다 개선됐다고 표현하지 않는다.

[7행 오프라인GUI](CLOUD_ROTATION_COHERENT_RESULTS_20261021.html) · [정확한값/5모드/출처brief](ROTATION_COHERENT_RESULTS_20261021.result-brief.json) · [원본summary](cloud-rotation-coherent-20261021T182000Z/summary.json)

## 고정 기하와 새 파형

D50mm, 층SC/dermis/fat/muscle0.1/5/5/15mm·윗면부착, XY0.625/SC2/bulk14·14·40을유지했다. 원래 square 기준은225 mm²×4의 별도 형상이다. 회전 가족은 총900 mm²의 물리4패드/독립2출력/공통GND/50 Ω이다. pad0→out0, pad1→out1, pad2·3→GND이며면적281.25/281.25/168.75/168.75mm², fullfaces720/720/432/432이다. `asym-return2-rot90-xy80` mask·물성·접촉은그대로다. fullfaces가격자·가장자리·접촉수렴을뜻하지않는다.

cached square3h 두행은3000/3030/9000/9090Hz4선, 신규sine/coherent5행은3000/3030Hz2선·beat30Hz·고조파0이다. sine control은각출력의자기기본파만, coherent는두출력모두두주파수를포함하며mix ratio0.5/1.0과phase90°/270°의4조합이다. 비구동주파수종단은0V through50Ω이다. 초기2/2.01kHz기록과별도다.

**새회전sine의fullROI/volume NPZ와40phi는이번worker에서실제한번계산했다.** 기존nativepost sine에전체ROI NPZ가있었다고가정하지않았다. 기존sine electrical/contact/centre-field만별도회귀했고`passed=true, maximum_absolute_error=0`이다. 이는새fullROI를과거배열과재현검증했다는뜻이아니다. 배열새해석을한과학worker와완료JSON만복사한이문서작성과정을구분한다. 새PDE0이다.

raw sourceVpp는50Ω앞전체다중tone파형의max−min이다. 기본파Vpp또는2√2RMS와같지않다. 신규5행의 raw bracket은 output별 upper1 Vpp, 폭≤1 µV 검증을 통과했다. cached2행의 nominal scalar는 과거 source 정의이며 새 actual waveform bracket을 계산한 값이 아니다. 정규화모드에서는저장된스케일된bounds를그대로보존했고, column정규화뒤unitary여부를별도표시했다. 실제하드웨어파형·위상·보정은미검증이다.

## raw 실제 source 1 Vpp 비교

|조건|source Vpp (신규actual bounds / cached nominal)|ROI mean / P10 (V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|full RMS mean / P10(V/m)|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square · square3h|cached nominal 1.0 Vpp / output|4.06184894 / 3.64573574|0.0807616216|4.97132719|25.2592218 / 23.4357186|2.30694946 / 2.10466937|
|회전 cached · square3h 1:1|cached nominal 1.0 Vpp / output|4.42654541 / 3.98719667|0.0793127416|5.38131052|32.5014435 / 26.1632633|2.48930139 / 2.26800249|
|rotation-sine-control|[[1.0, 1.0], [1.0, 1.0]]|4.17338703 / 3.75916507|0.0793127416|5.07354821|30.6426548 / 24.6669612|2.22914016 / 2.0311167|
|rotation-coherent-r0p5-p090|[[0.9999992568803825, 1.0], [0.9999992519145955, 1.0]]|3.20225166 / 2.91941142|0.0716010483|3.76929354|34.2219079 / 27.2450346|1.66156965 / 1.51395335|
|rotation-coherent-r0p5-p270|[[0.9999992568803825, 1.0], [0.9999992519145955, 1.0]]|3.17899875 / 2.88963419|0.0728662057|3.77082175|32.5331086 / 25.5767676|1.66159157 / 1.51399121|
|rotation-coherent-r1-p090|[[0.9999992544051025, 1.0], [0.9999992543822719, 1.0]]|3.12507186 / 2.85070944|0.0701042168|3.57860613|44.6719683 / 33.8235937|1.57632538 / 1.43627999|
|rotation-coherent-r1-p270|[[0.9999992544051025, 1.0], [0.9999992543822719, 1.0]]|3.12499954 / 2.85051456|0.0701138466|3.57865153|44.6403454 / 33.8176677|1.57635137 / 1.43631848|

## 원래 square의 동일 8개 피부·접촉 부담 (skin8)

|조건|source Vpp (신규actual bounds / cached nominal)|ROI mean / P10 (V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|full RMS mean / P10(V/m)|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square · square3h|cached nominal 1.0 Vpp / output|4.06184894 / 3.64573574|0.0807616216|4.97132719|25.2592218 / 23.4357186|2.30694946 / 2.10466937|
|회전 cached · square3h 1:1|cached nominal 0.9894546450470344 Vpp / output|4.37986591 / 3.94515026|0.0793127416|5.32456269|32.1587042 / 25.8873624|2.46305082 / 2.2440856|
|rotation-sine-control|[[1.0735507840960077, 1.0735507840960077], [1.0735507840960077, 1.0735507840960077]]|4.48034292 / 4.03565461|0.0793127416|5.44671166|32.8964461 / 26.4812355|2.39309517 / 2.18050692|
|rotation-coherent-r0p5-p090|[[1.4401325329259227, 1.440133603117455], [1.4401325257745259, 1.440133603117455]]|4.61167023 / 4.20434249|0.0716010483|5.42828628|49.2841196 / 39.2364899|2.39288229 / 2.18029509|
|rotation-coherent-r0p5-p270|[[1.4401326856127952, 1.440133755804441], [1.4401326784613977, 1.440133755804441]]|4.57818341 / 4.16145975|0.0728662057|5.43048769|46.8520279 / 36.8339664|2.39291411 / 2.18034984|
|rotation-coherent-r1-p090|[[1.5178242353099387, 1.5178253669927877], [1.517824235275286, 1.5178253669927877]]|4.74331334 / 4.3268791|0.0701042168|5.43169916|67.8042466 / 51.3383085|2.39258665 / 2.18002221|
|rotation-coherent-r1-p270|[[1.5178244364116535, 1.5178255680946524], [1.5178244363770006, 1.5178255680946524]]|4.7432042 / 4.32658388|0.0701138466|5.43176879|67.7562576 / 51.3293207|2.39262641 / 2.18008091|

skin8는접촉Jmax/J95·접촉전압·SC/접촉손실·SC+dermis 체적vectorJmax/J95·SC+dermis손실의8개수치한도이며sourcepower또는1Vpp상한은없다. 신규5조건의활성한도는`SC_power_W`다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드를GUI와brief에모두보존했다. legacy는sourcepower/1Vppceiling을추가한다. 수치한도를인체안전한계로해석하지않는다.

### 원래 square 대비와 새 sine 대비의 해석

원래square의skin8 목표mean/P10은4.06184894/3.64573574V/m, 표면P95/전체비표적P95는25.2592218/23.4357186V/m다. 저장된8gate는이원래square기준이며신규sine와coherent모두[PASS,PASS,FAIL,FAIL,FAIL,FAIL,FAIL,FAIL]이다.

새sine의skin8 mean/P10=`4.48034292/4.03565461V/m`, 표면P95/비표적P95=`32.8964461/26.4812355V/m`다. coherent r1/φ90°에서는mean/P10=`4.74331334/4.3268791V/m`로높지만, 표면P95=`67.8042466`, 비표적P95=`51.3383085V/m`도높다. 이때actualsourceupper는두출력각`1.5178253669927877Vpp`이므로동일1Vpp개선으로서술하지않는다. sine대비판정기준을다시만들지않고같은단위의절대값으로함께제시한다.

ROI는중심r≤5mm·깊이15–20mm, x/y수평·+z안쪽이다. CV/P10/mean·최대·전역hotspot·wholeXY보조ROI·고변조체적을GUI에표시했다. maxTIS는기본파2074방향표본최대(연속방향최대의하한), fixedTIS는(X+Y)/√2 기본파변조다. fullRMS는각행의활성선전체를포함하므로cachedsquare4선/신규sine2선을구분한다. 가중ECDF/fractional ROI/exactzoverlap을유지하고이상원기둥체적으로재정규화하지않았다. SC경계의전역최고전기장을깊이집중으로해석하지않는다.

## 신규 5조건의 8개 저장 판정

### rotation-sine-control

|gate|단위|원래square|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.06184894|4.48034292|10.3030415|PASS|
|primary_maxTIS_p10|V/m|3.64573574|4.03565461|10.6952038|PASS|
|surface_0_5_maxTIS_p95|V/m|25.2592218|32.8964461|30.23539|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.76652902e-06|8.34850446e-06|7.4933789|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.20945313e-06|8.69845145e-06|5.95652741|FAIL|
|primary_complement_maxTIS_p95|V/m|23.4357186|26.4812355|12.9951933|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.93996553e-05|2.14201844e-05|10.4152838|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.11556557e-05|2.41670546e-05|14.2344867|FAIL|

### rotation-coherent-r0p5-p090

|gate|단위|원래square|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.06184894|4.61167023|13.5362317|PASS|
|primary_maxTIS_p10|V/m|3.64573574|4.20434249|15.3221954|PASS|
|surface_0_5_maxTIS_p95|V/m|25.2592218|49.2841196|95.1133725|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.76652902e-06|9.80136161e-06|26.2000256|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.20945313e-06|9.8071317e-06|19.4614495|FAIL|
|primary_complement_maxTIS_p95|V/m|23.4357186|39.2364899|67.4217489|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.93996553e-05|2.59666876e-05|33.8512835|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.11556557e-05|2.94930938e-05|39.409973|FAIL|

### rotation-coherent-r0p5-p270

|gate|단위|원래square|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.06184894|4.57818341|12.7118088|PASS|
|primary_maxTIS_p10|V/m|3.64573574|4.16145975|14.1459514|PASS|
|surface_0_5_maxTIS_p95|V/m|25.2592218|46.8520279|85.4848429|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.76652902e-06|9.78315848e-06|25.9656464|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.20945313e-06|9.79785714e-06|19.3484754|FAIL|
|primary_complement_maxTIS_p95|V/m|23.4357186|36.8339664|57.1702025|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.93996553e-05|2.51135032e-05|29.453348|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.11556557e-05|2.85206845e-05|34.8135221|FAIL|

### rotation-coherent-r1-p090

|gate|단위|원래square|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.06184894|4.74331334|16.7771969|PASS|
|primary_maxTIS_p10|V/m|3.64573574|4.3268791|18.6832894|PASS|
|surface_0_5_maxTIS_p95|V/m|25.2592218|67.8042466|168.433632|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.76652902e-06|9.80733259e-06|26.2769065|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.20945313e-06|9.80944196e-06|19.489591|FAIL|
|primary_complement_maxTIS_p95|V/m|23.4357186|51.3383085|119.0601|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.93996553e-05|2.96555994e-05|52.866631|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.11556557e-05|3.3603119e-05|58.8375208|FAIL|

### rotation-coherent-r1-p270

|gate|단위|원래square|후보|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.06184894|4.7432042|16.7745101|PASS|
|primary_maxTIS_p10|V/m|3.64573574|4.32658388|18.6751918|PASS|
|surface_0_5_maxTIS_p95|V/m|25.2592218|67.7562576|168.243646|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.76652902e-06|9.80733259e-06|26.2769065|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.20945313e-06|9.80944196e-06|19.489591|FAIL|
|primary_complement_maxTIS_p95|V/m|23.4357186|51.3293207|119.021749|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.93996553e-05|2.96553065e-05|52.8651209|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.11556557e-05|3.3603119e-05|58.8375208|FAIL|

## 출력별 전력·프로브·출처

접촉surfaceJ와SC+dermis체적전체vectorJ를구분하며SC/contact/SC+dermis/sourcepower를별도로보존한다. signed ideal-source/metal-delivered/50Ωloss를출력별합계·그룹총합·주파수별로구분했다. 음의주파수별값을삭제하지않았다. pure sine의 비구동 기본파 금속단 전달전력은 음수지만 출력합계·그룹총합과 혼동하지 않는다. 신규5조건 signed spectrum에 남은9000/9090 Hz행은 cached basis의0계수/0전력선으로 활성구동이 아니다. 실제source/metal흡수·sink/compliance와AWG두tone위상동기는미검증이다. 출력RMS합은공통GND귀환전류와같은양이아니다.

신규5조건×5모드각40개의nativephi무부하예측을condition JSON에연결했다. 깊이5/10/15/20mm ×중심/X·Y±5mm의5개probe중심 ×X/Y차동방향이며tipgap5mm다. probe중심위치·중심간격과tipgap은다르다. raw JSON은복소전위차로재구성한전체Vpp bounds/RMS/기본파envelope·스펙트럼및수치검사를포함한다. 신규40phi검사와field waveform audit는모두저장PASS다. cached두행은과거raw40에연결하며정규화별영수증을새로발급하지않았다. ETA5001/DSOX1202Aactualswitch·팬텀portimpedance/부하·보정은미검증으로loaded결과를만들지않았다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, config SHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/summary](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json), SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `asym-return2-rot90-xy80` / sourcecase `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/summary.json), SHA256 `8de92edabdcdbe5a0ec7601882ce497e7d2a6c480fa478dbb71853f281041933`
  - [rawunloaded40](../data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/probes.json), SHA256 `24c7b539964ab0a24e18ea3c999758650aa898c40684cf186dd6aab131e46932`
- `rotation-sine-control` / sourcecase `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary](cloud-rotation-coherent-20261021T182000Z/rotation-sine-control/condition.json), SHA256 `a244ae9fb80bec31f95d98b5e351c13770155aee119c4b40b3b2bbe2a37a17f7`
  - [rawunloaded40](cloud-rotation-coherent-20261021T182000Z/rotation-sine-control/probes.json), SHA256 `872ca98c4ba07db2a49280ca36290f743cb8af1454ff3d45b795b014b41cbdca`
- `rotation-coherent-r0p5-p090` / sourcecase `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r0p5-p090/condition.json), SHA256 `b2c4b538e130cae906fa27f57372e21e4d0ec481d81ee88567d3e30313cea88e`
  - [rawunloaded40](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r0p5-p090/probes.json), SHA256 `92aa8ab9b4ce7f2c160fd986ba29102a192e7b8c5b533fd1491f2a5ebc385a82`
- `rotation-coherent-r0p5-p270` / sourcecase `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r0p5-p270/condition.json), SHA256 `443f7477e2df14dc7f3ce6b632e393d4504d14d166cb4ec8e9eb11e43ab87159`
  - [rawunloaded40](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r0p5-p270/probes.json), SHA256 `e2035bb64b0f68e28ed4d45390058d3d0d37204bd361dbcfbddad8af2f9c5a68`
- `rotation-coherent-r1-p090` / sourcecase `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r1-p090/condition.json), SHA256 `f3a6510e3fc97de563205f59dc10bd9c785dc2c328a4322271f2780b0ba58a5c`
  - [rawunloaded40](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r1-p090/probes.json), SHA256 `fe39043daf8048c46619f1c3819d34a08ce668be190d64de33a672a24a2e882d`
- `rotation-coherent-r1-p270` / sourcecase `asym-return2-rot90-xy80` / run `cloud-one-return-rotation-20261021T174000Z`
  - source `3381113eeee81b0925890d5d4d17496764901fd5`, config SHA256 `94bbb78869a0e75d7c7c5e2c59a926f5d9d37528738923af82315d3ab1aaf594`
  - [condition/summary](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r1-p270/condition.json), SHA256 `259557b13aa5faa2cfeaf71e71585541037c737b1a38f2939496f4dc8aab4c5b`
  - [rawunloaded40](cloud-rotation-coherent-20261021T182000Z/rotation-coherent-r1-p270/probes.json), SHA256 `5fbf765e99e05a8143c4de0644ceb245b9f4ce9387f95703c63e20608a3b83ea`

기하physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`, native source `3381113eeee81b0925890d5d4d17496764901fd5`, scout implementation/preregistration `307138efb279d7594c74bca6c4d65aafd2efdee9`다. 실제seed/정규화후coefficient vectors·sourcewaveform·unitary여부는원본condition과brief에보존했다. volumeNPZ SHA는producer가발행한reference이며문서작성과정에서NPZ를열거나재해시하지않았다. native링크는로컬archive이며GitHub의파일제공을보장하지않는다. 이문서의JSON/설정해시검증을시뮬레이션재현·수렴·실험검증과구분한다.

## 실행·발행·수치 범위

큐[summary](cloud-rotation-coherent-context-20261021T182000Z/queue/summary.json)는`completed_preregistered_queue`, 계산/GET/발행3단계exit0이다. actualwall `54.018978110994794s`, CPU1, peakRSS `540442624bytes`, 새PDE0이다. [발행영수증](cloud-rotation-coherent-context-20261021T182000Z/coherent-publication-20261021T182000Z.json)은`published_completed_batch`, `2026-10-21T17:57:09.784777+00:00`, commit `4dff5b18fe9812eb8ddf815538ecc3ac85c8c006`이다.

첫interpreter경로의[admission실패](cloud-rotation-coherent-context-20261021T182000Z/admission-failure-preserved.json)는큐나계산시작전에발생했다. 실패spec은보존하고resolvedinterpreter경로만고친새spec으로과학계산을한번실행했다. root선정과동료의특정후보승인을구분한다.

native5개방정식·파형검사·8개비교는SC/XY/bulk/edge/contact수렴이나실험검증이아니다. PBS계면을실제피부검증값으로취급하지않는다. AWG두tone/출력간위상동기/흡수·sink/compliance는미검증이므로실험준비완료로표현하지않는다. 이전[양의exclusive square3h amplitude bounds](ROTATION_AMPLITUDE_BOUNDS_20261021.md)는이번coherent또는다른기하를배제하지않는다. C1/생리적활성동등성/인체안전/COMSOL검증을새로주장하지않는다.

[이전ratio4 GUI](CLOUD_ROTATION_RATIO_RESULTS_20261021.html)와[과거44조건/4·8·12·16패드snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)은그대로보존한다. 이번화면은새물리공간맵을만들지않은정적오프라인JSON표다. 다음새후보의실행완료를이보고서에서주장하지않는다.
