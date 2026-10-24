#!/usr/bin/env python3
"""Pure packed offline GUI for an existing best1 versus genuine single pair.

render(payload) returns HTML in memory only. The caller owns source validation,
resource guards and publication. No native reads, solves, exports or file writes.
"""
from __future__ import annotations
import base64
import gzip
import hashlib
import json
import math
import struct

ANALYSIS_SCHEMA = 'task1-best1-single-pair-comparison-v1'
MODES = ('raw_1Vpp', 'skin_contact_only')
MATCHES = ('ROI_energy_RMS', 'centre20_E_RMS')
REGIONS = ('primary_r5_depth15_20', 'surface_0_5', 'primary_complement', 'total')
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2', 'contact_voltage_RMS_max_V',
           'bulk_skin_J_vector_RMS_max_A_m2', 'bulk_skin_J_vector_RMS_p95_A_m2',
           'SC_power_W', 'contact_power_W', 'skin_SC_plus_dermis_power_W', 'source_power_W')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def binary(value, size, label):
    require(isinstance(value, str) and len(value) <= (size+2)//3*4+4, 'Bounded base64 required: '+label)
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid base64: '+label) from error
    require(len(data) == size, 'Display shape/byte count differs: '+label)
    return data


def validate(payload):
    require(isinstance(payload, dict), 'Packed comparison object required')
    a, s = payload.get('analysis', {}), payload.get('spatial', {})
    require(a.get('schema') == ANALYSIS_SCHEMA, 'Unknown comparison schema')
    require(a.get('candidate_adopted') is not True and a.get('same_field_RMS_implies_same_modulation_or_activation') is not True,
            'RMS comparison cannot claim adoption or modulation/activation equivalence')
    require(set(a.get('modes', {})) == set(MODES), 'Separate raw/skin8 source comparisons required')
    circuit = a.get('single_pair', {}).get('circuit', {})
    require(circuit.get('n_pads') == 2 and circuit.get('n_outputs') == 1 and circuit.get('n_return_nodes') == 1 and
            circuit.get('source_resistance_ohm') == 50, 'Genuine one-output two-pad common-return 50ohm single pair required')
    for mode in MODES:
        m = a['modes'][mode]
        require(number(m.get('reference_amplitude_scale'), True) and len(m.get('reference_source_Vpp_intervals_V', [])) == 2,
                'Actual TIS source amplitude and two output Vpp intervals required')
        require(all(number(m.get('reference_burdens', {}).get(k)) for k in BURDENS), 'Nine separate TIS burdens required')
        require(set(m.get('matches', {})) == set(MATCHES), 'ROI energy and centre matches must remain separate')
        for key in MATCHES:
            c = m['matches'][key]
            require(number(c.get('amplitude_scale'), True) and number(c.get('required_source_Vpp'), True), 'Positive genuine C1 source scale required')
            require(all(number(c.get('burdens', {}).get(k)) for k in BURDENS), 'Nine separate C1 burdens required')
            require(all(number(c.get(k)) for k in ('achieved_ROI_energy_RMS_V_m', 'achieved_centre20_E_RMS_V_m', 'source_current_RMS_mA')),
                    'Saved actual matched RMS/current required')
    grid = s.get('grid', {})
    for name in ('x_edges_mm', 'y_edges_mm', 'z_faces_mm'):
        edges = grid.get(name)
        require(isinstance(edges, list) and 3 <= len(edges) <= 201 and
                all(type(v) in (int, float) and math.isfinite(v) for v in edges) and
                all(y > x for x, y in zip(edges, edges[1:])), 'Actual increasing native faces required: '+name)
    nx, ny, nz = (len(grid[k])-1 for k in ('x_edges_mm', 'y_edges_mm', 'z_faces_mm'))
    require(len(grid.get('XY_actual_depths_mm', [])) == 5 and len(grid.get('XY_requested_depths_mm', [])) == 5 and
            all(number(v) for v in grid['XY_actual_depths_mm']+grid['XY_requested_depths_mm']), 'Five actual/requested native XY depths required')
    for name in ('XZ_actual_y_mm', 'YZ_actual_x_mm'):
        require(type(grid.get(name)) in (int, float) and math.isfinite(grid[name]), 'Actual native central plane required')
    require(s.get('fieldunits', 'V/m') == 'V/m' and s.get('contactunits', 'A/m2') == 'A/m2', 'Common V/m and A/m2 units required')
    for key, pads in (('TIS', 4), ('C1', 2)):
        c = s.get(key, {}); centres = c.get('pad_centres', [])
        require(isinstance(centres, list) and len(centres) == pads and {p.get('pad') for p in centres} == set(range(pads)),
                'Physical pad identities required: '+key)
        for p in centres:
            require(p.get('node') in (-1, 0, 1, 'out0', 'out1', 'GND', 'gnd') and
                    all(type(p.get(k)) in (int, float) and math.isfinite(p[k]) for k in ('x_mm', 'y_mm')) and number(p.get('area_mm2'), True),
                    'Actual pad role/centroid/area required')
        mask = binary(c.get('pad_mask_b64'), nx*ny*2, key+' Int16 mask')
        require(all(-1 <= x[0] < pads for x in struct.iter_unpack('<h', mask)), 'Unknown physical pad in display mask')
        outlines = c.get('physical_outlines')
        require(isinstance(outlines, list) and len(outlines) == pads and {p.get('pad') for p in outlines} == set(range(pads)),
                'Exact physical outlines required; no bounding-box contact substitution')
        for p in outlines:
            poly = p.get('polygon_mm')
            require(p.get('node') in (-1, 0, 1, 'out0', 'out1', 'GND', 'gnd') and isinstance(poly, list) and 3 <= len(poly) <= 20000 and
                    all(isinstance(v, list) and len(v) == 2 and all(type(x) in (int, float) and math.isfinite(x) for x in v) for v in poly),
                    'Finite exact physical polygon required')
        planes = c.get('RMS', {})
        require(isinstance(planes.get('xy'), list) and len(planes['xy']) == 5, 'Five Float16 XY RMS planes required')
        for i, plane in enumerate(planes['xy']):
            binary(plane, nx*ny*2, key+' RMS xy'+str(i))
        binary(planes.get('xz'), nx*nz*2, key+' RMS xz')
        binary(planes.get('yz'), ny*nz*2, key+' RMS yz')
        contact = c.get('contactJ'); contact = contact.get('values_b64') if isinstance(contact, dict) else contact
        binary(contact, nx*ny*2, key+' Float16 contact J')
        for region in REGIONS:
            stats = s.get('regions', {}).get(key, {}).get(region, {})
            require(all(number(stats.get(k)) for k in ('mean', 'p10', 'p95', 'max', 'std', 'volume_m3', 'energy_RMS_V_m')),
                    'Authoritative Float64 regional RMS statistics required: '+key+'/'+region)
    # JSON must preserve all source data without NaN/Infinity coercion or custom encoders.
    json.dumps(payload, ensure_ascii=False, allow_nan=False)
    return payload


SCRIPT = r'''
'use strict';
(async()=>{if(!window.DecompressionStream)throw Error('이 브라우저는 내장 gzip 해제를 지원하지 않습니다. 최신 Chromium에서 열어 주세요.');
const packed=document.getElementById('packed').textContent.trim(),raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0)),payload=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
const A=payload.analysis,S=payload.spatial,G=S.grid,$=id=>document.getElementById(id),F=(x,d=6)=>typeof x==='number'&&Number.isFinite(x)?x.toLocaleString('en-US',{maximumSignificantDigits:d}):'미제공',P=x=>F(100*x,5)+'%',modes={raw_1Vpp:'TIS raw 기준 · 최대출력1 Vpp',skin_contact_only:'TIS skin8 기준 · 8개 부담 제한'},matches={ROI_energy_RMS:'목표 ROI 에너지 RMS 일치',centre20_E_RMS:'중심 깊이20 mm RMS 일치'},primary='primary_r5_depth15_20',cache=new Map(),palette=[[68,1,84],[65,68,135],[42,120,142],[34,168,132],[122,209,81],[253,231,37]];
function E(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}function fill(id,o,v){Object.entries(o).forEach(([k,t])=>{const e=E('option',t);e.value=k;$(id).append(e);});$(id).value=v;}
fill('mode',modes,'skin_contact_only');fill('match',matches,'ROI_energy_RMS');fill('plane',{xy:'수평 XY',xz:'수직 XZ',yz:'수직 YZ'},'xz');fill('depth',Object.fromEntries(G.XY_actual_depths_mm.map((v,i)=>[i,`요청 ${F(G.XY_requested_depths_mm[i])} → 실제 ${F(v)} mm`])),'3');fill('range',{global:'전체 native volume 공통 범위',primary_ROI:'목표 ROI 공통 범위 · 표시 clipping'},'primary_ROI');
function half(h){const sign=h&32768?-1:1,e=(h>>10)&31,f=h&1023;return e===31?(f?NaN:sign*Infinity):sign*(e?Math.pow(2,e-15)*(1+f/1024):Math.pow(2,-14)*f/1024);}function decode(s,type='f'){const key=type+s;if(cache.has(key))return cache.get(key);const raw=Uint8Array.from(atob(s),c=>c.charCodeAt(0)),view=new DataView(raw.buffer),out=type==='h'?new Int16Array(raw.length/2):new Float32Array(raw.length/2);for(let i=0;i<out.length;i++)out[i]=type==='h'?view.getInt16(i*2,true):half(view.getUint16(i*2,true));cache.set(key,out);return out;}
function color(v,max){if(!Number.isFinite(v))return'#e8eef2';let t=Math.max(0,Math.min(1,v/max))*5,i=Math.min(4,Math.floor(t)),f=t-i;return'rgb('+palette[i].map((v,k)=>Math.round(v+(palette[i+1][k]-v)*f)).join(',')+')';}function role(n){return n===0||n==='out0'?'out0':n===1||n==='out1'?'out1':'GND';}
function frame(canvas,xe,ye,down=false){const w=Math.max(170,canvas.clientWidth),h=canvas.classList.contains('field-map')?290:175,d=Math.min(2,devicePixelRatio||1);canvas.width=w*d;canvas.height=h*d;const c=canvas.getContext('2d');c.scale(d,d);c.fillStyle='#fff';c.fillRect(0,0,w,h);const b={l:43,r:12,t:12,b:31},pw=w-b.l-b.r,ph=h-b.t-b.b,X=x=>b.l+(x-xe[0])/(xe.at(-1)-xe[0])*pw,Y=y=>b.t+(down?(y-ye[0]):(ye.at(-1)-y))/(ye.at(-1)-ye[0])*ph;return{c,w,h,b,pw,ph,X,Y,xe,ye,down};}
function axes(f,xlab,ylab){const{c,X,Y,xe,ye,b,w,h}=f;c.strokeStyle='#b9cad4';c.lineWidth=.7;c.strokeRect(b.l,b.t,f.pw,f.ph);c.fillStyle='#607889';c.font='10px system-ui';c.textAlign='center';for(const x of[xe[0],0,xe.at(-1)])c.fillText(F(x,4),X(x),h-17);c.fillText(xlab,b.l+f.pw/2,h-3);c.textAlign='right';for(const y of[ye[0],(ye[0]+ye.at(-1))/2,ye.at(-1)])c.fillText(F(y,4),b.l-4,Y(y)+3);c.save();c.translate(10,b.t+f.ph/2);c.rotate(-Math.PI/2);c.textAlign='center';c.fillText(ylab,0,0);c.restore();}
function pixels(f,v,max,scale){const{c,X,Y,xe,ye}=f;for(let j=0;j<ye.length-1;j++)for(let i=0;i<xe.length-1;i++){c.fillStyle=color(v[j*(xe.length-1)+i]*scale,max);const x=X(xe[i]),y=Y(ye[j]),yy=Y(ye[j+1]);c.fillRect(x,Math.min(y,yy),X(xe[i+1])-x+.1,Math.abs(yy-y)+.1);}}
function locate(e,x){for(let i=0;i<e.length-1;i++)if(x>=e[i]&&x<e[i+1])return i;return-1;}function hover(canvas,f,v,scale,key,plane,z,unit){canvas.onpointermove=e=>{const r=canvas.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top,x=f.xe[0]+(px-f.b.l)/f.pw*(f.xe.at(-1)-f.xe[0]),t=(py-f.b.t)/f.ph,y=f.down?f.ye[0]+t*(f.ye.at(-1)-f.ye[0]):f.ye.at(-1)-t*(f.ye.at(-1)-f.ye[0]),i=locate(f.xe,x),j=locate(f.ye,y);if(i<0||j<0)return;const a=(f.xe[i]+f.xe[i+1])/2,b=(f.ye[j]+f.ye[j+1])/2,value=v[j*(f.xe.length-1)+i]*scale,xyz=plane==='xy'?[a,b,z]:plane==='xz'?[a,G.XZ_actual_y_mm,b]:[G.YZ_actual_x_mm,a,b];$('hover').textContent=`${key} · xyz ${xyz.map(x=>F(x,5)).join(', ')} mm · ${Number.isFinite(value)?F(value,7)+' '+unit:'영역 밖 / 미지원 (NaN)'} · Float16 표시값`;};}
function layout(canvas,key){const data=S[key],f=frame(canvas,G.x_edges_mm,G.y_edges_mm),{c,X,Y}=f;for(const p of data.physical_outlines){const xy=p.polygon_mm;c.beginPath();c.moveTo(X(xy[0][0]),Y(xy[0][1]));for(const[x,y]of xy.slice(1))c.lineTo(X(x),Y(y));c.closePath();c.fillStyle={out0:'#e78b50',out1:'#4386c9',GND:'#bdcbd4'}[role(p.node)];c.fill();c.strokeStyle='#27485d';c.lineWidth=.8;c.stroke();}c.strokeStyle='#718c9c';c.beginPath();c.ellipse(X(0),Y(0),Math.abs(X(25)-X(0)),Math.abs(Y(25)-Y(0)),0,0,2*Math.PI);c.stroke();c.fillStyle='#153b52';c.font='bold 10px system-ui';c.textAlign='center';for(const p of data.pad_centres)c.fillText(`${p.pad}:${role(p.node)}`,X(p.x_mm),Y(p.y_mm));axes(f,'x [mm]','y [mm]');}
function field(canvas,key,scale,max){const plane=$('plane').value,i=Number($('depth').value),p=S[key].RMS,v=decode(plane==='xy'?p.xy[i]:p[plane]),xe=plane==='yz'?G.y_edges_mm:G.x_edges_mm,ye=plane==='xy'?G.y_edges_mm:G.z_faces_mm,f=frame(canvas,xe,ye,plane!=='xy');pixels(f,v,max,scale);canvas.dataset.vmax=String(max);const{c,X,Y}=f;c.strokeStyle='white';c.lineWidth=1.3;c.setLineDash([4,3]);if(plane==='xy'){c.beginPath();c.ellipse(X(0),Y(0),Math.abs(X(5)-X(0)),Math.abs(Y(5)-Y(0)),0,0,2*Math.PI);c.stroke();}else{const fixed=plane==='xz'?G.XZ_actual_y_mm:G.YZ_actual_x_mm,r=Math.sqrt(Math.max(0,25-fixed*fixed));c.strokeRect(X(-r),Y(15),X(r)-X(-r),Y(20)-Y(15));for(const z of[.1,5.1,10.1]){c.beginPath();c.moveTo(X(xe[0]),Y(z));c.lineTo(X(xe.at(-1)),Y(z));c.stroke();}}c.setLineDash([]);axes(f,plane==='yz'?'y [mm]':'x [mm]',plane==='xy'?'y [mm]':'+z depth [mm]');hover(canvas,f,v,scale,key,plane,G.XY_actual_depths_mm[i],'V/m');}
function contact(canvas,key,scale,max){const data=S[key],raw=typeof data.contactJ==='string'?data.contactJ:data.contactJ.values_b64,v=decode(raw),f=frame(canvas,G.x_edges_mm,G.y_edges_mm);pixels(f,v,max,scale);canvas.dataset.vmax=String(max);axes(f,'x [mm]','y [mm]');hover(canvas,f,v,scale,key,'xy',0,'A/m²');}
function table(head,rows){const box=E('div',undefined,'scroll'),t=E('table'),h=E('tr');head.forEach(s=>h.append(E('th',s)));const th=E('thead');th.append(h);const body=E('tbody');rows.forEach(row=>{const r=E('tr');row.forEach(v=>r.append(E('td',v)));body.append(r);});t.append(th,body);box.append(t);return box;}
const labels={surface_J_RMS_max_A_m2:'접촉면 normal J 최대 [A/m²]',surface_J_RMS_p95_A_m2:'접촉면 normal J P95 [A/m²]',contact_voltage_RMS_max_V:'접촉 전압 최대 RMS [V]',bulk_skin_J_vector_RMS_max_A_m2:'SC+dermis 벡터 J 최대 [A/m²]',bulk_skin_J_vector_RMS_p95_A_m2:'SC+dermis 벡터 J P95 [A/m²]',SC_power_W:'SC 손실 [W]',contact_power_W:'접촉 계면 손실 [W]',skin_SC_plus_dermis_power_W:'SC+dermis 손실 [W]',source_power_W:'총 source 전력 [W]'};
function sourceRatios(mode,match){const r=match.ratios_vs_reference||{},mx=r.source_Vpp_to_max_TIS_output_interval,each=r.source_Vpp_to_each_TIS_output_interval||[],rows=[];if(mx)rows.push(['TIS 최대 출력 대비',F(mx.lower)+'–'+F(mx.upper)+' ×',P(mx.lower-1)+'–'+P(mx.upper-1)]);each.forEach((v,i)=>rows.push(['TIS out'+i+' 대비',F(v.lower)+'–'+F(v.upper)+' ×',P(v.lower-1)+'–'+P(v.upper-1)]));$('source-ratios').replaceChildren(table(['C1 high-Z source Vpp 비교','배수의 수치 구간','변화율 (증가·감소를 실제값대로)'],rows));}
function power(mode,match){const host=$('signed-power');host.replaceChildren();for(const[key,p]of[['TIS',mode.reference_signed_output_power_evidence],['C1',match.signed_output_power_evidence]]){if(!p){host.append(E('p',key+' signed 출력별 영수증 미제공'));continue;}const rows=[];if(p.totals)rows.push(['그룹',F(p.totals.ideal_source_power_W),F(p.totals.metal_delivered_power_W),F(p.totals.source_resistor_loss_W)]);if(p.spectrum){rows.push(['단일 출력 / 그룹',F(p.ideal_source_power_W),F(p.metal_delivered_power_W),F(p.source_resistor_loss_W)]);p.spectrum.forEach(f=>rows.push([f.frequency_Hz+' Hz',F(f.ideal_source_power_W),F(f.metal_delivered_power_W),F(f.source_resistor_loss_W)]));}for(const out of p.outputs||[]){rows.push(['out'+out.output_index,F(out.ideal_source_power_W),F(out.metal_delivered_power_W),F(out.source_resistor_loss_W)]);(out.spectrum||[]).forEach(f=>rows.push(['out'+out.output_index+' / '+f.frequency_Hz+' Hz',F(f.ideal_source_power_W),F(f.metal_delivered_power_W),F(f.source_resistor_loss_W)]));}host.append(E('h3',key),table(['주파수·출력','signed source W','signed metal W','50 Ω loss W'],rows));}}
function update(){const modeID=$('mode').value,matchID=$('match').value,mode=A.modes[modeID],match=mode.matches[matchID],scales={TIS:mode.reference_amplitude_scale,C1:match.amplitude_scale},region=$('range').value==='global'?'total':primary,fmax=Math.max(...['TIS','C1'].map(k=>S.regions[k][region].max*scales[k])),jmax=Math.max(mode.reference_burdens.surface_J_RMS_max_A_m2,match.burdens.surface_J_RMS_max_A_m2),plane=$('plane').value,depth=Number($('depth').value);$('depth').disabled=plane!=='xy';$('field-legend').textContent=`E RMS 공통 0–${F(fmax)} V/m · ${region==='total'?'전체 native volume 범위':'목표 ROI 표시 범위: 초과값 clipping'}`;$('contact-legend').textContent=`접촉 normal J RMS 공통 0–${F(jmax)} A/m²`;$('match-note').textContent=`${modes[modeID]} · ${matches[matchID]}. 일치시킬 TIS 목표: ROI 에너지 RMS ${F(mode.target_ROI_energy_RMS_V_m)} V/m / 중심20 mm RMS ${F(mode.target_centre20_E_RMS_V_m)} V/m. 선택하지 않은 기준·공간분포·접촉부담은 동시에 일치시키지 않았습니다.`;
for(const key of['TIS','C1']){const n=key==='TIS'?mode.reference_burdens:match.burdens,stats=S.regions[key][primary],amp=scales[key],host=$(key+'-stats');host.replaceChildren();for(const[label,val]of[['ROI 에너지 RMS',F(stats.energy_RMS_V_m*amp)+' V/m'],['ROI 평균 / P10',F(stats.mean*amp)+' / '+F(stats.p10*amp)+' V/m'],['접촉 J95',F(n.surface_J_RMS_p95_A_m2)+' A/m²'],['총 source 전력',F(n.source_power_W)+' W']]){const box=E('div');box.append(E('span',label),E('b',val));host.append(box);}$(key+'-source').textContent=key==='TIS'?`50 Ω 앞 실제 source Vpp: out0/out1 ${JSON.stringify(mode.reference_source_Vpp_intervals_V)} V · 출력별 RMS전류 ${(mode.reference_output_RMS_by_output_mA||[]).map(v=>F(v)).join(' / ')} mA`:`50 Ω 앞 source ${F(match.required_source_Vpp)} Vpp · 단일 출력 RMS ${F(match.source_current_RMS_mA)} mA · 부하 연결 metal ${F(match.loaded_metal_Vpp)} Vpp · 접촉 ${F(n.contact_voltage_RMS_max_V)} V RMS`;layout($(key+'-layout'),key);field($(key+'-field'),key,amp,fmax);contact($(key+'-contact'),key,amp,jmax);$(key+'-plane').textContent=plane==='xy'?`XY 실제 z=${F(G.XY_actual_depths_mm[depth])} mm (요청 ${F(G.XY_requested_depths_mm[depth])} mm)`:`${plane.toUpperCase()} 실제 ${plane==='xz'?'y':'x'}=${F(plane==='xz'?G.XZ_actual_y_mm:G.YZ_actual_x_mm)} mm · +z 깊이`;}
sourceRatios(mode,match);const ratios=match.ratios_vs_reference?.burdens||{};$('burdens').replaceChildren(table(['별개 부담 지표','TIS (4 pads / 2 outputs)','C1 (2 pads / 1 output)','C1/TIS 비율'],Object.entries(labels).map(([k,t])=>[t,F(mode.reference_burdens[k]),F(match.burdens[k]),F(ratios[k])+' ×'])));const rr=[];for(const region of[primary,'surface_0_5','primary_complement','total'])for(const key of['TIS','C1']){const r=S.regions[key][region],a=scales[key];rr.push([key,region,F(r.mean*a),F(r.p10*a),F(r.p95*a),F(r.max*a),F(r.std*a),F(r.energy_RMS_V_m*a),F(r.volume_m3)]);}$('regions').replaceChildren(table(['조건','영역','평균 V/m','P10 V/m','P95 V/m','최대 V/m','표준편차 V/m','에너지 RMS V/m','표현체적 m³'],rr));const mod=mode.reference_primary_maxTIS_statistics;$('modulation').replaceChildren(table(['다른 물리량','TIS','C1 단일3 kHz sine'],[['목표 ROI 기본파 maxTIS 평균 V/m',F(mod?.mean),'0 · envelope 변동 없음'],['목표 ROI 기본파 maxTIS P10 V/m',F(mod?.p10),'0 · TIS와 생리 동등성 주장 없음']]));const sh=S.shape_comparison?.[modeID]?.[matchID];$('shape').replaceChildren();if(sh){$('shape').append(table(['실제 계산된 RMS scalar 공간분포 비교','값'],[['가중 RMS 차이 [V/m]',F(sh.weighted_RMS_difference_V_m)],['TIS 목표 에너지 RMS 대비 상대 차이',F(sh.relative_RMS_difference_to_TIS_ROI_energy)],['목표 내 TIS ±10% RMS 범위 셀의 체적 비율',F(sh.target_fraction_within_10_percent_of_TIS)]]),E('p',typeof sh.definition==='string'?sh.definition:JSON.stringify(sh.definition||{}),'muted'));}else $('shape').append(E('p','별도 공간분포 차이 지표 미제공. RMS 목표 일치만으로 분포 일치를 주장하지 않습니다.'));
power(mode,match);$('losses').textContent=JSON.stringify({TIS_layer_contact_source_losses_W:mode.reference_layer_contact_source_losses_W||null,C1_additional_burdens:match.additional_burdens||null},null,2);$('probes').textContent=JSON.stringify({scaled_unloaded_probe_count:Array.isArray(match.unloaded_probe40)?match.unloaded_probe40.length:null,raw_probe_reference:match.raw_probe_reference||null,loaded_prediction:'held: actual port impedance, ground, attenuation settings and transfer functions unverified'},null,2);}
for(const id of['mode','match','plane','depth','range'])$(id).addEventListener('change',update);$('provenance').textContent=JSON.stringify({reference:A.reference,single_pair:A.single_pair,geometry_comparison:A.geometry_comparison,holds:A.holds,spatial_proofs:S.proofs,provenance:payload.provenance},null,2);let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(update,100);});window.task1Best1Pair=Object.freeze({render:update,payload});update();$('loading').remove();
})().catch(e=>{document.getElementById('loading').textContent='화면 데이터 해제/표시 실패: '+e.message;console.error(e);});
'''

CSS = '''*{box-sizing:border-box}body{margin:0;background:#f1f5f7;color:#18384d;font:14px/1.55 system-ui,-apple-system,sans-serif}header{background:linear-gradient(115deg,#103047,#17647a);color:white;padding:28px max(20px,calc((100vw - 1320px)/2))}h1{font-size:clamp(25px,3vw,36px);margin:8px 0 14px;line-height:1.25}header p{max-width:1050px;color:#d2e7ee;margin:7px 0}.eyebrow{letter-spacing:.12em;font-size:11px;color:#a8d5e1}main{max-width:1360px;margin:auto;padding:20px}.notice{border:1px solid #e8cfaa;background:#fff3df;color:#83591f;border-radius:10px;padding:14px 17px;font-size:12px}.controls{display:flex;flex-wrap:wrap;gap:12px;background:#fff;border:1px solid #d8e5ec;border-radius:11px;padding:14px;margin:17px 0;position:sticky;top:0;z-index:2}label{display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:700;color:#617e90}select{font:inherit;font-size:12px;background:#fff;color:#163c54;border:1px solid #c8dce6;border-radius:7px;padding:8px;max-width:300px}select:focus{outline:2px solid #479cb5}.note{background:#e8f2f6;border-left:3px solid #298aa5;padding:11px 15px;font-size:12px}.legends,.cards{display:grid;grid-template-columns:1fr 1fr;gap:17px;margin:16px 0}.legend{font-size:11px;background:#fff;padding:12px;border:1px solid #dce7ed;border-radius:8px}.gradient{height:9px;border-radius:5px;margin-top:8px;background:linear-gradient(90deg,#440154,#414487,#2a788e,#22a884,#7ad151,#fde725)}.case-card{min-width:0;background:#fff;border:1px solid #dce7ed;border-radius:13px;padding:18px;box-shadow:0 4px 15px #17384b06}.case-card h2{font-size:19px;margin:5px 0}.badge{font-size:11px;display:inline-block;padding:4px 9px;border-radius:15px;background:#e9f3f7;color:#276b83}.case-card.C1 .badge{background:#fff0db;color:#8b601e}.small{font-size:11px;color:#627e90}.stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:13px 0}.stats div{background:#f1f6f9;border-radius:7px;padding:9px}.stats span{display:block;font-size:10px;color:#607d8e}.stats b{display:block;font-size:13px;font-variant-numeric:tabular-nums;margin-top:4px}.source{font-size:11px;color:#3b647c;overflow-wrap:anywhere;min-height:40px}canvas{width:100%;height:175px;display:block}.field-map{height:290px;border-top:1px solid #e4edf2}.top{display:grid;grid-template-columns:1fr 1fr;gap:8px;border-top:1px solid #e4edf2;padding-top:10px}figure{margin:0;min-width:0}figcaption{text-align:center;font-size:10px;color:#607e90}.scroll{overflow:auto;background:#fff;border:1px solid #d9e6ed;border-radius:9px;margin:12px 0}table{border-collapse:collapse;width:100%;font-size:11px;white-space:nowrap}th,td{padding:9px 11px;border-bottom:1px solid #e3edf2;text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}th{background:#eaf2f6}tr:last-child td{border:0}h2.section{font-size:19px;margin:27px 0 9px}h3{font-size:13px}details{border-top:1px solid #d2e3eb;padding:12px 0;margin-top:12px}summary{cursor:pointer;color:#2e6e89;font-size:12px;font-weight:700}.muted{font-size:11px;color:#617e90}pre{font-size:10px;white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf2f6;border-radius:7px;padding:12px}.hover{background:#153d52;color:#d6eaf3;font-size:11px;padding:10px 14px;border-radius:8px;position:sticky;bottom:5px;z-index:3}.role{font-size:10px;color:#607d8e}.role i{display:inline-block;width:9px;height:9px;margin:0 4px 0 9px}.out0{background:#e78b50}.out1{background:#4386c9}.gnd{background:#bdcbd4}.footer{font-size:11px;color:#607d8e;line-height:1.8;margin:18px 0}a{color:#176d91}@media(max-width:760px){main{padding:13px}.cards,.legends{grid-template-columns:1fr}.controls{position:relative;gap:9px}label{flex:1 1 45%}select{max-width:100%;width:100%;font-size:11px}.case-card{padding:14px}header{padding:25px 18px}.stats b{font-size:12px}}'''


def render(payload: dict) -> str:
    """Return a gzip/base64-packed self-contained HTML string, without I/O.

    Float16 is used only for native-cell display. Source Float64 statistics,
    source/input definitions and ratios remain authoritative and unmodified.
    """
    validate(payload)
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    packed = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode('ascii')
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode('ascii')
    cards = []
    for key, title, tag, desc in (
        ('TIS', '현재 best1 · f35', '물리4 pads · 독립2 outputs · 900 mm²', '모서리 완화형 native 계단 윤곽. 두 기본파3 kHz/3.03 kHz의 실제 합성 구동.'),
        ('C1', '단일 전극쌍 · 3 kHz sine', '물리2 pads · 독립1 output · 450 mm²', '15×15 mm 정방형 source와 귀환 전극을 포함한 실제 전극쌍. TIS와 전극 형상이 다릅니다.'),
    ):
        cards.append('<article class="case-card '+key+'" data-case-id="'+key+'"><span class="badge">'+tag+'</span><h2>'+title+'</h2><p class="small">'+desc+'</p><div id="'+key+'-stats" class="stats"></div><p id="'+key+'-source" class="source"></p><canvas id="'+key+'-field" class="field-map"></canvas><p id="'+key+'-plane" class="small"></p><div class="top"><figure><canvas id="'+key+'-layout" class="layout-map"></canvas><figcaption>z=0 정확한 물리 polygon · 배선</figcaption></figure><figure><canvas id="'+key+'-contact" class="contact-map"></canvas><figcaption>z=0 접촉 normal J RMS · native patch 셀 표시</figcaption></figure></div></article>')
    template = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-__HASH__'; style-src 'unsafe-inline'"><title>현재 best1 vs 단일 전극쌍 · 작업1</title><style>__CSS__</style><body>
<header><div class="eyebrow">TASK 1 · EXISTING NATIVE RESPONSE · RMS MATCH</div><h1>현재 best1과 단일 전극쌍을 같은 RMS에서 비교</h1><p>목표 ROI 에너지 RMS 또는 중심20 mm RMS를 맞추는 데 필요한 실제 source Vpp·전류·피부 부담을 나란히 확인합니다. 전기장 RMS 일치는 TIS 변조·공간분포·생리적 활성화의 일치가 아닙니다.</p></header>
<main><div class="notice"><b>전극 형상과 접촉면적이 다른 대조입니다.</b> TIS는 모서리 완화형4개/900 mm²·2출력이고, C1은 정방형2개/450 mm²·1출력입니다. 같은 모서리 완화형의2전극 native 응답은 이 비교에 없습니다. 따라서 차이를 TIS 방식 하나의 인과 효과로 분리할 수 없습니다. 두 경우 모두 기존50 Ω와 공통 GND 귀환을 유지합니다.</div>
<section class="controls" aria-label="저장된 비교 선택"><label for="mode">TIS 기준 진폭<select id="mode"></select></label><label for="match">C1에 맞출 전기장 RMS<select id="match"></select></label><label for="plane">단면<select id="plane"></select></label><label for="depth">XY 실제 깊이<select id="depth"></select></label><label for="range">공통 색상 범위<select id="range"></select></label></section><p id="loading" class="note">내장된 gzip 데이터를 해제하고 있습니다. 외부 네트워크를 사용하지 않습니다.</p><p id="match-note" class="note"></p>
<div class="legends"><div class="legend"><span id="field-legend"></span><div class="gradient"></div></div><div class="legend"><span id="contact-legend"></span><div class="gradient"></div></div></div><p class="role"><i class="out0"></i>out0 <i class="out1"></i>out1 <i class="gnd"></i>공통 GND 귀환 · 주ROI r≤5 mm/깊이15–20 mm · +z 피부 표면0에서 안쪽</p>
<section class="cards">__CARDS__</section><p id="hover" class="hover">셀 위의 포인터로 실제 native 좌표와 표시값을 확인합니다.</p><p class="footer">지도는 저장된 native RMS scalar의 Float16 표시이며 raw E의 순간값이나 TIS 변조 지도가 아닙니다. 보간하지 않고 실제 비균일 z face 간격으로 그립니다. 정량 표는 원래 Float64 통계를 사용합니다. NaN은 영역 밖·미지원이지0이 아닙니다. 목표 범위 clipping은 표시만 바꾸며 표면 층 경계의 높은 값을 깊이 집중으로 해석하지 않습니다. 접촉 J 부분접촉면은 해당 native 셀로 표시합니다. 정확 형상은 별도 polygon을 참조합니다. 체적 SC+dermis J 지도는 미제공이고 최대/P95 통계만 아래에 있습니다.</p>
<h2 class="section">실제 source Vpp는 각 출력과 비교</h2><div id="source-ratios"></div><p class="muted">모든 source Vpp는50 Ω 앞 open/high-Z 전체 합성 파형의 최대−최소입니다. 주파수별 Vpp가 아닙니다. 부하 연결 metal Vpp·접촉 RMS 전압·실제 계측기 loading을 서로 구분합니다. raw/skin8 선택은 TIS 기준 진폭을 뜻하며, C1에는 선택한 RMS에 맞춘 별도 source Vpp를 적용합니다. skin8은 원래8개 피부·접촉 수치 제한만 적용하며 source 전력/1Vpp 상한은 없어 실제 source가1Vpp를 넘을 수 있습니다.</p>
<h2 class="section">RMS 일치와 공간분포 차이</h2><div id="shape"></div><div id="regions"></div><p class="muted">에너지 RMS=sqrt(가중 평균(E_RMS²))이며 평균 E_RMS와 다릅니다. 두 매칭 정의는 별개이고 선택하지 않은 정의는 일반적으로 일치하지 않습니다. 실제 fractional ROI와 native 표현 체적을 유지합니다. ±10% 분포 비율은 생리적 활성 범위가 아닙니다.</p>
<h2 class="section">TIS 변조와 단일 sine의 envelope는 별도</h2><div id="modulation"></div>
<h2 class="section">전류밀도·접촉전압·전력의 개별 비교</h2><div id="burdens"></div><p class="muted">접촉면 normal J의 면적 가중P95와 피부 체적 벡터 J의 체적 가중P95는 다른 통계입니다. RMS 목표만 맞췄고 전류·전력·접촉면적·피부 부담을 동시에 일치시킨 비교가 아닙니다. 전력이 작아도 접촉 J가 더 높을 수 있습니다. 수치 기준은 인체안전 한계가 아닙니다.</p>
<details><summary>signed 출력별/주파수별 전력과 실제 각층 손실</summary><div id="signed-power"></div><pre id="losses"></pre><p class="muted">음수와 비활성 주파수0을 보존합니다. phasor power와 native quadratic loss는 각 원형 수치이며 방법간 미세 잔차를0으로 강제하지 않습니다. 과거 skin_power_W=SC+contact는 SC+dermis 총손실이 아닙니다.</p></details>
<details><summary>무부하 프로브 출처와 실제 계측기 보류</summary><pre id="probes"></pre><p class="muted">프로브 중심과 팁 간격5 mm는 별개입니다. 실제 ETA5001의 tip별4MΩ∥7pF 두 shunt는 차동8MΩ/3.5pF의 등가이며 별도 병렬 branch를 더하지 않습니다. Scope 입력은 probe 출력 downstream입니다. 실제 port impedance/ground/switch/대역폭·보정이 없어 phantom-loaded 예측은 보류합니다.</p></details>
<details><summary>소스 · native 재사용 · 검증 범위</summary><pre id="provenance"></pre></details><div class="notice"><b>미채택 진단</b> best1은 현재 선정 기준의 대표 후보이며 모든 검증을 통과한 해법이 아닙니다. nominal PBS 접촉/SC2 기존 응답을 비교합니다. 전체 SC/XY/bulk/edge/contact 수렴·PBS 피부 전이·실험·인체안전·생리적 활성화·장비 sink/compliance는 미검증입니다. 과거 e7의 SC4 진단을 f35에 이전하지 않습니다. 저장 입력 해시·표시 검증과 독립 시뮬레이션 재현은 별개입니다. 신규 PDE는 수행하지 않습니다.</div><p class="footer"><a href="../CLOUD_VOLUME_RESULTS_20261021_v8.html">과거4·8·12·16-pad 원본 화면</a></p><noscript>오프라인 JavaScript와 브라우저 내장 gzip 해제가 필요합니다. 외부 서비스·스크립트·네트워크는 사용하지 않습니다.</noscript></main>
<script id="packed" type="application/octet-stream">__PACKED__</script><script>__SCRIPT__</script></body></html>'''
    return template.replace('__HASH__', script_hash).replace('__CSS__', CSS).replace('__CARDS__', ''.join(cards)).replace('__SCRIPT__', SCRIPT).replace('__PACKED__', packed)
