"""Pure UI for user-owned plot ranges; no file or research I/O on import.

The physical fixed-scale contract remains immutable provenance/defaults. Manual
display settings are separate, exportable and never alter scientific arrays.
"""
from __future__ import annotations
import copy
import math
import re

SCHEMA = 'task1-manual-ranges-v1'
LIMIT = 1e9
GROUP_FIELDS = {
    'EColour': {'cMin', 'cMax'}, 'JColour': {'cMin', 'cMax'},
    'wave': {'xMin', 'xMax', 'yMin', 'yMax'},
    'profile': {'xMin', 'xMax', 'yMin', 'yMax'},
    'space': {'xMin', 'xMax', 'yMin', 'yMax', 'zMin', 'zMax'},
}
FIELDS = {'xMin', 'xMax', 'yMin', 'yMax', 'cMin', 'cMax'}


def _fields(value, allowed):
    if not isinstance(value, dict) or not set(value) <= allowed:
        raise ValueError('Unknown manual-range field')
    for number in value.values():
        if type(number) not in (int, float) or not math.isfinite(number) or abs(number) > LIMIT:
            raise ValueError('Finite bounded manual number required')
    for axis in ('x', 'y', 'z', 'c'):
        low, high = axis+'Min', axis+'Max'
        if (low in value) != (high in value):
            raise ValueError('A complete minimum/maximum pair is required')
        if low in value and not 0 < value[high]-value[low] <= 2*LIMIT:
            raise ValueError('Manual maximum must exceed minimum')
    if value.get('cMin', 0) < 0:
        raise ValueError('Amplitude colour minimum cannot be negative')
    return copy.deepcopy(value)


def validate_settings(settings):
    """Validate browser settings JSON; never interpret code or arbitrary keys."""
    if not isinstance(settings, dict) or settings.get('schema') != SCHEMA or not set(settings) <= {'schema', 'groups', 'overrides', 'colorTransform'}:
        raise ValueError('Unsupported manual-range settings schema')
    groups = settings.get('groups', {})
    overrides = settings.get('overrides', {})
    if not isinstance(groups, dict) or not set(groups) <= set(GROUP_FIELDS) or not isinstance(overrides, dict) or len(overrides) > 128:
        raise ValueError('Unknown or excessive manual settings')
    for group, value in groups.items():
        _fields(value, GROUP_FIELDS[group])
    for key, value in overrides.items():
        if not isinstance(key, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,99}', key) or key in {'constructor', 'prototype', '__proto__'}:
            raise ValueError('Safe chart identifier required')
        _fields(value, FIELDS)
    if settings.get('colorTransform', 'log') not in ('linear', 'log'):
        raise ValueError('Unknown colour transform')
    return copy.deepcopy(settings)


CSS = r'''
#manual-range-controls{margin:0 0 18px;padding:16px;background:#e8f3f7;border:1px solid #93b9ca;border-radius:12px;overflow-wrap:anywhere}
#manual-range-controls h2{font-size:22px;margin:0 0 8px}.manual-note{font-size:12px;color:#43667b;margin:7px 0}.manual-global-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:12px 0}.manual-group{border:1px solid #bfd5e0;background:#fafdfe;padding:12px;border-radius:8px;min-width:0}.manual-group h3{font-size:14px;margin:0 0 7px}.manual-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.manual-fields label{display:flex;flex-direction:column;gap:3px;font-size:10px;color:#4c6d80;min-width:0}.manual-fields input{font:inherit;font-size:12px;min-width:0;width:100%;padding:6px;border:1px solid #b6cdda;border-radius:5px;background:white;color:#173d53}.manual-actions{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}.manual-actions button,.manual-load{font:inherit;font-size:11px;border:1px solid #7ea8bc;background:#fff;color:#175470;border-radius:5px;padding:6px 9px;cursor:pointer}.manual-actions button:hover,.manual-load:hover{background:#dceef6}.manual-error{font-size:11px;color:#9b3228;min-height:17px;margin:5px 0 0;overflow-wrap:anywhere}.manual-status{font-size:11px;color:#2c657d;overflow-wrap:anywhere}.manual-widget{border-top:1px solid #d9e6ed;padding:7px 0 5px;margin:3px 0 8px;min-width:0}.manual-caption{font-size:10px;color:#4e6e81;line-height:1.6;overflow-wrap:anywhere}.manual-widget details{margin:4px 0 0;padding:5px 0}.manual-widget summary{font-size:11px;cursor:pointer}.manual-clip{font-size:10px;color:#9b5f20;min-height:15px;overflow-wrap:anywhere}.manual-bar{height:7px;margin:5px 0 2px;background:linear-gradient(90deg,#440154,#414487,#2a788e,#22a884,#7ad151,#fde725);border-radius:2px}.manual-ticks{display:flex;justify-content:space-between;font-size:9px;color:#526f81;gap:2px;overflow-wrap:anywhere}.manual-ticks span{min-width:0}.manual-widget input:focus,.manual-group input:focus{outline:2px solid #6ba2bb;outline-offset:1px}
@media(max-width:760px){.manual-global-grid{grid-template-columns:1fr}#manual-range-controls{padding:12px}.manual-fields{gap:6px}.manual-actions button,.manual-load{font-size:10px}}
'''


SECTION = r'''
<section id="manual-range-controls" aria-label="모든 그래프 눈금 직접 조절">
<h2>눈금 범위 직접 조절</h2>
<p class="manual-note">아래 공통 설정이나 각 그래프 아래의 <b>눈금 직접 조절</b>에서 최소·최대값을 입력하세요. 적용한 값은 단면·방향·구동 조건을 바꿔도 유지됩니다. <b>표시 범위</b>만 바꾸며 팬텀·전극·원래 계산값은 그대로입니다.</p>
<div id="manual-global-groups" class="manual-global-grid"></div>
<div class="manual-actions"><button type="button" id="manual-reset-all">모든 수동 눈금 초기화</button><button type="button" id="manual-save-settings">눈금 설정 JSON 저장</button><label class="manual-load">눈금 설정 불러오기<input id="manual-load-settings" type="file" accept="application/json,.json" hidden></label></div>
<p class="manual-note">개별 그래프 설정이 공통 설정보다 우선합니다. 공통 범위를 적용하면 해당 항목의 개별 설정을 공통값으로 맞춥니다. 범위를 벗어난 데이터는 개수와 표시 잘림으로 알리며, 수치표와 hover에는 원값을 표시합니다. 두 등각 그림은 수치 축이 없는 위치 설명도입니다.</p>
<p id="manual-global-status" class="manual-status">눈금 설정 준비 중…</p><p id="manual-global-error" class="manual-error" role="alert"></p>
</section>
'''


SCRIPT = r'''
'use strict';
(()=>{
const $=id=>document.getElementById(id),SCHEMA='task1-manual-ranges-v1',LIMIT=1e9,FIELDS=['xMin','xMax','yMin','yMax','cMin','cMax'],PAIRS=[['xMin','xMax'],['yMin','yMax'],['cMin','cMax']],ALLOWED={EColour:['cMin','cMax'],JColour:['cMin','cMax'],wave:['xMin','xMax','yMin','yMax'],profile:['xMin','xMax','yMin','yMax'],space:['xMin','xMax','yMin','yMax','zMin','zMax']};
const contract=JSON.parse($('fixed-scale-contract').textContent);function freeze(o){if(o&&typeof o==='object'){for(const v of Object.values(o))freeze(v);Object.freeze(o);}return o;}window.task1FixedScaleContract=freeze(contract);
const E=contract.electric_field.upper_V_m,J=contract.current_density.upper_A_m2,records=new Map(),overrides=Object.create(null),formInputs=new Map();
function initialGroups(){return{EColour:{cMin:0,cMax:E},JColour:{cMin:0,cMax:J},wave:{yMin:-E,yMax:E},profile:{yMin:0,yMax:E},space:{xMin:-25,xMax:25,yMin:-25,yMax:25,zMin:0,zMax:25.1}};}
let groups=initialGroups(),lastError=null;
const titles={EColour:'전기장 색 범위 · V/m',JColour:'전류밀도 색 범위 · A/m²',wave:'모든 파형 축 · ms / V/m',profile:'모든 선 프로파일 축 · mm / V/m',space:'공간 좌표 표시 범위 · mm'},labels={xMin:'X 최소',xMax:'X 최대',yMin:'Y 최소',yMax:'Y 최대',zMin:'깊이 Z 최소',zMax:'깊이 Z 최대',cMin:'색 최소',cMax:'색 최대'};
const copy=o=>JSON.parse(JSON.stringify(o)),nice=v=>Number.isFinite(v)?Number(v).toPrecision(6):'미설정';
function must(ok,message){if(!ok)throw Error(message);}
function finite(v){return typeof v==='number'&&Number.isFinite(v)&&Math.abs(v)<=LIMIT;}
function validateFields(value,allowed,nullable=false){must(value&&typeof value==='object'&&!Array.isArray(value),'숫자 눈금 객체가 필요합니다.');for(const [key,v]of Object.entries(value)){must(allowed.includes(key),'지원하지 않는 눈금 항목: '+key);must(nullable&&v===null||finite(v),'눈금은 절댓값 10⁹ 이하의 유한한 숫자여야 합니다.');}for(const axis of['x','y','z','c']){const lo=axis+'Min',hi=axis+'Max',hasLo=Object.hasOwn(value,lo)&&value[lo]!==null,hasHi=Object.hasOwn(value,hi)&&value[hi]!==null;must(hasLo===hasHi,'최소·최대값은 함께 입력하거나 함께 비워 주세요.');if(hasLo){must(Number.isFinite(value[hi]-value[lo])&&value[hi]>value[lo],'최대값은 최소값보다 커야 합니다.');if(axis==='c')must(value[lo]>=0,'진폭 색 범위의 최소값은 0 이상이어야 합니다.');}if(nullable&&Object.hasOwn(value,lo)&&value[lo]===null)must(value[hi]===null,'최소·최대값은 함께 비워 주세요.');}return value;}
function transform(){return $('paper-color')?.value||'log';}
function colorFraction(v,max,min=0){if(!Number.isFinite(v)||!(max>min))return 0;const d=Math.max(0,v-min),q=transform()==='log'?Math.log1p(d)/Math.log1p(max-min):(v-min)/(max-min);return Math.min(1,Math.max(0,q));}
function colorValueAtFraction(q,max,min=0){return min+(transform()==='log'?Math.expm1(q*Math.log1p(max-min)):q*(max-min));}
function rgb(v,max,min=0){const palette=[[68,1,84],[65,68,135],[42,120,142],[34,168,132],[122,209,81],[253,231,37]],z=colorFraction(v,max,min)*5,i=Math.min(4,Math.floor(z)),f=z-i;return'rgb('+palette[i].map((a,k)=>Math.round(a+(palette[i+1][k]-a)*f)).join(',')+')';}
function errorText(error,id='manual-global-error'){lastError=error?String(error.message||error):null;const host=$(id);if(host)host.textContent=lastError||'';}
function currentRange(id,defaults,options){const range={...defaults},kind=options.kind;if(kind==='EMap')Object.assign(range,groups.EColour);if(kind==='JMap')Object.assign(range,groups.JColour);if(kind==='wave')Object.assign(range,groups.wave);if(kind==='profile')Object.assign(range,groups.profile);if(['EMap','JMap','layout'].includes(kind)){for(const [plotAxis,physical]of[['x',options.axisX],['y',options.axisY]])if(['x','y','z'].includes(physical)){range[plotAxis+'Min']=groups.space[physical+'Min'];range[plotAxis+'Max']=groups.space[physical+'Max'];}}Object.assign(range,overrides[id]||{});validateFields(range,FIELDS);return range;}
function inputLabel(key,options){if(key[0]==='c')return labels[key]+' ['+(options.colorUnit||'V/m')+']';const axis=key[0],unit=axis==='x'?options.xLabel:options.yLabel;return labels[key]+(unit?' · '+unit:'');}
function fieldKeys(defaults,options){return FIELDS.filter(k=>Object.hasOwn(defaults,k)&&(k[0]!=='c'||options.colour!==false));}
function makeInput(key,label,placeholder=''){const wrap=document.createElement('label'),input=document.createElement('input');wrap.textContent=label;input.type='number';input.step='any';input.inputMode='decimal';input.placeholder=placeholder;input.dataset.rangeKey=key;input.dataset.field=key;input.name=key;input.min=String(-LIMIT);input.max=String(LIMIT);wrap.appendChild(input);return{wrap,input};}
function valuesFromInputs(inputs,allowBlank){const result={};for(const[key,input]of inputs){const raw=input.value.trim();if(!raw){must(allowBlank,'모든 최소·최대값을 입력해 주세요.');result[key]=null;}else{const v=Number(raw);must(finite(v),'유한한 숫자를 입력해 주세요.');result[key]=v;}}return result;}
function createPanel(record){const canvas=$(record.id);if(!canvas)return;const wrapper=document.createElement('div');wrapper.className='manual-widget';wrapper.dataset.manualCanvas=record.id;const caption=document.createElement('div');caption.className='manual-caption';const clipping=document.createElement('div');clipping.className='manual-clip';const bar=document.createElement('div');bar.className='manual-bar';const ticks=document.createElement('div');ticks.className='manual-ticks';const details=document.createElement('details'),summary=document.createElement('summary');details.dataset.manualFor=record.id;summary.textContent='눈금 직접 조절';details.appendChild(summary);const fields=document.createElement('div');fields.className='manual-fields';const inputs=new Map();for(const key of fieldKeys(record.defaults,record.options)){const {wrap,input}=makeInput(key,inputLabel(key,record.options));input.addEventListener('input',()=>record.dirty.add(key));fields.appendChild(wrap);inputs.set(key,input);}details.appendChild(fields);const actions=document.createElement('div');actions.className='manual-actions';const apply=document.createElement('button');apply.type='button';apply.dataset.action='apply';apply.textContent='이 그래프에 적용';const reset=document.createElement('button');reset.type='button';reset.dataset.action='reset';reset.textContent='공통값 따르기';actions.append(apply,reset);details.appendChild(actions);const err=document.createElement('p');err.className='manual-error';err.setAttribute('role','alert');details.appendChild(err);apply.addEventListener('click',()=>{try{applyChart(record.id,valuesFromInputs(inputs,false));err.textContent='';}catch(e){err.textContent=e.message;}});reset.addEventListener('click',()=>{try{resetChart(record.id);err.textContent='';}catch(e){err.textContent=e.message;}});wrapper.append(caption,clipping,bar,ticks,details);canvas.after(wrapper);record.panel={wrapper,caption,clipping,bar,ticks,inputs,err};}
function refreshPanel(record){if(!record.panel)createPanel(record);const panel=record.panel;if(!panel)return;const r=record.range,o=record.options,hasOverride=Object.keys(overrides[record.id]||{}).length>0;let text=(hasOverride?'개별 수동 설정':'공통/기본 설정')+' · X '+nice(r.xMin)+'–'+nice(r.xMax)+' · Y '+nice(r.yMin)+'–'+nice(r.yMax);if(o.colour!==false&&Number.isFinite(r.cMin)&&Number.isFinite(r.cMax))text+=' · 색 '+nice(r.cMin)+'–'+nice(r.cMax)+' '+(o.colorUnit||'V/m')+' / '+(o.kind==='JMap'?'linear':transform());panel.caption.textContent=text;for(const[key,input]of panel.inputs){input.parentElement.firstChild.textContent=inputLabel(key,o);if(document.activeElement!==input&&!record.dirty.has(key))input.value=String(r[key]);}const visible=o.colour!==false&&Number.isFinite(r.cMin)&&Number.isFinite(r.cMax);panel.bar.hidden=panel.ticks.hidden=!visible;if(visible){panel.ticks.replaceChildren(...[0,.25,.5,.75,1].map(q=>{const span=document.createElement('span');span.textContent=nice(o.kind==='JMap'?r.cMin+q*(r.cMax-r.cMin):colorValueAtFraction(q,r.cMax,r.cMin));return span;}));}refreshNote(record);}
function refreshNote(record){if(!record.panel)return;const n=record.note;if(!n){record.panel.clipping.textContent='';return;}const low=n.low||0,high=n.high||0,total=n.total||0,hidden=n.viewportHidden||0;record.panel.clipping.textContent=((low||high||hidden)?'표시 범위 밖: 아래 '+low+' / 위 '+high+' / 좌표 밖 '+hidden+' (전체 '+total+'). 색·축 경계의 잘림이며 원값은 유지됩니다.':'현재 데이터는 선택한 표시 범위 안에 있습니다.')+(typeof n.message==='string'&&n.message?' '+n.message:'');}
function get(id,defaults,options={}){must(typeof id==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,99}$/.test(id)&&!['__proto__','prototype','constructor'].includes(id),'안전한 그래프 ID가 필요합니다.');validateFields(defaults,FIELDS);must(['EMap','JMap','wave','profile','layout'].includes(options.kind),'그래프 종류가 필요합니다.');let record=records.get(id);if(!record){record={id,defaults:{...defaults},options:{...options},range:null,note:null,panel:null,dirty:new Set()};records.set(id,record);}else{record.defaults={...defaults};record.options={...options};}record.range=currentRange(id,record.defaults,record.options);refreshPanel(record);return{...record.range};}
function note(id,value){const record=records.get(id);must(record,'등록된 그래프가 필요합니다.');must(value&&typeof value==='object','표시 범위 진단이 필요합니다.');for(const key of['low','high','total','viewportHidden'])if(value[key]!==undefined)must(Number.isFinite(value[key])&&value[key]>=0,'범위 진단 개수는 0 이상이어야 합니다.');must(value.message===undefined||typeof value.message==='string'&&value.message.length<=1000,'표시 진단 문구가 너무 길거나 형식이 맞지 않습니다.');record.note={...value};refreshNote(record);}
function clearDirty(record,keys=null){if(keys===null){record.dirty.clear();if(record.panel)record.panel.err.textContent='';}else for(const key of keys)record.dirty.delete(key);}
function redrawAll(){refreshGlobals();window.task1Best1Pair?.render();window.task1FieldShape?.render();window.task1PaperFigure?.render();for(const record of records.values())refreshPanel(record);const status=$('manual-global-status');if(status)status.textContent='수동 설정 유지 · '+records.size+'개 그래프 · 변수 변경 시 자동 눈금 조정 없음';}
function applyChart(id,fields){const record=records.get(id);must(record,'먼저 그래프를 표시해 주세요.');const applicable=fieldKeys(record.defaults,record.options);must(Object.keys(fields).every(k=>applicable.includes(k)),'이 그래프에서 사용할 수 없는 눈금 항목입니다.');const next={...(overrides[id]||{}),...fields};validateFields(next,FIELDS);const candidate={...currentRange(id,record.defaults,record.options),...next};validateFields(candidate,FIELDS);overrides[id]=next;clearDirty(record);errorText(null);redrawAll();return{...record.range};}
function affectedKeys(group,options,keys){if(group==='EColour')return options.kind==='EMap'?keys:[];if(group==='JColour')return options.kind==='JMap'?keys:[];if(group==='wave'||group==='profile')return options.kind===group?keys:[];if(group==='space'&&['EMap','JMap','layout'].includes(options.kind)){const fields=[];for(const[axis,physical]of[['x',options.axisX],['y',options.axisY]])for(const suffix of['Min','Max'])if(keys.includes(physical+suffix))fields.push(axis+suffix);return fields;}return[];}
function applyGroup(group,fields){must(Object.hasOwn(ALLOWED,group),'지원하지 않는 공통 그룹입니다.');validateFields(fields,ALLOWED[group],true);const next={...groups[group]};for(const[key,value]of Object.entries(fields)){if(value===null){if((group==='wave'||group==='profile')&&key[0]==='x')delete next[key];else next[key]=initialGroups()[group][key];}else next[key]=value;}validateFields(next,ALLOWED[group]);const old=groups[group];groups[group]=next;try{for(const record of records.values())currentRange(record.id,record.defaults,record.options);}catch(e){groups[group]=old;throw e;}for(const record of records.values()){const keys=affectedKeys(group,record.options,Object.keys(fields));if(overrides[record.id])for(const key of keys)delete overrides[record.id][key];clearDirty(record,keys);}errorText(null);redrawAll();return copy(groups[group]);}
function resetChart(id){must(records.has(id),'등록된 그래프가 필요합니다.');delete overrides[id];clearDirty(records.get(id));errorText(null);redrawAll();}
function resetAll(){groups=initialGroups();for(const id of Object.keys(overrides))delete overrides[id];for(const record of records.values())clearDirty(record);errorText(null);refreshGlobalInputs(true);redrawAll();}
function exportSettings(){return{schema:SCHEMA,groups:copy(groups),overrides:copy(overrides),colorTransform:transform()};}
function validateSettings(value){must(value&&typeof value==='object'&&!Array.isArray(value)&&value.schema===SCHEMA,'눈금 설정 JSON 형식이 맞지 않습니다.');must(Object.keys(value).every(k=>['schema','groups','overrides','colorTransform'].includes(k)),'알 수 없는 설정 항목입니다.');must(value.groups&&typeof value.groups==='object'&&!Array.isArray(value.groups),'공통 설정 객체가 필요합니다.');must(value.overrides&&typeof value.overrides==='object'&&!Array.isArray(value.overrides)&&Object.keys(value.overrides).length<=128,'그래프 설정이 너무 많거나 형식이 맞지 않습니다.');for(const[group,fields]of Object.entries(value.groups)){must(Object.hasOwn(ALLOWED,group),'알 수 없는 공통 그룹입니다.');validateFields(fields,ALLOWED[group]);}for(const[id,fields]of Object.entries(value.overrides)){must(/^[A-Za-z][A-Za-z0-9_-]{0,99}$/.test(id)&&!['__proto__','prototype','constructor'].includes(id),'안전하지 않은 그래프 ID입니다.');validateFields(fields,FIELDS);if(records.has(id)){const rec=records.get(id);must(Object.keys(fields).every(k=>fieldKeys(rec.defaults,rec.options).includes(k)),'이 그래프에서 사용할 수 없는 눈금 항목입니다.');}}must(!value.colorTransform||['linear','log'].includes(value.colorTransform),'알 수 없는 색 변환입니다.');return value;}
function importSettings(value){if(typeof value==='string'){must(value.length<=262144,'설정 파일은 256 KiB 이하여야 합니다.');value=JSON.parse(value);}validateSettings(value);const candidate=initialGroups();for(const[group,fields]of Object.entries(value.groups))candidate[group]={...candidate[group],...fields};const oldGroups=groups,oldOverrides=copy(overrides);groups=candidate;for(const id of Object.keys(overrides))delete overrides[id];for(const[id,fields]of Object.entries(value.overrides))overrides[id]={...fields};try{for(const record of records.values())currentRange(record.id,record.defaults,record.options);}catch(e){groups=oldGroups;for(const id of Object.keys(overrides))delete overrides[id];Object.assign(overrides,oldOverrides);throw e;}if(value.colorTransform&&$('paper-color'))$('paper-color').value=value.colorTransform;for(const record of records.values())clearDirty(record);errorText(null);refreshGlobalInputs(true);redrawAll();return exportSettings();}
function snapshot(){const charts={};for(const[id,record]of records)charts[id]={id,kind:record.options.kind,options:{...record.options},defaults:{...record.defaults},range:{...record.range},note:record.note?{...record.note}:null,override:{...(overrides[id]||{})}};return{schema:SCHEMA,groups:copy(groups),overrides:copy(overrides),charts,colorTransform:transform()};}
function validateForTest(){try{for(const record of records.values()){const expected=currentRange(record.id,record.defaults,record.options);validateFields(record.range,FIELDS);must(Object.keys(expected).every(key=>expected[key]===record.range[key]),'그래프 수동 범위가 바뀌었습니다: '+record.id);must(!!record.panel,'개별 눈금 조절기가 없습니다: '+record.id);must(record.panel.inputs.size===fieldKeys(record.defaults,record.options).length,'개별 눈금 입력 개수가 다릅니다.');}return{passed:true,registered_charts:records.size,per_chart_controls:records.size,automatic_rescaling:false,manual_overrides:Object.keys(overrides).filter(id=>Object.keys(overrides[id]).length).length,groups:copy(groups),colorTransform:transform()};}catch(e){return{passed:false,error:e.message};}}
function refreshGlobalInputs(force=false){for(const[group,inputs]of formInputs)for(const[key,input]of inputs)if(force||document.activeElement!==input&&!input.dataset.dirty){input.value=groups[group][key]===undefined?'':String(groups[group][key]);if(force)delete input.dataset.dirty;}}
function refreshGlobals(){refreshGlobalInputs();const oldLabel=$('fixed-scale-global-transform'),oldTicks=$('fixed-scale-global-ticks');if(oldLabel)oldLabel.textContent='공통 기본 색 변환 · '+transform()+' / 개별 범위는 각 그래프 참조';if(oldTicks)oldTicks.replaceChildren(...[0,.25,.5,.75,1].map(q=>{const span=document.createElement('span');span.textContent=nice(colorValueAtFraction(q,groups.EColour.cMax,groups.EColour.cMin))+' V/m';return span;}));}
function boot(){const host=$('manual-global-groups');if(!host)return;for(const[group,keys]of Object.entries(ALLOWED)){const box=document.createElement('div');box.className='manual-group';box.dataset.manualGroup=group;const title=document.createElement('h3');title.textContent=titles[group];box.appendChild(title);const grid=document.createElement('div');grid.className='manual-fields';const inputs=new Map();for(const key of keys){const label=labels[key]+(group==='wave'?(key[0]==='x'?' [ms]':' [V/m]'):group==='profile'?(key[0]==='x'?' [mm]':' [V/m]'):group==='space'?' [mm]':'');const empty=(group==='wave'||group==='profile')&&key[0]==='x';const{wrap,input}=makeInput(key,label,empty?'현재 시간창/좌표축 따름':'');input.addEventListener('input',()=>{input.dataset.dirty='true';});grid.appendChild(wrap);inputs.set(key,input);}box.appendChild(grid);const actions=document.createElement('div');actions.className='manual-actions';const apply=document.createElement('button');apply.type='button';apply.dataset.action='apply';apply.textContent='이 항목 공통 적용';apply.addEventListener('click',()=>{try{applyGroup(group,valuesFromInputs(inputs,true));for(const input of inputs.values())delete input.dataset.dirty;refreshGlobalInputs();errorText(null);}catch(e){errorText(e);}});actions.appendChild(apply);box.appendChild(actions);host.appendChild(box);formInputs.set(group,inputs);}refreshGlobalInputs(true);$('manual-reset-all').addEventListener('click',resetAll);$('manual-save-settings').addEventListener('click',()=>{try{const blob=new Blob([JSON.stringify(exportSettings(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='TIS-manual-ranges.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);errorText(null);}catch(e){errorText(e);}});$('manual-load-settings').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;must(file.size<=262144,'설정 파일은 256 KiB 이하여야 합니다.');importSettings(await file.text());}catch(e){errorText(e);}finally{event.target.value='';}});const status=$('manual-global-status');if(status)status.textContent='각 그래프의 눈금 직접 조절을 열거나 공통 범위를 적용하세요.';refreshGlobals();}
window.task1ManualRanges=Object.freeze({get,note,applyChart,applyGroup,resetChart,resetAll,exportSettings,importSettings,snapshot,validateForTest,colorFraction,colorValueAtFraction,rgb,transform,redrawAll});
window.task1FixedScales=Object.freeze({contract,transform,colorFraction,colorValueAtFraction,redrawAll,validateForTest,snapshot});
document.addEventListener('change',event=>{if(event.target.id==='paper-color')redrawAll();});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
'''


def render_helper():
    """Return the helper script; caller owns CSP hashing and document insertion."""
    return SCRIPT
