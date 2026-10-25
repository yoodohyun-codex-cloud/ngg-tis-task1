# 작업1: Perimeter fixed face-union 패드 (2026-10-21)

신규 `perimeter-shell225-notch-xy80`는 **채택하지 않는다**. skin8에서 표면P95는 낮아지지만, 목표ROI 평균/P10이 원래 square보다 낮고 기준cutoff 이상 표면체적과 전체비표적 지표가 증가했다. 저장8개 gate 중 표면P95만PASS, 나머지7개FAIL이다. 더낮은CV나한표면지표만으로 깊이집중 성공을 판정하지 않는다.

[2행 오프라인GUI](CLOUD_PERIMETER_SHELL_RESULTS_20261021.html) · [정확한5모드/출처brief](PERIMETER_SHELL_RESULTS_20261021.result-brief.json) · [volume](cloud-perimeter-shell-context-20261021T185000Z/volume.json) · [8개screen](cloud-perimeter-shell-context-20261021T185000Z/screen.json)

## 실제 접촉 형상과 비교 범위

원래225mm² square4개와 새perimeter4개는 모두225mm²×4=900mm²이지만, **패드 형상과위치를 함께바꾼 비교**다. 독립적인 형상효과로 해석하지 않는다. 새패드는 각576개 full native-face직사각형의 고정 stepped union이다. smooth annular arc/convex hull 또는 strict outermost576으로 대체하지 않는다. 전체cutoff ties를 보존한 radial prefix에서 outerdiagonal face(67,67)를 제거한 notch를 포함한다. pad마다4-neighbour component1개/noholes이며4회전·x/y반사대칭이다. partialfaces/clipping/면적재정규화는없다.

bbox폭/높이22.5mm는접촉사각형의크기가아니다. bboxcentre각축±13.125mm와 실제면적centroid각축±13.638237847222221mm를구분한다. `center_mm`는면적centroid다. 후속mesh는동일fixedphysical boundary를교차시켜야하며 radial ranking을다시해패드형상을바꾸면수렴검증이아니다. minpadgap3.75mm=6XYcells이나 바깥vertex의이상D50rim여유는0.02344849663989379mm뿐이다. 외벽staircase/edge/contact불확실성과수렴미검증을유지한다.

D50mm, SC/dermis/fat/muscle0.1/5/5/15mm·윗면, XY0.625/SC2/bulk14·14·40/351680cells이다. 물리4pads/독립2outputs/공통GND/50Ω, pad0(Q3)→out0, pad1(Q1)→out1, pad2(Q4)·3(Q2)→동일GND다. phase0°/0°, square_3h 3000/3030/9000/9090Hz와다른주파수0Vthrough50Ω종단을유지한다. private isolated returns나새전원을가정하지않는다. nominal1Vpp는기존wholewave before50Ω정의이며새hardware waveform bracket검증은아니다. 초기2/2.01kHz기록과별도다.

주ROI 중심r≤5mm·깊이15–20mm, x/y수평·+z안쪽이다. 모든전기장V/m, CV/P10mean은무차원이다. maxTIS는기본파2074방향표본최대(연속방향최대의하한), fixedTIS는(X+Y)/√2기본파변조, RMS는4선전체벡터전기장RMS다. fractionalROI/exactzoverlap·가중ECDF·staircase geometry와원래square rawcutoff를유지했다. 이상원기둥체적으로재정규화하지않고SC전역최고값을깊이집중으로해석하지않는다.

## 동일 과거 nominal1Vpp

|조건|각출력 nominal Vpp|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|perimeter fixed face union (신규)|1|3.683420745 / 3.373850513|0.06437681876|4.308663569|17.00506951 / 23.33228047|2.085126023 / 1.950512172|

## 동일8개 피부·접촉부담 (skin8)

|조건|각출력 nominal Vpp|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|perimeter fixed face union (신규)|1.030042389|3.794079503 / 3.475209043|0.06437681876|4.438106116|17.51594243 / 24.03323792|2.14776819 / 2.009110218|

신규활성limiter는`surface_J_RMS_p95_A_m2`(접촉면J95)다. skin8source는`1.0300423889810162nominalVpp`로1Vpp를넘는다. skin8는원래square의8개피부·접촉수치한도이며sourcepower/1Vppceiling을포함하지않는다. legacy만이둘을추가하고 동일전류/전력에도1Vpp상한은없다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드에서절대ROImean/P10/CV/P10mean/max, wholeXY보조ROI, surface/complementP95, 고변조체적·전역hotspot을보존했다. 수치한도를인체안전한계로표현하지않는다.

## 신규8개 저장판정

|gate|단위|원래square|신규|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.794079503|-6.592304198|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.475209043|-4.677428878|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|17.51594243|-30.65525714|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.752377232e-06|25.56931429|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.771897321e-06|19.03225675|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|24.03323792|2.54960963|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|2.082141307e-05|7.328778778|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.219408237e-05|4.908506378|FAIL|

낮은표면P95와원래ROIcutoff이상표면체적증가를동시에보존했다. 원래square rawmean/P10 cutoff를새패드결과에맞춰바꾸지않았고 저장판정을재계산하지않았다.

## 전류·손실·signed power 범위

contact surfaceJ와SC+dermis체적전체vectorJ, 접촉전압, SC/contact/SC+dermis/sourcepower, 각출력RMS전류를5모드모두보존했다. sourcepower는그룹총합이고 출력RMS합은공통GND귀환전류와동일하지않다. rawfullskin audit는SC/dermis/fat/muscle/contact/50Ωloss와주파수별그룹sourcepower를보존한다. legacy `skin_power_W`는SC+contact로실제SC+dermis피부손실과다르다.

상세signed per-output/per-frequency금속단전력영수증은이volume bundle에없어 **미제공**으로표시한다. 그룹sourcepower만으로각출력의역전력/흡수능력이확인됐다고주장하지않고 새signed수치를계산하지않았다. 실제하드웨어source/metal흡수·compliance는미검증이다.

## raw nativephi40와출처

각행의raw square_3h 무부하40개는깊이5/10/15/20mm ×중심·X/Y±5mm의5개probe중심 ×X/Y차동방향, tipgap5mm다. probe중심간격과팁간격을구분한다. 복소전위차의전체파형Vpp/RMS/변조·스펙트럼·수치검사에연결했다. 이번volume audit는정규화별새probe40영수증을발급하지않았다. ETA5001/DSOX1202A실제switch·팬텀portimpedance/부하·보정은미검증으로loaded예측은보류다. 기존C1/맵을새perimeter결과로재명명하지않는다.

- `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json), SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`, configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [rawunloaded40](../data-native/cloud-perimeter-shell-20261021T185000Z/postprocess/perimeter-shell225-notch-xy80/probes.json), SHA256 `da6ff0f59e36827fce26f3e418fb52a0073d44f0df488cfa576a8e67254b31ed`

physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`, native source `257d56bc7300efaf691d2f017369b29065a7edf0`, volume implementation/preregistration `619f7165bac61dcbd9626b416c016ac8bdb7aa1d`를구분한다. native5개방정식검증을통과했지만SC/XY/bulk/edge/contact·연속방향수렴·실험검증을승격하지않는다. PBSnominal계면을실제피부접촉검증값으로취급하지않는다. native/probe snapshot은현재로컬이며모든원시데이터가공개됐다고가정하지않는다. 이문서는JSON/설정해시확인과저장값복사만했으며E/phi/NPZ배열을읽거나재계산하지않았다. 파일해시검증과시뮬레이션재현·수렴·실험검증을구분한다.

## 실제실행·발행

새native조건1개/4주파수×2출력=8RHS의완료영수증이다. native실행summarywall `102.2644240640002s`,7단계큐elapsed `119.55306170599943s`, `completed_preregistered_queue`,전단계exit0이다. volumeaudit `new_PDE_solves=0`은앞선새native조건1개와다른단계의통계다. 발행`published_completed_batch`, `2026-10-21T18:21:32.470225+00:00`,commit `8e7625916dd8df3c46254a1d588d6fcabfe9b861`다. COMSOL5.3a/예정5.3.1.201설치·실행가능성은미검증을유지한다.

- [volume](cloud-perimeter-shell-context-20261021T185000Z/volume.json), SHA256 `60e19c019800cd3b958dda4f183254dcc3687743314ea6016e1fcc0f28987564`
- [screen](cloud-perimeter-shell-context-20261021T185000Z/screen.json), SHA256 `8f54c169e54dc8535e11e856406d51483e1de9d968e1c89daee234e060e45548`
- [volume_plan](cloud-perimeter-shell-context-20261021T185000Z/volume-plan.json), SHA256 `fbb7c987e0217c882da2b5d9b29bf5750a3dcaf03478617ac939a01a52300aff`
- [screen_plan](cloud-perimeter-shell-context-20261021T185000Z/screen-plan.json), SHA256 `8e21f61fb988c87a1bd1718279508a4b6a03764dfcf9868559103559a9a3e73f`
- [decision](cloud-perimeter-shell-context-20261021T185000Z/decision.json), SHA256 `d17b0c5854884d3f2623c5c6862054b1c99c32227fe8f3c02579ff99964591ed`
- [queue](cloud-perimeter-shell-context-20261021T185000Z/queue/summary.json), SHA256 `cd342ee593f9ae6f5e0ffa7c85d455e74bbfcd9f1ee8d414fe00ef7da34acc3c`
- [publication](cloud-perimeter-shell-context-20261021T185000Z/perimeter-shell-publication-20261021T185000Z.json), SHA256 `dccba91139cd113729af60ee7891771f5c64d25304126369c3a86fab08ace403`
- [feedback_after](cloud-perimeter-shell-context-20261021T185000Z/feedback-after.json), SHA256 `33c82e601c7f13ef6eb47cdd2ea0cb351f97088e99d0d13e9616016a2046ac84`
- [native_summary](../data-native/cloud-perimeter-shell-20261021T185000Z/summary.json), SHA256 `d54bb51aa7ed63fdf14b46fc3decf6a8765b6d88194e138bce7399f964a732f2`
- [native_preregistration](../data-native/cloud-perimeter-shell-20261021T185000Z/preregistration.json), SHA256 `1a4a6c81c59956d5d575001278b4dd2a5470c596033efe19777e65586e8c9218`
- [geometry_mask_proof](../data-native/cloud-perimeter-shell-20261021T185000Z/geometry-audit/perimeter-mask-proof.json), SHA256 `0a3a0ec56556a02eccdf2841d91400366e410c1c743707fd87d4e4b254ace1de`
- [physical_design](../data-native/cloud-perimeter-shell-20261021T185000Z/geometry-audit/perimeter-design.json), SHA256 `90438a284ff031bfaa01ba75e6b4501391ebf5005e1836011b359363e366b538`
- [baseline-square15-xy80 raw fullskin audit](../data-native/cloud-mesh-c1-20261019T190000Z/audit/spatial-full-skin-xy80.json), SHA256 `5692424f91609d5fc7859930b717e27be540897b6f0a9f90c05c90b2a50ee666`
- [perimeter-shell225-notch-xy80 raw fullskin audit](../data-native/cloud-perimeter-shell-20261021T185000Z/audit/perimeter-shell225-notch-xy80.json), SHA256 `36abc8672624e2e65b1ad823fcd086ee6bc0bd0d04ee4423f57f40127080ee0f`

[과거접선이동GUI](CLOUD_TANGENTIAL_RETURN_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다. 이번화면은새물리공간맵을만들지않은오프라인JSON표다. 후속sine/coherent후보의완료결과를이보고서에섞지않는다.
