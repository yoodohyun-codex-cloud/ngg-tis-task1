# 작업1: Rounded SC4 접촉 임피던스 불확실성 (2026-10-21)

명목 PBS 계면의 complex specific Z를0.5배·2배로 바꾼 두 조건도 모두 미채택이다. 고정 SC2 배율에서0.5배는6/8이지만 SC손실이 원cap을 넘고, 2배는5/8이며 접촉전압·접촉손실이 원cap을 넘는다. 실제 부담을 원래8cap에 다시 맞추면0.5배는4/8(목표2개·두P95 실패),2배는6/8(비표적6개 통과·목표2개 실패)다. 고정 A 결과를 동일 표면 부담의 성과로 해석하지 않는다.

[오프라인GUI](CLOUD_ROUNDED_CONTACT_SENSITIVITY_RESULTS_20261021.html) · [정확한4조건×고정/보조5모드brief](ROUNDED_CONTACT_SENSITIVITY_RESULTS_20261021.result-brief.json) · [원본summary](cloud-rounded-contact-sensitivity-20261021T210000Z/summary.json)

## 물리·접촉·평가정의

D50 mm, 층0.1/5/5/15 mm, 윗면, 각225/총900 mm²의 fixed rounded full-face union, 중심(±10,±10) mm를 유지했다. XY0.625 mm·SC4·bulk14/14/40·361728셀·tissue/10nm코팅/배선/출력은 고정했다. 물리4패드/독립2출력/공통GND/50Ω, pad0out0/pad1out1/pad2·3GND, 비구동주파수출력0V·50Ω 종단이다. 원래SC2 square는 고정된 과학적 비교 기준으로 계속 표시한다.

원래 Rs 차감·접촉면적 변환이 완료된 specific complex Z(Ω·m²)의 실수부·허수부를 모든4주파수에서0.5/2로 곱했다. 추가 Rs 차감, 접촉면적 재스케일링, source50Ω 변경은0이다. 물리 maskSHA a18c9697232e5f486acc06a16129c2e4ffb0dee45fb6ec5b0edbe34d1b9def29는 동일하다. PBS→피부 전이의 명목모델 불확실성 진단이며 실제 피부 측정값·통계적 신뢰구간·생리적 범위·최적화된 접촉모델이 아니다. 임의의 변화율 PASS/FAIL 한도도 추가하지 않았다.

선택 SC2 실제 복소계수·5개 A·source 전체파형Vpp를 그대로 썼다. 3000/3030Hz·beat30Hz이며9000/9090Hz계수0, source Vpp는50Ω전 전체합성파형max−min bracket이다. 원래square control만4선square3h다. nominalSC4 JSON 결과는 재사용했고 nominalfield를 재계산하지 않았다.

주ROI r≤5mm·깊이15–20mm와 보조wholemodeledXY 같은깊이, 표면0–5mm/각complement/total을 유지했다. z=0표면,+z깊이,x/y수평이다. maxTIS는2074개실수단위방향표본의기본파최대(연속방향최대의하한),fixedTIS는(X+Y)/√2,fullRMS는활성선전체벡터RMS다. 가중ECDF/fractionalvolume/원SC2cutoff를 고정하고 scalar를배율적용한뒤 ≥cutoff체적을 계산했다. 단위V/m,CV무차원. SC층전역hotspot은깊이집중이아니다.

고정군의5개 A는이전SC2배율일뿐, 각접촉조건에서동일전류·동일전력·동일skin8부담을새로보장하지않는다. 보조군만각조건의실제전류/손실을원래SC2 current/power/8caps에다시맞춘다. skin8에는sourcepower/1Vpp상한이없고legacy만둘을더한다. 출력RMS전류합은GND귀환전류가아니다. 모든cap은수치비교기준이며인체안전한계가아니다.

## 고정 SC2 skin8와 실제부담재맞춤을 분리

### 고정 SC2 skin8 A: 동일부담을 뜻하지 않음

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.10341998712|4.06479281915|3.64696331556|0.0811326088194|4.96708813006|25.3703779833|23.6483963978|2.19802509977|2.0057067355|
|SC4 complex Z ×0.5|1.10341998712|4.06571050587|3.64767459021|0.0811518226398|4.96848486472|25.3901550745|23.6611226392|2.19859821316|2.006195804|
|SC4 complex Z ×2|1.10341998712|4.06294549219|3.6455295537|0.0810943037527|4.96428239214|25.3442896312|23.6288184442|2.19687263015|2.00472239265|

### 각 SC4 접촉조건을 원 SC2 8cap에 보조 재맞춤

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.10343276518|4.0648398911|3.64700554888|0.0811326088194|4.96714565097|25.3706717826|23.6486702558|2.1980505538|2.0057299624|
|SC4 complex Z ×0.5|1.10038815379|4.05453927752|3.63765198636|0.0811518226398|4.9548331109|25.3203913223|23.5961096965|2.19255719213|2.00068344118|
|SC4 complex Z ×2|0.79856852565|2.94044011288|2.63834731551|0.0810943037527|3.59275680798|18.3422017369|17.1006787334|1.58992347227|1.4508602564|

0.5배 고정A의 SC_power=2.178311132000553e−6 W는 원cap2.166357019889475e−6 W를 넘는다. 2배 고정A의 contactVoltage=0.003709768567634118 V와 contactPower=3.2124110551618027e−6 W는 원cap0.0026848384569140493 V/1.827275482305884e−6 W를 넘는다. 따라서6/8·5/8은8개의공간화면검사갯수이며실제8부담충족을뜻하지않는다.

보조skin8 A는nominal1.1034327651767097,0.5배1.10038815379035(SC_power limiter),2배0.7985685256495305(contactVoltage limiter)다. 원래SC2 A1.1034199871234145를고정한열과혼동하지않는다.

## 고정SC2 배율의5모드

### raw_1Vpp

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|SC4 complex Z ×0.5|1|3.68464460796|3.30578984682|0.0811518226398|4.50280484557|23.0104179467|21.4434421302|1.99253071253|1.81816155898|
|SC4 complex Z ×2|1|3.68213875008|3.30384585764|0.0810943037527|4.49899625715|22.9688513231|21.414165703|1.99096686284|1.81682624571|

### equal_total_source_output_RMS_sum

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.16594628202|4.29512799294|3.85362180136|0.0811326088194|5.24855268646|26.8080134747|24.9884542399|2.3225781867|2.1193619278|
|SC4 complex Z ×0.5|1.16594628202|4.29609768121|3.85437338104|0.0811518226398|5.25002856835|26.8289112527|25.0019016254|2.32318377608|2.1198787098|
|SC4 complex Z ×2|1.16594628202|4.29317598553|3.85210679408|0.0810943037527|5.24558795884|26.7804468024|24.9677668839|2.32136041135|2.11832180626|

### equal_total_power

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.15513676953|4.25530777103|3.81789479263|0.0811326088194|5.19989324417|26.5594758183|24.7567857554|2.30104551551|2.09971327881|
|SC4 complex Z ×0.5|1.15513676953|4.2562684693|3.8186394044|0.0811518226398|5.20135544314|26.5801798525|24.7701084698|2.30164549046|2.10022526972|
|SC4 complex Z ×2|1.15513676953|4.25337386072|3.81639383102|0.0810943037527|5.19695600261|26.5321647171|24.7362901923|2.29983903018|2.09868280027|

### skin_contact_only

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.10341998712|4.06479281915|3.64696331556|0.0811326088194|4.96708813006|25.3703779833|23.6483963978|2.19802509977|2.0057067355|
|SC4 complex Z ×0.5|1.10341998712|4.06571050587|3.64767459021|0.0811518226398|4.96848486472|25.3901550745|23.6611226392|2.19859821316|2.006195804|
|SC4 complex Z ×2|1.10341998712|4.06294549219|3.6455295537|0.0810943037527|4.96428239214|25.3442896312|23.6288184442|2.19687263015|2.00472239265|

### legacy_composite_full_skin

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|SC4 complex Z ×0.5|1|3.68464460796|3.30578984682|0.0811518226398|4.50280484557|23.0104179467|21.4434421302|1.99253071253|1.81816155898|
|SC4 complex Z ×2|1|3.68213875008|3.30384585764|0.0810943037527|4.49899625715|22.9688513231|21.414165703|1.99096686284|1.81682624571|

## 원SC2 상수로각조건재맞춤의5모드

### raw_1Vpp

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|SC4 complex Z ×0.5|1|3.68464460796|3.30578984682|0.0811518226398|4.50280484557|23.0104179467|21.4434421302|1.99253071253|1.81816155898|
|SC4 complex Z ×2|1|3.68213875008|3.30384585764|0.0810943037527|4.49899625715|22.9688513231|21.414165703|1.99096686284|1.81682624571|

### equal_total_source_output_RMS_sum

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.16590158952|4.29496335414|3.85347408616|0.0811326088194|5.24835150143|26.8069858827|24.9874963944|2.32248915874|2.11928068942|
|SC4 complex Z ×0.5|1.16446550031|4.29064152685|3.84947822789|0.0811518226398|5.24336089728|26.7948378466|24.9701485684|2.32023327304|2.11718640941|
|SC4 complex Z ×2|1.16876090973|4.30353983528|3.86140589018|0.0810943037527|5.25825095837|26.8450955678|25.0280397881|2.32696424185|2.12343549576|

### equal_total_power

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.15511278948|4.25521943302|3.81781553509|0.0811326088194|5.19978529706|26.5589244572|24.7562718172|2.30099774698|2.09966968984|
|SC4 complex Z ×0.5|1.15428357643|4.25312475596|3.81581892733|0.0811518226398|5.19751368114|26.5605475228|24.7518130731|2.29994547701|2.09867402683|
|SC4 complex Z ×2|1.15676434514|4.25936681994|3.82177108995|0.0810943037527|5.20427845919|26.5695482593|24.7711433661|2.30307947928|2.10163982235|

### skin_contact_only

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1.10343276518|4.0648398911|3.64700554888|0.0811326088194|4.96714565097|25.3706717826|23.6486702558|2.1980505538|2.0057299624|
|SC4 complex Z ×0.5|1.10038815379|4.05453927752|3.63765198636|0.0811518226398|4.9548331109|25.3203913223|23.5961096965|2.19255719213|2.00068344118|
|SC4 complex Z ×2|0.79856852565|2.94044011288|2.63834731551|0.0810943037527|3.59275680798|18.3422017369|17.1006787334|1.58992347227|1.4508602564|

### legacy_composite_full_skin

|조건|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|fullRMS mean|fullRMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|nominal SC4 rounded|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|SC4 complex Z ×0.5|1|3.68464460796|3.30578984682|0.0811518226398|4.50280484557|23.0104179467|21.4434421302|1.99253071253|1.81816155898|
|SC4 complex Z ×2|0.79856852565|2.94044011288|2.63834731551|0.0810943037527|3.59275680798|18.3422017369|17.1006787334|1.58992347227|1.4508602564|

## 원래8개공간검사: 고정배율과보조재맞춤

### nominal SC4 rounded · 고정SC2skin8 · 6/8

|검사|기준|후보|변화%|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|4.06479281915|0.0724762931209|V/m|PASS|
|primary_maxTIS_p10|3.64573573913|3.64696331556|0.033671569074|V/m|PASS|
|surface_0_5_maxTIS_p95|25.2592218317|25.3703779833|0.440061662893|V/m|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|7.65616071429e-06|-1.42107630471|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|8.13138950893e-06|-0.950899102325|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|23.6483963978|0.907494326573|V/m|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.92793743929e-05|-0.620015461328|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|2.10680266459e-05|-0.414210819888|m3|PASS|

### nominal SC4 rounded · 보조rematchskin8 · 6/8

|검사|기준|후보|변화%|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|4.0648398911|0.0736351731941|V/m|PASS|
|primary_maxTIS_p10|3.64573573913|3.64700554888|0.0348299997727|V/m|PASS|
|surface_0_5_maxTIS_p95|25.2592218317|25.3706717826|0.441224799754|V/m|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|7.65616071429e-06|-1.42107630471|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|8.13138950893e-06|-0.950899102325|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|23.6486702558|0.908662876495|V/m|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.92795208773e-05|-0.619260373812|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|2.10683196146e-05|-0.412825995164|m3|PASS|

### SC4 complex Z ×0.5 · 고정SC2skin8 · 6/8

|검사|기준|후보|변화%|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|4.06571050587|0.0950691254271|V/m|PASS|
|primary_maxTIS_p10|3.64573573913|3.64767459021|0.0531813390443|V/m|PASS|
|surface_0_5_maxTIS_p95|25.2592218317|25.3901550745|0.518358180831|V/m|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|7.65681919643e-06|-1.4125978436|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|8.13302455357e-06|-0.930982493777|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|23.6611226392|0.961797084029|V/m|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.92813902969e-05|-0.609624018845|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|2.1072278878e-05|-0.394111078187|m3|PASS|

### SC4 complex Z ×0.5 · 보조rematchskin8 · 4/8

|검사|기준|후보|변화%|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|4.05453927752|-0.179959033018|V/m|FAIL|
|primary_maxTIS_p10|3.64573573913|3.63765198636|-0.221731725612|V/m|FAIL|
|surface_0_5_maxTIS_p95|25.2592218317|25.3203913223|0.242166964001|V/m|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|7.64169084821e-06|-1.60738689517|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|8.12004464286e-06|-1.08909181625|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|23.5961096965|0.684387443695|V/m|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.92401987568e-05|-0.821955318364|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|2.10119667001e-05|-0.679198805304|m3|PASS|

### SC4 complex Z ×2 · 고정SC2skin8 · 5/8

|검사|기준|후보|변화%|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|4.06294549219|0.0269963410438|V/m|PASS|
|primary_maxTIS_p10|3.64573573913|3.6455295537|-0.00565552328593|V/m|FAIL|
|surface_0_5_maxTIS_p95|25.2592218317|25.3442896312|0.336779177245|V/m|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|7.65552455357e-06|-1.42926736037|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|8.12975446429e-06|-0.970815710873|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|23.6288184442|0.823955375353|V/m|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.92755155759e-05|-0.639906623896|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|2.10617250189e-05|-0.443997781303|m3|PASS|

### SC4 complex Z ×2 · 보조rematchskin8 · 6/8

|검사|기준|후보|변화%|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|2.94044011288|-27.6083341562|V/m|FAIL|
|primary_maxTIS_p10|3.64573573913|2.63834731551|-27.6319650052|V/m|FAIL|
|surface_0_5_maxTIS_p95|25.2592218317|18.3422017369|-27.3841377254|V/m|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|5.81303013393e-06|-25.1527919285|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|6.46842773438e-06|-21.2075684472|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|17.1006787334|-27.0315579436|V/m|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.58663462612e-05|-18.2132566137|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|1.68161858259e-05|-20.5121027887|m3|PASS|

## 실제전류·부담·전력·프로브

|조건/비교|출력RMS mA|접촉Jmax/J95 A/m²|접촉전압RMS V|SC loss W|contact loss W|SC+dermis loss W|sourcepower W|
|---|---|---|---|---|---|---|---|
|nominal SC4 rounded/고정A|[1.3982391197369397, 1.3986938178851096]|[17.82270799684118, 12.09078010618836]|0.00187683567291|2.16630684617e-06|1.62393932955e-06|0.000673753879601|0.00103652302789|
|nominal SC4 rounded/보조재맞춤|[1.398255311915983, 1.3987100153297427]|[17.822914391065783, 12.090920122351182]|0.00187685740743|2.16635701989e-06|1.62397694153e-06|0.00067376948438|0.00103654703474|
|SC4 complex Z ×0.5/고정A|[1.3999640059187797, 1.400418278400195]|[17.92922788498149, 12.128621984208797]|0.000944026227389|2.178311132e-06|8.16497333995e-07|0.000675443011733|0.0010380127955|
|SC4 complex Z ×0.5/보조재맞춤|[1.3961173676597607, 1.3965703919505799]|[17.87996429417097, 12.095296540728542]|0.000941432355412|2.16635701989e-06|8.12016568817e-07|0.000671736322928|0.00103231640018|
|SC4 complex Z ×2/고정A|[1.3948173977075458, 1.3952729711746208]|[17.614247130696654, 12.01595762974007]|0.00370976856763|2.14279580853e-06|3.21241105516e-06|0.000670414861409|0.0010335653755|
|SC4 complex Z ×2/보조재맞춤|[1.009459032676601, 1.0097887408894055]|[12.747805482712938, 8.696204238301075]|0.00268483845691|1.12233749914e-06|1.68257254168e-06|0.000351144862215|0.000541353111722|

source/metal/50Ω의signed출력별·주파수별전력과합계,물리패드전류,GNDnet/localJ를brief/GUI에보존했다. 음의값을지우지않고동일출력의다른주파수흡수와총합양수를구분한다. GNDnet상쇄는localJ=0/절연회로를뜻하지않는다.

각새접촉조건은native복소φ40개를계산했다:깊이5/10/15/20mm × 중심/(±5,0)/(0,±5)mm × X/Y방향,tipgap5mm. 중심위치와tip간격은별개다. 두5모드묶음각40개의무부하Vpp bounds/RMS/기본파envelope를보존했고rawprobesJSON에는스펙트럼/저장검사도있다. 두조건모두waveform검사PASS/RMS상대오차0/envelope오차≤1.3877787807814457e−17V다. ETA5001부하R/C·대역폭·스위치·감쇠/보정은미검증이다. 원래square raw40은기존영수증을연결하고새normalizedprobe를발급하지않았다.

## 실제실행·감사복구·저장공간·출처

native2조건/각8RHS는127.891274238초·115.813991998초,각sampledaggregatepeakRSS531939328B·686538752B다. native전체controller244.015705587초와개별case시간을구분한다. 새선택구동후처리29.282941925초/peakRSS511250432B/새PDE0/CPU1이며nominalSC4는저장결과재사용이다. 누적13800초예산과1CPU/3GiBRSS/2GiBreserve를유지했다. native5gate완료는접촉모델검증이나후보채택이아니다.

첫native큐는두basis완료뒤root가nominal-contact SC4square를changed-Z full-skin감사에넘겨 identicalcontactZ guard에서실패했다. 원로그/실패를보존하고새큐에서각case의own-physics raw3h진단감사만완료했다(exit0×3). own-case cutoff는그진단에만사용했고과학비교의원SC2 caps/cutoff/current/power를바꾸지않았다. 이는canonical baseline교체나후보검증통과가아니다. PDE재계산0개다.

root인계의free2.1969GiB 스냅샷은새native예상217MB와2GiBreserve를함께만족하지못한다. 이는작성자가새로측정한live용량이아니다. 두case의fullcomplex E/φ16개와실패증거를로컬보존하며삭제/reserve완화/외부유료자원을사용하지않았다. 다음작업은cachedJSON/기존맵의C1비교이며새PDE시작을약속하지않는다.

|조건|source run/case|nativecommit|configSHA256|
|---|---|---|---|
|원래 SC2 square 기준|cloud-mesh-c1-20261019T190000Z/baseline-square15-xy80|38f005ecefc2c432cd6424a06f599f93682cc202|f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b|
|nominal SC4 rounded|cloud-rounded-sc4-20261021T204000Z/rounded-fullface225-sc4-xy80|4b553e473be0f46e4f5b7d72cb30ee5c68eb7c82|5cac8156e6a18af31a17e899f4726dd8cd749dc497c5ea4a5afe10c8ba28b0a0|
|SC4 complex Z ×0.5|cloud-rounded-contact-20261021T210000Z/rounded-fullface225-contact0p5-sc4-xy80|f1b17a8d1f0cc8d40339a5827edce755877822e8|9c6659815cd974c2fcf340f4a84cfb9d19c1a391c2c2641def7191e0569c86c6|
|SC4 complex Z ×2|cloud-rounded-contact-20261021T210000Z/rounded-fullface225-contact2-sc4-xy80|f1b17a8d1f0cc8d40339a5827edce755877822e8|8dbf73441922856594759d12df5a96c999ff550331e5ce35860480121dcf87f5|

후처리구현commit `598d99ee9ab792a263d37ae14f683891e46f492c`와nativeproducercommit을구분한다. 아래SHA는작은JSON을대조했고raw/config/mask/NPZ는completedreceipt선언을인용한다.

- [summary](cloud-rounded-contact-sensitivity-20261021T210000Z/summary.json), SHA256 `4621cf2292097b79421eacc0ce0c4df2af2bad86189426436d0d1eed182275b9`
- [nominal_SC4_condition](cloud-rounded-sc4-sensitivity-20261021T204000Z/rounded-opt-e7b3bf639935-SC4-same-command/condition.json), SHA256 `05aa7358ba050c3c753d4e8deb10f4ddcdb1b39c1d6ed40c30459dd63687dc48`
- [nominal_SC4_summary](cloud-rounded-sc4-sensitivity-20261021T204000Z/summary.json), SHA256 `f4d99e42fb11b225b0764b2d6bc8d090405efdcee981890f3411246d2be585fb`
- [previous_SC4_doc_snapshot](ROUNDED_SC4_SENSITIVITY_RESULTS_20261021.result-brief.json), SHA256 `c1b5eaa9b875b4dad9821b23c5e4e2068ca11b4aa62b78f0f830540ca36e9c5c`
- [canonical_SC2_baseline_summary](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json), SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
- [native_summary](../data-native/cloud-rounded-contact-20261021T210000Z/summary.json), SHA256 `7b95c2cf4e2d4e0531aa8877063f7d6c66fa108d15911d94a07ca7e73a5e7f82`
- [frozen_source_manifest](../data-native/cloud-rounded-contact-20261021T210000Z/frozen-source-manifest.json), SHA256 `bfc8a82eb594bcb71c7720b53ae19fde1eeca795753009d9134337c5e913d3c6`
- [decision](cloud-rounded-contact-context-20261021T210000Z/decision-after-bounds.json), SHA256 `0f7eb8698b5fd6881dd58666e12df85457f3e99341566d2fcdc592079ff716fe`
- [preregistration](cloud-rounded-contact-context-20261021T210000Z/contact-sensitivity-plan.json), SHA256 `2f570a18b5ced35bc2c2d10c55aca959b8c2bec1b1a39712786dc012842a2402`
- [failed_native_queue](cloud-rounded-contact-context-20261021T210000Z/queue-native/summary.json), SHA256 `eff4c06eda648738fc4cda90459e01811273f4cf5a83ae013fd8d4266c083bc1`
- [audit_recovery_queue](cloud-rounded-contact-context-20261021T210000Z/queue-audit-recovery/summary.json), SHA256 `f939335af01908b7f5dccebbb6bcebdae433b1e5011bd1d0262a5029a76dbb88`
- [post_queue](cloud-rounded-contact-context-20261021T210000Z/queue-post/summary.json), SHA256 `fd24857ae7c0a1ca00c7f33f0029b8fcb07666757356864a932689dbe1adb668`
- [failure_disposition](cloud-rounded-contact-context-20261021T210000Z/audit-failure-disposition.json), SHA256 `fe1f53d4233c9f67318b54e4e0fb84dc4dcfa145499e76d17b30146a51d431b1`
- [feedback_after_contact](cloud-rounded-contact-context-20261021T210000Z/feedback-after-contact.json), SHA256 `74a95017f71ebfa5edcd93671a1909dfb71f7a034802a7ae714c57d86687ed82`
- [snapshot_inventory](cloud-rounded-contact-context-20261021T210000Z/completed-snapshot-inventory.json), SHA256 `eb5c0a9c54c3fdd44b51c25c81c3fb9fe1f354c4f44361941ea85b8098082aa6`
- [rounded-fullface225-contact0p5-sc4-xy80_condition.json](cloud-rounded-contact-sensitivity-20261021T210000Z/rounded-fullface225-contact0p5-sc4-xy80-same-command/condition.json), SHA256 `84ae313ca0a450607f0fc4c6cfc0758441362074ec2faf067fd5b8c4483473ec`
- [rounded-fullface225-contact0p5-sc4-xy80_probes.json](cloud-rounded-contact-sensitivity-20261021T210000Z/rounded-fullface225-contact0p5-sc4-xy80-same-command/probes.json), SHA256 `1d613de6eb4af73d0ec7153a535c09c05dd7d11f65ca949ed9dcb574d3670aa0`
- [rounded-fullface225-contact0p5-sc4-xy80_native-volume-metrics.json](cloud-rounded-contact-sensitivity-20261021T210000Z/rounded-fullface225-contact0p5-sc4-xy80-same-command/native-volume-metrics.json), SHA256 `7c8af8c522b0b71c7df227590879e2a7a8ea9b944110d518497650b5cdf4a41b`
- [rounded-fullface225-contact0p5-sc4-xy80_native_case](../data-native/cloud-rounded-contact-20261021T210000Z/cases/rounded-fullface225-contact0p5-sc4-xy80.json), SHA256 `a7ceebd974fddd3ed48f5c49badbe36fd96941700827d882c0108a08ec80a345`
- [rounded-fullface225-contact0p5-sc4-xy80_mesh_metadata](../data-native/cloud-rounded-contact-20261021T210000Z/bases/rounded-fullface225-contact0p5-sc4-xy80/mesh-metadata.json), SHA256 `c13189c9e5432dbf8a4d0ecc006eef6bba6c567152d4af379a8dd1633b5e9a47`
- [rounded-fullface225-contact2-sc4-xy80_condition.json](cloud-rounded-contact-sensitivity-20261021T210000Z/rounded-fullface225-contact2-sc4-xy80-same-command/condition.json), SHA256 `ce186b358343d7a4555dcbc96e8407bfb8bd6060051bfbd2b6cc953eade59cb4`
- [rounded-fullface225-contact2-sc4-xy80_probes.json](cloud-rounded-contact-sensitivity-20261021T210000Z/rounded-fullface225-contact2-sc4-xy80-same-command/probes.json), SHA256 `1d29206f7bb1ee71e92b240f8b686b1eeabcd131a5309a54fa1c7c9aab33d945`
- [rounded-fullface225-contact2-sc4-xy80_native-volume-metrics.json](cloud-rounded-contact-sensitivity-20261021T210000Z/rounded-fullface225-contact2-sc4-xy80-same-command/native-volume-metrics.json), SHA256 `46bf14621cc3d9e576f41d5859b9b6222951ca8bb08f5ca8c783e6798d40ab2f`
- [rounded-fullface225-contact2-sc4-xy80_native_case](../data-native/cloud-rounded-contact-20261021T210000Z/cases/rounded-fullface225-contact2-sc4-xy80.json), SHA256 `73fc4522b88594fe2d4187743e3e71fbe24c3d3f7e9e293b28dff03c62238fdc`
- [rounded-fullface225-contact2-sc4-xy80_mesh_metadata](../data-native/cloud-rounded-contact-20261021T210000Z/bases/rounded-fullface225-contact2-sc4-xy80/mesh-metadata.json), SHA256 `316eec0c67198044f502f6dcc7a840c4454a5bc12176b1f9fd7d4d21e498da06`
- rounded-fullface225-contact0p5-sc4-xy80 [config](../data-native/cloud-rounded-contact-20261021T210000Z/configs/rounded-fullface225-contact0p5-sc4-xy80.properties) · [mask](../data-native/cloud-rounded-contact-20261021T210000Z/masks/rounded-fullface225-contact0p5-sc4-xy80.csv) · [public compact snapshot case](cloud-rounded-contact-context-20261021T210000Z/completed-native-snapshot/cases/rounded-fullface225-contact0p5-sc4-xy80.json)
- rounded-fullface225-contact2-sc4-xy80 [config](../data-native/cloud-rounded-contact-20261021T210000Z/configs/rounded-fullface225-contact2-sc4-xy80.properties) · [mask](../data-native/cloud-rounded-contact-20261021T210000Z/masks/rounded-fullface225-contact2-sc4-xy80.csv) · [public compact snapshot case](cloud-rounded-contact-context-20261021T210000Z/completed-native-snapshot/cases/rounded-fullface225-contact2-sc4-xy80.json)

전체SC/XY/bulk/edge/contact/방향수렴·실제피부계면·source흡수/phase동기/compliance·instrumentloading·실험·활성화·인체안전·COMSOL5.3a 예정5.3.1.201 설치/실행·독립영구fullcomplexbackup/restore는미검증이다. 본문서는완료JSON만읽고native E/φ/grid/mask/config/NPZ를열거나과학수치를재계산하지않았다.
