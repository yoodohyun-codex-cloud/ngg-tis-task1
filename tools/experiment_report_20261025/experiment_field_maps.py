"""Pure insertion of native XZ TIS maps; no IO or numerical run on import.

The registered parent supplies already verified native scalar cell arrays. This
adapter never infers fields from summaries, interpolates fields, or changes the
original experiment summary. Parent owns rendering/browser tests/publication.
"""
import json,math,re,hashlib,base64


def apply(document,payload):
    if 'experiment-field-map-data' in document:raise ValueError('Native experiment maps already inserted')
    if not isinstance(payload,dict)or not isinstance(payload.get('cells'),list)or not payload['cells']:
        raise ValueError('Actual shared native cells required')
    cases=payload.get('cases');cells=payload['cells']
    if not isinstance(cases,list)or len(cases)!=3:raise ValueError('Exactly three native/same-sine comparison maps required')
    for key in ('slice_y_mm','dx_mm'):
        if type(payload.get(key))not in(int,float)or not math.isfinite(payload[key]):raise ValueError('Finite native coordinate metadata required')
    if payload['dx_mm']<=0:raise ValueError('Positive actual native XY cell width required')
    for cell in cells:
        if not isinstance(cell,dict)or any(type(cell.get(k))not in(int,float)or not math.isfinite(cell[k])for k in('x','z','dz'))or cell['dz']<=0:
            raise ValueError('Finite cell centres and physical z widths required')
    for case in cases:
        if not isinstance(case,dict)or not isinstance(case.get('id'),str)or not isinstance(case.get('label'),str):raise ValueError('Named actual comparison cases required')
        values=case.get('values')
        if not isinstance(values,list)or len(values)!=len(cells)or any(type(v)not in(int,float)or not math.isfinite(v)for v in values):raise ValueError('Finite matching raw native scalar arrays required')
        maximum=case.get('global_max')
        if type(maximum)not in(int,float)or not math.isfinite(maximum)or maximum<0:raise ValueError('Actual full-volume global maximum required')
    encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
    if document.count('<main>')!=1 or document.count('</html>')!=1:raise ValueError('Expected standalone experiment view')
    result=document.replace('<main>','<main>'+SECTION,1)
    result=result.replace('</style>',CSS+'\n</style>',1)
    insertion='<script id="experiment-field-map-data" type="application/json">'+encoded+'</script><script>'+SCRIPT+'</script>'
    result=result.replace('</html>',insertion+'</html>',1)
    # The supplied original presently has no CSP. If a CSP is added by the
    # parent, admit only this exact new script alongside its existing hashes.
    if 'Content-Security-Policy'in result:
        digest=base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
        result,count=re.subn(r"(script-src\s+)([^;\"]+)",lambda m:m.group(1)+m.group(2)+" 'sha256-"+digest+"'",result,count=1)
        if count!=1:raise ValueError('Existing CSP must explicitly allow the exact native map script')
    return result


CSS='''
.emap-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.emap-panel{min-width:0;border:1px solid #d8e2e9;border-radius:7px;padding:10px;background:#fff}.emap-panel h3{font-size:14px;margin:0 0 6px;overflow-wrap:anywhere}.emap-panel canvas{width:100%;height:auto;display:block}.emap-info{font-size:11px;line-height:1.5;overflow-wrap:anywhere;min-height:4.5em}.emap-controls{display:flex;flex-wrap:wrap;gap:9px;align-items:end;margin-bottom:9px}.emap-controls input{width:105px;max-width:100%}.emap-buttons{display:flex;flex-wrap:wrap;gap:8px;align-items:end}.emap-error{color:#a03928;min-height:1.5em;font-size:12px}.emap-hover{padding:8px;background:#edf4f8;border-radius:5px;overflow-wrap:anywhere;font-size:12px}.emap-note{font-size:12px;color:#536b7e;line-height:1.6}@media(max-width:1000px){.emap-grid{grid-template-columns:1fr}}
'''

SECTION='''<section id="native-field-maps"><h2>세 정현파 조건의 실제 전기장 분포 · 같은 눈금</h2><p class="emap-note">기본파 최대 방향 TIS 변조를 실제 native 셀 값으로 표시합니다. 절단면은 요청 y=0에 가장 가까운 실제 y 좌표이며 아래에 명시합니다. 3kHz 두 조건은 기존 복소 기저를 정현파로 합성한 결과이고, 2kHz 조건만 새 PDE입니다. 각 지도에 표시하는 값과 통계표의 전역 값·부피 통계·검증 상태를 구분합니다.</p><div id="emap-controls" class="emap-controls"></div><div class="emap-buttons"><button id="emap-reset" type="button">공통 초기 눈금 복원</button><button id="emap-save" type="button">지도 눈금 JSON 저장</button><label>지도 눈금 JSON 불러오기<input id="emap-load" type="file" accept=".json,application/json"></label></div><p id="emap-error" class="emap-error" role="alert"></p><p id="emap-scope" class="emap-note"></p><div id="emap-grid" class="emap-grid"></div><p id="emap-hover" class="emap-hover">지도 셀 위에 포인터를 올리면 실제 x/y/z 좌표와 원시 변조값을 확인할 수 있습니다.</p><p class="emap-note">XY 두께와 Z 셀 높이는 제공된 실제 격자입니다. 셀 사이 보간·평활화·색 재분포를 하지 않습니다. 초기 색 상한은 세 조건의 전체 부피 최대를 함께 포함합니다. 수동 범위 밖 값은 표시만 포화되며 원시 값과 통계는 바뀌지 않습니다. 피부·층 경계 hotspot이나 색상만으로 깊이 집중·활성화·안전을 판정하지 않습니다.</p></section>'''

SCRIPT=r'''(()=>{'use strict';
const D=JSON.parse(document.getElementById('experiment-field-map-data').textContent),$=id=>document.getElementById(id),fmt=x=>Number.isFinite(x)?Number(x).toPrecision(6):'미제공',key='task1-experiment-native-map-ranges-v1';
const defaults={xmin:-25,xmax:25,zmin:0,zmax:25.1,cmin:0,cmax:Math.max(1e-12,...D.cases.map(c=>c.global_max))};let ranges={...defaults};
function valid(v){return Object.keys(defaults).every(k=>typeof v[k]==='number'&&Number.isFinite(v[k]))&&v.xmax>v.xmin&&v.zmax>v.zmin&&v.cmax>v.cmin;}
try{const stored=JSON.parse(localStorage.getItem(key)||'null');if(stored&&valid(stored))ranges={...stored};}catch(e){}
const inputs={},canvases=[],infos=[],clips=[];
for(const[field,label]of[['xmin','X 최소 mm'],['xmax','X 최대 mm'],['zmin','깊이 Z 최소 mm'],['zmax','깊이 Z 최대 mm'],['cmin','공통 색 최소 V/m'],['cmax','공통 색 최대 V/m']]){const l=document.createElement('label');l.textContent=label;const input=document.createElement('input');input.type='number';input.step='any';input.value=String(ranges[field]);input.dataset.emapRange=field;input.onchange=()=>setRanges({[field]:Number(input.value)});l.append(input);$('emap-controls').append(l);inputs[field]=input;}
for(const scenario of D.cases){const panel=document.createElement('article');panel.className='emap-panel';const title=document.createElement('h3');title.textContent=scenario.label;const canvas=document.createElement('canvas');canvas.width=600;canvas.height=500;canvas.dataset.scenario=scenario.id;const info=document.createElement('p');info.className='emap-info';panel.append(title,canvas,info);$('emap-grid').append(panel);canvases.push(canvas);infos.push(info);}
function save(){try{localStorage.setItem(key,JSON.stringify(ranges));}catch(e){}}
function setRanges(next){const candidate={...ranges,...next};if(!valid(candidate)){$('emap-error').textContent='최대값은 최소값보다 커야 하며 모든 값은 유한한 숫자여야 합니다. 변경을 적용하지 않았습니다.';for(const k of Object.keys(defaults))inputs[k].value=String(ranges[k]);return false;}ranges=candidate;for(const k of Object.keys(defaults))inputs[k].value=String(ranges[k]);$('emap-error').textContent='';save();draw();return true;}
function colour(t){t=Math.max(0,Math.min(1,t));const stops=[[20,25,80],[37,99,170],[37,181,167],[217,223,84],[245,115,45],[153,15,41]],z=t*(stops.length-1),i=Math.min(stops.length-2,Math.floor(z)),f=z-i;return'rgb('+stops[i].map((v,j)=>Math.round(v+(stops[i+1][j]-v)*f)).join(',')+')';}
function draw(){clips.length=0;$('emap-scope').textContent='실제 XZ 절단면 y='+fmt(D.slice_y_mm)+' mm · +z는 표면에서 아래 방향 · native XY 셀 폭 '+fmt(D.dx_mm)+' mm · 세 조건 공통 색 '+fmt(ranges.cmin)+'–'+fmt(ranges.cmax)+' V/m';D.cases.forEach((scenario,index)=>{const canvas=canvases[index],ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=63,T=24,R=100,B=65,pw=W-L-R,ph=H-T-B,X=x=>L+(x-ranges.xmin)/(ranges.xmax-ranges.xmin)*pw,Z=z=>T+(z-ranges.zmin)/(ranges.zmax-ranges.zmin)*ph;ctx.clearRect(0,0,W,H);ctx.fillStyle='#f6f8fa';ctx.fillRect(0,0,W,H);ctx.save();ctx.beginPath();ctx.rect(L,T,pw,ph);ctx.clip();let below=0,above=0,rawMin=Infinity,rawMax=-Infinity;D.cells.forEach((cell,i)=>{const v=scenario.values[i];rawMin=Math.min(rawMin,v);rawMax=Math.max(rawMax,v);if(v<ranges.cmin)below++;if(v>ranges.cmax)above++;ctx.fillStyle=colour((v-ranges.cmin)/(ranges.cmax-ranges.cmin));const x0=X(cell.x-D.dx_mm/2),x1=X(cell.x+D.dx_mm/2),z0=Z(cell.z-cell.dz/2),z1=Z(cell.z+cell.dz/2);ctx.fillRect(x0,z0,x1-x0,z1-z0);});ctx.setLineDash([5,4]);ctx.lineWidth=1;ctx.strokeStyle='rgba(255,255,255,.85)';for(const depth of[.1,5.1,10.1]){ctx.beginPath();ctx.moveTo(L,Z(depth));ctx.lineTo(L+pw,Z(depth));ctx.stroke();}if(Math.abs(D.slice_y_mm)<=5){const half=Math.sqrt(Math.max(0,25-D.slice_y_mm*D.slice_y_mm));ctx.strokeStyle='#fff';ctx.lineWidth=2;ctx.strokeRect(X(-half),Z(15),X(half)-X(-half),Z(20)-Z(15));}ctx.restore();ctx.setLineDash([]);ctx.strokeStyle='#263b4b';ctx.lineWidth=1;ctx.strokeRect(L,T,pw,ph);ctx.font='12px system-ui';ctx.fillStyle='#263b4b';ctx.textAlign='center';for(let k=0;k<=5;k++){const x=ranges.xmin+(ranges.xmax-ranges.xmin)*k/5,z=ranges.zmin+(ranges.zmax-ranges.zmin)*k/5;ctx.fillText(Number(x).toPrecision(3),X(x),H-B+20);ctx.textAlign='right';ctx.fillText(Number(z).toPrecision(3),L-7,Z(z)+4);ctx.textAlign='center';}ctx.fillText('x [mm]',L+pw/2,H-12);ctx.save();ctx.translate(14,T+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText('+z depth [mm]',0,0);ctx.restore();for(let p=0;p<ph;p++){ctx.fillStyle=colour(1-p/ph);ctx.fillRect(L+pw+17,T+p,14,1);}ctx.fillStyle='#263b4b';ctx.textAlign='left';ctx.fillText(fmt(ranges.cmax),L+pw+35,T+8);ctx.fillText(fmt(ranges.cmin),L+pw+35,T+ph);infos[index].textContent='실제 native 셀 '+D.cells.length+'개 · 절단면 원시 min/max '+fmt(rawMin)+' / '+fmt(rawMax)+' V/m · 전체 부피 최대 '+fmt(scenario.global_max)+' V/m · 색 하한 미만 '+below+' / 상한 초과 '+above+' 셀 (선택 절단면 전체)';canvas.dataset.cmin=String(ranges.cmin);canvas.dataset.cmax=String(ranges.cmax);canvas.dataset.clippedLow=String(below);canvas.dataset.clippedHigh=String(above);clips.push({id:scenario.id,below,above,rawMin,rawMax,globalMax:scenario.global_max});canvas.onpointermove=event=>{const box=canvas.getBoundingClientRect(),px=(event.clientX-box.left)/box.width*W,pz=(event.clientY-box.top)/box.height*H;if(px<L||px>L+pw||pz<T||pz>T+ph)return;const x=ranges.xmin+(px-L)/pw*(ranges.xmax-ranges.xmin),z=ranges.zmin+(pz-T)/ph*(ranges.zmax-ranges.zmin);let found=-1;for(let i=0;i<D.cells.length;i++){const c=D.cells[i];if(x>=c.x-D.dx_mm/2&&x<c.x+D.dx_mm/2&&z>=c.z-c.dz/2&&z<c.z+c.dz/2){found=i;break;}}if(found<0){$('emap-hover').textContent=scenario.label+' · 이 위치는 제공된 native 셀 밖입니다.';return;}const c=D.cells[found];$('emap-hover').textContent=scenario.label+' · 원시 native centre x='+fmt(c.x)+', y='+fmt(D.slice_y_mm)+', z='+fmt(c.z)+' mm · 최대 방향 TIS 변조 '+fmt(scenario.values[found])+' V/m · 색상 클리핑 전 값';};});}
$('emap-reset').onclick=()=>setRanges({...defaults});$('emap-save').onclick=()=>{const blob=new Blob([JSON.stringify({schema:key,ranges},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='experiment-field-map-ranges.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};$('emap-load').onchange=async()=>{try{const file=$('emap-load').files[0];if(!file)return;if(file.size>16384)throw Error('작은 지도 눈금 설정 파일만 허용합니다.');const data=JSON.parse(await file.text());if(data.schema!==key)throw Error('눈금 설정 버전이 다릅니다.');setRanges(data.ranges);}catch(e){$('emap-error').textContent='설정을 불러오지 않았습니다: '+e.message;}};
window.task1ExperimentFieldMaps=Object.freeze({getRanges:()=>({...ranges}),setRanges,reset:()=>setRanges({...defaults}),getClipping:()=>clips.map(x=>({...x})),sourceScope:()=>({slice_y_mm:D.slice_y_mm,dx_mm:D.dx_mm,cases:D.cases.map(c=>({id:c.id,label:c.label,global_max:c.global_max})),native_cells:D.cells.length})});draw();
})();'''
