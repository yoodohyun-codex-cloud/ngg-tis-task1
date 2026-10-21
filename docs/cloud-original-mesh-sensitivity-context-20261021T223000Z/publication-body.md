최신 fine 후보의 동일 구동을 기존 SC4와 XY coarse 기저에 적용한 배치를 15.316131초에 완료했습니다. 계산과 피드백 GET 큐가 모두 exit0이며 새 PDE는 0입니다. CPU 1개, peak RSS 496185344바이트, 기존 원시 자료·과거 NPZ·실패 기록을 보존했습니다.

SC2 fine의 목표 mean/P10은 4.011539371/3.595322017 V/m입니다. 동일 계수·global g·fine skin8 배율 1.093481770을 고정한 SC4에서는 4.011547419/3.595328369, 표층 P95 25.251245740, 전체 비표적 P95 23.395226994 V/m입니다. 사전등록한 20개 민감도 지표를 모두 통과했고 최대 상대 변화는 0.018279849%, 16개 screen 상태 변화는 0개였습니다. 이는 두 SC 격자의 진단이며 전체 SC/XY/bulk/edge/contact 수렴을 뜻하지 않습니다.

XY 1.25 mm에서는 목표 mean/P10 4.022653821/3.610932913, 표층 P95 24.968443398, 전체 비표적 P95 23.245041565 V/m입니다. fine 0.625 mm와 비교해 접촉 정상 J_RMS_P95가 9.5310254%, SC 손실이 5.7515280%, 접촉 손실이 5.9560392% 낮아 각각 2% 진단 기준을 넘었습니다. raw와 fixed-fine skin8의 동일 세 항목, 총 6/20 실패입니다. 상태 변화가 0/16이어도 XY 민감도는 실패이며 과거 세 파형의 XY 실패도 해소되지 않았습니다. 모든 기저의 native 방정식 5개 gate 통과와 격자 정확도는 별개입니다.

세 격자 모두 목표 2개는 기준 mean/P10=4.061848942/3.645735739 V/m에 못 미치고, 비표적 6개만 통과해 6/8·미채택입니다. 저장된 fine 방향 상한 mean/P10=4.013348657/3.596625406도 기준의 2074 방향 하한보다 낮습니다. 이 고정 native 모델에서 평가 방향 수만 늘려 목표 미달을 해소할 수 없다는 조건부 근거이며, 정식 구간 증명·격자 수렴·모든 배치의 물리적 불가능성은 아닙니다.

각 mesh에서 새로 전류·전력·피부 부담을 맞추지 않았습니다. 5개 모드 이름은 원래 fine 비교를 가리키는 식별자이며 같은 fine 진폭을 복사했습니다. actual 새 전류·전력·8개 cap 비율을 보고합니다. SC4/XY의 고정 skin8 조건은 원래 cap 이내이지만 각각 최대 cap 비율이 0.999967723/0.942782356으로 달라 동일 부담이라고 주장하지 않습니다. 실제 native ROI 부피도 유지했고 coarse 부피를 fine 또는 해석적 원통 부피로 강제 재정규화하지 않았습니다.

D50 mm·층 0.1/5/5/15 mm·윗면·15 mm 정방형 225 mm²×4/총900·실제 출력2/common GND/50Ω·다른 주파수 0V through50Ω·PBS 접촉·bulk14/14/40은 같습니다. SC4 설정은 SC cell2→4만, coarse는 h.625→1.25 및 같은 물리 패드의 mask 표현만 바뀝니다. 전체 ROI 2074 지표·5모드·signed power·피부/접촉 부담과 각 40개 nativeφ 프로브를 실제 재계산했습니다. 새 파생 scalar NPZ만 미생성했고 원시 기저·정확 계수/진폭·ROI 가중치·코드 SHA의 재구성 recipe를 보존했습니다. 새 지도나 등록된 scalar export CLI·독립 export 재현 검증을 제공했다고 표시하지 않습니다.

다음 필수 수치 질문은 더 촘촘한 XY 계산입니다. 기존 800000셀/Java nx120 한도 안에서 h=50/120≈0.4167 mm, 791280셀을 검토할 수 있지만 새 설정과 실행은 아직 등록하지 않았습니다. 보수적 native 저장 상한 474768000B에 post reserve128MiB와 원래 디스크 여유2GiB를 포함하면 2756469376B가 필요합니다. 실제 여유는 최종 전용 preflight에서 갱신합니다. h.3125 mm는 별도로 800k 셀과 nx120 한도를 초과하므로 그 한도를 자동으로 늘리지 않습니다. 현재 새 finer native는 저장 공간 gate가 차단합니다. 남은 시간 예산 소진과 혼동하지 않습니다.

저장된 C1 단일 전극쌍 자료로 최신 fine 후보의 RMS 비교를 갱신하는 작은 JSON 배치를 준비 중입니다. C1은 귀환 포함 2패드/450 mm²/1출력이고 TIS는 4패드/900 mm²/2출력이므로 footprint 차이를 유지합니다. 새 C1 결과가 완료됐다고 아직 주장하지 않습니다. ETA5001 부하·finite tip port·스코프 실제 설정·PBS 피부 전이·COMSOL5.3a/5.3.1.201 실행·독립 영구 raw backup·실험/활성화/안전은 미검증입니다. 예산13800초/CPU1/RSS3GiB/디스크2GiB를 유지하고 설치·삭제·예산 확대·main 병합·무기한 daemon은 없습니다.

[4행 격자 GUI](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/CLOUD_ORIGINAL_MESH_SENSITIVITY_RESULTS_20261021.html), [보고서](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/ORIGINAL_MESH_SENSITIVITY_RESULTS_20261021.md), [실제 계산 summary](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/cloud-original-mesh-sensitivity-20261021T223000Z/summary.json), [조건부 방향 상한 기록](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/cloud-original-drive-refinement-context-20261021T222000Z/saved-target-direction-bound-disposition.json).
