# 귀환 순전류 cancellation 구동 결과

기존 두 adjacent 기저에서 6개 구동 조건을 계산했으며 **6개 모두 미채택**이다. τ=1의 지정 귀환 패드 순전류 cancellation은 통과했지만 목표 ROI mean/P10 및 표층 P95 개선으로 이어지지 않았다. 새 PDE는 0이다.

고정 조건은 D50 mm·층0.1/5/5/15 mm·상면, 물리 패드4개·독립 출력2개·공통 GND 노드1개·50 Ω이다. 목표는 중앙 r≤5 mm·상면 z=0에서 +z 깊이15–20 mm이며 원래 부분 셀 부피 가중치와 cutoff를 유지했다. 전체 XY 깊이15–20 mm는 별도 보조 ROI다.

기준은 원래 opposite 4-square의 square3h/3000·3030·9000·9090 Hz다. 새 조건은 실제3000/3030 Hz 두 carrier와 beat30 Hz만 사용하며, 각 adjacent 형상에서 τ=0/0.5/1을 비교했다. 원 source0(−10,−10), source1(+10,−10), return2(+10,+10), return3(−10,+10) mm의 물리 위치·면적·배선은 그대로다.

아래 값은 원래 square의 **8개 피부·접촉 수치 상한**에서 최대 방향 기본 TIS 변조(V/m)다. 상한은 인체 안전 한계나 활성화 역치가 아니다.

| 조건 | τ | ROI mean | ROI P10 | 표층0–5 P95 | 전체 비표적 P95 | 활성 부담 제한 | 선별 |
|---|---:|---:|---:|---:|---:|---|---|
| 원래 opposite 4-square | 기준 | 4.06185 | 3.64574 | 25.2592 | 23.4357 | 기준 | 유지 |
| adjacent-square | 0 | 3.45958 | 3.15735 | 53.1583 | 26.9792 | 피부 조직 벡터 J RMS P95 | FAIL |
| adjacent-square | 0.5 | 3.26047 | 2.7357 | 59.8452 | 33.2884 | 피부 조직 벡터 J RMS P95 | FAIL |
| adjacent-square | 1 | 3.38278 | 2.83846 | 64.3246 | 40.8208 | 피부 조직 벡터 J RMS P95 | FAIL |
| adjacent-cross | 0 | 3.43902 | 3.14066 | 50.3287 | 26.8584 | 피부 조직 벡터 J RMS P95 | FAIL |
| adjacent-cross | 0.5 | 3.28159 | 2.75323 | 57.9184 | 33.5538 | 피부 조직 벡터 J RMS P95 | FAIL |
| adjacent-cross | 1 | 3.4278 | 2.87553 | 62.8995 | 41.4056 | 피부 조직 벡터 J RMS P95 | FAIL |

모든 조건은 ROI mean/P10 두 항목과 표층 P95 항목에서 실패했다. τ=1에서는 표층의 고정 cutoff 초과 부피 두 항목이 통과한 경우가 있지만, 목표 절대량과 비표적 분포를 함께 개선하지 못했다. 접촉 법선 J95와 활성 제한인 SC+dermis **조직 벡터 J RMS P95**는 다른 지표다.

순전류 응답은 각 주파수의 복소 patch J×면적을 먼저 적분한 R[pad,output]다. q0=−R3000[2,0]/R3000[2,1], q1=−R3030[3,1]/R3030[3,0]이며 실제 계수는 c3000=[1,τq0], c3030=[τq1,1]이다. +jwt·0.5 Vpeak 기저의 cosine 위상을 명시했다. τ=0은 동일 geometry·exclusive 주파수 할당·RMS/TIS 대조이며 과거 sine 시간파형과 바이트 단위 동일한 대조가 아니다.

| 형상 | q0 | q1 | 귀환 응답 조건수3000/3030 |
|---|---|---|---|
| adjacent-square | -0.444065727 +0.0598989522j | -0.443857053 +0.0593857305j | 2.58482 / 2.5837 |
| adjacent-cross | -0.439524159 +0.0613537698j | -0.439304028 +0.060840933j | 2.55546 / 2.55429 |

**q는 두 기존 source의 구동 가중치다. 독립 GND 귀환 전류를 명령하거나 수동 50 Ω 임피던스를 바꾸지 않는다.** 공통 GND 노드는 계속1개다.

| τ=1 조건 | 3000 Hz return2 순전류/source 상대 잔차 | return2 국소 J peak A/m² | 3030 Hz return3 상대 잔차 | return3 국소 J peak A/m² |
|---|---:|---:|---:|---:|
| adjacent-square | 8.42113e-17 | 2.8771 | 1.61989e-16 | 2.89105 |
| adjacent-cross | 1.53014e-17 | 3.26237 | 3.89233e-16 | 3.2789 |

순전류 잔차 기준2e−6을 통과해도 국소 J와 절대 patch 전류 적분은 0이 아니다. 이 결과는 절연 전원이나 독립 전극쌍을 구현·검증했다는 뜻이 아니다. 국소 J 값은 raw 주파수별 peak이며, 표의 skin8 최종 RMS와 혼동하지 않는다.

각 출력의 실제 source 파형 Re[0.5∑c_f exp(j2πft)]을 공통1/30초에서 재구성하고, **단 하나의 전역 배율** 1/max(Vpp_upper0,Vpp_upper1)을 적용했다. 원전압 조건에서 각 출력 Vpp≤1이고 최대 upper가1이며, 두 출력 모두 정확히1 Vpp라고 하지 않는다. raw Vpp 구간 폭≤1 µV를 확인했다. 아래는 skin8 정규화 후 upper이며 별도 수치 비교이므로1 Vpp를 넘을 수 있고 구간 폭도 함께 스케일된다.

| 조건 | τ | skin8 amplitude scale | source Vpp upper out0/out1 | source RMS mA out0/out1 | ideal source W out0/out1 |
|---|---:|---:|---|---|---|
| adjacent-square | 0 | 1.07809 | 1.07809 / 1.07809 | 1.4566 / 1.45751 | 0.000513186 / 0.000513715 |
| adjacent-square | 0.5 | 1.17893 | 1.1788 / 1.17893 | 1.50095 / 1.50164 | 0.000494808 / 0.00049521 |
| adjacent-square | 1 | 1.22259 | 1.22235 / 1.22259 | 1.51381 / 1.51432 | 0.000477277 / 0.000477576 |
| adjacent-cross | 0 | 1.07328 | 1.07328 / 1.07328 | 1.4474 / 1.44833 | 0.000507178 / 0.00050772 |
| adjacent-cross | 0.5 | 1.18826 | 1.18812 / 1.18826 | 1.51081 / 1.51154 | 0.000502111 / 0.000502535 |
| adjacent-cross | 1 | 1.2407 | 1.24045 / 1.2407 | 1.53426 / 1.5348 | 0.000491023 / 0.000491346 |

Raw·출력별 RMS 전류 합 일치·총 source 전력 일치·skin/contact8상한·기존 복합 상한의 **5개 정규화**와 source Vpp 양 끝값, 접촉 전압·9개 부담 값, 패드별 전류 및 signed source/metal/resistor power는 [압축 JSON 원표](cloud-return-current-context-20261021T172000Z/result-brief.json)에 있다. 전류 합은 장부상 출력별 RMS 합이며 공통 GND 전류가 아니다. source/metal의 음수 전력은 주파수별로 보존하고 흡수 필요 여부를 기록했다. multitone 생성·동기 위상·전력 흡수·출력 compliance 능력은 실험 장비에서 검증되지 않았다.

6조건 모두 새 복소 E의 2074개 방향 maxTIS·고정 대각 방향 TIS·vector RMS를 구분해 계산하고, 40개 native φ 차동 프로브와 전기장 방향 시간파형/RMS/envelope 검사를 통과했다. 프로브 중심은 깊이5/10/15/20 mm×중심·두 축±5 mm이며 X/Y 팁 간격5 mm다. 실제 source 계수를 적용한 Vpp 하·상한/RMS/스펙트럼은 무부하 예측이다. ETA5001 phantom loading·실제 장비 전달함수·새 C1·연속 방향 최대값·SC/XY/bulk/edge/contact 수렴·실험/활성화 검증은 완료하지 않았다.

실제 계산은 70.012928초, peak RSS 553181184 bytes, CPU1이었다. 유한600초/조건60초 안에서 종료했고 큐는 정상 종료했다. 원본·캐시·실패 증거를 보존했으며 신규 PDE·추가 출력·절연 변경·자동 채택은0이다. 수치 도구 source commit은 `9f3f68767ba3fa27e447ecd5d588e5631327d980`, 실행 시 기록된 구현 HEAD는 `f5b2757564efa68b31fdc01bab54ccafac6309ff`, 결과 공개 commit은 `87235086555b4464bd3595c5ec30e00b0aabf99c`다. 원 기저의 별도 source/config/native SHA는 각 condition과 operator 기록에 연결된다.

댓글 [6321929825](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825)는 이 배치의 등록·시작 이후 도착했고, [실제 후속 GET](cloud-return-current-context-20261021T172000Z/feedback-after.json)에 보존했다. 이 후속 피드백이 이미 실행한 계획을 선정했다고 소급하지 않는다. stable ID 채택/처분은 별도 장부에서 연결한다.

- [원 실행 summary](cloud-next-return-current-20261021T172000Z/summary.json)
- [6조건·5정규화·q·국소 J·signed power·40프로브 근거를 연결한 압축 JSON](cloud-return-current-context-20261021T172000Z/result-brief.json)
- [static 6조건 표](RETURN_CURRENT_RESULTS_20261021.html)
- [등록과 원본 SHA](cloud-return-current-context-20261021T172000Z/preregistration.json)
- [종료 큐](cloud-return-current-context-20261021T172000Z/queue/summary.json)
