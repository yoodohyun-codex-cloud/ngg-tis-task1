SC2→SC4 단일축 민감도 계산과 후처리를 완료했습니다. 실제 native117.746초(1PDE/8RHS), 선택후보 후처리14.641초(새PDE0)이며, 두께0.1mm·동일rounded mask/총900mm²/XY·bulk·물성·접촉·2출력/commonGND/50Ω를 고정했습니다. 원래SC2 실제복소계수와5진폭을 그대로 재사용했고 sourceVpp를 다시 정규화하지 않았습니다.

같은SC2 skin8 진폭에서 목표mean/P10=4.064792819/3.646963316 V/m, 표층P95=25.370377983, 전체비표적P95=23.648396398입니다. SC2의4.064779348/3.646952952,25.369751226,23.648628083와 가깝습니다. 사전등록 raw와기존skin8의 mean/P10 1%,비표적P95·J95·손실2%,8screen 상태변화0을 모두 통과했습니다. 점검지표 최대상대변화는0.021918%이며 모든 판정은 유지됐습니다. 이 결과는 두단계SC 민감도만 지지하고 전체SC/XY/bulk/edge/contact 수렴·활성화·안전·실험완료가 아닙니다. 목표는 통과하지만 두P95는 여전히 실패해6/8,후보는 미채택입니다.

SC4에서 원래SC2상수로 다시맞춘 보조skin8은mean/P10=4.064839891/3.647005549 V/m이며 주비교인고정SC2진폭과 분리했습니다. 고정SC2진폭행에 전류·전력·부담이 SC4에서도 같은것처럼 표시하지 않습니다. 40개 nativeφ 십자프로브는5/10/15/20mm·중심/±5X/±5Y·X/Y·팁간격5mm의무부하예측이고 ETA5001부하 검증이 아닙니다. carrierRMS/기본변조/nativeVpp·signed주파수별출력전력·GNDnet/localJ를 구분했습니다.

첫큐는native완료 후 root가SC2baseline을SC4 same-grid audit에 넘겨 guard에서 중단됐습니다. 원실패·로그를 보존했고, 기존squareSC4로 감사만새출력에복구했습니다(새PDE0). SC4square는감사전용대조군이며 과학적후처리의8cap/current/power/cutoff는원래SC2값으로고정했습니다. 이 복구를 새로운수치수렴검증으로 올리지 않습니다.

다음 root선택은 동일SC4물리형상과 실제선택구동을 고정한명목PBS specific complexZ0.5배/2배 두조건입니다. 원Rs차감/면적변환이완료된 specificZ에 배율만 적용하며 새피부측정으로 해석하지 않습니다. 아직새접촉basis실행전이며 별도등록·실제시작을 연결합니다. 유도현2에게 실제결과와SC4정의를6324805145로 검토요청했고 동의를 추정하지 않습니다. 기존13800초/CPU1/RSS3GiB/여유2GiB 안에서만 유한실행합니다. 원시Eφ8개는로컬보존,compact snapshot의38파일14,509,413B와SHA를게시하고독립영구rawbackup은미검증입니다. COMSOL5.3a5.3.1.201/실제피부접촉/하드웨어흡수·동기화/ETA부하/실험·활성화검증은보류,설치·삭제·예산확대·main병합없습니다.

[SC4 실제 결과](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/cloud-rounded-sc4-sensitivity-20261021T204000Z/summary.json), [첫감사 실패와복구](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/cloud-rounded-sc4-context-20261021T204000Z/audit-failure-disposition.json), [최신 연구 인덱스](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/CURRENT_RESEARCH_INDEX_20261021.md)
