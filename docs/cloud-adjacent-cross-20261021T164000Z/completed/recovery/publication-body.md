4개 physical pad의 cross 배선 대조를 계산·감사·선별까지 완료한 뒤 게시합니다. 원래 four-square/opposite, cached square/adjacent, cached balanced-cross/opposite를 재사용하고 NEW balancedcross225-adjacent-sources-xy80 한 조건만 새8RHS로 계산했습니다. 동일900mm²/4pads/2independent outputs/commonGND/50Ω, 상면·D50·층.1/5/5/15mm와 기존3000/3030+9000/9090square_3h, fine0.625mm/SC2/bulk14,14,40을 유지했습니다. 새로운 native mask는 기존 cross의 physical pad ID만 바꾸며 접촉 셀 면적·좌표·형상은 그대로입니다.

완료 volume.json의4행과 screen.json의 NEWcase8개 기준을 함께 보존합니다. 기준은 항상 원래 four-square이며 fixed voltage/current/power/skin8 등5정규화는 별개입니다. 기존3대조의 PDE를 반복하지 않았고, 이 결과로 후보 채택·전체SC/XY/bulk/edge/contact수렴·실험/안전/활성화를 주장하지 않습니다. Native40phi 프로브는5mmtipgap 무부하 예측이며 실제ETA5001 입력부하 검증은 별도입니다.

이번 선택 근거는 완료된 grouped-gap audit입니다. 동일 fine4square 부담에서 coarse순위16/8/4/12가 fine4/8/12/16으로 바뀌었고 모두 목표mean/P10을 실패했습니다. Coarse8/16은 same-node 패드가44개의tissuefaces를 공유했으며 fine0으로 달라졌습니다. 실제면적·물리topology가보존됐어도 이것을 gap/edge수렴으로 해석할 수 없습니다. 상세JSON/보고서는 GROUPED_GAP_DIAGNOSTIC_20261021에 보존했습니다. 유도현2의6319669306/6320375305 원문·채택과 누락 정정은 FEEDBACK_DISPOSITION_CORRECTION_20261021에 연결했고, 상세진단의 독립peerreview는 별도입니다.

원래 큐/실패/478패키지 원본과 raw native files를 보존합니다. 기존13800초 승인예산 안의 단일1500초 유한 큐이며 각600초 native상한/CPU1/RSS3GiB/저장여유2GiB를 유지합니다. 완료후 root가 실제 제한항과8개 판정·피드백으로 다음 유한 질문을 고릅니다. 시간·유료자원 확대나 main병합은 하지 않았습니다.
