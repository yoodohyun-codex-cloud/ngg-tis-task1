# 작업1: 고정perimeter outline의 안쪽 이동 (2026-10-21)

신규 `perimeter-shell225-inward0p625-xy80`는 **미채택**이다. skin8에서목표ROI mean/P10이기준에미달했다. 표면P95·complementP95·complement의기준P10이상체적만통과해3PASS/5FAIL이다. 낮아진비표적P95만으로목표영역집중성공을판정하지않는다.

[3행 오프라인GUI](CLOUD_PERIMETER_INWARD_RESULTS_20261021.html) · [정확한5모드/출처brief](PERIMETER_INWARD_RESULTS_20261021.result-brief.json) · [volume](cloud-perimeter-inward-context-20261021T194000Z/volume.json) · [8gate](cloud-perimeter-inward-context-20261021T194000Z/screen.json)

## 동일shape의position-only contrast와남는교란

원래square→cachedperimeter는shape+placement복합변경이지만, 부모perimeter→신규는같은고정outline/면적을보존한position-only contrast다. 4pad모두각x/y성분0.625mm씩원점방향으로이동했다: pad0(+.625,+.625),pad1(−.625,−.625),pad2(−.625,+.625),pad3(+.625,−.625)mm. centroid각축±13.638237847222221→±13.013237847222221mm,bboxcentre±13.125→±12.5mm를구분한다. gap3.75→2.5mm(6→4XYcells),rim여유0.02344849663989379→0.8504011420479287mm가함께변하므로isolated rim효과나수렴검증으로해석하지않는다.

각pad576full-face steppedunion/225mm²,총900mm²/2304faces,partialfaces/clipping/재정규화없음이다. smootharc/convexhull/strictoutermost576아님,후속grid는동일physicaloutline과교차시키며rerank금지다. D50mm/층SC·dermis·fat·muscle0.1·5·5·15mm/윗면/XY0.625SC2bulk14·14·40을유지한다.

물리4pads/독립2outputs/공통GND50Ω,pad0→out0,pad1→out1,pad2·3→동일GND다. square_3h3000/3030/9000/9090Hz,phase0°/0°,비구동주파수0Vthrough50Ω,기존nominal1Vpp wholewave before50Ω를보존했다. scalar는새hardware waveform bracket검증이아니다. 초기2/2.01kHz기록과별도다.

주ROI중심r≤5mm·깊이15–20mm,+z안쪽,x/y수평이다. 전기장V/m,CV/P10mean은무차원이다. maxTIS는기본파2074방향표본최대(연속방향최대의하한),fixedTIS는(X+Y)/√2기본파변조,RMS는4선전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/staircasegeometry와원래squarecutoff를유지하고SC전역최고값을깊이집중으로해석하지않는다.

## raw 동일nominal1Vpp

|조건|각출력 nominal Vpp|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached perimeter 부모|1|3.683420745 / 3.373850513|0.06437681876|4.308663569|17.00506951 / 23.33228047|2.085126023 / 1.950512172|
|동일 outline 안쪽 이동 (신규)|1|3.734343238 / 3.41552315|0.06556588973|4.381978446|16.98381473 / 23.19796689|2.11433404 / 1.97455984|

## 원래square의동일8개피부·접촉부담 (skin8)

|조건|각출력 nominal Vpp|ROI mean / P10(V/m)|CV|ROI max(V/m)|surfaceP95 / complementP95(V/m)|fullRMS mean / P10(V/m)|
|---|---:|---:|---:|---:|---:|---:|
|원래 4-square 기준|1|4.061848942 / 3.645735739|0.08076162164|4.971327189|25.25922183 / 23.43571858|2.306949463 / 2.104669371|
|cached perimeter 부모|1.030042389|3.794079503 / 3.475209043|0.06437681876|4.438106116|17.51594243 / 24.03323792|2.14776819 / 2.009110218|
|동일 outline 안쪽 이동 (신규)|0.9119817727|3.405652966 / 3.114894857|0.06556588973|3.996284471|15.48892946 / 21.15612297|1.928234106 / 1.800762584|

신규활성limiter는contactnormalJ95인`surface_J_RMS_p95_A_m2`다. rawmean이부모보다높아도skin8에서는source0.911981772699nominalVpp로줄어mean3.405652965746/P103.114894857063V/m가기준4.061848941602/3.645735739130V/m에미달한다. skin8는접촉Jmax/J95·접촉전압·SC/접촉손실·SC+dermis체적vectorJmax/J95·SC+dermis손실8개수치한도이며sourcepower/1Vpp상한없음,legacy만이둘추가,동일전류/전력도1Vpp상한없음이다. raw/동일출력RMS전류합/동일sourcepower/skin8/legacy의5모드에서절대ROImean/P10/CV/P10mean/max·wholeXY보조ROI·표면/전체비표적P95·고변조체적·전역hotspot을보존했다. 수치한도는인체안전한계가아니다.

## 신규8개저장판정

|gate|단위|원래square|신규|변화%|저장판정|
|---|---|---:|---:|---:|---|
|primary_maxTIS_mean|V/m|4.061848942|3.405652966|-16.15510535|FAIL|
|primary_maxTIS_p10|V/m|3.645735739|3.114894857|-14.56059682|FAIL|
|surface_0_5_maxTIS_p95|V/m|25.25922183|15.48892946|-38.68010042|PASS|
|surface_0_5_high_volume_at_primary_r5_depth15_20_mean|m3|7.766529018e-06|9.566981027e-06|23.18219638|FAIL|
|surface_0_5_high_volume_at_primary_r5_depth15_20_p10|m3|8.209453125e-06|9.650136719e-06|17.54908118|FAIL|
|primary_complement_maxTIS_p95|V/m|23.43571858|21.15612297|-9.727013928|PASS|
|primary_complement_high_volume_at_primary_r5_depth15_20_mean|m3|1.939965525e-05|1.994765485e-05|2.824790404|FAIL|
|primary_complement_high_volume_at_primary_r5_depth15_20_p10|m3|2.115565566e-05|2.072766865e-05|-2.02303826|PASS|


## 전류·손실·무부하40개와compact snapshot

contactsurfaceJ·SC+dermis체적vectorJ·접촉전압·SC/contact/SC+dermis/sourcepower를구분했다. 그룹sourcepower와각outputRMS전류합·GND전류를혼동하지않는다. rawfullskin의SC/dermis/fat/muscle/contact/50Ωloss/sourcegroup총합을별도로보존했고legacy skin_power_W는SC+contact다. 원volume bundle에없던상세signed per-output영수증은아래완료된별도addendum으로연결한다. 이문서가새수치를계산하거나하드웨어흡수능력을주장하지않는다.

각row의rawsquare_3h 예측은깊이5/10/15/20mm ×중심·X/Y±5mm의5개probe중심 ×X/Y차동방향,tipgap5mm다. probe중심위치/중심간격과팁간격은다르다. 신규[공개docs복사probeJSON](cloud-perimeter-inward-context-20261021T194000Z/completed-native-snapshot/postprocess/perimeter-shell225-inward0p625-xy80/probes.json)의40개내용·complete/allnumericalcheckspassed와source SHA일치를확인했다. 기존2row는과거docs snapshot의upstreamraw40영수증으로native파일을재개방하지않았다. 이번volume audit는정규화별새probe40영수증을발급하지않았다. ETA5001/DSOX1202Aactualswitch·팬텀portimpedance/부하·보정은미검증으로loaded예측은보류다.

- `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`,configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),source SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `perimeter-shell225-notch-xy80` / run `cloud-perimeter-shell-20261021T185000Z`
  - source `257d56bc7300efaf691d2f017369b29065a7edf0`,configSHA256 `f447c99072d8460b11775add881fc84abaa528766bcab79766d3fbc042f7fec8`
  - [rawunloaded40](../data-native/cloud-perimeter-shell-20261021T185000Z/postprocess/perimeter-shell225-notch-xy80/probes.json),source SHA256 `da6ff0f59e36827fce26f3e418fb52a0073d44f0df488cfa576a8e67254b31ed`
- `perimeter-shell225-inward0p625-xy80` / run `cloud-perimeter-inward-20261021T194000Z`
  - source `492af6b7a19b0af00552b8801e8305f2b63c968f`,configSHA256 `a05416f839fbd903b98c3565e8d29198a9b89b585767a13e25a14b96c9e389db`
  - [rawunloaded40](cloud-perimeter-inward-context-20261021T194000Z/completed-native-snapshot/postprocess/perimeter-shell225-inward0p625-xy80/probes.json),source SHA256 `f70ff14c30a842970c559acf976e01a9c346903956687a4e76611c25c22c5faf`

완료compact snapshot의producerinventory는38파일/14,778,671bytes다. 전체complex E/phi는로컬에남으며 `full_complex_native_backup_verified=false`다. compact파일해시검증은전체raw복원/독립persistentbackup검증이아니다. 로컬배열유실시동일source/config8RHS재계산이필요하며기록된원nativewall99.61987869600125s를참고비용으로남긴다. 원본/실패증거를삭제하지않았다. 이문서는선택한docs JSON/설정만읽었고NPZ/E/phi/native디렉터리내용을열거나재해시하지않았다.

## 첫큐실패와PDE재실행없는복구

원래큐는`failed_preserved`다. native/fullskin/register3단계exit0뒤volume단계만exit1이었다. root가cachedshellsummary를newinward뒤에append해등록순서originalsquare,cachedshell,newinward와달랐고`verify_preregistration before arrays/metrics`에서차단됐다. 이미완료된nativewall은`99.61987869600125s`다. 원실패큐/plan/argv를보존했다. prepared-inputs-inventory의running=true는당시준비snapshot기록이며현재실행상태가아니다.

별도recoveryqueue는`completed_preregistered_queue`,volume/screen/GET/publish4단계exit0,elapsed`14.997982565997518s`다. `native_rerun=false, fullskin_rerun=false, registration_rerun=false, new_PDE=0`이며volume scalar는교정된등록순서로처음실행했다. 원큐7단계모두성공으로덮어쓰거나새PDE재실행으로표시하지않는다. 발행`published_completed_batch`, `2026-10-21T18:59:50.483407+00:00`,commit `dee30384bb33df033e413a2518a301988ee8d5a2`다.

physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,native source `492af6b7a19b0af00552b8801e8305f2b63c968f`,volume implementation/preregistration `4c2cd0c579b344e2b8dbbad742f82dc92b23b1ec`를구분한다. native5개방정식검증은PASS지만SC/XY/bulk/edge/contact·방향수렴/실험/ETAloaded/활성화/인체안전검증을승격하지않는다. PBSnominal계면은실제피부검증값이아니다. COMSOL5.3a/예정5.3.1.201설치·실행가능성은미검증이다. root가별도guard에서완료한새map은아래map summary/worker영수증으로연결하며이문서에서새로render하지않았다. 후속rounded/full-face shapeprobe는별도준비계획이며실제결과를예측하지않는다.

- [volume](cloud-perimeter-inward-context-20261021T194000Z/volume.json),SHA256 `fb61399c2d81dc6c417de3b72adc42f50c05d79080d0857ca23b97e90f661306`
- [screen](cloud-perimeter-inward-context-20261021T194000Z/screen.json),SHA256 `e4f7be04107ad69b055fe0fc60e164a1069209ec176e393f3f2a76f7f40c1811`
- [volume_plan](cloud-perimeter-inward-context-20261021T194000Z/volume-plan.json),SHA256 `f81c1ead6048df8603a7051bf9b4b5ac8496cd2fd3d7ab0f7e4ffaa7e54cae60`
- [screen_plan](cloud-perimeter-inward-context-20261021T194000Z/screen-plan.json),SHA256 `94bb3e2c9bd3f449eb4af363d05688cb9018669f6abb5a877212acb407d372fc`
- [decision](cloud-perimeter-inward-context-20261021T194000Z/decision.json),SHA256 `a42a99c19facb6decc110792610254d82dc775e016abd73b9f1e3b26dbbebb4f`
- [original_failed_queue](cloud-perimeter-inward-context-20261021T194000Z/queue/summary.json),SHA256 `735acce1b199604e45fb097cfb980214368f145f645f5623654212cb9a913aa1`
- [postprocess_failure_disposition](cloud-perimeter-inward-context-20261021T194000Z/postprocess-failure-disposition.json),SHA256 `e610b156038d87146ff41d369cc9d64fa014873795c688fd60a2a42acdae826e`
- [recovery_plan](cloud-perimeter-inward-context-20261021T194000Z/postprocess-recovery-plan.json),SHA256 `48e4de636238c089a2acc9b35043e2ba4373a1c6492f74997137e51c2dcbdff6`
- [recovery_queue](cloud-perimeter-inward-context-20261021T194000Z/queue-postprocess-recovery-20261021T190000Z/summary.json),SHA256 `e7d9bec5da31b5786076d7b11513c023ce230b94622aea8c5dbc26e3945a558d`
- [publication](cloud-perimeter-inward-context-20261021T194000Z/perimeter-inward-publication-20261021T194000Z.json),SHA256 `0b86d63f513d91610198ed473b4c63916c8653f456027c0f7d642f94a889fff4`
- [feedback_after](cloud-perimeter-inward-context-20261021T194000Z/feedback-after.json),SHA256 `bdaf5d22b8beee6cb31308fffe512aee405ac32fe292a78d07dff3bfc4dc9f5b`
- [prepared_inventory](cloud-perimeter-inward-context-20261021T194000Z/prepared-inputs-inventory.json),SHA256 `e02a33224d5d3bb1833af474a3a200af3908033feb67c98775ddc0d4d2c8ff5f`
- [completed_snapshot_inventory](cloud-perimeter-inward-context-20261021T194000Z/completed-snapshot-inventory.json),SHA256 `cf0eb3da4b06d577bd443194dccd0842791aed379f5f40686ff39084064bcc40`
- [prepared_geometry_proof](cloud-perimeter-inward-context-20261021T194000Z/prepared-inputs/geometry-audit/perimeter-mask-proof.json),SHA256 `552961594e8eb0ee73638320b1e844ed636a32ef490dd85dc67046672c68c7bc`
- [prepared_physical_design](cloud-perimeter-inward-context-20261021T194000Z/prepared-inputs/geometry-audit/perimeter-design.json),SHA256 `d65c68fb3f9b08851a43ee0352641d6b0fddf47b527cf0f5f33501455a7d644a`
- [native_summary_snapshot](cloud-perimeter-inward-context-20261021T194000Z/completed-native-snapshot/summary.json),SHA256 `89e2324453f47bd0addada3935fd70ed6ab5c99c0927500279154c9f4e56d562`
- [verified_parent_snapshot](PERIMETER_SHELL_RESULTS_20261021.result-brief.json),SHA256 `3c09e2121db7d44387f6c4a2561ec0498207e9c12acda9ceda034f034fb57c5b`

[과거drive최적화GUI](CLOUD_PERIMETER_DRIVE_OPTIMIZATION_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다. 이번화면은새물리맵을생성하지않은오프라인JSON표다.

## 완료된 signed 출력전력·공간맵 addendum

[3기하×5모드 saved-phasor signed power audit](cloud-inward-output-power-20261021T195500Z.json)는 `completed_saved_phasor_audit`, source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`이다. source/metal/50Ωloss를각주파수·각출력·그룹총합으로분리해GUI에표시하며음의값을clip/abs처리하지않았다. 이root audit는E/phi/grid/mask/config/NPZ읽기와새PDE/RHS/정규화탐색이0이다. 기존volume지표·8gate는바뀌지않았고하드웨어흡수/sink/compliance나독립native재계산을검증하지않았다.

[실제공간맵13PNG+HTML](cloud-perimeter-inward-native-maps-20261021T195000Z/index.html)은root guard `completed`, wall `10.919404157997633s`, max120s로완료됐다. [map summary](cloud-perimeter-inward-native-maps-20261021T195000Z/summary.json)와[worker receipt](cloud-perimeter-inward-context-20261021T194000Z/maps-worker-receipt.json)에연결한다. raw/skin8 maxTIS/fixedTIS/RMS의global공통범위와명시된deepROI clipping보조범위를유지한다. deepXY padmarkers는윗면패드중심투영이며깊은위치의전극이아니다. 맵은display only/score·gate재계산없음/미채택이고수렴·활성화·실험증거가아니다. 이문서에서PNGdecode·새render를하지않았다.

- [signed_output_power_addendum](cloud-inward-output-power-20261021T195500Z.json),SHA256 `40f3ba57dbddf5003332f5488801fd177852149a58bf13e28e6d4aa3cb732bd5`
- [maps_summary](cloud-perimeter-inward-native-maps-20261021T195000Z/summary.json),SHA256 `14d094d8aa5a91bf9a501fd41eadeb2aa04ce4e4fb1d21c16eb3fa8801ac73b4`
- [maps_worker_receipt](cloud-perimeter-inward-context-20261021T194000Z/maps-worker-receipt.json),SHA256 `e7567fd8e9f61115d2746ae3d449aa15b5445900fa68062f0940c9c16c08d0ec`
- [maps_HTML](cloud-perimeter-inward-native-maps-20261021T195000Z/index.html),SHA256 `c304da81a400c698d025a4a6f26d47ea99f98d416ddee435706259218fdc902a`
