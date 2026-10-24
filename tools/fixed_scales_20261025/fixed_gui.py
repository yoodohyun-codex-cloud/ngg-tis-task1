"""Pure deterministic GUI scale migration; original packed science stays unchanged."""
import base64,hashlib,html,json,re
import fixed_legacy

def once(text,before,after):return fixed_legacy.once(text,before,after)

def function(script,name,change):
    start=script.index('function '+name+'(')
    stop=script.find('\nfunction ',start+1)
    if stop<0:raise ValueError('A following function anchor is required: '+name)
    original=script[start:stop];modified=change(original)
    return script[:start]+modified+script[stop:]

def patch_paper(script):
    script=once(script,"'use strict';","'use strict';\nconst TASK1_LOCKED_E=window.task1FixedScaleContract.electric_field.upper_V_m;\nif(!(TASK1_LOCKED_E>0))throw Error('Fixed field contract required');")
    script=once(script,"const carrierMax=Math.max(all.TIS.max.rms3000,all.TIS.max.rms3030,all.C1.max.rms3000,all.C1.max.rms3030);", "const carrierMax=TASK1_LOCKED_E;")
    script=once(script,"const max=metric==='am'?Math.max(all.TIS.max.am,all.C1.max.am):carrierMax;", "const max=TASK1_LOCKED_E;")
    script=once(script,"ymax=max>0?max*1.04:1;", "ymax=TASK1_LOCKED_E;")
    script=once(script,"+(metric==='am'?' · 두 경우 공통 / clipping 없음':' · 두 주파수·두 경우 공통 / clipping 없음')", "+' · 전체 지원 조건 고정 / 자동 조정 없음'")
    def profile(block):
        block=once(block,"const{g,w,h}=cv('paper-profile-'", "const{el,g,w,h}=cv('paper-profile-'")
        block=once(block,"limit=max>0?max:1,tr=setupAxes(g,w,h,profile.x[0],profile.x.at(-1),limit,0,", "limit=TASK1_LOCKED_E,tr=setupAxes(g,w,h,profile.axis==='z'?0:-25,profile.axis==='z'?25.1:25,limit,0,")
        block=once(block,"g.fillStyle='white';", "el.dataset.vmin='0';el.dataset.vmax=String(limit);el.dataset.coordinateMin=String(tr.u0);el.dataset.coordinateMax=String(tr.u1);el.dataset.scaleMode='fixed_all_conditions';g.fillStyle='white';")
        block=once(block,"if(v>=profile.x[0]&&v<=profile.x.at(-1))", "if(v>=tr.u0&&v<=tr.u1)")
        return block
    script=function(script,'drawProfile',profile)
    def wave(block):
        block=once(block,"const{g,w,h}=cv('paper-wave-'", "const{el,g,w,h}=cv('paper-wave-'")
        return once(block,"g.fillStyle='white';", "el.dataset.vmin=String(-ymax);el.dataset.vmax=String(ymax);el.dataset.scaleMode='fixed_all_conditions';g.fillStyle='white';")
    script=function(script,'drawWave',wave)
    def map_(block):
        block=once(block,"const id='paper-map-'+c+'-'+m,{g,w,h}=cv(id)", "const id='paper-map-'+c+'-'+m,{el,g,w,h}=cv(id)")
        anchor="nu=p.u_mm.length,nv=p.v_mm.length;"
        after=anchor+"el.dataset.vmin='0';el.dataset.vmax=String(max);el.dataset.scaleMode='fixed_all_conditions';el.dataset.axisOrientation=p.kind==='XY'?'y_up':'depth_down';if(p.kind==='XY'){const yy=tr.y;tr.y=v=>tr.pad.t+tr.height-(yy(v)-tr.pad.t);tr.up=true;}"
        block=once(block,anchor,after)
        block=once(block,"g.fillRect(tr.x(ue[i]),tr.y(ve[j]),Math.max(.2,tr.x(ue[i+1])-tr.x(ue[i])+.15),Math.max(.2,tr.y(ve[j+1])-tr.y(ve[j])+.15));", "g.fillRect(tr.x(ue[i]),Math.min(tr.y(ve[j]),tr.y(ve[j+1])),Math.max(.2,tr.x(ue[i+1])-tr.x(ue[i])+.15),Math.max(.2,Math.abs(tr.y(ve[j+1])-tr.y(ve[j]))+.15));")
        return block
    script=function(script,'drawMap',map_)
    script=once(script,"v=tr.v0+(e.clientY-r.top-tr.pad.t)/tr.height*(tr.v1-tr.v0);", "v=tr.v0+(tr.up?1-(e.clientY-r.top-tr.pad.t)/tr.height:(e.clientY-r.top-tr.pad.t)/tr.height)*(tr.v1-tr.v0);")
    script=once(script,"const expected=metric==='am'?Math.max(state.metrics.TIS.max.am,state.metrics.C1.max.am):Math.max(state.metrics.TIS.max.rms3000,state.metrics.TIS.max.rms3030,state.metrics.C1.max.rms3000,state.metrics.C1.max.rms3030);must(state.limits[metric]===expected,'Carrier panels must share the four-panel carrier maximum; AM shares its two-panel maximum');", "const expected=TASK1_LOCKED_E;must(state.limits[metric]===expected,'All electric-field maps must retain the registered fixed range');")
    return script

HELPER=r'''
'use strict';
(()=>{const contract=JSON.parse(document.getElementById('fixed-scale-contract').textContent);function freeze(o){if(o&&typeof o==='object'){for(const v of Object.values(o))freeze(v);Object.freeze(o);}return o;}
window.task1FixedScaleContract=freeze(contract);
const E=contract.electric_field.upper_V_m,J=contract.current_density.upper_A_m2;
function snapshot(){const ids=['TIS-field','C1-field','TIS-contact','C1-contact','shape-TIS','shape-C1',...['TIS','C1'].flatMap(c=>['rms3000','rms3030','am'].map(m=>'paper-map-'+c+'-'+m)),...['TIS','C1'].flatMap(c=>['surface','target'].map(p=>'paper-wave-'+c+'-'+p)),...['am','rms'].map(m=>'paper-profile-'+m)];return ids.map(id=>{const c=document.getElementById(id);if(!c)throw Error('Missing registered canvas '+id);return{id,min:Number(c.dataset.vmin),max:Number(c.dataset.vmax),scale_mode:c.dataset.scaleMode,axis_orientation:c.dataset.axisOrientation||null,coordinate_min:c.dataset.coordinateMin===undefined?null:Number(c.dataset.coordinateMin),coordinate_max:c.dataset.coordinateMax===undefined?null:Number(c.dataset.coordinateMax)};});}
function validateForTest(light=false){try{const rows=snapshot();for(const row of rows){const current=row.id.endsWith('-contact'),signed=row.id.startsWith('paper-wave-'),upper=current?J:E;const low=signed?-E:0;if(row.min!==low||row.max!==upper||row.scale_mode!=='fixed_all_conditions')throw Error('Fixed range changed at '+row.id);}
const paper=window.task1PaperFigure.getState(),shape=window.task1FieldShape.getState();if(Object.values(paper.common_maxima_V_m).some(v=>v!==E)||shape.common_max_V_m!==E)throw Error('Layer range differs');
for(const [k,v]of Object.entries(paper.profile_limits))if(v.display_maximum_V_m!==E)throw Error('Profile range differs '+k);
const range=document.getElementById('range');if(!range.disabled||range.options.length!==1)throw Error('Legacy automatic range remains');
const p=light?{passed:true,scope:'range_only'}:window.task1PaperFigure.validateForTest();if(!p.passed)throw Error(p.error);return{passed:true,canvas_count:rows.length,electric_field_upper_V_m:E,signed_waveform_range_V_m:[-E,E],current_density_upper_A_m2:J,automatic_rescaling:false,all_layers_fixed:true,paper_checks:p,canvases:rows};
}catch(e){return{passed:false,error:e.message};}}
window.task1FixedScales=Object.freeze({snapshot,validateForTest,contract});})();
'''

def render(base_html,payload):
    contract=payload['fixed_scale_contract']
    if contract['schema']!='task1-fixed-scale-contract-v1' or contract['automatic_rescaling'] is not False:raise ValueError('Immutable scale contract required')
    if 'id="fixed-scale-contract"'in base_html:raise ValueError('Do not replace an already fixed GUI')
    scripts=re.findall(r'<script>(.*?)</script>',base_html,re.S)
    if len(scripts)!=3:raise ValueError('Exactly three reviewed executable GUI layers required')
    transformed=[fixed_legacy.patch_original(scripts[0]),fixed_legacy.patch_vectors(scripts[1]),patch_paper(scripts[2])]
    result=base_html
    for before,after in zip(scripts,transformed):result=once(result,'<script>'+before+'</script>','<script>'+after+'</script>')
    result=fixed_legacy.patch_static(result)
    result=once(result,'실제 전극 배치와 측정 위치','실제 전극 배치와 계산 표본 위치')
    result=once(result,'각 위치에서 TIS와 C1의 파형 y축은 공통이며, 표층과 깊은 위치의 y축은 각각 따로 표시합니다.', 'TIS와 C1, 표층과 목표 위치의 모든 파형은 같은 고정 ±전기장 상한을 사용합니다. 방향·구동·시간 창 변경으로 y축이 바뀌지 않습니다.')
    result=once(result,'네 carrier RMS 지도는 주파수·경우 전체에서 하나의 공통 무클리핑 범위를 쓰고, envelope 변조깊이는 두 경우에 공통인 별도 범위를 씁니다.', 'Carrier RMS·변조·순간 전기장 지도와 선 프로파일은 모두 같은 고정 V/m 범위를 사용합니다. 물리량의 정의는 각각 유지하며 선택에 따른 자동 조정은 없습니다.')
    cjson=json.dumps(contract,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\u003c')
    block='<script id="fixed-scale-contract" type="application/json">'+cjson+'</script><script>'+HELPER+'</script>'
    result=once(result,'<body>','<body>'+block)
    notice='<section id="fixed-scale-notice" style="background:#e6f1f6;border:1px solid #8bb4c6;border-radius:10px;padding:14px;margin:0 0 18px;overflow-wrap:anywhere"><b>전체 조건 비교용 눈금 고정</b><p>전기장 지도·선 프로파일: 0–'+html.escape(str(contract['electric_field']['upper_V_m']))+' V/m · 모든 파형: ±'+html.escape(str(contract['electric_field']['upper_V_m']))+' V/m · 접촉 전류밀도: 0–'+html.escape(str(contract['current_density']['upper_A_m2']))+' A/m².</p><p>단면·깊이·방향·주파수·시간·구동·RMS 매칭을 바꿔도 눈금은 유지됩니다. 선형/log1p는 같은 고정 범위의 색 변환입니다. 전기장 전체 범위가 넓으므로 작은 깊이 값은 선형 그림에서 작게 보일 수 있습니다. XY는 +y 위쪽, 수직 단면은 +z 깊이 아래쪽입니다.</p></section>'
    result=once(result,'<main>','<main>'+notice)
    hashes=["'sha256-"+base64.b64encode(hashlib.sha256(s.encode()).digest()).decode()+"'"for s in [HELPER]+transformed]
    match=re.search(r'script-src ([^;\"]+)',result)
    if match is None:raise ValueError('Existing script CSP required')
    result=result[:match.start()]+'script-src '+' '.join(hashes)+result[match.end():]
    before_data=re.findall(r'<script\s+[^>]*type="(?:application/octet-stream|application/json)"[^>]*>.*?</script>',base_html,re.S)
    after_data=re.findall(r'<script\s+[^>]*type="(?:application/octet-stream|application/json)"[^>]*>.*?</script>',result,re.S)
    if before_data!=after_data[1:]:raise ValueError('Packed scientific data or prior proof JSON changed')
    return result
