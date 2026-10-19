# 20 mm 표적·피부 계면 부담 최적화 — explore-20261017T133224038032Z

갱신 UTC: 2026-10-17T21:05:01.974430+00:00. 검증 완료 3720개 해석 조건, 위상·파형 포함 124982개 후보. 탐색 진행 중이며 전역 최적을 보장하지 않는다.

기준(격자 0.625 mm): 20 mm 변조 깊이 **2.954644 V/m**, 실제 총 E RMS **1.477618 V/m**.

## 작업 1 · 각 출력 1 Vpp 고정 TIS 최적화

현재 가장 세밀한 TIS 격자 0.625 mm의 1 Vpp 고정 선두: 0 nm / 전극 4개 / 15 mm / 3000+30 Hz / square_3h. 포락선 변동 폭 **3.946983 V/m**, 실제 RMS 2.078989 V/m.

단일 출력 대조군은 이 순위에서 제외한다. 격자별 선두를 별도 저장하며 피부 부담 제한 선두와 구분한다.

현재 피부부담 제한 **실제 E RMS** 1위: 0 nm / 2개 전극 / 20 mm 정사각형 / 2000 + 10 Hz / square_3h.

각 출력 1 Vpp에서 20 mm 변조 깊이 0.000000 V/m, 실제 E RMS 1.992210 V/m.

기준 피부 부담 이하로 출력 조정(1.000000 Vpp) 시 변조 깊이 **0.000000 V/m (-100.00%)**.

같은 출력 조정 후 실제 총 E RMS **1.992210 V/m**. 이 보고서의 후보 선별은 실제 RMS와 기본파 변조 깊이의 선두를 모두 보존한다.

전극 2개/출력 1개 후보는 단일 반송파 대조군이며 TIS가 아니다. 실제 RMS가 높아도 포락선 변조 깊이는 0이다.

현재 두 반송파 후보의 피부 부담 제한 변조 깊이 선두: **2.954644 V/m**, 0 nm / 전극 4개 / 2000+10 Hz. 실제 E RMS 선두와 별도 평가한다.

점수는 같은 격자 기준의 최대 접촉 J RMS, SC 전력, 접촉 전력, 접촉 전압을 모두 넘지 않는 출력 축소를 적용한다. 동등 총입력전력 비교도 별도 저장한다.

## 초기 후보 (피부 부담 제한 점수 순)

|코팅 nm|전극 수|한 변 mm|반송파/차이 Hz|파형|원 변조 V/m|부담 제한 변조 V/m|원 E RMS V/m|

|---:|---:|---:|---|---|---:|---:|---:|

|10|2|20|2000/10|square_3h|0.0000|0.0000|2.0239|

|10|2|20|2000/5|square_3h|0.0000|0.0000|2.0239|

|10|2|20|2000/20|square_3h|0.0000|0.0000|2.0239|

|10|2|20|2000/50|square_3h|0.0000|0.0000|2.0239|

|50|2|20|2000/10|square_3h|0.0000|0.0000|2.0239|

|50|2|20|2000/5|square_3h|0.0000|0.0000|2.0239|

|50|2|20|2000/20|square_3h|0.0000|0.0000|2.0239|

|50|2|20|2000/50|square_3h|0.0000|0.0000|2.0239|

|30|2|20|2000/10|square_3h|0.0000|0.0000|2.0225|

|30|2|20|2000/5|square_3h|0.0000|0.0000|2.0225|

|30|2|20|2000/20|square_3h|0.0000|0.0000|2.0225|

|30|2|20|2000/50|square_3h|0.0000|0.0000|2.0225|

## CV / EIS 해석

50 nm 시료는 무제약 Rs 제거 시 비수동 경계가 되므로 수동성 제한 피팅을 사용했다. 50/100 nm의 CPE 지수 경계 도달과 Rs 불확실성은 별도 표시한다.

CV의 paired bare 곡선은 두 표에서 다르다. 스캔 속도 미상으로 CSC·CIC나 안전 전압창을 계산하지 않았다.

## 작업 2 · 횡격막 문헌과 조건부 전기적 크기 비교

문헌의 실제 치료 전류 38–54 mA(30 Hz/200 µs), 평균48 mA(50 Hz/펄스폭 표기 불일치)는 peak/RMS 정의와 표적 V/m가 미보고다. 보편적 횡격막 활성화 임계값으로 사용하지 않는다. 원문과 한계: [DIAPHRAGM_REFERENCES.md](../../../docs/DIAPHRAGM_REFERENCES.md).

diaphragm-comparison.json/GUI는 보고 전류를 출력별 최대 peak 또는 RMS로 가정한 별도 비교와 1/2/5/10/20 Vpp 선형 모델 민감도를 저장한다. 전기장·전류는 전압에 비례, 손실전력은 제곱에 비례한다. 이는 펄스/TIS의 생리적 동등성이나 안전한 자극 설정을 뜻하지 않는다. 30/50/80 Hz 단일 출력 추가 계산은 연속파 대조군이며 문헌의 짧은 이상성 펄스 재현이 아니다.

## GitHub PR 점검

마지막 조회: 2026-10-17T20:57:30.521582+00:00; 상태 ok. 리뷰·댓글·CI는 pull-requests.json에 저장한다. 새 검토 의견은 입력 자료로 검증하며 자동 병합하지 않는다.

## 한계

- Simulation electric fields are not neural activation or a stimulation success threshold.

- PBS-minus-Rs is an unvalidated dry-contact surrogate; coating ranking needs Rs/contact sensitivity.

- Total pad count <=8, at most4 independent outputs; shared ground and zero-voltage50-ohm termination at other frequencies.

- Three/four independent outputs require additional synchronized source hardware beyond the existing two-output EDU33212A.

- The burden score caps max surface J RMS, SC power, contact power and contact voltage at the same-mesh bare reference.

- All raw candidates use1 Vpp/output; matched-budget comparisons scale all outputs together downward.

- Square/triangle waveforms include only fundamental and third harmonic; higher carriers permit sine only.

- Surface maxima depend on mesh and ideal square pad edges; finalists need mesh refinement.

- Phantom conductivity and relative permittivity are held fixed versus frequency; measured tissue dispersion is unavailable.

- CV scan rate is unknown; no clinical safety, CIC or safe voltage window is inferred.

- Finite design and phase search does not prove a global optimum.
