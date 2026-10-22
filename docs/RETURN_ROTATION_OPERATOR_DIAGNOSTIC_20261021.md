# 공통 GND 귀환 전류 응답 진단 — 2026-10-21

저장된 작은 복소 전류·접촉 자료를 실제 적분해 원본 square와 단일 회전 조건의 귀환 응답 rank가 각각1, 원래 비대칭 조건은2임을 확인했습니다. **독립 전압 출력 수는 세 조건 모두2개**이며, rank는 두 GND패드의 순전류 분포를 구분할 수 있는 응답 차원입니다. 두 귀환 패드에 독립 전류원을 추가한 계산이 아닙니다.

[원 결과](cloud-return-rotation-operator-20261021T180000Z/summary.json) · [등록](cloud-return-rotation-operator-context-20261021T180000Z/preregistration.json) · [피드백·저장 포함 완료 큐](cloud-return-rotation-operator-context-20261021T180000Z/queue/summary.json)

| 형상 | 주파수 Hz | 귀환 rank | 최소/최대 특잇값 | 두 귀환 행의 상대 차이 |
|---|---:|---:|---:|---:|
| opposite-square | 3000 | 1 | 8.69333914e-16 | 2.86279518e-15 |
| opposite-square | 3030 | 1 | 7.19854773e-16 | 1.75554121e-15 |
| opposite-asymmetric | 3000 | 2 | 0.0361055425 | 0.0698687961 |
| opposite-asymmetric | 3030 | 2 | 0.0361809302 | 0.0700077786 |
| one-return-rot90 | 3000 | 1 | 1.44365786e-16 | 1.83832468e-15 |
| one-return-rot90 | 3030 | 1 | 3.98647951e-16 | 3.16404266e-15 |

기존 native 응답의 수치 해상도2e−6을 고정했습니다. rank1은 정상 진단 결과이며 역행렬·q·새 구동 가중치를 만들지 않았습니다. 원본/회전의 두 귀환 행 차이는 약1e−15이고 parent는약0.07입니다. 전류 보존 및 신호 패드 적분전류와 source matrix 일치도 같은 결과에 보존했습니다.

회전 후 x=y 반사가 source 두 패드는 각각 고정하고 GND패드를 맞바꾸는 형상이라는 가설과 실제 응답은 부합하지만, 이를 독립된 연속체 대칭 증명·전체 격자 수렴으로 표시하지 않습니다. rank나순전류0은 국소J0·격리된전극쌍·공간선택성·장비구현성을 뜻하지 않습니다.

작은 density/source 행렬과 contacts만 읽었습니다. E/φ/grid/NPZ·새PDE·새장합성0이며 실제수치 진단 시간은 0.08662493500014534초입니다. 실제계산·GET·공개저장은 모두완료했고 후보채택/전체수렴/실험검증은별개입니다.

다음은 [한 전극 회전 형상의 두 출력 전압 비율4조건](cloud-rotation-ratio-context-20261021T180500Z/decision.json)입니다. 같은 두 실제전압원을 조절하며 귀환전류응답을 독립 자유변수로 역산하지 않습니다. 원본square8cap/ROI/cutoff와 회전1/1캐시를 보존하고 새PDE 없이4freqRMS·기본파TIS·피부부담·40nativeφ를 비교합니다.
