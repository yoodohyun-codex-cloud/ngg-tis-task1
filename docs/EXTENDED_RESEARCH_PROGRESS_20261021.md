# 추가 시간 승인 후 실제 실행과 연속 큐

2026-10-21 10:53 UTC, 단일 계산 워커가 구동 패드 위치 배치를 실제 시작했다. 사용자 시간 확대 승인에 따라 계산 담당자가 **7200초를 추가 배정**했고, 누적 한도는 **6600→13800초**다. 사용자가 정확히7200초를 지정한 것으로 기록하지 않는다. [승인·배정](cloud-extended-20261021T102700Z/budget-approval.json), [기존 지출·이력 보존 검사](cloud-extended-20261021T102700Z/budget-amendment.json)를 구분해 보존했다.

CPU1, 동시PDE1, PDE조건당600초, 800000셀, Java heap2GiB, 합산RSS3GiB, 여유디스크2GiB, 배치추가2GiB는 유지한다. 외부 유료 자원·설치·보안 변경·원본 삭제·main 병합은 수행하지 않았다. COMSOL5.3a/예정5.3.1.201은 계속 미검증이다.

## 완료 결과와 다음 선택 근거

아래 수치는 원래4패드 square 기준의 **8개 피부·접촉 부담 상한**에 맞춘 최대 방향 기본 차주파수 변조다. 목표는 중앙r≤5mm/깊이15–20mm 부피이며 단위V/m, 깊이 원점은 상면/+z가깊이다. 부피 가중 마스크·고정 cutoff·5정규화·전체 비표적 통계는 [5조건 보고서](cloud-extended-20261021T102700Z/volume-return-position.json)와 [사전등록](cloud-extended-20261021T102700Z/volume-return-position-plan.json)에 있다. 표의 상한은 수치 비교 기준이며 사람의 안전 한계가 아니다.

| 조건 | 목표mean | 목표P10 | 표층P95 변화 | 전체 비표적P95 변화 |
|---|---:|---:|---:|---:|
| 기존4-square 기준 |4.06185|3.64574|0%|0%|
| 기존 비대칭 면적, 귀환δ0 |4.38354|3.95194|+27.42%|+10.43%|
| 귀환 바깥δ+0.625mm |4.49197|4.05062|+34.45%|+14.29%|
| 귀환 안쪽δ−0.625mm |4.23273|3.81353|+17.97%|+5.64%|

두 새 귀환 조건은 목표 절대 세기를 보존했지만 비표적P95와 고변조 부피가 증가해 채택하지 않았다. 바깥 조건의 활성 제한은 피부SC+dermis 손실, 안쪽 조건은 bulk-skinJ95다. 원래 primary mean4.061848941601601V/m를 고정 cutoff로 쓰면 바깥 조건의 표층/전체 비표적 고변조 부피는+8.84/+11.23%, 안쪽은+3.99/+4.76%다. 전역 최대는 두 조건 모두SC z0.025mm에 남는다. 목표/표층 비율 하나나 중심점으로 성공을 판정하지 않았다.

두 PDE는108.942/110.961초, 기존5개 방정식·전력·전류·면적·계면 gate를 통과했다. [등록·시작 근거](cloud-extended-20261021T102700Z/return-position-start/preregistration.json)에 source commit/configSHA/격자/물성·접촉·회로가 연결돼 있다. 이는 SC/XY/bulk/edge/contact 수렴 완료나 실험 검증이 아니다.

실제 정현파3000/3030Hz와9000/9090Hz 비교도 완료했다(새PDE0,34.895초). 같은 square 상한에서9k 목표mean/P10은2.85755/2.56281V/m로 낮고 제한은bulk-skinJmax다. Carrier뿐 아니라beat30→90Hz도 바뀌므로 순수carrier 효과나 생리적 동등성으로 해석하지 않는다. 새 단위 정현파 계수와 실제 주파수별 E/φ/전류/손실을 사용했다. [계산 근거](cloud-next-frequency-20261021T104000Z/summary.json), [정현파 GUI](CLOUD_FREQUENCY_RESULTS_20261021.html), [기존4/8/12/16패드 GUI](CLOUD_VOLUME_RESULTS_20261021_v6.html)를 별도로 보존한다. 새 주파수 공간 지도가 생성됐다고 표시하지 않는다.

40개 차동 프로브는 깊이5/10/15/20mm 십자 중심 위치와X/Y방향, **팁 간격5mm**의 native 복소φ 예측이다. 장비 부하 검증은 보류이며 ETA5001 뒤의 스코프 입력을 팬텀에 직접 병렬 연결하지 않았다. 새 주파수의 단일 전극쌍C1 비교는 아직 계산하지 않았다.

## 현재 실행과 자동 순차 단계

[고정 큐 계획](cloud-extended-20261021T102700Z/continuation-plan.json)은 최대1600초의 유한 실행이다. 실행 큐는 별도 이중 loop lock, 자식 계산은 전역 이중 execution lock을 소유한다. PID/startticks로 별도 세션의 Java까지 추적하며5초마다 heartbeat와 체크포인트를 기록한다. 중복 워커나 자동 재시도를 만들지 않는다.

1. 구동 패드만 안쪽0.625/1.25mm 이동한2조건 PDE, 순차 실행. [선정 근거](cloud-extended-20261021T102700Z/source-position-decision.json), [실행 전 등록](cloud-extended-20261021T102700Z/source-position-start/preregistration.json).
2. 각 조건의 native 피부J/6개 구획 손실·전역 최대·공간 분포 검사.
3. 기존SC4 기저에서 두 주파수 쌍을 재합성해SC 두께 방향 민감도 검사. SC4 자체square/sine 상한과SC2 절대square 상한을 **세 별도 cohort**로 표시하고, 고변조 부피 cutoff는 원래SC2값을 고정한다. [사전등록](cloud-extended-20261021T102700Z/SC4-frequency-plan.json).
4. GitHub PR1/2 head·공개 피드백을 실제GET으로 확인해 새ID/본문SHA를 저장한다. 수신을 자동 채택이나 검토자 동의로 처리하지 않는다.

10:53:43UTC [생존 확인 snapshot](cloud-extended-20261021T102700Z/execution-state-running.json)에서 큐PID11228/startticks2647812, 계산PID11229/startticks2647844가 일치했다. 당시 장부지출6025.864초, 활성 계산 차감 전 잔여7774.136초였다. 현재 활성 단계 시간도 실질 잔여에서 차감해야 한다. 실시간 상태는 `docs/cloud-extended-20261021T102700Z/queue-execution/heartbeat.json`, 종료 시 `summary.json`, 단계별 로그에 저장된다. 환경 종료 시 생존을 보장하는 서비스나 무기한 실행을 약속하지 않는다. 유한 큐 완료·예산·자원·오류를 종료 사유와 구분하며, 시도한 큐는 덮어쓰지 않고 다음 계획은 새 실행ID로 등록한다.

원본은 보존했다. 귀환 배치164파일/375577276bytes를 tar로 저장하고 별도 경로의 바이트SHA·배열decode 검사를 통과했다. [복원 근거](cloud-extended-20261021T102700Z/return-position-preservation.json)는 같은 환경의 로컬 복원이며 독립 영구 백업이나 시뮬레이션 재현 검증으로 표시하지 않는다.

유도현2의 [6312627319](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6312627319)는 구현28f3c17과 실제결과5418634에 연결했다. 10:45UTC [후속GET](cloud-extended-20261021T102700Z/feedback-after-return.json)에는 새 검토자 회신이 없었으며, [계획 공유](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6313872399)와 [실제 시작·결과 게시](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6314015870)는 계산 담당자의 게시물이다.
