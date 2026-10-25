새 PDE 조건 1개 / RHS 8개를 계산한 SC 유전율 단일 인자 가정 민감도입니다. 네 층 물성의 논문 교정·실험 검증 또는 후보 채택 결과로 해석하지 않습니다.

| 지표 | 기존 4패드 | 새 4패드 민감도 |
|---|---:|---:|
| 목표 ROI 전체 전기장 RMS mean (V/m) | 2.30695 | 0.424092 |
| 목표 ROI 전체 전기장 RMS P10 (V/m) | 2.10467 | 0.389283 |
| 목표 ROI 기본파 max2074 mean (V/m) | 4.06185 | 0.667465 |
| 접촉 정상방향 J RMS max (A/m²) | 25.4912 | 0.949902 |
| 총 실제 전원 전력 (W) | 0.00113592 | 0.00010712 |

동일1Vpp에서 접촉Jmax가 감소하더라도 SC실손실 증가와 목표 절대변조 감소를 함께 보아야 합니다. 동일Jmax 전압 환산은 수치 비교이며 구동 제안이 아닙니다. SC+contact 형태의 과거 skin_power_W를 SC+dermis로 비교하지 않습니다.

기본파 3000/3030 Hz 방향 변조와 전체 4주파수 RMS를 구분합니다. 2074 방향 검색 상태: complete. 잔차·전력·전류·면적·공유 flux 보존 검사는 독립 potential-gradient 진단 및 SC/XY/bulk/edge 수렴 검증을 대신하지 않습니다. SC 2셀 및 기존 XY/접촉 실패를 유지하며, 물성·접촉·실험·생리 활성화·안전 검증은 보류입니다.

뷰는 원시 Float64 필드를 변경하지 않습니다. 색상 범위·축 범위·클리핑 개수는 별도 표시하며 사용자 설정은 이 HTML의 localStorage에만 저장합니다. 소스 commit: 3b9fd031f42226201f1578307cebd4b67466332a; 결과 commit: ebbad61a7da19d13af17031ae53ab5047c3f71a8; run: task1-all-layer-sensitivity-20261025-run; case: baseline-square15-sc-eps1100-xy80.
