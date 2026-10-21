# 작업1: Rounded 구동의 SC2→SC4 단일축 민감도 (2026-10-21)

SC 두께 방향 2→4셀 민감도는 사전등록된 20개 변화율 검사와 16개 판정 상태 비교를 모두 통과했다. 최대 상대변화는 **0.02191785048%**다. 기존 SC2 배율을 고정한 SC4는 목표 mean/P10을 통과하지만 표층·전체 비표적 P95가 여전히 실패해 **6/8, 미채택**이다. 이는 두 SC 수준의 진단이며 전체 수렴·실험 검증 완료가 아니다.

[오프라인GUI](CLOUD_ROUNDED_SC4_SENSITIVITY_RESULTS_20261021.html) · [정확한4군×5모드brief](ROUNDED_SC4_SENSITIVITY_RESULTS_20261021.result-brief.json) · [원본summary](cloud-rounded-sc4-sensitivity-20261021T204000Z/summary.json)

## 고정 조건과 비교 정의

D50 mm, 층 SC0.1/dermis5/fat5/muscle15 mm, 윗면을 유지했다. rounded 도형은 각225/총900 mm², 중심(±10,±10) mm, 각576개의 전체 접촉면으로 된 고정 stepped union이며 smooth 원호가 아니다. XY0.625 mm·bulk14/14/40·명목 접촉/10nm코팅/Rs500/면적 스케일링을 고정하고 SC2→SC4, 총 셀351680→361728로 바꿨다. SC 두께는 계속0.1 mm다. 물리4패드/독립2출력/공통GND1개/50Ω, pad0out0/pad1out1/pad2·3GND다. 비구동 주파수 출력은0V·50Ω 종단이다.

선정 구동3000/3030 Hz·beat30 Hz, 9000/9090 Hz계수0이며 원래 square 기준만4선 square3h다. SC2 실제 복소계수와 source 전체파형 Vpp bracket을 그대로 사용했고 SC4에서 source 정규화를 새로 하지 않았다. Vpp는50Ω 전 전체합성파형 max−min이며 tone Vpp가 아니다.

주ROI r≤5 mm·깊이15–20 mm, 보조ROI 전체 modeled XY의 같은깊이, z=0표면/+z깊이, x/y수평이다. maxTIS는 기본파2074개 실수 단위방향 표본의 최대(연속방향 최대의 하한), fixedTIS는(X+Y)/√2, fullRMS는 활성선 전체벡터RMS다. 가중ECDF/fractionalXY/exactzoverlap/원래SC2cutoff를 유지했고 고변조체적은 scaled scalar ≥ cutoff다. E/TIS 단위V/m, CV무차원. SC전역최대를 깊이집중으로 판정하지 않는다.

SC4 고정군의5개 A는 기존SC2값 그대로여서 SC4에서 current/power/부담이 다시 같다고 주장하지 않는다. 고정skin8 A=1.1034199871234145, 보조SC4 rematchskin8 A=1.1034327651767097(limiter SC_power_W)다. 보조군도 원래SC2 current/power/8caps상수를 쓰며 SC4square cap은 쓰지 않았다. skin8는 sourcepower/1Vpp ceiling이 없고 약1.10Vpp가 필요하다. legacy만sourcepower+1Vpp상한을 추가한다. RMS전류합은 각출력의 전체주파수RMS 합이며 GNDnet전류가 아니다. 수치상수는 인체안전한계가 아니다.

## 원래 기준과 주·보조 비교

### raw_1Vpp

|군|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|full RMS mean|full RMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 4-square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|선정 SC2 rounded 구동|1|3.68380072432|3.30513584541|0.0811323013159|4.50152014477|22.9919264848|21.4321186487|1.99200384354|1.81771181662|
|SC4 · 기존 SC2 배율 고정|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|SC4 · 원 SC2 상수로 보조 재맞춤|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|

### skin_contact_only

|군|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|full RMS mean|full RMS P10|
|---|---|---|---|---|---|---|---|---|---|
|원래 SC2 4-square 기준|1|4.0618489416|3.64573573913|0.0807616216391|4.97132718867|25.2592218317|23.4357185812|2.30694946283|2.10466937124|
|선정 SC2 rounded 구동|1.10341998712|4.0647793478|3.64695295198|0.0811323013159|4.96706730017|25.3697512258|23.6486280834|2.19801685539|2.00569954929|
|SC4 · 기존 SC2 배율 고정|1.10341998712|4.06479281915|3.64696331556|0.0811326088194|4.96708813006|25.3703779833|23.6483963978|2.19802509977|2.0057067355|
|SC4 · 원 SC2 상수로 보조 재맞춤|1.10343276518|4.0648398911|3.64700554888|0.0811326088194|4.96714565097|25.3706717826|23.6486702558|2.1980505538|2.0057299624|

### SC4 · 기존 SC2 배율 고정 · 5모드

|모드|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|full RMS mean|full RMS P10|
|---|---|---|---|---|---|---|---|---|---|
|raw_1Vpp|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|equal_total_source_output_RMS_sum|1.16594628202|4.29512799294|3.85362180136|0.0811326088194|5.24855268646|26.8080134747|24.9884542399|2.3225781867|2.1193619278|
|equal_total_power|1.15513676953|4.25530777103|3.81789479263|0.0811326088194|5.19989324417|26.5594758183|24.7567857554|2.30104551551|2.09971327881|
|skin_contact_only|1.10341998712|4.06479281915|3.64696331556|0.0811326088194|4.96708813006|25.3703779833|23.6483963978|2.19802509977|2.0057067355|
|legacy_composite_full_skin|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|

### SC4 · 원 SC2 상수로 보조 재맞춤 · 5모드

|모드|A|ROI mean|ROI P10|CV|ROI max|surface P95|complement P95|full RMS mean|full RMS P10|
|---|---|---|---|---|---|---|---|---|---|
|raw_1Vpp|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|
|equal_total_source_output_RMS_sum|1.16590158952|4.29496335414|3.85347408616|0.0811326088194|5.24835150143|26.8069858827|24.9874963944|2.32248915874|2.11928068942|
|equal_total_power|1.15511278948|4.25521943302|3.81781553509|0.0811326088194|5.19978529706|26.5589244572|24.7562718172|2.30099774698|2.09966968984|
|skin_contact_only|1.10343276518|4.0648398911|3.64700554888|0.0811326088194|4.96714565097|25.3706717826|23.6486702558|2.1980505538|2.0057299624|
|legacy_composite_full_skin|1|3.68381293305|3.30514523764|0.0811326088194|4.50153902234|22.9924944984|21.4319086782|1.9920113152|1.81771832929|

## SC민감도와 과학적8gate를 분리

사전등록1%/2%변화율검사는 raw와기존SC2skin8 두A에서만20개다. 목표mean/P10은1%,비표적P95·J95·각손실/sourcepower는2%,8gate상태변화허용0개다. 전체5모드가모두이20개검사대상이라는뜻은아니다.

|모드|지표|SC2|SC4 같은 A|상대변화 %|허용 %|판정|
|---|---|---|---|---|---|---|
|raw_1Vpp|primary_maxTIS_mean|3.68380072432|3.68381293305|0.000331416477355|1|PASS|
|raw_1Vpp|primary_maxTIS_p10|3.30513584541|3.30514523764|0.000284170824333|1|PASS|
|raw_1Vpp|surface_0_5_maxTIS_p95|22.9919264848|22.9924944984|0.00247049139123|2|PASS|
|raw_1Vpp|primary_complement_maxTIS_p95|21.4321186487|21.4319086782|0.000979700242294|2|PASS|
|raw_1Vpp|surface_J_RMS_p95_A_m2|10.9592944588|10.9575503863|0.0159140946377|2|PASS|
|raw_1Vpp|bulk_skin_J_vector_RMS_p95_A_m2|6.1912792518|6.19145851768|0.00289545777158|2|PASS|
|raw_1Vpp|SC_power_W|1.77929655521e-06|1.77925534597e-06|0.00231604130525|2|PASS|
|raw_1Vpp|contact_power_W|1.33349972214e-06|1.33379199661e-06|0.0219178504829|2|PASS|
|raw_1Vpp|skin_SC_plus_dermis_power_W|0.000553353751079|0.000553375065156|0.00385179965031|2|PASS|
|raw_1Vpp|source_power_W|0.00085129332981|0.000851328675736|0.00415202673357|2|PASS|
|skin_contact_only|primary_maxTIS_mean|4.0647793478|4.06479281915|0.000331416477327|1|PASS|
|skin_contact_only|primary_maxTIS_p10|3.64695295198|3.64696331556|0.00028417082434|1|PASS|
|skin_contact_only|surface_0_5_maxTIS_p95|25.3697512258|25.3703779833|0.00247049139123|2|PASS|
|skin_contact_only|primary_complement_maxTIS_p95|23.6486280834|23.6483963978|0.000979700242301|2|PASS|
|skin_contact_only|surface_J_RMS_p95_A_m2|12.0927045506|12.0907801062|0.0159140946377|2|PASS|
|skin_contact_only|bulk_skin_J_vector_RMS_p95_A_m2|6.8315812723|6.83177907785|0.00289545777158|2|PASS|
|skin_contact_only|SC_power_W|2.16635701989e-06|2.16630684617e-06|0.00231604130525|2|PASS|
|skin_contact_only|contact_power_W|1.62358347495e-06|1.62393932955e-06|0.0219178504829|2|PASS|
|skin_contact_only|skin_SC_plus_dermis_power_W|0.000673727928951|0.000673753879601|0.00385179965031|2|PASS|
|skin_contact_only|source_power_W|0.00103647999296|0.00103652302789|0.00415202673358|2|PASS|

고정SC2skin8의8gate는6/8이며 SC2와상태가같다. 보조SC4skin8도같은두P95가실패한다. sensitivityPASS가과학적화면FAIL을대체하지않는다.

|검사|기준|SC4 고정 A|변화 %|단위|판정|
|---|---|---|---|---|---|
|primary_maxTIS_mean|4.0618489416|4.06479281915|0.0724762931209|V/m|PASS|
|primary_maxTIS_p10|3.64573573913|3.64696331556|0.033671569074|V/m|PASS|
|surface_0_5_maxTIS_p95|25.2592218317|25.3703779833|0.440061662893|V/m|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|7.76652901786e-06|7.65616071429e-06|-1.42107630471|m3|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|8.209453125e-06|8.13138950893e-06|-0.950899102325|m3|PASS|
|primary_complement_maxTIS_p95|23.4357185812|23.6483963978|0.907494326573|V/m|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|1.93996552549e-05|1.92793743929e-05|-0.620015461328|m3|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|2.11556556606e-05|2.10680266459e-05|-0.414210819888|m3|PASS|

## 실제전류·부담·signedpower·nativeφ40

|군|출력 RMS mA|접촉Jmax/J95 A/m²|접촉전압RMS V|SC loss W|contact loss W|SC+dermis loss W|sourcepower W|
|---|---|---|---|---|---|---|---|
|SC4 · 기존 SC2 배율 고정|[1.3982391197369397, 1.3986938178851096]|[17.82270799684118, 12.09078010618836]|0.00187683567291|2.16630684617e-06|1.62393932955e-06|0.000673753879601|0.00103652302789|
|SC4 · 원 SC2 상수로 보조 재맞춤|[1.398255311915983, 1.3987100153297427]|[17.822914391065783, 12.090920122351182]|0.00187685740743|2.16635701989e-06|1.62397694153e-06|0.00067376948438|0.00103654703474|

모든5모드의부담·signed출력별/주파수별source/metal/50Ω전력·물리패드전류·GNDnet/localJ는brief/GUI에보존했다. 음의전력을clamp하지않는다. raw ideal source총0.0008513286757362501W,metal delivered총0.0006907002385163736W,50Ωloss총0.0001606284372198765W다. 교차주파수음의ideal/metal전력흡수요구와총합양수를구분한다. GNDnet상쇄가localJ=0이나절연회로를뜻하지않는다.

SC4의40개 native복소φ 차동프로브는 깊이5/10/15/20mm × 중심/(±5,0)/(0,±5)mm × X/Y방향이며 tipgap5mm다. probe중심간격과tip간격은 별개다. raw probesJSON에 Vpp bounds/RMS/기본파envelope/스펙트럼, 두5모드묶음에 각각 scaled40개를 보존했다. waveform저장검사PASS/RMS상대오차0/envelope오차최대1.3877787807814457e−17V다. SC2예측은 기존것을 재사용했다. 모두무부하이며 ETA5001 입력R/C·대역폭·스위치·감쇠/보정은 미검증이다. 전체XYZ native scalar체적은 이번에생성하지 않았고 중심20XYZ와fixed/max체적을 구분한다.

[SC4 raw40](cloud-rounded-sc4-sensitivity-20261021T204000Z/rounded-opt-e7b3bf639935-SC4-same-command/probes.json) · [선정SC2 condition](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-e7b3bf639935/condition.json)

## 실제실행·감사복구·출처

새native1조건/8RHS 117.745909533초, sampledaggregate peakRSS 531206144B. 선택구동후처리14.641102108초/peakRSS497627136B/새PDE0. CPU1·기존누적13800초예산이다. native5gate와SC민감도PASS는별개다.

첫 큐는 native완료 후 root가SC2 baseline을SC4 same-grid full-skin감사에 넘겨guard에서실패했다. 원로그/실패영수증을보존했고 새큐에서기존squareSC4를 감사용same-grid대조군으로사용해복구했다. 복구·민감도큐 모든단계exit0, PDE재실행0개다. SC4square scalar/cap을과학비교에쓰지않고 원SC2 current/power/8caps/cutoff를고정했다.

첫publication schema실패도보존했고 새v2발행은published_completed_batch · 2026-10-21T19:39:36.476567+00:00 · commit `a164e07ce7a89fbef19f7d016e035ef673398688`다.

|계층|source run/case|source commit|config SHA256|
|---|---|---|---|
|원래 SC2 4-square 기준|cloud-mesh-c1-20261019T190000Z/baseline-square15-xy80|38f005ecefc2c432cd6424a06f599f93682cc202|f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b|
|선정 SC2 rounded 구동|cloud-rounded-fullface-20261021T200000Z/rounded-fullface225-xy80|10a70e9cfa19537825f2f5e829b7d1d14acbd35c|cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0|
|SC4 · 기존 SC2 배율 고정|cloud-rounded-sc4-20261021T204000Z/rounded-fullface225-sc4-xy80|4b553e473be0f46e4f5b7d72cb30ee5c68eb7c82|5cac8156e6a18af31a17e899f4726dd8cd749dc497c5ea4a5afe10c8ba28b0a0|

민감도구현commit `889ecd0f618af9d45495c37e7b1f87ef11e42d03`와nativeproducercommit을구분한다. SC4 [config](../data-native/cloud-rounded-sc4-20261021T204000Z/configs/rounded-fullface225-sc4-xy80.properties)·[mask](../data-native/cloud-rounded-sc4-20261021T204000Z/masks/rounded-fullface225-sc4-xy80.csv)·[frozen-source manifest](../data-native/cloud-rounded-sc4-20261021T204000Z/frozen-source-manifest.json)·[public compact snapshot](cloud-rounded-sc4-context-20261021T204000Z/completed-native-snapshot/summary.json)에연결했다. raw/config/mask의SHA는completedreceipt를인용하며본작성에서재해시하지않았다.

- [summary](cloud-rounded-sc4-sensitivity-20261021T204000Z/summary.json), SHA256 `f4d99e42fb11b225b0764b2d6bc8d090405efdcee981890f3411246d2be585fb`
- [condition](cloud-rounded-sc4-sensitivity-20261021T204000Z/rounded-opt-e7b3bf639935-SC4-same-command/condition.json), SHA256 `05aa7358ba050c3c753d4e8deb10f4ddcdb1b39c1d6ed40c30459dd63687dc48`
- [selected_SC2_condition](cloud-rounded-drive-optimization-20261021T203000Z/rounded-opt-e7b3bf639935/condition.json), SHA256 `48fabf8729c4efeb7ffb39737c49fba09bab29185dbc39ddaeede7684e11374e`
- [native_case](../data-native/cloud-rounded-sc4-20261021T204000Z/cases/rounded-fullface225-sc4-xy80.json), SHA256 `41104307d05b7779451d7b32b64e59fb108065ce2a38414816bd43b36876a3a2`
- [decision](cloud-rounded-sc4-context-20261021T204000Z/decision.json), SHA256 `7fffabb7057f841a08e47ca71c4f3846f70c9aae658084d1958c168ef72a9ab4`
- [preregistration](cloud-rounded-sc4-context-20261021T204000Z/sensitivity-plan.json), SHA256 `2c877a7c5f97e7870dc4a9de442252e8d268ca8b3b3106636d5f57d798444b2b`
- [failure_disposition](cloud-rounded-sc4-context-20261021T204000Z/audit-failure-disposition.json), SHA256 `55e2c82d4297c00a135da34bb1f3096c406ed600aa4170f8c92388ff4f0183e4`
- [failed_native_queue](cloud-rounded-sc4-context-20261021T204000Z/queue-native/summary.json), SHA256 `39f4ab0f24e239682260f9794ca28a5d9e62f19926b36f9922c533ac9dea4304`
- [audit_recovery_queue](cloud-rounded-sc4-context-20261021T204000Z/queue-audit-recovery/summary.json), SHA256 `30d4a32bee9773837bef539c6dfa7d2dedfad746addd6e55a1dd3d6150bd9120`
- [sensitivity_queue](cloud-rounded-sc4-context-20261021T204000Z/queue-sensitivity/summary.json), SHA256 `f4f4bd46b1dd4e9806bb34cbe3df7cf780c5023f0d467dc2200db541d78f1939`
- [publication](cloud-rounded-sc4-context-20261021T204000Z/rounded-sc4-publication-20261021T204000Z-v2.json), SHA256 `1e807ce159d4e5d0302d0830396ce97dd9fcdeed7cc13bc245508f441829988b`
- [feedback_after](cloud-rounded-sc4-context-20261021T204000Z/feedback-after-sensitivity.json), SHA256 `bb508f3a4e6255a93c9e35f032baba81e708a1fe7fe033104a3866633e3bc8c0`
- [SC4_probe40](cloud-rounded-sc4-sensitivity-20261021T204000Z/rounded-opt-e7b3bf639935-SC4-same-command/probes.json), SHA256 `4a62627da1f923ce2d9ab0ada767d5bfb81d171acb00ae9a7d67c1b9c41709d3`

두SC수준진단뿐이므로 SC/XY/bulk/edge/contact/방향전체수렴·실험·활성화·인체안전·PBS계면의실제피부유효성·hardware흡수/동기화/compliance·instrument부하·독립영구fullcomplexbackup/restore·COMSOL5.3a 예정5.3.1.201 설치/실행은 미검증이다. 본문서는완료JSON만읽고 native E/φ/grid/mask/config/NPZ를읽거나과학수치를재계산하지않았다.

다음root선택은동일SC4형상/선정구동의명목PBS specificcomplexZ×0.5/×2로별도등록·실행한다. 본완료결과에는포함하지않는다.
