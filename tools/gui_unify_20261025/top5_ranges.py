"""Pure Top5 manual-range adapter; scientific packed payload is byte-preserved.

No decode, read/write, browser, numerical run or test occurs on import. The sole
parent supplies the already-verified compact HTML, owns execution and publication.
"""
import re,hashlib,base64

def _function(script,name):
    pattern=r'function '+re.escape(name)+r'\([^\n]*'
    match=re.search(pattern,script)
    if not match:raise ValueError('Expected original Top5 function: '+name)
    return match.group(0)

def apply(document):
    if 'task1-top5-manual-ranges-v1' in document:raise ValueError('Manual ranges already applied; preserve version')
    scripts=list(re.finditer(r'<script([^>]*)>(.*?)</script>',document,re.S))
    executable=[x for x in scripts if 'function frame('in x.group(2)and'function field('in x.group(2)]
    if len(executable)!=1:raise ValueError('One verified Top5 renderer expected')
    match=executable[0];script=match.group(2)
    packed=[x.group(0)for x in scripts if re.search(r'\bid=["\']packed["\']',x.group(1))]
    if len(packed)!=1:raise ValueError('Original compact scientific payload required')
    before=packed[0]
    def change(name,new):
        nonlocal script
        original=_function(script,name)
        script=script.replace(original,new,1)
    change('color',"function color(v,max,min=0){if(!Number.isFinite(v))return'#e7edf2';const t=Math.max(0,Math.min(1,(v-min)/(max-min)))*5,i=Math.min(4,Math.floor(t)),f=t-i;return'rgb('+palette[i].map((x,k)=>Math.round(x+(palette[i+1][k]-x)*f)).join(',')+')';}")
    change('frame',"function frame(canvas,xe,ye,flipY){const[c,w,h]=canvasSetup(canvas),m={l:43,r:12,t:11,b:31},pw=w-m.l-m.r,ph=h-m.t-m.b,isField=canvas.classList.contains('field-map'),plane=isField?$('plane').value:'xy',x0=plane==='yz'?manual.yMin:manual.xMin,x1=plane==='yz'?manual.yMax:manual.xMax,y0=plane==='xy'?manual.yMin:manual.zMin,y1=plane==='xy'?manual.yMax:manual.zMax,X=x=>m.l+(x-x0)/(x1-x0)*pw,Y=y=>m.t+(flipY?(y-y0)/(y1-y0):(y1-y)/(y1-y0))*ph;c.save();c.beginPath();c.rect(m.l,m.t,pw,ph);c.clip();canvas.dataset.manualXMin=String(x0);canvas.dataset.manualXMax=String(x1);canvas.dataset.manualYMin=String(y0);canvas.dataset.manualYMax=String(y1);return{c,w,h,m,pw,ph,X,Y,xe,ye,flipY,x0,x1,y0,y1};}")
    change('axes',"function axes(f,xlabel,ylabel){const{c,X,Y,m,w,h,x0,x1,y0,y1}=f;c.restore();c.strokeStyle='#b6c5d2';c.lineWidth=.8;c.strokeRect(m.l,m.t,f.pw,f.ph);c.fillStyle='#536779';c.font='10px system-ui';c.textAlign='center';for(const x of[x0,(x0+x1)/2,x1])c.fillText(fmt(x,4),X(x),h-17);c.fillText(xlabel,m.l+f.pw/2,h-3);c.textAlign='right';for(const y of[y0,(y0+y1)/2,y1])c.fillText(fmt(y,4),m.l-4,Y(y)+3);c.save();c.translate(11,m.t+f.ph/2);c.rotate(-Math.PI/2);c.textAlign='center';c.fillText(ylabel,0,0);c.restore();}")
    rect=_function(script,'rectangles').replace('role=false,pads=[])','role=false,pads=[],minimum=0)').replace('color(v*scale,max)','color(v*scale,max,minimum)')
    change('rectangles',rect)
    hover=_function(script,'hover').replace('x=f.xe[0]+(px-f.m.l)/f.pw*(f.xe.at(-1)-f.xe[0])','x=f.x0+(px-f.m.l)/f.pw*(f.x1-f.x0)').replace("y=f.flipY?f.ye[0]+yy*(f.ye.at(-1)-f.ye[0]):f.ye.at(-1)-yy*(f.ye.at(-1)-f.ye[0])","y=f.flipY?f.y0+yy*(f.y1-f.y0):f.y1-yy*(f.y1-f.y0)")
    hover=hover.replace('if(i<0||j<0)', 'if(px<f.m.l||px>f.m.l+f.pw||py<f.m.t||py>f.m.t+f.ph||i<0||j<0)')
    change('hover',hover)
    field=_function(script,'field').replace('max=display.color_limits[mode][metric][range][1]','max=manual.eMax').replace("canvas.dataset.vmin='0'","canvas.dataset.vmin=String(manual.eMin)").replace('rectangles(f,values,max,scale);','setClipping(canvas,values,scale,manual.eMin,max);rectangles(f,values,max,scale,null,false,[],manual.eMin);')
    change('field',field)
    contact=_function(script,'contact').replace('max=display.contact_color_limits[mode][1]','max=manual.jMax').replace("canvas.dataset.vmin='0'","canvas.dataset.vmin=String(manual.jMin)").replace('rectangles(f,values,max,scale);','setClipping(canvas,values,scale,manual.jMin,max);rectangles(f,values,max,scale,null,false,[],manual.jMin);')
    change('contact',contact)
    burden=_function(script,'renderBurdens').replace('Math.min(150,ratio*100)/1.5','Math.min(manual.burdenMax,ratio)/manual.burdenMax*100')
    # The original source has a parenthesized percentage expression; keep the
    # numerical ratio and label, changing only its finite visual bar scale.
    change('renderBurdens',burden)
    update=_function(script,'update').replace('clim=display.color_limits[mode][metric][range],jc=display.contact_color_limits[mode]','clim=[manual.eMin,manual.eMax],jc=[manual.jMin,manual.jMax]')
    start="$('field-legend').textContent=";end=";$('contact-legend').textContent="
    a=update.index(start);b=update.index(end,a)
    update=update[:a]+"$('field-legend').textContent=`수동 공통 ${fmt(manual.eMin)}–${fmt(manual.eMax)} V/m · 배치·정규화·물리량 변경 후 유지 · 범위 밖 값은 표시 clipping만 적용`"+update[b:]
    update=update.replace('geometry(v.geo,data);field(v.main,row,data);contact(v.j,row,data);renderEvidence',"geometry(v.geo,data);field(v.main,row,data);contact(v.j,row,data);v.caption.textContent+=` · E 색 하한 미만 ${v.main.dataset.clippedLow} / 상한 초과 ${v.main.dataset.clippedHigh} 셀`;v.geometrynote.textContent+=` 접촉 J 색 하한 미만 ${v.j.dataset.clippedLow} / 상한 초과 ${v.j.dataset.clippedHigh} 셀. 부담 막대 축 0–${fmt(manual.burdenMax)}×.`;renderEvidence")
    change('update',update)
    anchor="function decode(s,kind)"
    if script.count(anchor)!=1:raise ValueError('Expected Top5 decode boundary')
    script=script.replace(anchor,MANUAL_SCRIPT+'\n'+anchor,1)
    old_tail="window.task1Top5=Object.freeze({render:update,catalog,display});update();"
    if script.count(old_tail)!=1:raise ValueError('Expected Top5 public renderer contract')
    script=script.replace(old_tail,"window.task1Top5=Object.freeze({render:update,catalog,display});window.task1Top5Manual=Object.freeze({getState:()=>({...manual}),setRanges:commitManual,reset:()=>commitManual({...manualDefaults}),getClipping:()=>Array.from(document.querySelectorAll('.field-map,.contact-map'),c=>({kind:c.className,min:Number(c.dataset.vmin),max:Number(c.dataset.vmax),low:Number(c.dataset.clippedLow),high:Number(c.dataset.clippedHigh),xMin:Number(c.dataset.manualXMin),xMax:Number(c.dataset.manualXMax),yMin:Number(c.dataset.manualYMin),yMax:Number(c.dataset.manualYMax)}))});update();",1)
    result=document[:match.start(2)]+script+document[match.end(2):]
    result=result.replace('</style>',CSS+'\n</style>',1)
    digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    result,count=re.subn(r"script-src 'sha256-[A-Za-z0-9+/=]+'", "script-src 'sha256-"+digest+"'",result,count=1)
    if count!=1:raise ValueError('Expected single renderer CSP pin')
    if before not in result:raise ValueError('Scientific packed payload changed')
    return result

CSS='''
.top5-manual{margin:14px 0;background:#fff;border:1px solid #b8cbd7;border-radius:10px;padding:14px;min-width:0}.top5-manual h2{margin:0 0 9px;font-size:16px}.top5-manual-fields{display:flex;flex-wrap:wrap;gap:9px}.top5-manual input{font:inherit;padding:6px;width:105px;max-width:100%;border:1px solid #aabcc9;border-radius:5px}.top5-manual button{font:inherit;padding:6px 9px;border:1px solid #aabcc9;background:#f4f8fa;border-radius:5px;cursor:pointer}.top5-manual-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.top5-manual small{display:block;line-height:1.6;margin:8px 0;color:#536779}.top5-manual-error{color:#9a3024;min-height:1.5em;overflow-wrap:anywhere}
'''

MANUAL_SCRIPT=r'''
// task1-top5-manual-ranges-v1. Display-only: never modify catalog/display arrays.
const manualDefaults={xMin:-25,xMax:25,yMin:-25,yMax:25,zMin:0,zMax:25.1,eMin:0,eMax:Math.max(1,...Object.values(display.color_limits).flatMap(m=>Object.values(m).filter(r=>r&&Array.isArray(r.global)).map(r=>r.global[1]))),jMin:0,jMax:Math.max(1,...Object.values(display.contact_color_limits).filter(r=>Array.isArray(r)).map(r=>r[1])),burdenMax:1.5};
let manual={...manualDefaults};const manualKey='task1-top5-manual-ranges-v1';
function validManual(v){return Object.keys(manualDefaults).every(k=>typeof v[k]==='number'&&Number.isFinite(v[k]))&&v.xMax>v.xMin&&v.yMax>v.yMin&&v.zMax>v.zMin&&v.eMax>v.eMin&&v.jMax>v.jMin&&v.burdenMax>0;}
try{const stored=JSON.parse(localStorage.getItem(manualKey)||'null');if(stored&&validManual(stored))manual={...stored};}catch(e){}
const manualPanel=el('section',undefined,'top5-manual');manualPanel.id='top5-manual-ranges';manualPanel.append(el('h2','모든 배치의 공통 수동 눈금'));
const manualFields=el('div',undefined,'top5-manual-fields'),manualInputs={};
for(const[key,label]of[['xMin','X 최소 mm'],['xMax','X 최대 mm'],['yMin','Y 최소 mm'],['yMax','Y 최대 mm'],['zMin','깊이 Z 최소 mm'],['zMax','깊이 Z 최대 mm'],['eMin','E 색 최소 V/m'],['eMax','E 색 최대 V/m'],['jMin','J 색 최소 A/m²'],['jMax','J 색 최대 A/m²'],['burdenMax','부담/기준 비율 최대']]){const l=el('label',label),input=el('input');input.type='number';input.step='any';input.value=String(manual[key]);input.dataset.top5Range=key;input.addEventListener('change',()=>commitManual({...manual,[key]:Number(input.value)}));l.append(input);manualFields.append(l);manualInputs[key]=input;}
const manualError=el('p',undefined,'top5-manual-error');manualError.id='top5-manual-error';manualError.setAttribute('role','alert');manualPanel.append(manualFields,el('small','X/Y는 전극 배치도·접촉 지도·수평면에 공통 적용하고, 수직면의 세로축은 Z 깊이 범위를 사용합니다. E/J 색 범위는 모든 조건에서 유지됩니다. 초기 공통 상한은 저장된 모든 정규화 범위를 포함하며, 표시용 클리핑은 원시 값·통계·순위·비율을 바꾸지 않습니다. 막대의 표시 상한도 직접 조절합니다. 작은 화면에서는 표를 가로로 스크롤할 수 있습니다.'),manualError);
const manualActions=el('div',undefined,'top5-manual-actions');
function commitManual(next){if(!validManual(next)){manualError.textContent='모든 값은 유한한 숫자이며 각 최대는 최소보다 커야 합니다. 잘못된 설정은 적용하지 않았습니다.';for(const k of Object.keys(manualDefaults))manualInputs[k].value=String(manual[k]);return false;}manual={...next};manualError.textContent='';for(const k of Object.keys(manualDefaults))manualInputs[k].value=String(manual[k]);try{localStorage.setItem(manualKey,JSON.stringify(manual))}catch(e){}update();return true;}
const resetButton=el('button','공통 초기 범위 복원');resetButton.type='button';resetButton.onclick=()=>commitManual({...manualDefaults});manualActions.append(resetButton);
const saveButton=el('button','눈금 JSON 저장');saveButton.type='button';saveButton.onclick=()=>{const blob=new Blob([JSON.stringify({schema:manualKey,ranges:manual},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='top5-manual-ranges.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};manualActions.append(saveButton);
const loadLabel=el('label','눈금 JSON 불러오기'),loadInput=el('input');loadInput.type='file';loadInput.accept='.json,application/json';loadInput.style.width='180px';loadInput.onchange=async()=>{try{const file=loadInput.files[0];if(!file)return;if(file.size>16384)throw Error('작은 눈금 설정 JSON만 허용합니다.');const loaded=JSON.parse(await file.text());if(loaded.schema!==manualKey)throw Error('눈금 설정 버전이 다릅니다.');if(!commitManual(loaded.ranges))return;}catch(e){manualError.textContent='설정을 불러오지 않았습니다: '+e.message;}};loadLabel.append(loadInput);manualActions.append(loadLabel);manualPanel.append(manualActions);
const controls=document.querySelector('.controls');controls.insertAdjacentElement('afterend',manualPanel);$('range').value='global';$('range').disabled=true;$('range').title='모든 조건의 비교를 위해 아래 공통 수동 색 범위를 사용합니다.';
function setClipping(canvas,values,scale,lo,hi){let low=0,high=0;for(const v of values){const x=v*scale;if(!Number.isFinite(x))continue;if(x<lo)low++;if(x>hi)high++;}canvas.dataset.clippedLow=String(low);canvas.dataset.clippedHigh=String(high);}
'''
