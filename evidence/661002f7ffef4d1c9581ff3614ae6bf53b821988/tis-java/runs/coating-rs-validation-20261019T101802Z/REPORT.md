# 5코팅 × Rs 처리 유한 검증 — 실제 계산 시작

사전등록·코드/입력검사 게시 commit: `5af117bd6b53d6f1b8fb74c486ff75b098da8e17`. 사용자 “시뮬레이션 계속 돌려봐 변수 알아서 바꿔서”에 따라 별도 새run을 시작했다. **2026-10-19 19:19:26 KST** 실제 `/proc` 감사에서 driver PID28172/startticks10292630·정확명령, Java PID28173/CoatingRsBasis 및 전용/진단 lock2개점유를 확인했다. 이 시점 이후 생존은다시확인한다.

완료 bare-minusRs 기준1개를 원결과/기저SHA참조재사용했고, 첫 새 `coat000-full-measured`를 계산중이었다. **재사용1/신규완료0/신규착수1/신규상한9**이며10조건최종완료나개선으로보고하지않는다. 현재결과는controller/summary/cases/postprocess를확인한다.

조건은15mm4패치·두공통GND출력1Vpp HighZ/50Ω·3000/3030/9000/9090Hz,XY0.416666667mm/SC2·bulk14/14/40·791280셀이다. 초기bare/10/30/50/100nm × 선택Rs차감/전체실측Z를비교하며원파형/위상/조직물성을유지한다. 전체실측Z는구조적스트레스이고통계CI/건식피부실측이아니다.

재사용 bare square_3h 기준의20mm 실제RMS/TIS는 **0.020774741/0.039441073 V/cm**,J최대/J95는 **2.309632/1.174767 mA/cm²**,접촉V RMS0.038000993V,SC/접촉손실 **1.876053/25.093173µW**,총전원1090.475169µW다. 이는새코팅결과가아닌고정비교기준이다. 코팅별원1Vpp·같은파형bare부담상한·총전력상한을나란히비교하며부담항목별우열/미수렴을보존한다.

기존800000셀·600초/조건(해석+후처리)·6600초/전체·1CPU/heap2GiB/RSS3GiB/동시1/디스크여유2GiB상한이다. 실제CPU affinity1개와thread1을고정했고컴파일/회로selftest/10입력수용·두비등록입력거절·전용16검사를통과했다. 전체110분은상한이며새코팅시간예측이아니다.

원탐색needs_physical_validation·원/companion중단·완료3k SC/XY결과·rawXLSX/MPH/CV·기존GUI/current.json을보존했다. 새코팅의독립수렴·전체3D·Rs피팅구간민감도·정확2pad C1·건식접촉·생리/실측보류는유지한다. nativeφ/E및공간진단실패는완료에포함하지않고부분파일/실패를보존한다. 기존작업2 activation/COMSOL5.3a 사양은별도유지하며새막모델/COMSOL/생체실행은없다.

다음변수후보: 완전한C4기저가있는03739/03655/03740의8전극·50nm·3000/3005Hz에서기존2+2행재현후동일재현위상의1+3배분을비교할수있다. 현재C2/3000·3030Hz와다른조건이므로직접선두승격하지않으며,별도유한사전등록과자원점유충돌확인후에만후처리한다. nativeφ부재/전체3D·접촉·생리보류를유지한다.

## 첫 부분 결과 · 2026-10-19 19:34 KST 저장 snapshot

완료bare기저재사용1 + 새계산완료2(`coat000-full-measured`, `coat010-minusRs`), 총3조건/9원파형을 별도 [정적HTML](../coating-rs-report-20261019T103447Z/NGG-TIS-coating-rs-summary.html)·[CSV](../coating-rs-report-20261019T103447Z/metrics-cm.csv)·3그래프로저장했다. 이는10조건최종결과가아니며후속완료조건은새sourceversion/새보고서로연결한다. 아래는동일형상/격자/각출력1Vpp의square_3h다.

|접촉·코팅|20mm RMS/TIS V/cm|J최대/J95 mA/cm²|접촉V RMS|SC/접촉 µW|총전원 µW|
|---|---:|---:|---:|---:|---:|
|bare−Rs 재사용|0.020774741 /0.039441073|2.309632 /1.174767|0.038000993|1.876053 /25.093173|1090.475169|
|bare 전체 실측Z|0.016032027 /0.030418820|0.821976 /0.571897|0.181588472|0.614309 /251.105759|735.023334|
|10nm−Rs|0.020932762 /0.039761265|2.789889 /1.329725|0.003086833|2.198144 /2.347275|1138.184943|

bare전체Z는원TIS약22.875%감소/J최대감소와함께접촉손실약10배·접촉전압증가가나타났다. 10nm−Rs의원TIS+0.811824%는J최대약20.8%/SC손실증가를동반한다. 같은파형bare부담상한에서는각각0.209270/0.827858Vpp·TIS0.006365742/0.032916679V/cm로bare원0.039441073보다작다. 총전력상한TIS는각0.030418820/0.038919000V/cm이며bare전체Z는1Vpp상한에묶여전력예산을다쓰지않는다. 원1Vpp목적을교체하지않고지표별상반변화를보존한다.

bare전체Z의solver312.904초·해석+후처리335.668초/600초,JavaRSS968294400bytes,driverpeak1099468800bytes였다. residual9.06e−10/power1.63e−10/current2.44e−9를통과했고새120native trace/3공간결과가완료됐다. [독립206검사](audit/coat000-full-measured-independent.json)는28출력SHA·scalar/보존·native/공간상태를감사했다. 목표평균/표층평균비는square RMS0.03303893/TIS0.05510285이며표층평균이더크다. 2074/8218/32794 중심방향점수변화는0이지만방향전역최대/전체3D·접촉수렴인증은아니다.

실제HTML/CSV/SVG의 [233검사](audit/first-report-display-verification.json)는27파생표시행/9원행·360저장probe행의단위/값/파일SHA/정적구조를확인했다. 전용보고서16/메타데이터연계6구현검사도통과했다. 실제브라우저UI나실측검사는아니다. 포맷터3.431초/RSS91447296bytes·메타데이터연계1.416초/RSS107646976bytes,새PDE/파형/ROI재계산0이다.

새완료2조건의6행/240trace를 [별도불변registry](registry/index.json)에실제연결했다. 과거125042행본문재처리0·완료bare중복신규행0이며합집합125048행버전/유효TIS123700/완료probe1560이다. 물리조건unique수나125048새계산을뜻하지않는다. 새24개의정확2pad C1비교는자료부족이며기존3486/2868·F009두anchor는보존한다. 원125042index도SHA동일이다.

C4다음단계는 [유한입력준비](../c4-phase-allocation-preparation-20261019T102803Z/README.md)만완료(새PDE/원324재현/새8064행계산0). 코팅batch와동시에수치후처리하지않으며동일기저의14실제carrier배분×64공통위상×3파형×3기저를사전등록했다. 50nm·3000/3005Hz의8패치조건이므로현재C2선두와다르고동일bare대조부재/φ부재는보류다.

## 후속 19:38 KST 불변 snapshot

완료4/10조건=새PDE3+bare재사용1,30nm−Rs계산중을실제/proc·명령/startticks·lock으로다시확인했다([관측](process-audit-partial.json)). 새 [두번째정적HTML](../coating-rs-report-20261019T103824Z/NGG-TIS-coating-rs-summary.html)/[CSV](../coating-rs-report-20261019T103824Z/metrics-cm.csv)는12원행/36표시행/480저장probe·10조건상태를보존하며실제299파일/단위/scalar검사를통과했다. 첫snapshot/실패/과거GUI를보존했고원SIJSON은그대로다.

새9행/360native를기존125042행참조에연결한불변snapshot2의합집합은125051행버전/유효TIS123703/완료probe1680이다. 원125042몸체재처리0·bare신규중복행0·새36C1비교는자료부족이다. 등록entrypoint는 `python tis-java/register_coating_results.py --run tis-java/runs/coating-rs-validation-20261019T101802Z` 이며새완료sourcehash가있을때만유한메타데이터처리한다. 같은hash는unchanged기존불변파일을검사/재사용한다. source/결과변화시 `report_coating_rs.py --run ... --output <별도새디렉터리>` 로저장scalar만내보내며같은hash재내보내기는없다. export성공은원run완료나브라우저검사를뜻하지않는다.

## 최종 계산 완료와 최신 GUI 연결 · 2026-10-19 20:13 KST

20:12:15 KST에10/10조건 완료(새PDE9+bare재사용1),총3183.125초/6600초다. 원3파형씩30행·1200native프로브·30공간후처리를저장했다. 변경코팅·접촉SC/XY/whole3D/건식/생리·실측보류를유지하며잔차통과로이를해제하지않았다. [최종단일GUI](../coating-rs-gui-20261019T111251Z/NGG-TIS-coating-rs-summary.html)는30원행/90표시행/1200프로브요약과3내장SVG를담고,별도[대표GUI](../../gui/NGG-TIS-latest.html)에서같은정확HTML바이트를연결한다. main초기GUI/구탐색cm파일이새run을소비하지않던원인을수정했고옛포인터/결과는보존했다. [검증·원인기록](../gui-refresh-20261019T110558Z/REPORT.md)·[실제브라우저표시](../gui-refresh-20261019T110558Z/final-browser/actual-browser-verification.json).

최종불변registry는새27행/1080native를기존125042참조에연결했고합집합125069행버전/유효TIS123721/완료probe2400이다. 물리조건unique수/125069새계산으로부르지않는다. 새108정확2padC1비교는자료부족이며기존3486/2868·F009두anchor를보존한다. 같은hash는unchanged재사용,과거행본문/정상수치/기저재처리0이다. 다음C4배분·공통위상단계는기존유한입력준비를유지하며별도코드/원행재현/실행사전등록후기존상한내에서진행한다. 새상주worker/주기·모델·사용량변경0이다.
