최신 회전 TIS와 단일 자극 전극쌍의12개 RMS 매칭을 계산했습니다. 실제 source-return2패드·출력1개·3000Hz sine의 C1 기준을 재검증하고, 회전square/sine/coherent-r1p090 각각 raw/피부8cap에 대해 중심20mm fieldRMS와 목표ROI 에너지RMS를 별도로 맞췄습니다. ROIenergyRMS는 sqrt(부피가중 E_RMS² 평균)이며 meanE_RMS가 아닙니다.

[완료 summary](https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/blob/codex/task1-cloud-restart-20261020/docs/cloud-rotation-coherent-single-pair-20261021T183500Z/summary.json)에 각target의 필요sourceVpp/current/skinJ/contactV/loss/power와40개 scaled nativephi 무부하 probe를 저장했습니다. 원회전 geometry/source/normalization/candidateID와 소스·설정 해시를 유지합니다. C1은225mm²패드2개·총450mm², TIS는281.25/281.25/168.75/168.75mm²4패드·총900mm²로footprint가 다릅니다.

같은 fieldRMS는 같은 TIS 변조·피부부담·전류/전력·생리학적 활성화·인체안전을 뜻하지 않습니다. 원래 C1 비교·원시파일을 보존하고 새PDE0/참조장 재합성0으로 계산했습니다. 후보는 미채택이며 COMSOL/ETA부하/격자·접촉수렴/실험검증 상태를 승격하지 않았습니다. 기존13800초 예산 안의 유한 계산·피드백 GET·게시를 완료했습니다. 다음은 사전검토 중인 귀환패드 접선이동1조건입니다.
