# 작업1: Original candidate single-pair RMS comparison (2026-10-21)

최신 fine original-refine-3e018f8a317a의 raw/skin8 TIS field RMS에 맞춘 단일 전극쌍 C1 비교다. 첫4행은 원래4-square3h raw/skin8의 과거2기준 매칭을 원형 그대로 재사용하고, 뒤4행만 이번 최신 후보의 새 JSON 기반 매칭이다. 총8개 모두 미채택 진단이다. 새 PDE/native RHS/배열 decode는0이고 기존 C1의 nativephi 단위 응답을 사용했다.

[8행 오프라인 GUI](CLOUD_ORIGINAL_SINGLE_PAIR_RESULTS_20261021.html) · [정확한8match brief](ORIGINAL_SINGLE_PAIR_RESULTS_20261021.result-brief.json) · [원본summary](cloud-original-single-pair-20261021T224000Z/summary.json)

## 실제 비교 정의·회로·footprint

팬텀 D50mm·SC/dermis/fat/muscle0.1/5/5/15mm·윗면·XY.625SC2bulk14/14/40의 nominal PBS 접촉 모델만 비교한다. C1은 source(−10,−10)와 return(+10,−10) 전극을 포함한 square225mm²×2=450mm²/독립출력1개/귀환노드1개/50Ω의3000Hz pure sine이다. TIS는 square225mm²×4=900mm²/독립출력2개/공통GND1/50Ω이며 source0SW/source1NE·return2SE/3NW다. 비구동 주파수 출력은0Vthrough50Ω다. 전극 footprint·전류·접촉부담·전력은 RMS 매칭으로 같아지지 않는다.

centre20_E_RMS는 (0,0,깊이20mm)의 전체field 벡터 RMS이고 ROI_energy_RMS는 r≤5mm·깊이15–20mm에서 sqrt(weighted mean(E_RMS²))=hypot(saved weighted mean,saved weighted population std)이다. 평균 E_RMS 자체와 구분한다. 두 기준을 각각 맞추므로 다른 기준 RMS는 일반적으로 같지 않다. +z는 표면0에서 팬텀 안쪽, x/y는 수평이다. 단일3000Hz sine의 envelope variation은0이며 field RMS 동등성이 TIS 변조·생리적 활성화·안전 동등성을 뜻하지 않는다.

required_source_Vpp/actual_source_Vpp는50Ω 앞의 open/high-Z 전체source 파형 max-minus-min이다. source_voltage_RMS_V는 실제 source phasor에서 얻은 별도 물리량이고 최신4match에 저장됐다. 과거baseline4alias에는 없으므로 N/A로 두며 Vpp/√8로 채워 넣지 않는다. loaded_metal_Vpp는 기존50Ω·팬텀 회로가 연결된 전극 metal 전압이고 contact_voltage_RMS_max_V는 계면 접촉 전압으로 서로 다르다. metal의 loaded는 실제 측정기 loading을 검증했다는 뜻이 아니다.

## 매칭 전압·전류·전력

|TIS reference/mode|match|TISsourceVpp out0/out1|요구 C1sourceVpp|C1sourceRMSV|C1metalVpp|C1currentRMSmA|C1sourcepowerW|
|---|---|---|---:|---:|---:|---:|---:|
|original-SC2-square3h--raw|centre20_E_RMS|[[1.0, 1.0], [1.0, 1.0]]|1.64641036263|N/A|1.433672794|1.54104500224|0.000878432244881|
|original-SC2-square3h--raw|ROI_energy_RMS|[[1.0, 1.0], [1.0, 1.0]]|1.64934406634|N/A|1.43622742514|1.54379095765|0.000881565553559|
|original-SC2-square3h--skin_contact_only|centre20_E_RMS|[[1.0, 1.0], [1.0, 1.0]]|1.64641036263|N/A|1.433672794|1.54104500224|0.000878432244881|
|original-SC2-square3h--skin_contact_only|ROI_energy_RMS|[[1.0, 1.0], [1.0, 1.0]]|1.64934406634|N/A|1.43622742514|1.54379095765|0.000881565553559|
|original-SC2-refine-3e018f8a317a--raw|centre20_E_RMS|[[0.9961371089748255, 0.9961378444424639], [0.9999992474456438, 1.0]]|1.41608895685|0.500663052077|1.23311190053|1.32546348056|0.000649850054061|
|original-SC2-refine-3e018f8a317a--raw|ROI_energy_RMS|[[0.9961371089748255, 0.9961378444424639], [0.9999992474456438, 1.0]]|1.41920101311|0.50176333012|1.23582183877|1.32837637449|0.000652709467861|
|original-SC2-refine-3e018f8a317a--skin_contact_only|centre20_E_RMS|[[1.0892577694395789, 1.089258573660034], [1.093480947452011, 1.0934817703564808]]|1.54846745952|0.547465920537|1.34838538404|1.44937015327|0.00077702725765|
|original-SC2-refine-3e018f8a317a--skin_contact_only|ROI_energy_RMS|[[1.0892577694395789, 1.089258573660034], [1.093480947452011, 1.0934817703564808]]|1.55187043631|0.548669054519|1.3513486521|1.45255534968|0.000780446265542|

최신 skin8의 C1 ROI-energy match는 source1.551870436311588Vpp, I_RMS1.452555349675261mA, source power0.0007804462655418804W다. contact J95=16.915446606385157A/m²로 해당 TIS12.466047323068057A/m² 및 original numerical cap13.553106044904386A/m²보다 크다. centre match는 source1.5484674595204853Vpp이며 실제 전류·전력·J95도 별도 행에 보존했다. 최신 TIS source power는0.0010269986618699802W다. 따라서 전력 감소만으로 같은 표면 부담을 확보했다고 해석하지 않는다. 이 cap은 수치 비교기준이며 인체안전 한계가 아니다. 새 C1 동일부담 재정규화 trial을 수행하지 않았다.

|TIS reference/mode|match|TIScentre/ROIenergy RMS V/m|C1centre/ROIenergy RMS V/m|C1contactJmax/J95 A/m²|C1volumeSC+dermis Jmax/J95 A/m²|C1contactVRMS V|
|---|---|---:|---:|---:|---:|---:|
|original-SC2-square3h--raw|centre20_E_RMS|2.09503782023/2.31263459234|2.09503782023/2.30852108757|24.6501621638/17.9459353884|24.5618153139/7.25270095445|0.00260573966686|
|original-SC2-square3h--raw|ROI_energy_RMS|2.09503782023/2.31263459234|2.09877092369/2.31263459234|24.694085765/17.9779128701|24.6055814917/7.26562438846|0.00261038277911|
|original-SC2-square3h--skin_contact_only|centre20_E_RMS|2.09503782023/2.31263459234|2.09503782023/2.30852108757|24.6501621638/17.9459353884|24.5618153139/7.25270095445|0.00260573966686|
|original-SC2-square3h--skin_contact_only|ROI_energy_RMS|2.09503782023/2.31263459234|2.09877092369/2.31263459234|24.694085765/17.9779128701|24.6055814917/7.26562438846|0.00261038277911|
|original-SC2-refine-3e018f8a317a--raw|centre20_E_RMS|1.80195654058/1.98993856005|1.80195654058/1.98557497752|21.2017752179/15.4354233311|21.1257874803/6.23809832716|0.00224121473627|
|original-SC2-refine-3e018f8a317a--raw|ROI_energy_RMS|1.80195654058/1.98993856005|1.80591659556/1.98993856005|21.248369125/15.4693448624|21.1722143936/6.2518074327|0.00224614012342|
|original-SC2-refine-3e018f8a317a--skin_contact_only|centre20_E_RMS|1.97040662809/2.17596153955|1.97040662809/2.17119004159|23.1837546999/16.8783540303|23.1006634941/6.82124680244|0.00245072745757|
|original-SC2-refine-3e018f8a317a--skin_contact_only|ROI_energy_RMS|1.97040662809/2.17596153955|1.97473687603/2.17596153955|23.234704288/16.9154466064|23.1514304775/6.83623745944|0.00245611327863|

원래square raw/skin8의4match는 과거 baseline aliases이며 새로 계산하지 않았다. 각reference의9burdens와 C1의 SC/dermis/SC+dermis/fat/muscle/contact/50Ω/source loss 및 signed output/group/frequency power를 GUI/brief에 보존했다. 음수/비활성0전력선을 제거하지 않았다. 원래alias에 미제공 sourceRMS/TIS signedperoutput/current는 N/A로 두었다.

## nativeφ40·계측기·검증 범위

각8match의40 unloaded nativeφ 차동 프로브 값/ID를 실제 summaryJSON pointer로 연결했다. 깊이5/10/15/20mm×중심·X±5/Y±5의5개 probe 중심×X/Y 두 수평방향,tipgap5mm다. 각 Vpp lower/upper·RMS·envelope variation을 저장했고 해당 amplitude로 공유된 원본 native sine spectrum/timewave 출처를 링크한다. source 단위 nativephi JSON은 upstreamSHA 영수증이며 이번 report에서 다시 열거나 해시하지 않았다.

ETA5001은 각 tip-to-reference-ground의4MΩ∥7pF shunt2개다. 둘의 차동 등가는8MΩ/3.5pF이며 이 값을 별도 병렬 branch로 더하지 않는다. DSOX1202A1MΩ∥16pF(명목±2%,C±3pF)는 probe 출력 downstream 부하다. 50×/500× 감쇠와 scope 표시 probe-factor는 nominal selectable 설정이고 실제 switch·ground·outputZ·portZ·대역폭·보정/전달함수는 미검증이다. 15MHz 대역폭만으로 임의 filter가 검증되지 않는다. phantom-loaded 실제예측과 수치 감쇠율 적용은 port response/실제 설정이 없어 보류했다.

최신3e fine skin8 목표 maxTIS mean4.011539371036533/P10 3.595322017410421V/m는 원래square4.061848941601601/3.6457357391300533V/m보다 낮고 screen은6/8(목표2FAIL)이다. 별도 SC4 두수준 진단은20/20 PASS였지만 XY-coarse는14/20·J95/SC/contactpower6FAIL이고 과거3waveXYFAIL도 남는다. 이번 C1은 nominalPBS SC2만으로 SC4/coarse/contact변형 결과를 매칭하지 않는다. 전체 수렴·edge/contact/PBS피부전이·장비 흡수/compliance·실험·생리·COMSOL5.3a·독립 native 영구백업·후보채택은 미검증이다.

native_basis_run_id=cloud-mesh-c1-20261019T190000Z; TIS_calculation_run_id=cloud-original-drive-refinement-20261021T222000Z; comparison_run_id=cloud-original-single-pair-20261021T224000Z. baseline aliases는 과거 source를 불변 재사용한다. 물리 native sourcecommit38f005ecefc2c432cd6424a06f599f93682cc202와 이번comparison codecommitd5bfd514dc77a16fd713cb8bb2746fcc01247771를 구분한다.

실제 calculated_unadopted, wall 0.10054841300006956s, peakRSS39075840bytes,CPU1,newPDE0/newRHS0/native_array_decodeFalse. Queue completed_preregistered_queue 모든 stage exit0. Publication 완료영수증은 작성시점 별도확인하지 않아 발행commit을 추측하지 않는다. 본문서는 docs JSON 및 명시된 instrument config만 읽고 저장값·해시를 대조했으며 배열·새 계산·렌더·Git 작업을 수행하지 않았다.

문서 해시와 sourceJSON 대조는 시뮬레이션 독립재현·전체격자수렴·실험검증·독립 native 영구백업이 아니다. 새 C1 modulation은0인 pure sine으로 TIS 변조값으로 치환하지 않는다.

## Source receipts

- [summary](cloud-original-single-pair-20261021T224000Z/summary.json), SHA256 `e830c0176d71d765d57398e5249a6a17068e89ecdec516b03a55371d607d8911`
- [queue](cloud-original-single-pair-context-20261021T224000Z/queue/summary.json), SHA256 `f3745bc148409d5a32a62a51b84cf7a7f5f1dd4b74eb14ceaf0c3c29a57b483c`
- [decision](cloud-original-single-pair-context-20261021T224000Z/decision.json), SHA256 `59054dd5116d95556343602380efd371adb09f5d1876489c011d806789296263`
- [feedback_before](cloud-original-single-pair-context-20261021T224000Z/feedback-before.json), SHA256 `de615af774db90e66ef4477bc6e10de2105d932c0a04205402602a098d28a400`
- [feedback_after](cloud-original-single-pair-context-20261021T224000Z/feedback-after.json), SHA256 `c9aaedab631e4eb8dc9dec02dd9883f7d6dce222e96de0fce794abe0fe97d26f`
- [instrument_config](../configs/task1_instrument_ETA5001_DSOX1202A.json), SHA256 `008329c985d199ba9632c34156a61cf72321c608fc557f19103d2ff351c987ae`
- [preregistration](cloud-original-single-pair-context-20261021T224000Z/preregistration.json), SHA256 `a0c8acad50a9ad335442ffb7f7cdbab2607642d8e51418422e59f782ea929890`
- [baseline_alias_source](cloud-rounded-single-pair-20261021T212000Z/summary.json), SHA256 `7e29ffa9e301461ed4a6fc90e8865dc71dd655255ce9b1cc301e549cfb4dd134`
- [fine_condition](cloud-original-drive-refinement-20261021T222000Z/original-refine-3e018f8a317a/condition.json), SHA256 `1e6b9dc90d1032d76d247567f71c62cf2d3fe4d6b28ad746e3b2cc102b61f366`
- [mesh_context](cloud-original-mesh-sensitivity-20261021T223000Z/summary.json), SHA256 `b4ec4b8d053e62256b4a3070e5da2918277e9a8cf32bc4092fefe7a678d18bbb`

C1source summary/config/단위probe SHA는 원본summary.single_stimulation 및 input_sha256의 upstream native receipt로 보존했고 이번보고서에서 native파일을 열거나 재해시하지 않았다.

[최신fineTIS5mode](CLOUD_ORIGINAL_DRIVE_REFINEMENT_RESULTS_20261021.html) · [별도SC/XY진단](CLOUD_ORIGINAL_MESH_SENSITIVITY_RESULTS_20261021.html) · [과거4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html).
