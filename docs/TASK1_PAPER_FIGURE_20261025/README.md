# 논문 구성을 참고한 Task1 TIS 그림

Grossman et al., Cell169(2017), DOI: https://doi.org/10.1016/j.cell.2017.05.024 의 Figure1A–C/Figure2를 참고해 이 연구의 계산값으로 새 그림을 그렸습니다. 논문 이미지와 원문은 배포 파일에 포함하지 않습니다.

`index.html`을 내려받아 열면 인터넷 없이 작동합니다. 기존 best1 f35 및 중앙 y=0 단일쌍, 과거 GUI와 수치·실패·수렴 상태를 보존했습니다.

- A: 실제 윗면 전극과 계산 표본 위치. (i)/(ii)는 실측이 아닌 실제 native 셀의 계산 표본입니다.
- B: 3000/3030Hz carrier 벡터 RMS와 x/y/z 고정방향 envelope 변조깊이. 네 carrier 지도는 하나의 공통 범위를 사용하고, 변조 지도는 별도의 공통 범위를 사용합니다. 선형/log1p 모두 상한 clipping 없이 실제 V/m tick을 표시합니다.
- C: 표층·목표 위치의 실제 복소 합성파와 ±analytic envelope. 이것은 지점의 전기장 파형이며 5mm 차동 프로브 전위차가 아닙니다.
- D: 실제 native 중앙선 프로파일과 보존된 Float64 ROI 통계. 선 프로파일과 부피 통계, 고정방향 변조와 기존2074표본방향 maxTIS를 구분합니다.

같은 주파수의 두 출력은 복소 합산 후 계산했습니다. 고정방향 복소 peak 투영을 a,b라 하면 envelope는 abs(a*exp(j*w1*t)+b*exp(j*w2*t)), 전체 beat 변조깊이는 2min(abs(a),abs(b))입니다. Δf30Hz는 envelope 변화율이며 선형 전기장의 새30Hz Fourier 성분이 아닙니다. C1은 변조0이어도 carrier RMS가 남습니다.

이 단계는 SHA256 검증된 기존 Float32 표시 벡터를 재사용하며 새 원시 복소장 decode/PDE/2074방향 검색을 수행하지 않았습니다. 기존 authoritative Float64 ROI 통계와 native 출처·표시 변환 오차 증거는 유지합니다. 독립 복소수 수식·형식11검사와 실제 화면336조합, 모바일390px, JS오류·외부요청0을 확인했습니다.

논문의 salineD50x10mm·절연 구동을 현재의 층상D50x25.1mm·윗면·공통GND/50ohm 모델과 동일시하지 않습니다. 기존 격자/접촉 실패·불확실성과 전체 수렴·실험 검증 보류는 유지합니다. 새 fat baseline/bulk 요청은 이 표시 후처리로 수행된 것이 아닙니다.

Windows 저장은 별도 Save-TIS-Results.ps1과 manifest를 사용합니다. 클라우드에는 C: 드라이브 직접 연결이 없으며 Windows 저장 및 OneDrive 동기화는 미확인입니다. 기존 파일·원본은 삭제하거나 덮어쓰지 않습니다.
