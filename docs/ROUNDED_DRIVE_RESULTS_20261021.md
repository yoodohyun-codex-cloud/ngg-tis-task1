# 작업1: Rounded geometry의 signed weak cross-drive (2026-10-21)

새 6조건은 모두 미채택이다. pure sine와 c=+.01 및 음수 두 조건은 목표 mean/P10을 통과했지만 비표적 지표에 실패했다. c=+.025/+.05는 목표 두 지표도 미달했다. 한 점·균일도·일부 고변조 체적의 개선을 깊이 집중 성공으로 판정하지 않는다. 원래 square 기준과 cached rounded square3h를 항상 함께 표시한다.

[8행 오프라인GUI](CLOUD_ROUNDED_DRIVE_RESULTS_20261021.html) · [정확한5모드/출처brief](ROUNDED_DRIVE_RESULTS_20261021.result-brief.json) · [원본summary](cloud-rounded-drive-20261021T202000Z/summary.json)

## 기하·회로·실제sourceVpp

새 6조건은 fixed rounded full-face225 geometry/위치를 전혀 바꾸지 않았다. 중심(±10,±10) mm, 각225/총900 mm², pad당576 full-face stepped union이며 D4 odd u²+v²≤730에560내부+16동률 face를 모두 포함한 고정 도형이다. smooth circle이 아니며 perimeter70 mm>square60 mm, gap2.5 mm(4XYcells)/rim2.002038133782378 mm의 hold를 유지한다. D50 mm/층0.1·5·5·15 mm/윗면/XY.625·SC2·bulk14·14·40, 물리4pads/독립2outputs/공통GND/50Ω, pad0out0/pad1out1/pad2·3GND다. command rank와 패드·출력수를 혼동하지 않는다.

신규 기본파3000/3030 Hz·beat30 Hz이며9000/9090Hz 계수와전력은0이다. square3h controls만4선을 포함한다. signed command seed는 -i[[1,c],[c,1]], common/difference weights1+c/1−c, 양수는common/음수는difference를 강화하고 전부 rank2다. 새K=+c²와이전unitary −c²는 별개다. 모든 mix는 ONE globalg로 raw 전체 source waveform Vpp upper의 최댓값만1Vpp로 맞췄고 출력별 독립 column정규화를 하지 않았다. 각출력이 정확히1Vpp라는 뜻은 아니다. sourceVpp는50Ω전 전체 파형 max−min bracket으로 raw폭≤1µV를 검증했으며 toneVpp나2√2RMS로 바꾸지 않는다. pure sine는별도 analytic1Vpp control이며 cachedsquare의과거 nominalscalar는 새actualbracket 검증이 아니다.

주ROI 중심r≤5mm·깊이15–20mm,x/y수평,+z안쪽을 유지했다. 모든 E/TIS 값 V/m, CV/P10mean무차원이다. maxTIS는기본파2074표본방향최대(연속방향최대의하한), fixedTIS는기본파(X+Y)/√2, fullRMS는각행의모든활성선 전체벡터RMS다. 가중ECDF/fractionalROI/exactzoverlap/원래square raw cutoff와staircasegeometry를 고정했고 analytic volume 재정규화는 없다. SC 전역 최대를 목표깊이 집중으로 해석하지 않는다.

## raw source whole-wave Vpp 기준

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached rounded square3h|cached nominal 1|4.05249095969 / 3.63880089209|0.080450718365|4.95540788828|24.9859667213 / 23.5375931838|2.30217685964 / 2.10115028133|
|rounded-sine-control|[[1.0, 1.0], [1.0, 1.0]]|3.82072511773 / 3.43069438158|0.080450718365|4.67200336179|23.5569953375 / 22.1914556708|2.06134379772 / 1.8814510437|
|rounded-cross-gain-p0p01|[[0.9999989032555817, 0.999999641556984], [0.9999992471554926, 1.0]]|3.73993253006 / 3.35711309237|0.0810085463234|4.57949047955|23.2787614146 / 21.7447944744|2.02107465121 / 1.84436605543|
|rounded-cross-gain-p0p025|[[0.99999909154544, 0.9999998300631121], [0.9999992473691492, 1.0]]|3.6217243409 / 3.24545459679|0.0818892228496|4.4441105227|22.8116002563 / 21.3475237166|1.96216668007 / 1.79010369484|
|rounded-cross-gain-p0p05|[[0.9999992611357055, 1.0], [0.9999991154390687, 0.9999998677272892]]|3.43227170153 / 3.06563525582|0.0834823512262|4.22707126482|22.4736866135 / 21.0566386377|1.86778199853 / 1.70312867455|
|rounded-cross-gain-m0p01|[[0.9999989032555817, 0.999999641556984], [0.9999992471554926, 1.0]]|3.82587379873 / 3.43812963662|0.0799155346477|4.67200543873|23.4153147296 / 22.2269213028|2.06080673721 / 1.88101218541|
|rounded-cross-gain-m0p025|[[0.99999909154544, 0.9999998300631121], [0.9999992473691492, 1.0]]|3.83343136888 / 3.44883210044|0.0791527168818|4.67201362644|23.4119759841 / 22.3231497124|2.06004212365 / 1.88012034427|

## 동일8개 피부·접촉부담 (skin8)

|조건|sourceVpp: 신규actualbounds / cachednominal|ROImean / P10V/m|CV|ROImaxV/m|surfaceP95 / complementP95V/m|fullRMSmean / P10V/m|
|---|---|---:|---:|---:|---:|---:|
|원래 4-square 기준|cached nominal 1|4.0618489416 / 3.64573573913|0.0807616216391|4.97132718867|25.2592218317 / 23.4357185812|2.30694946283 / 2.10466937124|
|cached rounded square3h|cached nominal 0.982372542559|3.98105584777 / 3.57465808423|0.080450718365|4.86805664662|24.5455276563 / 23.1226852617|2.26159533502 / 2.06411234417|
|rounded-sine-control|[[1.0797774416085857, 1.0797774416085857], [1.0797774416085857, 1.0797774416085857]]|4.12553279271 / 3.70438640228|0.080450718365|5.04472383718|25.4363121576 / 23.9618332298|2.22579253218 / 2.03154839448|
|rounded-cross-gain-p0p01|[[1.0903052708087035, 1.0903060757834966], [1.0903056457650002, 1.090306466596235]]|4.07767262216 / 3.66028211371|0.0810085463234|4.99304808356|25.3809841047 / 23.7084900303|2.20359076169 / 2.01092423701|
|rounded-cross-gain-p0p025|[[1.1058811184491049, 1.1058819351625961], [1.1058812907717592, 1.1058821230927625]]|4.00520020337 / 3.5890902199|0.0818892228496|4.9146623801|25.2269409226 / 23.6078448504|2.16992505401 / 1.97964367461|
|rounded-cross-gain-p0p05|[[1.1312396660805222, 1.1312405019137375], [1.1312395012625855, 1.1312403522814898]]|3.88272476234 / 3.46797076548|0.0834823512262|4.78183421924|25.4231445245 / 23.8201224611|2.11291064548 / 1.92664813662|
|rounded-cross-gain-m0p01|[[1.0907328760251012, 1.0907336813155961], [1.0907332511284515, 1.0907340722816068]]|4.17301090853 / 3.75008513958|0.0799155346477|5.09591551791|25.5398815888 / 24.2436603869|2.24779212466 / 2.051684081|
|rounded-cross-gain-m0p025|[[1.1069651530671307, 1.1069659705812014], [1.1069653255587037, 1.1069661586955855]]|4.24347879704 / 3.81774042221|0.0791527168818|5.17176097743|25.9162651226 / 24.7109712871|2.28039691637 / 2.08122959538|

5모드 raw/동일출력RMS전류합/동일총sourcepower/skin8/legacy를 보존했다. skin8는원래square의8개접촉·피부수치한도이며sourcepower/1Vpp ceiling이 없다. 신규6조건의limiter는 모두SC_power_W이며skin8의실제sourceupper1.0798–1.1313Vpp가1Vpp를넘으므로 raw동일전압gain과구분한다. cachedrounded square3h의limiter는SC+dermis vectorJ95로다르다. legacy만sourcepower/1Vpp상한을추가하고 동일전류/전력에도1Vpp상한이 없다. 이한도는인체안전한계가 아니다.

5모드의절대목표mean/P10/CV/P10mean/max·fixedTIS/fullRMS·wholeXY보조ROI·표면/전체비표적P95·원래cutoff이상체적·전역hotspot과각burden을GUI/brief에보존했다. 전역SC최대값은깊이집중이아니다.

## 신규저장8gate · 원래square raw기준 고정

|조건|mean|P10|surfaceP95|surface high@mean|surface high@P10|complementP95|complement high@mean|complement high@P10|
|---|---|---|---|---|---|---|---|---|
|rounded-sine-control|PASS|PASS|FAIL|PASS|FAIL|FAIL|FAIL|FAIL|
|rounded-cross-gain-p0p01|PASS|PASS|FAIL|PASS|PASS|FAIL|PASS|FAIL|
|rounded-cross-gain-p0p025|FAIL|FAIL|PASS|PASS|PASS|FAIL|PASS|PASS|
|rounded-cross-gain-p0p05|FAIL|FAIL|FAIL|PASS|PASS|FAIL|PASS|PASS|
|rounded-cross-gain-m0p01|PASS|PASS|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|
|rounded-cross-gain-m0p025|PASS|PASS|FAIL|FAIL|FAIL|FAIL|FAIL|FAIL|

각gate의원래값·후보값·변화율·단위·요구방향은원본condition JSON과GUI에보존했다. sine는목표2와surface high@mean만통과, +.01은목표2·surface고체적2·complement high@mean만통과했다. +.025는목표2와complementP95가실패하고 +.05는목표2·surfaceP95·complementP95가실패했다. 음수두조건은목표2PASS/비표적6FAIL이다.

## nativeφ40·carrierRMS·signed power·범위

새 pure-sine fullROI·fixed/max scalar volume·40nativeφ는 이번worker에서 계산했다. cachednativepost의electrical/contact/centre-field regression PASS/error0은 별도검사이며 과거sine NPZ 복원검증이 아니다. 새6조건 모두 fullvolume X/Y/Z directional scalar archives는 미생성이고 centre20의X/Y/Z값만 별도로 저장했다. fixeddiagonal/2074maximum volume archive와 혼동하지 않는다. 본보고서는docs JSON만읽고 native E/φ/grid/mask/config/NPZ를 읽거나 scientific 계산·렌더를 수행하지 않았다.

신규6조건×5모드 각각40개 무부하 예측은 condition JSON normalizations/.../probe40_unloaded에 있고 raw probes JSON에는 전체파형Vpp bounds/RMS/기본파envelope/스펙트럼과저장검사가 있다. 깊이5/10/15/20mm×중심·X/Y±5mm의5개probe중심×X/Y차동방향,tipgap5mm다. probe중심위치와팁간격을 구분한다. 각rawJSON의40 records/sourceID/SHA/unloaded/저장numericalcheckspass와파형audit를확인했다. cached2행은검증된과거docs raw40영수증을 보존하고 normalizedprobe를재발급하지않았다. ETA5001/DSOX1202A 실제switch·보정·팬텀portimpedance/부하·filter응답은미검증으로loaded예측은보류다.

저장raw carrier별RMS/balance의목표r5와wholeXY보조ROI통계는별도로표시했고다른정규화에새scale/recompute하지않았다. carrierRMS·전체fieldRMS·방향별TIS·최대표본방향TIS는별개다. 각모드signed ideal source/metal delivered/50Ωloss의출력별합계·주파수별값·그룹총합을보존했다. 음수와비활성9000/9090Hz의0계수·전력선을제거하지않았다. GND net전류와localJ·patch절대전류적분은brief/원본에별도로보존했다.

- `baseline-square15-xy80` / sourcecase `baseline-square15-xy80` / run `cloud-mesh-c1-20261019T190000Z`
  - source `38f005ecefc2c432cd6424a06f599f93682cc202`, configSHA256 `f838aeab4f1729e3eb064318781e49ef72c99f28a90b4f416097cfbdec92b64b`
  - [condition/upstream sourceJSON](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json),SHA256 `f57f94297cf5de0347af346a650fb5441ff9328f68f3764f2d4a9768324186d1`
  - [rawunloaded40](../data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/probes.json),SHA256 `2e20cb1ab1e4b1068c64723ae8a0cd3c7a1146448829cc5cae4e289ff02b9b09`
- `rounded-fullface225-xy80` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](../data-native/cloud-rounded-fullface-20261021T200000Z/postprocess/rounded-fullface225-xy80/summary.json),SHA256 `b12cc83e82cdacf457128d950ea315abe86973b0450d1eb169a1a8f3eaedef40`
  - [rawunloaded40](../data-native/cloud-rounded-fullface-20261021T200000Z/postprocess/rounded-fullface225-xy80/probes.json),SHA256 `6b0118b3cda87d31ed712d0c9e66bbd28e6bc68ab445d735c4c6c09924efe642`
- `rounded-sine-control` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-20261021T202000Z/rounded-sine-control/condition.json),SHA256 `6259d5d0d5bc58bf79ece548cb9e2d640ce0d0e2e1261333a55abaffa895277d`
  - [rawunloaded40](cloud-rounded-drive-20261021T202000Z/rounded-sine-control/probes.json),SHA256 `9a4b6090de6a4375c365dd47384b0ed2cd8145ec7dbb5f6973aed3ed662615a3`
- `rounded-cross-gain-p0p01` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-p0p01/condition.json),SHA256 `e5fe2a7c6a8de0576c92db15fb0dfb011bc6b08119d15e9c13e6681d3d2b6718`
  - [rawunloaded40](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-p0p01/probes.json),SHA256 `cc7026a33e00f5bc296f16fffa2482398e2dbe3c2a563a8ebc05db92b4947016`
- `rounded-cross-gain-p0p025` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-p0p025/condition.json),SHA256 `d8d6d95e0ea5eb94306dbb337ca86d974faa459c3e2bccd05dfc40ae664f541f`
  - [rawunloaded40](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-p0p025/probes.json),SHA256 `048a42f2e2c63fc7ed58de2fd68d54ddb12686d8756ca81820f778b0772dabb3`
- `rounded-cross-gain-p0p05` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-p0p05/condition.json),SHA256 `171c15caa770ce848d1487253b085b9042eff61dea921bdfcfced1ecc2de9826`
  - [rawunloaded40](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-p0p05/probes.json),SHA256 `b55ffb843753cc202fe945e6d2a9244ccd6d2358e39b3fdba9c80aab89079c50`
- `rounded-cross-gain-m0p01` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-m0p01/condition.json),SHA256 `7f620d5cb29c526be25a103e959e44213d17b651837fe7918e69eac07a205857`
  - [rawunloaded40](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-m0p01/probes.json),SHA256 `2b161730dea1917381bec678dc6b9351089a8746f9f8a271cb3e7810971f7465`
- `rounded-cross-gain-m0p025` / sourcecase `rounded-fullface225-xy80` / run `cloud-rounded-fullface-20261021T200000Z`
  - source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`, configSHA256 `cd9053286100f9ecb03180c1313f3fbca51d225a072594b97567f84aa4275ed0`
  - [condition/upstream sourceJSON](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-m0p025/condition.json),SHA256 `529d2444e26e5ff185bdda83e9b2ef3f2b366ccf3cc7330b05514341fbbb39a7`
  - [rawunloaded40](cloud-rounded-drive-20261021T202000Z/rounded-cross-gain-m0p025/probes.json),SHA256 `b4f280c5ef38323cfa6d261d10229f93ed50cdaf1c25d12df3c558db7a84d357`

## 실제실행·검증보류·다음준비단계

계산/GET/발행3단계 exit0, queue completed_preregistered_queue, 과학worker wall 62.56190262400196s, peakRSS 543285248bytes, CPU1, newPDE0다. queue elapsed 71.81026686900441s와worker시간은구분한다. 발행 published_completed_batch, 2026-10-21T19:15:36.924968+00:00, commit 34b2de9cbf83b4e8ddf95466479ba2ed73812aba다.

각주파수·출력·그룹의signed source/metal/resistorpower를 구분하고 음수를제거하지않는다. 비구동/교차주파수에서금속단의음의전력과실제source흡수요구는 hardware sinking/compliance 검증과다르다. 물리GND net전류상쇄는localJ=0을뜻하지않고독립절연출력/귀환삭제를 주장하지 않는다. SC/XY/bulk/edge/contact·방향수렴/실험/생리활성/C1동등성/인체안전/COMSOL5.3a 설치·실행을 새로검증하지않았다. PBS계면은실제피부검증값이아니다. fullcomplex native 독립persistentbackup은미검증이고원본·실패증거는보존한다.

다음5gene phase/asymmetry local optimizer는 코드 준비 단계이고 아직실행하지 않았다. 계획은2074방향 목표ROI와3λ eigen/Gershgorin off-target surrogate를구분하고 선택final240+30s reserve를보존한다. 새실행·최적조건·familyglobalopt·깊이집중성공을 미리 주장하지 않는다.

native source `10a70e9cfa19537825f2f5e829b7d1d14acbd35c`,physicalmodel `d5ed6dbc1cdc2056cec02e223bac7e2bd5252a05dc976b028f7726a9ef272fa8`,scout implementation/preregistration `d82c38220522d9fb912e085843b7b35876291e89`를구분한다. 이번docs해시검증은시뮬레이션재현/수렴/실험검증이아니며새물리fieldmap을생성하지않았다.

- [summary](cloud-rounded-drive-20261021T202000Z/summary.json),SHA256 `6dfcdd1648bc2609484df339e2ceca53c4d7aa9ecb066e3cb7b6bba6aaec9cfa`
- [decision](cloud-rounded-drive-context-20261021T202000Z/decision.json),SHA256 `6c1741743847575e598560ce2c30c61c04246726e4d890d39a1b12b86b1b867a`
- [queue_plan](cloud-rounded-drive-context-20261021T202000Z/queue-plan.json),SHA256 `b8a191a7e937f701f0e0dbecb04a5dce8c66c0b129dcb75ed3b89c0fd098b9f5`
- [queue](cloud-rounded-drive-context-20261021T202000Z/queue/summary.json),SHA256 `5a55e1a073351f39ff1f29fdc6b48870d746e691d8049ecfb9d3604862c2e121`
- [publication](cloud-rounded-drive-context-20261021T202000Z/rounded-drive-publication-20261021T202000Z.json),SHA256 `1362072380df8e17222e41e767ed8b3c3379e1ac3b0adb80da29712057edaea6`
- [feedback_after](cloud-rounded-drive-context-20261021T202000Z/feedback-after.json),SHA256 `fd6c9deee2dfd61c95540a85007d0cad76d26cdc2e209fc146d2dc324f691e50`
- [verified_rounded_snapshot](ROUNDED_FULLFACE_RESULTS_20261021.result-brief.json),SHA256 `23643003dc3f2df01891b541a81962bc61bd419012a05a50138b522885a6048f`
- [preregistration](cloud-rounded-drive-context-20261021T202000Z/preregistration.json),SHA256 `28bcd6db134f49695d1feed44e9d53b091b3bf1d8cf55df23e482362b8fe7148`
- [cached_volume](cloud-rounded-fullface-context-20261021T200000Z/volume.json),SHA256 `95b1593cf23d2a539c57007f3909b56ba59692148768514fcae9b13dc65fd590`

[이전rounded형상2행GUI](CLOUD_ROUNDED_FULLFACE_RESULTS_20261021.html)와[과거44조건/4·8·12·16pad snapshot](CLOUD_VOLUME_RESULTS_20261021_v8.html)을보존한다.
