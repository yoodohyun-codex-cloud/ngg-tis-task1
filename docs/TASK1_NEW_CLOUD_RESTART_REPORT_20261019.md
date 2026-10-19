# 작업 1 연구 결과와 새 클라우드 재시작 보고서

작성 기준: **2026-10-19 UTC**. 대상은 **고정 팬텀의 NGG–TIS 전기장·전극 설계인 작업 1만**이다.
이 문서는 기존 결과를 검토한 연구·이관 계획이며, 새 환경 생성·데이터 이관·계산 실행의 완료 보고가 아니다.

## 1. 판단과 우선순위

**현재까지 절대 표적 TIS, 공간 선택도, 피부·접촉 부담을 동시에 개선한 검증 완료 설계는 없다.**
중심점 원전압 점수의 명목 Best1은 유지하되, 새 환경의 첫 목표는 더 큰 탐색이 아니라
**원시 자료 복구 확인 → 동일 기준 재현 → 접촉 가장자리·ROI 수렴 → 실측 보정 → 제한된 형상 비교**로 정한다.
최신 타원은 선택도 비율이 **28.48% 증가**하지만 원 1 Vpp에서 ROI 평균은 **1.18% 감소**하고
J최대·접촉전압은 약 **2.45배**다. **18개 파형별 수렴 비교 중 7개 실패**, 타원 SC2→4의
J최대 **73.15% 증가**가 남으므로 기존 선두를 대체하지 않는다. 이 유한 탐색 결과는 모든 상부 전극 설계의
개선 가능성을 부정하는 증명도 아니다. [선택도 결과][selectivity]

사용자의 최종 목표는 **15–20 mm 깊이에 실제로 집중된 TIS 전계**다. 한 중심점의 원전압 점수 증가는
역사적 목적/benchmark로 보존하고, 후속 주목적은 절대 ROI mean/P10과 깊이별 분포·지배적 극대 위치·
표층 및 다른 비표적 영역의 P95/max·표적밖 상대 고변조 부피를 함께 판단하는 것이다.
표면의 지배적 최대가 그대로인데 비율만 좋아진 결과는 “상대 선택도 개선”으로 보고하며 “깊이 집중 성공”이라 하지 않는다.
상대 지도 cutoff는 고정 비교 규칙으로만 쓰고 물리/활성화 역치를 만들지 않는다. 달성 가능성은 아직 입증되지 않았다.

후속 새 환경의 운영은 **유한 배치를 이어가는 연구 반복**을 지향한다. 계산 Codex가 단일 실행 lock과
사전등록 예산 안에서 계산·결과 보존을 맡고, dot 검토는 별도 피드백 문서에서 안정적인 ID와
source/adoption commit, 제안·채택·실행·검증 상태를 기록한다. 한 배치가 끝나면 다음 타당한 과학적 단계를
선택하되, 수렴·접촉·자료/디스크 장애가 있으면 허용된 비파괴 진단으로 해결하고 남는 blocker를 보고한다.
새 결과 없는 수신확인 반복, 중복 계산, 무제한 sweep, 조용한 예산 확대나 원자료 삭제는 하지 않는다.
현재는 이 운영 규약의 준비 단계이며 새 환경 연결·worker 실행·자동 상호작용이 시작된 것은 아니다.

작업 2의 횡격막 형상·막흥분·문헌·힘 모델은 새 환경의 설정·계산 대상으로 넣지 않는다.
작업 1의 전계 포락선, 같은 RMS, 전류·손실 또는 상대 부담 상한으로 활성화·모집·안전성을 추론하지 않는다.
이 문서에는 사람 자극 설정이나 보편적인 물리 역치가 없다.

## 2. 어떤 버전을 이어받는가

| 역할 | 이번에 확인한 고정 버전 | 사용 원칙 |
|---|---|---|
| main의 연구 안내 | `d988268553718c468f5c559c4c6e46429901c623` | README가 연구 코드·결과의 별도 위치를 안내한다. 최신 연구 구현이 main에 통합됐다는 뜻은 아니다. |
| 작업 1 코드·결과 기준 | PR #3 `8c3a30a778cc9bf19ccb52ca523598bff0a84650` | 새 구현 기준을 정할 때 이 SHA와 각 run의 실제 실행 코드/설정 SHA를 함께 고정한다. |
| 이 보고서 이전 문서 검토 | PR #2 `f4b6d5fa789582c94655bdb961d152782cb1ae42` | 기존 피드백 ID·상태·실패와 문서 검토 이력을 보존한다. PR #2 전체를 작업 1 실행 기반으로 가져올 이유는 없다. |
| 최신 선택도 GUI·그림 | `ef7c069ff009a959d37a4532b349dcd4a837e56c` | 표시 패키지다. 원시 수치 기저의 대체물이 아니다. |

main을 복제한 뒤 기존 README의 브랜치 전환·설치·재계산 예시를 곧바로 실행하는 방법은 권장하지 않는다.
기존 실행기는 결과·GUI 포인터에 쓰기 동작을 할 수 있다. 향후 새 실행 공간은 **고정된 작업 1 코드와
의존성 목록을 검토한 독립 체크아웃**으로 준비하고, 실행하지 않는 읽기 전용 복구 단계부터 시작한다.
`pipeline_ngg.py`는 bootstrap 검사가 아니라 실제 피팅·계산·GUI 생성 파이프라인이다. 과거 문서의
Python≥3.10/JDK≥17 권장, 최근 실행의 Java 21 경로, `numpy>=2.3,<3` 요구를 하나의 검증된 lockfile로
간주하지 않는다. 설치 버전·코드 호환·시험 결과는 새 환경에서 별도로 기록해야 한다.
이번 조회에서 PR #3은 open·미병합·`mergeable=false`였다. 충돌 해결이나 자동 병합은 이관의 선행조건이 아니며
이번에는 수행하지 않았다. PR #2는 문서 게시 위치로만 사용한다. [main 안내][main] · [피드백][feedback]

### 상태 파일과 보고서의 시점을 구분한다

- 원 탐색 REPORT에는 “탐색 진행 중”이 남아 있지만 해당 고정 버전의 controller는
  **`needs_physical_validation`**이다. 저장된 PID·heartbeat는 현재 프로세스 생존 증거가 아니다.
  [REPORT][exploration] · [controller][exploration-controller]
- Rs-window의 REPORT/일부 GUI는 **2/10 관측 시점**을 그대로 보존한다.
  최종 상태는 **FINAL_COMPLETION과 summary의 10 semantic 슬롯 완료**로 확인한다.
  새 PDE 8개와 기존 한 기저의 두 alias를 10개 새 계산으로 세지 않는다.
  [부분 기록][rs-partial] · [최종 기록][rs-final] · [summary][rs-summary]
- 최신 선택도는 **`disk_budget_not_run`**이다. 완료된 결과가 있고 마지막 두 C1은 시작하지 못했다.
  이를 전체 계획 완료 또는 solver 실패로 바꾸지 않는다. [summary][selectivity-summary]

## 3. 유지할 물리 조건과 비교 정의

### 팬텀·회로·파형

| 항목 | 고정하거나 명시해야 할 내용 |
|---|---|
| 형상 | 지름 **50 mm**, SC/dermis/fat/muscle 두께 **0.1/5/5/15 mm**, 총 25.1 mm. z=0은 표면, +z는 깊이. 층 경계 0/0.1/5.1/10.1/25.1 mm. |
| 외부 경계 | 전극은 상부에만 부착하고 측면·바닥은 절연. z=15–20 mm ROI는 바닥에서 5.1–10.1 mm 떨어져 있어 이 유한 경계의 영향을 포함한다. |
| 초기 재시작 회로 | 두 출력·네 패드·공통 GND, 출력마다 **High Z 명령 1 Vpp**, 개방 소스 **0.5 Vpeak**, 직렬 **50 Ω**. 전극 크기·형상·배치는 후속 제한 탐색에서 바꿀 수 있다. |
| 전류 경로 | 공통 귀환망을 유지한다. 임의의 신호–귀환 쌍에만 전류가 흐른다고 가정하지 않는다. 다른 주파수의 출력도 0 V/50 Ω 종단으로 남으며 출력 제거와 다르다. 실제 장비 low 연속성은 확인 대상이다. |
| 복소수 규약 | peak phasor, `Re(V exp(+jωt))`. 부하 후 전극 전압, 소스 명령 Vpp, RMS, 프로브 차동 Vpp를 구분한다. 최신 C2 비교는 소스 위상 0°/0°. |
| 초기 기준 | 2000/2010 Hz 정현파·bare. 오래된 20 mm 중심점 결과를 유지하며 최신 3 kHz 결과의 동일 조건 대조로 쓰지 않는다. |
| 후기 C2 기준 | 3000/3030 Hz, square_3h는 9000/9090 Hz의 3차도 보존한다. sine/triangle_3h를 별도 비교한다. Rs500/1000/2000은 EIS 피팅 창 하한이지 구동 반송파가 아니다. |
| 고조파 | sine 계수 (1,0), square_3h (3/(2√2),1/(2√2)), triangle_3h (0.9,−0.1). 3차 위상은 기본 위상의 3배. 기본파 TIS 점수와 고조파 포함 총 RMS·전류·손실·시간 파형을 분리한다. 이상적인 전체 square 파형은 아니다. |

각 조건은 설정 파일과 실제 실행 코드로 확정한다. 4출력 C4 결과는 별도 이력이며 현재 두 출력 팬텀 회로의
기준을 교체하지 않는다. 물성은 기존 주파수 고정 σ/ε 가정을 사용한 결과다. 새 환경에서 실측 분산 물성을
채택하면 새 operator와 별도 검증이 필요하며, 기존 값을 측정된 참값으로 재명명하지 않는다.
[탐색 정의][optimization] · [선택도 사전 계획][selectivity-plan]

### 점·평면·부피·실측 프로브

| 결과 종류 | 정확한 영역·의미 | 서로 대체할 수 없는 이유 |
|---|---|---|
| 역사적 목적 | `(0,0,20) mm` 한 점의 기본파 방향최대 TIS | 중심점 증가가 전체 깊이 영역의 개선을 뜻하지 않는다. |
| 기존 평면 통계 | z=20 mm, r≤5 mm 원과 z=0.025 mm 표층 원 등의 면적가중 통계 | 평면 mean/mean 비율을 최신 부피 mean/P95 비율과 연결해 추세를 만들지 않는다. |
| 채택·실행된 새 ROI | **r≤5 mm, z=15–20 mm**의 유한 부피. mean/P10/min/P95/max와 표적밖 영역을 별도 기록 | 해부학적 횡격막 ROI가 아니다. 20 mm 점이나 프로브 간격 5 mm의 이름만 바꾼 것이 아니다. |
| 최신 선택도 | ROI 부피 평균 TIS / 표층 z=0–5 mm TIS P95 | 비율과 절대 mean/P10을 함께 본다. 비표적 z=5–10 mm 및 나머지 부피도 별도 보고한다. |
| 방향 지표 | 위치별 2,074방향 최대와 고정 `(1,1,0)/√2` 투영 | 위치마다 다른 최적 방향은 하나의 실제 섬유 방향이나 연속 경로가 아니다. |
| 계측 비교 | 깊이 5/10/15/20 mm × 중심 `(0,0),(±5,0),(0,±5) mm` × 수평 X/Y, **팁 gap 5 mm** | 중심 pitch 5 mm와 팁 gap은 별개다. 후보당 40 차동쌍이며 실제 측정 완료 수가 아니다. |

프로브 전압은 존재하는 native 복소 전위의 **φ(plus)−φ(minus)**에서 실제 carrier·위상·고조파와 시간 구간을
적용해야 한다. 비균일장에 단순 `E×gap`을 적용하거나 E-only 자료를 native φ로 부르지 않는다.
ETA5001의 명목 50/500 배율, BNC 전압, DSOX1202A 표시 배율을 분리하고 실제 R/C 입력 부하·팁 배치·주파수 응답·
잡음·교정을 확인해야 한다. 아직은 무부하 예측과 명목 표시 비교다. [표본 사양 검토][integration] · [선택도 계획][selectivity-plan]

최신 코팅 Best1의 중앙20 mm X 무부하 프로브 Vpp는 **27.390405–27.394077 mV**다.
과거 bare 사례의 약27.572–27.587 mV와 섞지 않으며, 이 구간은 **시간 극값의 수치 경계**이지 측정 오차막대가 아니다.
같은 Best1의 새 부피 ROI mean **0.04059343651 V/cm**, P10 **0.03638396092 V/cm**, mean/표층P95
**0.160870888**도 옛 평면 비율과 다른 정의이므로 정의 변경 자체를 개선으로 보고하지 않는다.
[최신 결과 안내와 고정 패키지 연결][main]

진짜 C1은 실제 두 전극 단일 출력 대조군이다. TIS 회로의 다른 출력을 0으로 둔 것과 다르다.
C1의 두 반송파 TIS=0은 전기장=0이 아니다. 중심점 총 E RMS 맞춤과 ROI RMS 평균 맞춤도 별도 정의로 유지한다.
F009 완료 범위는 기존 **03542-1/03522-1 두 고정 비교**이며 이후 모든 후보로 확대하지 않는다. [피드백][feedback]
최신 형상 연구의 C1은 네 기저×두 실제 carrier×세 파형=24원행/960trace다.
중심 RMS matching은 24완료/204보류이며 ROI RMS 대안도 **별도로** 24완료/204보류다. 두 분모를 합쳐
48개 고유 C1 기저가 완료됐다고 표시하지 않는다. [최신 결과 안내][main]

### 부담과 전력 기준을 바꾸지 않는다

| 비교 계열 | 기준 | 포함 항목 |
|---|---|---|
| 원 탐색·3 kHz 형상/파형 비교 | 해당 run에 고정된 같은 격자 bare/reference. 3 kHz 최종 형상 비교는 새 3 kHz reference-sine | Jmax, SC 손실, 접촉 손실, 접촉전압. **J95는 별도 보고, 상한 제외**. |
| 코팅·Rs-window | **같은 선두 형상·격자·파형의 원 bare 1 kHz-fit** | 위 네 항목. 새 코팅 Best1로 기준을 교체하지 않는다. **J95 제외**. |
| 최신 형상 선택도 | 같은 격자·파형의 **10 nm/Rs500 코팅 square** 주 비교. 동일 bare 부피 결과가 있을 때만 별도 비교 | Jmax, **J95 포함**, 접촉전압, SC·접촉 손실. 이전 상한 정의는 그대로 보존한다. |

부담 상한은 모든 출력에 공통 진폭 scale≤1을 적용해 각 항목을 기준 이하로 제한한다.
J·V·I·E는 진폭에 비례하고 전력은 제곱에 비례하므로 전력 항에는 제곱근 비율을 사용한다.
모든 부담이 동시에 같은 값이 된다는 뜻이 아니다. 0/누락값 처리도 원 계산 계약을 유지한다.
출력≤1 Vpp의 전력 **상한**, 두 후보가 실제 같은 전력인 **쌍별 비교**, 출력 상한을 넘을 수 있는
unclipped equal-power는 서로 다르다. 쌍마다 기준 전력이 다르면 전역 순위표로 합치지 않는다.
이 기준들은 공학적 비교이며 안전 한계나 같은 활성화 조건이 아니다. [3 kHz 결과][mesh3k] · [Rs 검토][integration] · [선택도 결과][selectivity]

## 4. 근거별 연구 경과

아래 수치는 기존 보고서·저장 결과의 검토값이다. 이번 문서 작업에서 재계산하지 않았다.
검사 수·후처리 행·고유 설정·새 PDE 조건을 같은 분모로 세지 않는다.

| 단계·날짜(UTC) | 확인된 수행과 결과 | 남는 제한과 해석 |
|---|---|---|
| 초기 bare 보정 · 10-17 | 0.1× PBS 3전극 EIS, 노출 1 cm². Rs=213.279972 Ω. 54조건+4세밀격자 계산. h=1.25 mm에서 RC→NGG의 중심 TIS **2.482399→2.951848 V/m (+18.91%)**. [초기 결과][initial] | 접촉 가정 변경 효과다. PBS−Rs를 건식 접촉으로 적용한 가정이며 표면 최대는 여전히 SC에 있다. |
| 유한 확장 탐색 · 10-17 | 처리3,741과 수용3,720 조건·124,982 위상/파형 후보를 구분한다. h=0.625 mm bare 03542-1의 3 kHz square_3h 중심 TIS **3.946983 V/m**. [탐색][exploration] · [현재 안내][main] | 후보행·처리/거절 수를 더해 PDE 수로 만들지 않는다. controller는 `needs_physical_validation`. 전역 최적·현재 실행 중·표면 수렴 완료로 읽지 않는다. |
| 2 kHz/3 kHz 격자 · 10-17~19 | 2 kHz 등록 10/10 독립 SC/XY gate 완료는 그 조건에 한정. 별도 3 kHz 10/10(새9+재사용1), 최종 **84판정 통과**, 168개 인접 변화를 보존. [검증 범위][mesh-scope] · [3 kHz 최종][mesh3k] | bulk-z 고정. SC8+최종 XY의 결합 및 전체 3D 수렴은 없음. 원 h0.625부터 Jmax 누적 **+7.7536%**. 3 kHz reference-sine 대비 leader-square raw **+30.079%**, 부담/전력 상한에서는 **−11.564/−13.336%**. |
| 5코팅×Rs 처리 · 10-19 | bare/10/30/50/100 nm × 선택−Rs/전체 실측Z, 10조건=새9+재사용1. 같은 최종 격자 10 nm−Rs square의 raw TIS **+0.8118%**, Jmax **+20.7937%**. [코팅 결과][coating] | 같은 파형 bare 기준 부담/전력 상한 TIS는 **−16.5421/−1.3237%**. full-Z는 PBS 구조적 스트레스 시나리오이며 건식 측정이나 신뢰구간이 아니다. |
| C4 배분·위상 · 10-19 | 기존 3기저의 원324행 재현, 8,064슬롯=108재사용+7,956새 후처리. 새 PDE 0. 최고 증가가 부동소수점 수준이며 1+3/3+1 최고는 같은 기저·파형 2+2의 약 **70.7107%**. [C4][c4] | 50 nm·8패드/4출력·3000/3005 Hz로 C2 3000/3030과 다름. 8,218방향 검사는 선별685행뿐. 독립 C4 수렴·matching bare·native φ는 보류. |
| Rs 창 입력과 장 전파 · 10-19 | 입력15슬롯=새8fit+기존7, 추가 passivity fallback2. 장 전파10슬롯=**새8 PDE+기존50 nm 기저 두 alias**, 새24행/960native. [입력][rs-input] · [최종][rs-final] | 같은 격자/파형 원 bare1k 대비 코팅 square raw **+0.5947~0.8272%**, Jmax **+19.3337~21.1001%**. 부담 상한 **−15.5404~−16.7738%**, 전력 상한 **−1.2958~−1.3960%**. 변경 접촉의 독립 수렴은 별도다. |
| 고정 팬텀 부피 선택도 · 10-19 | **19새 TIS+4새 실제 C1=23새 PDE 조건**, 기존 Best1 1재사용으로 완료 ledger24. 직사각 C1 두 건은 2 GiB 예약 한도로 시작 전 중단. [결과][selectivity] · [summary][selectivity-summary] | **7/18 파형별 수렴 비교 실패**. disk 중단과 수치 실패를 분리한다. 선택도·전력 효율의 일부 명목 이득과 절대 ROI/접촉극값 손해가 공존한다. |

Rs 입력에서 50 nm의 세 창이 같은 Rs=214.13262432777125 Ω을 갖는 것은 활성 상한 제약과 n=0.2 하한의 결과다.
불확실성이 사라졌다는 뜻이 아니다. 음의 차감 실수부를 만든 원 fit과 fallback 기록을 함께 보존한다.
피팅 창별 사용점·잔차가 달라 잔차 최솟값만으로 실제 계면 모델을 선택할 수 없다. [Rs 입력][rs-input]

### 명목 Best1과 같은 격자 대조

후기 코팅 Best1 `coat010-f0500-minusRs-square_3h`의 h=50/120 mm 중심 TIS는
**0.0397673338723 V/cm (3.97673338723 V/m)**다. 같은 격자의 원 bare1k 대조는
**0.0394410731022 V/cm (3.94410731022 V/m)**다. 역사적 h=0.625 mm의 3.946983 V/m와
직접 백분율을 비교하면 접촉 효과와 격자 효과를 섞게 된다. 이 Best1은 해당 유한 중심점 원전압 비교의 명목 선두이며
부피 ROI·부담·실측 검증의 최적 설계가 아니다. [최종 Rs 결과][rs-final] · [고정 기준 검토][integration]

### 최신 타원에서 얻은 것과 잃은 것

조건은 같은 h=0.5 mm, SC2, bulk14/14/40, 10 nm/Rs500, square_3h다.
15 mm square와 225 mm²·장축24 mm·중심반경17 mm의 접선 방향 타원을 비교했다.

| 원 1 Vpp 지표 | 같은 격자 square | 타원 | 결과 |
|---|---:|---:|---|
| ROI 평균 TIS (V/cm) | 0.040617638 | 0.040138552 | −1.1795% |
| ROI P10 TIS (V/cm) | 0.036455915 | 0.036431177 | −0.0679% |
| ROI mean / 표층 P95 | 0.16077746 | 0.20657103 | +28.4826% |
| Jmax (mA/cm²) | 2.6838244 | 6.5685439 | 약 2.45배 |
| 면적가중 J95 (mA/cm²) | 1.3329886 | 1.2002528 | −9.9578% |
| 최대 접촉 RMS 전압 (mV) | 2.826722 | 6.9181687 | 약 2.45배 |

실제 같은 소스 전력 **1013.8861871 µW**, 양쪽 출력≤1 Vpp의 쌍별 비교에서는 ROI 평균 **+4.6868%**지만
Jmax/접촉전압은 약 **+159.27%**다. 최신 J95 포함 복합 부담 상한에서는 타원의 scale=0.4085874265,
ROI 평균 **0.0164001077731 V/cm**, 기준 대비 **−59.6232%**다.
타원 SC2→4에서 Jmax **+73.1508%**인 상태이므로 이를 수렴된 최대 부담이나 안전량으로 해석하지 않는다.
낮은 J95·손실과 높은 극값을 모두 보여줘야 한다. [선택도 결과][selectivity] · [같은 전력 CSV][matched-power]

## 5. 재사용 가능한 것과 다시 확인할 것

| 항목 | 재사용 범위 | 재시작 시 필요한 확인 |
|---|---|---|
| 원본 XLSX·MPH·CV, 기존 results | 변경 없이 보존할 원자료와 역사 | 파일명은 **[PBS swelling 시간] [PEDOT 두께]**. 실제 바이트·LFS 객체·SHA, 누락과 버전 확인. EIS 측정 부호·노출 면적과 CV 조건을 혼동하지 않음. |
| 설정·코드·사전등록·완료/실패 | 해당 버전의 계산 의미와 범위를 재사용 | run별 code/config/input SHA, 실제 실행 코드 사본과 패키지/Java 버전. 최신 소스만으로 과거 실행을 설명하지 않음. |
| 원시 복소 기저 | 같은 operator·경계·격자·주파수일 때 선형 중첩의 근거 | 실제 파일 복구·decode·단위/축/주파수/소스 순서 확인. Rs/물성/접촉/형상 변경을 단순 진폭 scaling으로 대체하지 않음. |
| 저장 scalar·ROI·프로브·회로 | 해당 저장 결과와 그림을 읽는 용도 | 기저/분석 코드 hash·ROI 가중치·정규화 참조 확인. 일부 회로 감사 통과가 전체 공간장 수렴을 대신하지 않음. |
| 2 kHz/3 kHz 독립 SC/XY gate | 등록된 조건과 축별 비교에서만 재사용 | 변경 코팅·접촉·형상·부분 접촉면, 결합 격자 및 bulk-z/전체 영역 검증은 별도. |
| GUI·figure 패키지 | 보존된 결과의 표시와 설명 | 정확 artifact hash와 참조 자산. 생산자의 223개 브라우저 검사는 정확 HTML 메모리 로드 범위이며 사용자 PC 파일 열기·실측 검사가 아님. |

**Exporter 계약은 동일하지 않다.** 기존 `ExploreBasis`는 복소 E와 표면 전류·회로를 내보내지만
조직 native φ는 내보내지 않는다. 후기 전위 보존 producer의 자료가 별도로 있는지 확인해야 하며,
오래된 E-only 캐시 전체를 “native 전위 보관본”이라 부르면 안 된다. [ExploreBasis][explore-code]

`SelectivityShapeBasis`는 little-endian Float64/complex128 E와 φ를 무손실 저장한다.
부분 접촉면의 **표면 E는 full cell face h² 평균**, 접촉 J는 **I/실제 겹침 면적**으로 구분하는
재구성 변경이 들어 있다. 이전 exporter와 호환된다고 가정하지 말고, 정렬된 full-face square 재현과
부분 접촉 회로/단위/면적·전류 검사를 각각 유지한다. 같은 숫자나 포맷 이름만으로 캐시를 합치지 않는다.
[SelectivityShapeBasis][shape-code] · [등록 계획][selectivity-plan]

## 6. 보존·이관 목록과 실제 저장소 접근 제한

이 문서 환경은 원 계산 저장소에 접근하지 못했다. 2026-10-19 17:46 UTC 기준 현재 호스트
`9ae23b0fe99f`의 `/workspace` 가용 공간은 **19,345,063,936 B**였지만, 이곳의
`/workspace/ngg-tis-simulation`은 오래된 `work` 체크아웃이고 대상 선택도 run과 `bases/`가 없다.
기록에 남은 두 게시용 `/tmp` 체크아웃도 없었다. **경로명·저장소 이름·환경 설정이 같아도 공유 저장소의 증거가 아니다.**
원 계산 호스트의 고유 마운트/boot 식별자가 비교 기록에 없어 같은 물리 저장소라고 확정할 수 없으며,
현재 문서 환경의 여유 공간을 원 작업의 사용 가능 용량으로 보고하지 않는다.

원 실행의 종료 감사는 16:51:16 UTC 가용 **2,171,097,088 B**를 기록했고, 다음 C1의 시작 전 요구량은
예약 공간 포함 **2,267,054,848 B**였다. 서로 다른 시점의 기록이며 현재 원 저장소 용량은 미확인이다.
2 GiB 예약 한도는 낮추지 않았고 두 C1을 자동 재개하지 않는다. [종료 감사][disk-audit] · [실패 기록][failure]

**GitHub에 보고서가 있다는 사실은 원시 기저의 백업 완료를 뜻하지 않는다.**
게시 범위에는 **전체 native E/φ/volume 기저가 원 계산 저장소의 로컬 자료로 남아 있음**이 명시돼 있다.
local-only 목록은 698경로이며 lock 등도 포함하므로 “698개 원시 기저”로 세면 안 된다.
게시된 192개 작은 complex source/loss 회로 파일, 선택 지도·프로브·scalar는 전체 공간 기저를 복구할 수 있는
대체 자료가 아니다. 별도 백업의 존재·완전성은 아직 검증하지 못했다. [게시 범위][publication-scope]

| 보존 대상 | 향후 보관 위치·원칙 | 이관 수용 증거 |
|---|---|---|
| 코드·설정·사전등록·보고서·테스트·환경 lock/버전 | Git의 고정 commit과 필요 시 읽기 전용 source bundle | commit/파일 SHA, 실제 실행 코드 매핑. main·PR2·PR3 역할 분리. |
| 원본 XLSX/MPH/CV·기존 결과 | 원본을 보존하는 영속 저장소; 기존 Git/LFS 이력도 유지 | LFS 포인터가 아닌 실제 객체 바이트, 크기·SHA, 원본 대비 일치. |
| 전체 E/φ·grid·contact density·source/loss·ROI 가중치와 분석 의존 파일 | 계산 인스턴스 수명과 독립적인 **불변 binary 영속 저장소** | 원 저장소 inventory, 고유 객체/버전, byte SHA256·실제 크기, 복구 후 decode. 전체 대상 누락 0. |
| 완료·부분·실패·미실행·constraint/alias 기록 | 원 run을 수정하지 않는 불변 manifest와 관련 파일 | 상태별 목록, parent/source reference, 실패/미수렴 보존. 성공한 행만 선택적으로 남기지 않음. |
| 원시 프로브·지표·registry·GUI/figure | 기저·코드·설정·분석 revision을 참조하는 불변 결과 | 시맨틱 슬롯/고유기저/새 PDE/후처리행 분모와 hash를 구분. 이전 current.json 보존. |
| 임시 렌더·빌드·패키지 캐시 | 영속 원자료와 별도 임시 공간 | 실제 의존성·열린 파일·백업/복구 증거를 확인한 뒤에만 정리 후보 심사. 이번 삭제 후보나 삭제 승인이 아님. |

### 원 환경을 폐기하기 전 필요한 복구 검사

1. **원 저장소 식별:** 실제 작업/run 존재, hostname·boot ID·mount·device와 시간, 원 경로·링크 대상,
   실행/열린 파일을 읽기 전용으로 확인한다. 다른 작업의 상태를 이 환경에서 추정하지 않는다.
2. **전체 inventory:** path, 역할, 논리 크기와 실제 점유량, SHA256, run/case/config/source SHA,
   dtype/endianness/shape/units, 압축 형식, 주파수·소스 순서, 의존 참조, 백업 위치/버전과 누락을 기록한다.
   hardlink/중복·별도 마운트를 구분하며 `.gitignore`의 “cache” 이름만으로 삭제 가능하다고 보지 않는다.
3. **독립 복구:** 별도 영속 사본에서 깨끗한 읽기 전용 검증 공간으로 실제 복구한다.
   모든 보존 대상의 byte hash/크기를 대조하고 각 형식의 배열을 decode해 차원·단위·유한값·좌표·소스/주파수 대응을 확인한다.
4. **사용 가능성 확인:** 대표 같은 격자 bare·코팅 Best1·부분 접촉 타원·C1에서 저장 scalar/ROI/프로브의
   지정 표본을 동결 분석 코드로 재현한다. 이는 향후 수행할 제한된 복구 검사이며 이번에는 실행하지 않았다.
   E-only 옛 기저에는 존재하지 않는 φ 재현을 요구하거나 성공으로 표시하지 않는다.
5. **폐기 보류:** 불일치·누락·미복구 의존성이 하나라도 남으면 원 환경/자료를 유지한다.
   해시 일치만으로 사용 가능성이 증명되는 것은 아니다. 전체 복구 결과와 정확한 대상·용량·복구 경로를 검토한 뒤
   항목별 확인 없이 되돌릴 수 없는 삭제를 진행하지 않는다. 현재 **이관 성공·복구 성공·폐기 가능 판정은 없다**.

### 저장 공간 설계

새 환경은 코드/Git, 불변 원시 데이터, 임시 계산·렌더 공간을 분리한다. mount별 용량을 확인하고
**남은 유한 작업의 예상 최대 추가 점유 + 압축/전송/검증 중 동시 사본 + Git/LFS/보고서 임시량 + 예약 여유**를
실행 전에 확보한다. 압축률이나 Git 중복 제거를 보장값으로 가정하지 않는다. 예상량과 실제 고수위 사용량을
run별로 기록하고 조건마다 다시 검사하며 부족하면 `not_run`으로 보존한다.

예를 들어 complex φ와 3성분 complex E는 Float64 기준 **64 B/셀/소스/주파수**다.
800,000셀×2소스×4주파수이면 **409,600,000 B(409.6 MB)**이며 grid·전류·전달행렬·ROI·임시 사본은 제외한
**비압축 산술 예시**다. 실제 측정된 run 크기나 충분한 디스크/메모리 용량이 아니다.
누적 보존량과 복구 공간을 먼저 산정하고, 원시 캐시 파괴나 예약 여유 축소로 부족분을 해결하지 않는다.

## 7. 검증을 우선하는 최소 재시작 단계 — 모두 후속 제안

| 단계 | 제한된 작업 | 다음 단계로 넘어갈 증거·중단 조건 |
|---|---|---|
| 0 · 출처와 보존 | 위 코드 버전·원 저장소 inventory·누락/접근 장애 확인 | 대상 storage와 의존성이 확인돼야 이관 범위를 확정. 원시 기저에 접근 못 하면 그 사실을 blocker로 유지하고 임의 재계산으로 대체하지 않음. |
| 1 · 작업 1 환경·복구 | 고정 코드/의존성만 독립 준비하고 작은 대표 bundle부터 복구 | 실제 Java/Python/라이브러리·OS·수치형식 기록, 위 복구 검사 통과. 설치 성공만으로 결과 재현 완료라 하지 않음. 작업 2 환경은 설치하지 않음. |
| 2 · 해석해·회로·단위 | 균일/직렬층 복소 회로, 50 Ω·공통귀환, 부호/peak/RMS·면적 변환, 고조파/진폭 scaling, full/partial-contact와 exporter regression | 기존 원 검사와 독립 해석값 일치, 잘못된 단위·이중 Rs/면적·누락 데이터 거절. 큰 팬텀 탐색 없이 최소 fixture로 먼저 판단. |
| 3 · 동일 baseline 교차해석 | 동일 geometry/물성/복소 contact/source/경계·좌표/정규화의 bare 기준 하나부터 독립 solver와 대조 | φ/E의 실수·허수, source current, contact J/V, 층별/총 power와 전류 수지를 함께 비교. 공통 표본·보간·J정의 차이와 양쪽 격자 오차를 분리. cross-solver 허용치는 실행 전 별도 등록하며 현재 미확정. |
| 4 · 접촉·ROI 수렴 | square 기준과 대표 타원부터 XY·SC·bulk 및 부분 접촉/가장자리·ROI 가중치/방향 표본을 독립 검사 | 기존 실패값과 원시 지도 유지. peak가 발산·정체하면 모서리 특이성/물리 접촉의 필요성을 판단하고 최대값 기반 순위 승격 보류. J95·평균 통과로 Jmax 실패를 덮지 않음. |
| 5 · 실측 복소Z·팬텀 대조 | 실제 건식/팬텀 접촉의 면적·압력·수화·온도·주파수, 팬텀 복소 물성, 장비 부하·깊이별 차동 파형을 측정·교정 | PBS 대용 가정과 실제 조건을 구분. 반복성/오차·측정면·de-embedding/Rs 규약 확보. 새 Z/물성이 operator를 바꾸면 단계 3/4의 관련 검증으로 돌아감. |
| 6 · 제한된 다목적 형상 비교 | 같은 D50/층/상부 회로에서 전극 크기·형상·배치만 작은 사전등록 pool로 비교 | 동일 면적군과 면적자유군 분리. 먼저 edge/contact gate 통과. ROI mean/P10·선택도·Jmax/J95/contactV·SC/contact/source power·출력전류의 상충관계를 같은 격자/기준으로 보고. 확인되지 않은 단일 optimum을 게시하지 않음. |

둥근 모서리는 전류 집중을 줄일 **검토 후보**이지 검증된 해결책이 아니다. 최신 coarse pool에
equal-area rounded 후보가 이미 있었으므로 같은 조건을 무조건 다시 계산하지 않는다. 접촉 경계·면적·곡률을
통제한 후 기존 자료로 가능한 검사와 새 해석이 필요한 검사를 구분한다. 날카로운 모서리의 수치 극값이
안정되지 않는다면 측정 가능한 접촉 모델·유한 공간 평균을 별도 정의하되 기존 Jmax를 삭제하거나 재명명하지 않는다.

최신 유한 연구의 **기존 수치 gate**는 다음과 같다. 향후 새 gate로 자동 승인하거나 안전 역치로 사용하지 않는다.
[등록 분석 계획][selectivity-plan]

| 기존 등록 판정 | 기준 | 해석 범위 |
|---|---:|---|
| 중앙/ROI TIS mean·P10, RMS, 표적/비표적 P95 비의 인접 변화 | 1% | 지정 지표·격자 쌍에 한정. 통계적 신뢰구간이 아님. |
| Jmax/J95/접촉전압 인접 변화 | 5% | 실제 최대값 수렴·연속체 인증과 구분. 실패를 그대로 유지. |
| SC/접촉/소스 전력 인접 변화 | 2% | 해당 새 선택도 계획의 전력 항목. |
| solver 상대 잔차 / 전력 수지 | 2e−7 / 2e−7 | 선형계·회로 대수 검사. 공간 수렴의 대체가 아님. |
| 전류 수지 / mask 면적 | 2e−6 / 1e−10 | 각각의 원 정의·분모를 유지. |

새 교차 solver·복구 scalar·실측 대조의 허용치와 새 예산은 **미확정 제안 항목**이다.
관측 후 통과하도록 허용치를 바꾸지 않고, 비교 정의·예상 수치/계측 불확실성과 함께 먼저 정한다.
기존 1 CPU·동시1·800,000셀·조건당600초·전체6,600초·heap2 GiB/RSS합계3 GiB·디스크여유2 GiB는
과거 실행 계약이다. 새 환경에서 실제 자원을 확인하기 전 그대로 실행 가능하다고 주장하거나 자동 증액하지 않는다.
실패·자원 부족·접근 단절 시 유한 단계를 중단하며 무제한 refinement·전수 sweep·상주 worker 재시작으로 연결하지 않는다.

### 후속 사용자 요구: 실험 4패드, 시뮬레이션 최대 16패드

사용자는 “채널”이 **팬텀에 붙이는 전극 패드 수**라고 명확히 했다. 실험 기준은 **4패드**이며
기존 회로에서는 **2출력**이다. 후속 시뮬레이션 범위는 최대 **16패드**이지 16개 독립 출력이 아니다.
4/8/12/16패드의 작은 비교를 우선 검토하되, `n_pads`, `n_outputs`, 신호/귀환 패드 수와 연결 그룹,
공통/분리 귀환 노드 및 carrier 배분을 설정과 결과에 각각 기록한다. 패드를 여러 조각으로 나눠 한 출력에
연결하는 경우와 출력 자체를 늘리는 경우는 다른 회로다. 후자는 별도 하드웨어/동기화·자원 검토가 필요하다.

초기 비교는 가능한 한 같은 2출력 소스 회로·총 소스 예산에서 패드 분할/배치를 검토한다.
패드별 면적 고정과 총 접촉면적 고정 비교를 분리하고, 출력 수 증가에 따른 총전류/전력 증가를
형상 이득으로 세지 않는다. 원 출력당1Vpp·같은 총전력·복합 부담 상한을 각각 보존하며 자동 전압 확대는 하지 않는다.
4패드 기준을 항상 보이는 UI에서 같은 단위·ROI·방향·색범위·정규화·수렴 상태로 비교한다.
이것은 **후속 구현 요구사항**이며 기존 producer의 패드/출력 제한을 변경하거나 16패드 해석/UI 검증을 완료한 것이 아니다.

### COMSOL을 사용할 경우

사용자 지정은 **COMSOL 5.3a**, 예정 build **5.3.1.201**, 사용자 제공 AC/DC 이용권 정보다.
**실제 설치·license checkout·빌드·모듈 실행 가용성은 미확인**이며 새 클라우드에서 사용할 수 있다고 가정하지 않는다.
사용한다면 이 버전을 확인하고 작은 해석해/회로 검사를 먼저 수행한 뒤 동일 작업 1 baseline을 비교한다.
다른 버전으로 조용히 대체하거나 이미 검증된 의존성으로 등록하지 않는다. 기존 준비 문서는 규약 참고 자료일 뿐
작업 1 D50 팬텀의 완성된 COMSOL 모델이나 실행 결과가 아니다. Java 저장 결과 열람·복구 자체에 COMSOL은 필요하지 않다.
[기존 5.3a 준비 상태][comsol]

[공식 COMSOL 5.3a AC/DC 매뉴얼](https://doc.comsol.com/5.3a/doc/com.comsol.help.acdc/ACDCModuleUsersGuide.pdf)은
해당 버전의 Electric Currents·회로/경계 인터페이스 계획 근거로만 사용한다. 문서의 존재는 설치·라이선스·실행 성공 증거가 아니다.

## 8. 이번 보고서에서 수행한 일과 아직 하지 않은 일

**수행:** AGENTS·현재 문서·고정 main/PR3와 단계별 보고서/저장 기록·두 exporter 코드를 읽고 비교 기준과 상태를 정리했다.
원 탐색 상태, Rs 최종 완료/부분 표시, J95 상한 포함 여부, E-only/native φ 차이와 부분 접촉 E 재구성 차이를 구분했다.
현재 문서 환경의 저장소 식별·가용 공간·대상 run 부재는 읽기 전용으로 확인한 별도 진단 결과를 인용했다.
이번 결과는 새 Markdown 보고서와 PROJECT_CONTEXT의 연결이며 기존 F001–F009의 상태를 변경하지 않는다.

**미수행:** 새 클라우드 환경 생성·설치, 원 계산 저장소 접속·전체 inventory, 데이터 업로드/이관·복구 시험,
원시 binary 재처리, 해석해/solver/mesh 새 실행, COMSOL 실행, 물성·접촉·장비 실측, 추가 형상/C1 계산,
worker/예약 한도 변경, 파일 삭제·이동·압축, main/PR3 변경·병합. 원시 기저 접근과 복구 검증이 남은
이관 blocker이며 새 환경을 만들었다는 이유만으로 원 환경을 폐기할 수 없다.

## 고정 출처

링크의 commit은 검토 시점에 고정했다. live branch의 후속 상태나 현재 프로세스 생존을 뜻하지 않는다.
검사 건수는 해당 생산자의 저장 감사 범위이며 이번 보고서가 모두 재실행한 검사가 아니다.

[main]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/d988268553718c468f5c559c4c6e46429901c623/README.md
[feedback]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/f4b6d5fa789582c94655bdb961d152782cb1ae42/docs/TASK1_FEEDBACK.md
[integration]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/f4b6d5fa789582c94655bdb961d152782cb1ae42/docs/TASK1_RESULT_INTEGRATION_PROPOSAL_v0.1.0.md
[initial]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/f4b6d5fa789582c94655bdb961d152782cb1ae42/tis-java/runs/ngg-initial-20261017-01/REPORT.md
[optimization]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/docs/OPTIMIZATION.md
[exploration]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/explore-20261017T133224038032Z/REPORT.md
[exploration-controller]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/explore-20261017T133224038032Z/controller.json
[mesh-scope]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/docs/LEADER_VALIDATION.md
[mesh3k]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/cb0775ac8b016ee0868f7de9d24a2e8c8fc7d9e7/tis-java/runs/leader-validation-3k-20261019T030136Z/FINAL_REPORT.md
[coating]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/661002f7ffef4d1c9581ff3614ae6bf53b821988/tis-java/runs/coating-rs-validation-20261019T101802Z/REPORT.md
[c4]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/cfc322b1e8503488eacd1ee877be1c20b1756969/tis-java/runs/c4-phase-allocation-20261019T121058Z/REPORT.md
[rs-input]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/272fc201b6db11be7add05298b8de63ae2325f51/tis-java/runs/eis-rs-window-analysis-20261019T123730Z/REPORT.md
[rs-final]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/947c984f9a154d750acf36379fc859b25b56ac4f/tis-java/runs/rs-window-tis-validation-20261019T135413Z/FINAL_COMPLETION.md
[rs-summary]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/947c984f9a154d750acf36379fc859b25b56ac4f/tis-java/runs/rs-window-tis-validation-20261019T135413Z/summary.json
[rs-partial]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/947c984f9a154d750acf36379fc859b25b56ac4f/tis-java/runs/rs-window-tis-validation-20261019T135413Z/REPORT.md
[selectivity-plan]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/ANALYSIS_PLAN.md
[selectivity]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/REPORT.md
[selectivity-summary]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/summary.json
[matched-power]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/matched-power-rows-cm.csv
[publication-scope]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/source-publication-scope.json
[disk-audit]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/audit/terminal-process-lock-observation.json
[failure]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/runs/selectivity-design-20261019T155933Z/failure.json
[explore-code]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/ExploreBasis.java
[shape-code]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/8c3a30a778cc9bf19ccb52ca523598bff0a84650/tis-java/SelectivityShapeBasis.java
[comsol]: https://github.com/yoodohyun-codex-cloud/ngg-tis-simulation/blob/f4b6d5fa789582c94655bdb961d152782cb1ae42/tis-java/thorax/comsol53a/README.md
