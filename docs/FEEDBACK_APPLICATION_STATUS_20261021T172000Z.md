# 새 회로·C1 검토 요구의 적용 상태 — 2026-10-21

댓글 [6321929825](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825)의 회로 명세·주파수별 signed power·C1 cohort 요구를 **수신 후 명시적으로 채택**한다. 기존 계산이 이 댓글 때문에 설계·실행됐다고 소급하지 않는다. 본 문서는 저장 JSON/소스의 metadata만 읽었으며 새 PDE·배열 분석·후처리·원격 작업을 하지 않았다. [원문·body SHA·조건별 정확한 증거](FEEDBACK_APPLICATION_STATUS_20261021T172000Z.json)를 연결한다. 후보는 모두 미채택이며 전체 격자·접촉·실험 검증 상태를 올리지 않는다.

## 수신·구현·실행·채택 시점

- 댓글 updated_at은 **17:10:52 UTC**, body SHA256은 `4362c45b25961dd7a3976d21a1cc4826763a3c00178dbccd90f0fe17bbed7aa7`이다. 실제 [GET](cloud-return-current-context-20261021T172000Z/feedback-after.json)은 **17:11:46.746061 UTC**, `/receipts/3/evidence/16`에 원문을 보존한다.
- return scout 구현 `9f3f68767ba3fa27e447ecd5d588e5631327d980`은17:09:50, 등록 `f5b2757564efa68b31fdc01bab54ccafac6309ff`는17:10:32이다. [큐](cloud-return-current-context-20261021T172000Z/queue/summary.json)는17:10:33.105801에 시작했고 계산단계는70.240836초다. **댓글은 이미 등록돼 실행 중인 계산 도중에 작성됐으며, 첫 저장 GET은 계산 종료 후다.** 댓글 작성 전 계산 완료라고 표시하지 않는다.
- 실제 return6 결과는 `87235086555b4464bd3595c5ec30e00b0aabf99c`에 공개됐고 큐는17:11:52.898540에 종료했다. 이번 문서가 수신 후 명시 적용 기록이며 문서 적용 커밋은 root 커밋 대기다. 실행을 다시 시작하거나 peer가 return 결과를 승인했다고 추론하지 않는다.
- C1 구현은 `a1724f684ade02a76741a762ebccb1dd6c054061`, 실제 완료는17:09:06.994905, 공개 결과는 `121bed2da204e99237f1d3e1876140703c2595a3`다. 이 계산은 댓글 작성 전 완료됐다.

## 귀환 전류는 독립 자유변수가 아니다

[return6 등록](cloud-return-current-context-20261021T172000Z/preregistration.json)과 [실제 summary](cloud-next-return-current-20261021T172000Z/summary.json)는 adjacent-square/cross 각각 tau0/0.5/1을 비교한다. 물리4패드·독립출력2개·ideal common GND1노드·출력별50Ω를 유지했다. GND 패드에 별도 전류원이나 명령 전류를 추가하지 않았다. 3000Hz의 출력 계수는 `[1,tau*q0]`, 3030Hz는 `[tau*q1,1]`이며 q는 **각 완료 회로에서 적분한 복소 physical-pad 응답**으로 계산됐다. 같은 주파수의 두 출력을 먼저 복소합성한다.

따라서 이번 변경은 **기존 두 전압원의 주파수별 진폭·위상 명령**이다. 수동 접촉/귀환 임피던스 또는 출력 수·귀환 topology를 바꾸지 않았다. 같은 geometry/물성/접촉·50Ω·0V/50Ω 비구동 종단을 유지하는 선형 회로의 저장 basis만 합성했다. 패드·접촉·물성·소스저항·종단·귀환 임피던스/노드·절연 topology를 바꾸면 그 변경을 포함한 새 회로 풀이가 필요하다. 기존 basis를 새 회로의 검증 결과로 재표시하지 않는다.

주파수별4패드 KCL/source 일치 한도2e−6, source/metal/50Ω signed power, raw 전체1/30초 source Vpp bracket 폭≤1µV(정규화 후 구간 폭은 실제 배율을 곱함) 및 전기장·40probe 시간파형 검사가 조건별 JSON에 있다. 두 출력 파형에 **단일 전역 배율**을 적용해 raw 최대 source 상한을1Vpp로 맞췄으며 출력별 독립 배율로 cancellation 비를 바꾸지 않았다. tau1의 net-current 잔차는 통과해도 국소 normal J와 절대 patch 전류적분은0이 아니며 isolated pair를 뜻하지 않는다. 소스 동기·흡수·compliance·실측은 미검증이다.

6조건 모두 목표mean/P10 gate가 실패해 미채택이다. 일부 tau1의 표층 고변조 부피2개는 감소했으므로 ‘비표적6gate가 모두 실패’라고 묶지 않는다. 모든8개 개별 판정과 절대값은 동반 JSON에 보존했다. 새 PDE0, 실제 scout70.012928초·peak RSS553181184bytes이며 이는 재계산한 수치가 아니다.

## 작은 혼합비의 음의 주파수별 전력

Weak r0.05는 raw actual1Vpp 모드에서 다음 **metal-delivered power(W)**를 보존한다. 양의 출력 합계가 이 음수를 없애지 않는다.

| 조건 | 출력0/3030Hz | 출력1/3000Hz | 총 ideal-source W | 총 metal-delivered W |
|---|---:|---:|---:|---:|
| r0.05,90° | −7.47521842065402e−7 | −7.5036939803777e−7 | 0.0008205212483027176 | 0.0006634330947005048 |
| r0.05,270° | −3.858088204489767e−7 | −3.867666933316831e−7 | 0.0008205212483033636 | 0.0006634330947007594 |

해당 선의 ideal-source power는 각각 양수이며50Ω 손실과 metal 전달 부호는 서로 다르다. 출력 전체 합계에 대한 negative flag를 주파수별 음수 없음으로 해석하지 않는다. 원 JSON의 개별 선·총계·원 flag를 수정하지 않고 동반 JSON에 복사했다. 실제 장비가 해당 단자 흡수·컴플라이언스를 지원한다는 결론은 없다. Strong8+weak6의 전체8screen 미통과 및 skin-only의1Vpp 초과 비교와 strict source ceiling 비교 구분도 유지한다.

## C1은 별도 footprint와 여섯 개 RMS 정규화 cohort

[실제 C1 summary](cloud-coherent-single-pair-20261021T172000Z/summary.json)는 원본225mm² 사각패드 **2개(총450mm²),1출력, 귀환1개,50Ω/common GND,3000Hz pure sine**다. 중심은(−10,−10)/(10,−10)mm다. 비교 TIS는225mm² **4개(총900mm²),2출력,공통GND 귀환2개**다. 두 footprint가 같다고 표시하지 않는다.

TIS 기준3개(raw coherent,skin8 coherent,원본 square3h) 각각에 대해 centre20 벡터 E RMS 일치와 ROI energy RMS 일치를 별개로 저장한6개 cohort다. ROI는 r≤5mm/깊이15–20mm에서 `sqrt(부피가중 평균(E_RMS²))`이며 `mean(E_RMS)`나 φ-gradient 대체값이 아니다. 피부상한 coherent ROI RMS 일치 C1은1.5799583328166869Vpp가 필요하며, 이는 TIS의source 파형 상한1.5129476764748433Vpp와도 다른 별도 정규화다.

필요 Vpp·전류·J·접촉 전압·구획별/전체 전력을 각 cohort에 그대로 연결했다. RMS 일치는 동일 총전류·전력·피부상한, TIS 변조 또는 생리적 동등성 비교가 아니며 목표부피/비표적8screen을 대체하지 않는다. 40프로브는팁 간격5mm의무부하 예측이며 계측기 부하 검증은 보류다.

## 다음 과학 질문의 제안 범위

다음 질문 하나로 **기존 비대칭4패드의 physical return pad2 하나만 중심을 유지해90° 회전**하는 geometry 대비를 제안한다.15×11.25mm 귀환을11.25×15mm로 바꾸고 면적·나머지3패드·회로·접촉·원파형은 고정한다. 기존 전체패드 axis/tangent, 위치 이동·역할교환·면적배분·coherent/귀환net-current 합성과 다르다. 두 귀환을 함께90° 돌리는 것은 원형 등방 팬텀에서 x↔y 반사 대칭 중복 가능성이 있어 제외한다.

root는 이 단일 조건을 [별도 결정](cloud-one-return-rotation-context-20261021T174000Z/decision.json)으로 선정했고 소스·등록을 준비 중이며, 아직 새 PDE/prepare를 시작하지 않았다. 새 geometry는 기존 E/φ 재합성으로 얻을 수 없고 fullface·D50·패드간격·면적 검증이 필요하다. 제안의 900초 추산과 구분해, root는 준비 최대120초와 계산·fullskin·부피·screen·피드백·게시까지 연결하는 유한 큐 최대1320초를 기존 누적13800초 안에서 예약한다. 새 PDE 자체는 한 조건 최대600초다. 개선이나 실험 구현성은 근거가 없으며 원본8screen·고정cap/cutoff를 유지한다. 실패하면 같은후보를자동정밀화하지않고, 통과하더라도별도SC/XY/bulk/가장자리/접촉 수렴성 이전에채택하지않는다.
