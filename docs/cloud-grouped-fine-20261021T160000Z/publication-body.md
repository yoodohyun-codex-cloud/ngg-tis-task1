Grouped4/8/12/16 XY fine 유한 배치의 **실제 완료 조건을 확인한 후** 결과를 게시합니다.

고정D50층/상면/900mm²/2outputs/commonGND/50Ω에서 기존strip가족을h1.25→0.625mm로비교했습니다. 원래4square finebaseline은재사용했고별도4strip기하대조군과8/12/16의4PDE만계산했습니다. pad수와독립출력수는구분하며,패드수가늘면strip너비·그룹외곽도함께바뀌는점을보존합니다.

공개부피원표에는원래4square+fine4strip/8/12/16의5행,ROImean/P10/분포,표층·전체비표적P95/hotspot/고변조부피,전류·Jmax/J95·접촉전압·피부/접촉/총손실,5정규화와40nativeφ무부하프로브를저장했습니다. 기존고정8선별의pass/fail과실제native방정식값·한도도별도파일에있습니다. 성공/실패결론은그원표를근거로판단하며후보채택·전체SC/XY/bulk/edge/contact수렴·실험검증을주장하지않습니다.

새32RHS와각fullskin·metadata·부피·선별·피드백의완료출처를검사한뒤게시합니다. 기존13800초예산안의단일4200초큐이고각native조건600초/1CPU/heap2GiB/RSS3GiB/저장여유2GiB는유지했습니다. 무제한상주worker나추가예산을생성하지않았습니다. 완료후root는실제부담제한과coarse/fine차이·유도현2피드백을읽고다음유한진단을선정해야합니다. 선별pass는별도진단자격이며자동채택이아닙니다.
