8조건 coherent-drive scout의 실제 종료·원 입력SHA 불변을 확인한 뒤 결과를 게시합니다. 기존4square225mm²×4/출력2/commonGND/50Ω/동일D50층/상면 기저를 재사용했고 새PDE·추가독립출력·절연변경은0입니다. 3000/3030Hz 두fundamental을 두출력 모두에 위상결합하며 기존 square3h4선·exclusive-sine 대조와 별도분기입니다.

source waveform은 .5*c의1/30초 전체 Thevenin max−min 구간으로 계산했습니다. 각출력의Vpp upper를1V로정규화하고 lower/upper구간폭≤1µV를강제했습니다. tone별Vpp나RMS를전체Vpp로대체하지않았고정규화후unitary라고부르지않습니다. 각frequency의E/phi/J를먼저coherent합성하고c†Lc손실·출력별signedpower·공통GND전류보존·skinJ/contactV/손실·5정규화를계산했습니다. 음의출력전력이있으면그대로기록하며sink/compliance능력은미검증입니다.

원래4square4선의8개피부/접촉한도·cutoff·r≤5mm/depth15–20mm부피ROI를고정했습니다. condition.json마다목표mean/P10/CV/max·표층/비표적P95/고변조부피·전역위치·fixed/maxTIS·전체carrierRMS와고정8선별판정이있습니다. 원본4pad/8/12/16그룹결과는별도GUI에보존합니다. 40개nativephi5mmtipgap프로브와복소E합성파형도재계산했습니다. 실제ETA5001입력부하·하드웨어다중톤/위상동기/안전/활성화·전체SC/XY/bulk/edge/contact수렴은검증되지않았습니다.

source9e81df2의24합성테스트를통과한뒤기존13800초승인예산안에한개의900초큐로등록했습니다. Scout600초/조건60초/CPU1/RSS3GiB/free2GiB와실행잠금/PID/startticks/checkpoint/실패보존을유지합니다. 결과pass는별도수렴진단후보일뿐채택이아닙니다. 종료후root가실제제한·개선근거·피드백으로다음유한질문을고릅니다. 무기한daemon/자동재시도/추가예산/main병합은없습니다.
