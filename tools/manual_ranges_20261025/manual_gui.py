"""Pure manual-range migration; preserve every old packed scientific data byte."""
import base64,hashlib,html,re
import manual_ui,manual_legacy,manual_paper

def once(text,before,after):
    if text.count(before)!=1:raise ValueError('Unexpected reviewed GUI anchor: '+before[:90])
    return text.replace(before,after,1)

def render(base_html,payload):
    proof=payload['manual_range_proof']
    if proof.get('new_PDE')!=0 or not proof.get('scientific_data_unchanged'):raise ValueError('Display-only source evidence required')
    if 'id="manual-range-controls"'in base_html:raise ValueError('Already manual GUI cannot be migrated again')
    scripts=re.findall(r'<script>(.*?)</script>',base_html,re.S)
    if len(scripts)!=4:raise ValueError('Exactly four reviewed fixed-GUI executable scripts required')
    changed=[manual_ui.SCRIPT,manual_legacy.patch_original(scripts[1]),manual_legacy.patch_vectors(scripts[2]),manual_paper.patch_paper(scripts[3])]
    result=base_html
    for before,after in zip(scripts,changed):result=once(result,'<script>'+before+'</script>','<script>'+after+'</script>')
    oldnotice=re.search(r'<section id="fixed-scale-notice".*?</section>',result,re.S)
    if oldnotice is None:raise ValueError('Old fixed policy notice required')
    stamp='<p class="manual-source" style="font-size:10px;overflow-wrap:anywhere">화면 소스 commit '+html.escape(payload.get('display_source_commit','미제공'))+' · 기존 계산값/Float64 통계 보존 · 표시 잘림 개수는 native 단면 표본 수이며 부피 통계가 아닙니다.</p>'
    result=result[:oldnotice.start()]+manual_ui.SECTION+stamp+result[oldnotice.end():]
    result=once(result,'</style>',manual_ui.CSS+'\nlabel[for="range"],.legends .gradient,#field-shape .shape-legend .shape-color,#shape-ticks,.paper-colorbox .paper-bar,.paper-colorbox .paper-ticks{display:none}\n</style>')
    result=once(result,'TIS와 C1, 표층과 목표 위치의 모든 파형은 같은 고정 ±전기장 상한을 사용합니다. 방향·구동·시간 창 변경으로 y축이 바뀌지 않습니다.',
        '각 파형의 X시간·Y전기장 최소/최대값을 직접 지정할 수 있습니다. 공통 적용 또는 개별 설정을 선택하며, 입력한 시간 범위에서 실제 복소 합성파를 다시 그립니다. 변수 선택은 사용자가 적용한 눈금을 초기화하지 않습니다.')
    result=once(result,'Carrier RMS·변조·순간 전기장 지도와 선 프로파일은 모두 같은 고정 V/m 범위를 사용합니다. 물리량의 정의는 각각 유지하며 선택에 따른 자동 조정은 없습니다.',
        'Carrier RMS·변조·순간 전기장 지도와 선 프로파일은 공통 기본값 또는 개별 수동 범위를 사용합니다. 각 그래프 아래 눈금 패널에서 최소/최대값을 바꾸고 범위 밖 개수를 확인할 수 있습니다. 물리량의 정의와 원래 수치는 유지합니다.')
    result=once(result,'log1p 색 변환은 log(1 + 값/(1 V/m))이며 tick은 원 V/m입니다.',
        'log1p 색 변환은 선택한 색 최소값을 뺀 값에 적용하며 tick과 hover는 원 단위 V/m입니다.')
    result=once(result,'전기장과 접촉 전류밀도 색 범위는 전체 지원 조건을 포괄하는 사전 고정 상한을 사용하며 선택에 따라 자동 조정하지 않습니다.',
        '전기장과 접촉 전류밀도의 표시 범위는 공통 설정 또는 각 그래프에서 직접 지정합니다. 사용자가 적용한 눈금은 변수 선택으로 초기화되지 않습니다.')
    result=once(result,'모든 지원 조건에서 같은 고정 전기장 범위를 사용하므로 표층 최대가 크면 깊은 영역의 색 차이가 작게 보일 수 있습니다. 시간·단면·주파수·구동 조건을 바꿔도 범위와 화살표 크기 분모는 자동 변경하지 않습니다.',
        '표시 범위는 각 그래프에서 직접 조절할 수 있습니다. 좁은 색 범위 밖의 값은 잘림 개수로 알리고 원래 hover 수치를 유지합니다. 화살표의 길이 표시와 단면 밖 성분을 실제 전기장의 변조 또는 활성화로 해석하지 않습니다.')
    hashes=["'sha256-"+base64.b64encode(hashlib.sha256(s.encode()).digest()).decode()+"'"for s in changed]
    csp=re.search(r'script-src ([^;\"]+)',result)
    if csp is None:raise ValueError('Existing strict CSP required')
    result=result[:csp.start()]+'script-src '+' '.join(hashes)+result[csp.end():]
    pattern=r'<script\s+[^>]*type="(?:application/octet-stream|application/json)"[^>]*>.*?</script>'
    if re.findall(pattern,base_html,re.S)!=re.findall(pattern,result,re.S):raise ValueError('Original numerical payload or reference contract changed')
    return result
