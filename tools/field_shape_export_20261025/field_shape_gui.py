"""Offline native-vector display; pure rendering, no research I/O on import.

The original centred-C1 GUI, its packed scientific payload and executable script
remain unchanged. This extension renders selected native-cell complex vectors;
it does not solve a PDE, calculate modulation, trace field lines or certify fat
properties. Instantaneous E and carrier RMS are separate physical quantities.
"""
from __future__ import annotations
import base64
import gzip
import hashlib
import json
import math
import re


CSS = r'''
#field-shape{margin:25px 0;padding:18px;background:#f9fcfd;border:1px solid #c7dde8;border-radius:12px}
#field-shape h2{margin:0 0 8px;font-size:23px}#field-shape p{max-width:1120px}
.shape-controls{display:flex;flex-wrap:wrap;gap:12px;padding:13px;border:1px solid #d8e6ed;background:white;border-radius:9px;margin:15px 0}
.shape-controls label{min-width:135px;flex:1 1 135px}.shape-controls select{max-width:none;width:100%}.shape-time{flex:2 1 240px!important}
.shape-controls input[type=range]{width:100%;accent-color:#17677e}.shape-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}.shape-card{min-width:0;padding:14px;background:white;border:1px solid #dce8ee;border-radius:10px}
.shape-card h3{font-size:17px;margin:2px 0 5px}.shape-map{height:340px!important;width:100%;display:block}.shape-iso{height:220px!important;width:100%;display:block}
.shape-legend{margin:10px 0;background:white;border:1px solid #d6e5ed;border-radius:8px;padding:12px}.shape-color{height:10px;background:linear-gradient(90deg,#440154,#414487,#2a788e,#22a884,#7ad151,#fde725);border-radius:3px}.shape-ticks{display:flex;justify-content:space-between;font-variant-numeric:tabular-nums;font-size:10px;padding-top:3px}
.shape-hover{font-size:12px;background:#123d52;color:#e4f4fa;border-radius:8px;padding:12px;margin:12px 0;min-height:65px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.shape-state{font-size:11px;color:#46677c;overflow-wrap:anywhere}.shape-note{font-size:12px;color:#496b7f}.shape-proof{font-size:11px}
@media(max-width:760px){#field-shape{padding:12px}.shape-row{grid-template-columns:1fr}.shape-map{height:330px!important}.shape-controls{padding:10px}.shape-controls label{min-width:0;flex:1 1 42%}.shape-card{padding:10px}.shape-iso{height:205px!important}}
'''


SCRIPT = r'''
(async()=>{
'use strict';
const $=id=>document.getElementById(id),root=$('field-shape'),status=$('shape-status');
const enc=$('field-shape-data').textContent.trim(),bytes=Uint8Array.from(atob(enc),x=>x.charCodeAt(0));
const raw=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
const P=JSON.parse(raw),A=P.analysis,COLORS=[[68,1,84],[65,68,135],[42,120,142],[34,168,132],[122,209,81],[253,231,37]];
const nice=x=>Number.isFinite(x)?Number(x).toPrecision(6):'미제공';
const decode=o=>{const s=atob(o.data_base64),b=Uint8Array.from(s,c=>c.charCodeAt(0)),d=new DataView(b.buffer);const a=new Float32Array(b.length/4);for(let i=0;i<a.length;i++)a[i]=d.getFloat32(i*4,true);return a;};
for(const p of P.planes)for(const c of ['TIS','C1'])for(const d of Object.values(p.fields[c]))d.decoded=decode(d);
const planeSelect=$('shape-plane');
for(const p of P.planes){const o=document.createElement('option');o.value=p.id;o.textContent=p.kind+' · '+p.fixed_axis+'='+nice(p.fixed_mm)+' mm'+(p.kind==='XY'?' (요청 깊이 '+nice(p.requested_mm)+' mm)':'');planeSelect.appendChild(o);}
for(const m of Object.keys(A.modes)){const o=document.createElement('option');o.value=m;o.textContent=m==='skin_contact_only'?'기존 skin8 부담 조건':'기존 원 인가전압 조건';$('shape-mode').appendChild(o);}
$('shape-mode').value='skin_contact_only';
const matchNames={ROI_energy_RMS:'목표 ROI 에너지 RMS 일치',centre20_E_RMS:'중앙 깊이20 mm RMS 일치'};
for(const m of Object.keys(A.modes[$('shape-mode').value].matches)){const o=document.createElement('option');o.value=m;o.textContent=matchNames[m]||m;$('shape-match').appendChild(o);}
$('shape-match').value='ROI_energy_RMS';
const cache={views:null,plane:null,transform:{},time_ms:0,scale:0};
function color(v,max){const z=Math.min(1,Math.max(0,max>0?v/max:0))*(COLORS.length-1),i=Math.min(COLORS.length-2,Math.floor(z)),t=z-i,a=COLORS[i],b=COLORS[i+1];return 'rgb('+a.map((v,k)=>Math.round(v+(b[k]-v)*t)).join(',')+')';}
function canvas(id){const el=$(id),r=el.getBoundingClientRect(),d=window.devicePixelRatio||1;el.width=Math.round(r.width*d);el.height=Math.round(r.height*d);const g=el.getContext('2d');g.scale(d,d);return {el,g,w:r.width,h:r.height};}
function instant(p,c,frequency,t,scale){const n=p.native_indices.length,E=new Float64Array(n*3);for(const [f,d]of Object.entries(p.fields[c])){if(frequency!=='all'&&frequency!==f)continue;const ph=2*Math.PI*Number(f)*t,co=Math.cos(ph),si=Math.sin(ph),v=d.decoded;for(let i=0;i<n*3;i++)E[i]+=scale*(v[i*2]*co-v[i*2+1]*si);}
const mag=new Float64Array(n);let max=0;for(let i=0;i<n;i++){if(p.native_indices[i]<0){mag[i]=NaN;continue;}mag[i]=Math.hypot(E[i*3],E[i*3+1],E[i*3+2]);max=Math.max(max,mag[i]);}return {E,mag,max};}
function edge(a,provided){if(provided&&provided.length===a.length+1)return provided;const b=[a[0]-(a[1]-a[0])/2];for(let i=1;i<a.length;i++)b.push((a[i-1]+a[i])/2);b.push(a[a.length-1]+(a[a.length-1]-a[a.length-2])/2);return b;}
function plot(c,p,V,max){const {el,g,w,h}=canvas('shape-'+c),pad={l:49,r:15,t:17,b:44},ue=edge(p.u_mm,p.u_edges_mm),ve=edge(p.v_mm,p.v_edges_mm),nu=p.u_mm.length,nv=p.v_mm.length,umin=ue[0],umax=ue.at(-1),vmin=ve[0],vmax=ve.at(-1),width=w-pad.l-pad.r,height=h-pad.t-pad.b;
const xp=u=>pad.l+(u-umin)/(umax-umin)*width,yp=v=>pad.t+(v-vmin)/(vmax-vmin)*height;
g.clearRect(0,0,w,h);g.fillStyle='#e9f0f3';g.fillRect(pad.l,pad.t,width,height);
for(let j=0;j<nv;j++)for(let i=0;i<nu;i++){const k=j*nu+i;if(p.native_indices[k]<0)continue;g.fillStyle=color(V.mag[k],max);g.fillRect(xp(ue[i]),yp(ve[j]),Math.max(.3,xp(ue[i+1])-xp(ue[i])+.2),Math.max(.3,yp(ve[j+1])-yp(ve[j])+.2));}
g.save();g.beginPath();g.rect(pad.l,pad.t,width,height);g.clip();
if(p.kind!=='XY'){for(const z of [.1,5.1,10.1]){g.beginPath();g.strokeStyle='rgba(255,255,255,.8)';g.setLineDash([4,3]);g.moveTo(pad.l,yp(z));g.lineTo(w-pad.r,yp(z));g.stroke();}g.setLineDash([]);
if(Math.abs(p.fixed_mm)<=5){const half=Math.sqrt(25-p.fixed_mm*p.fixed_mm);g.strokeStyle='#ffdd8c';g.lineWidth=2;g.strokeRect(xp(-half),yp(15),xp(half)-xp(-half),yp(20)-yp(15));}}
else if(p.fixed_mm>=15&&p.fixed_mm<=20){g.beginPath();g.strokeStyle='#ffdd8c';g.lineWidth=2;g.ellipse(xp(0),yp(0),5/(umax-umin)*width,5/(vmax-vmin)*height,0,0,Math.PI*2);g.stroke();}
const ax0=p.kind==='YZ'?1:0,ax1=p.kind==='XY'?1:2,stepU=Math.max(1,Math.round(nu/15)),stepV=Math.max(1,Math.round(nv/14)),length=Math.min(width/15,height/14)*.74,arrows=[];
for(let j=Math.floor(stepV/2);j<nv;j+=stepV)for(let i=Math.floor(stepU/2);i<nu;i+=stepU){const k=j*nu+i;if(p.native_indices[k]<0)continue;const a=V.E[k*3+ax0],b=V.E[k*3+ax1],q=Math.hypot(a,b);if(!(q>Math.max(max*1e-10,1e-14)))continue;
let dx=a/(umax-umin)*width,dy=b/(vmax-vmin)*height,l=Math.hypot(dx,dy);dx=dx/l*length;dy=dy/l*length;if($('shape-arrows').value==='magnitude'){const m=max>0?q/max:0;dx*=m;dy*=m;}const x=xp(p.u_mm[i]),y=yp(p.v_mm[j]),x0=x-dx*.5,y0=y-dy*.5,x1=x+dx*.5,y1=y+dy*.5,ang=Math.atan2(dy,dx),head=Math.max(2.2,Math.min(4,length*.21));
const draw=()=>{g.beginPath();g.moveTo(x0,y0);g.lineTo(x1,y1);g.moveTo(x1-head*Math.cos(ang-.55),y1-head*Math.sin(ang-.55));g.lineTo(x1,y1);g.lineTo(x1-head*Math.cos(ang+.55),y1-head*Math.sin(ang+.55));g.stroke();};g.lineWidth=2.8;g.strokeStyle='rgba(255,255,255,.88)';draw();g.lineWidth=1;g.strokeStyle='#102c40';draw();arrows.push(k);}
g.restore();g.strokeStyle='#527488';g.lineWidth=1;g.strokeRect(pad.l,pad.t,width,height);g.font='10px system-ui';g.fillStyle='#32556a';g.textAlign='center';for(const v of[-25,-10,0,10,25])if(v>=umin&&v<=umax){g.fillText(String(v),xp(v),h-24);}g.fillText(p.u_label,w/2,h-7);g.textAlign='right';for(const v of(p.kind==='XY'?[-25,-10,0,10,25]:[0,5,10,15,20,25]))if(v>=vmin&&v<=vmax)g.fillText(String(v),pad.l-6,yp(v)+3);
g.save();g.translate(12,h/2);g.rotate(-Math.PI/2);g.textAlign='center';g.fillText(p.v_label,0,0);g.restore();
if(p.kind!=='XY'){g.textAlign='left';g.fillText('z=0 표면 / 깊이 +z ↓',pad.l+5,pad.t+13);}cache.transform[c]={xp,yp,umin,umax,vmin,vmax,pad,width,height,arrows};return arrows.length;}
function iso(c){const {g,w,h}=canvas('shape-iso-'+c),caseData=P.cases[c],cx=w*.50,top=h*.23,sx=Math.min(w/64,6),sy=sx*.30,sz=h*.019;
const point=(x,y,z)=>[cx+(x-y)*sx*.70,top+(x+y)*sy+z*sz],circle=(r,z)=>{g.beginPath();for(let i=0;i<=100;i++){const a=i/100*2*Math.PI,[x,y]=point(r*Math.cos(a),r*Math.sin(a),z);i?g.lineTo(x,y):g.moveTo(x,y);}g.closePath();};
g.clearRect(0,0,w,h);circle(25,25.1);g.fillStyle='#dbe8ee';g.fill();g.strokeStyle='#819eaf';g.stroke();for(const angle of[.25*Math.PI,1.25*Math.PI]){const x=25*Math.cos(angle),y=25*Math.sin(angle),a=point(x,y,0),b=point(x,y,25.1);g.beginPath();g.moveTo(...a);g.lineTo(...b);g.stroke();}
circle(25,0);g.fillStyle='rgba(222,238,245,.86)';g.fill();g.strokeStyle='#6b8b9d';g.stroke();
for(const z of[15,20]){circle(5,z);g.fillStyle='rgba(237,168,68,.23)';g.fill();g.strokeStyle='#c78b35';g.stroke();}for(const angle of[0,Math.PI]){const a=point(5*Math.cos(angle),5*Math.sin(angle),15),b=point(5*Math.cos(angle),5*Math.sin(angle),20);g.beginPath();g.moveTo(...a);g.lineTo(...b);g.stroke();}
for(const p of(caseData.physical_outlines||[])){const poly=p.polygon_mm||[];if(!poly.length)continue;g.beginPath();for(let i=0;i<poly.length;i++){const v=point(poly[i][0],poly[i][1],0);i?g.lineTo(...v):g.moveTo(...v);}g.closePath();const node=p.node??((caseData.pad_centres||[]).find(x=>x.pad===p.pad)||{}).node;g.fillStyle=(node===0||node==='out0')?'#df8b54':(node===1||node==='out1')?'#478ac0':'#b3bdc7';g.fill();g.strokeStyle='#537183';g.stroke();}
g.font='10px system-ui';g.fillStyle='#36566a';g.fillText('D50 mm · 상면 전극 · 중앙 r5 / 깊이15–20 mm',8,h-8);const origin=point(-22,-22,0);for(const [label,dx,dy,dz]of[['x',9,0,0],['y',0,9,0],['+z 깊이',0,0,9]]){const q=point(-22+dx,-22+dy,dz);g.beginPath();g.strokeStyle='#36566a';g.moveTo(...origin);g.lineTo(...q);g.stroke();g.fillText(label,q[0]+3,q[1]+2);}}
function update(){const p=P.planes.find(x=>x.id===planeSelect.value)||P.planes[0],mode=$('shape-mode').value,match=$('shape-match').value,tms=Number($('shape-time').value),f=$('shape-frequency').value,m=A.modes[mode],scales={TIS:m.reference_amplitude_scale,C1:m.matches[match].amplitude_scale??m.matches[match].required_source_Vpp};
const views={TIS:instant(p,'TIS',f,tms/1000,scales.TIS),C1:instant(p,'C1',f,tms/1000,scales.C1)},max=Math.max(views.TIS.max,views.C1.max);cache.views=views;cache.plane=p;cache.time_ms=tms;cache.scale=max;
for(const c of['TIS','C1']){const count=plot(c,p,views[c],max);iso(c);$('shape-'+c+'-meta').textContent='case '+P.cases[c].case_id+' · '+P.cases[c].n_pads+' pads / '+P.cases[c].n_outputs+' outputs · 진폭 배율 '+nice(scales[c])+' · 표시 화살표 '+count;}
$('shape-time-value').textContent=nice(tms)+' ms / 3kHz 위상 '+nice((tms/1000*3000*360)%360)+'°';$('shape-range').textContent='공통 색 범위 0–'+nice(max)+' V/m · 현재 두 단면의 실제 순간 |E(t)| 최대 · 상한 clipping 없음';$('shape-ticks').replaceChildren(...[0,.25,.5,.75,1].map(v=>{const x=document.createElement('span');x.textContent=nice(v*max);return x;}));
$('shape-frequency-note').textContent=f==='all'?'TIS: 3000+3030 Hz 실제 합성 / C1: 3000 Hz sine. 시각은 두 경우의 같은 절대 t입니다.':f==='3030'?'3030 Hz 성분만 표시합니다. C1에는 이 성분이 없으므로 0 V/m입니다.':'3000 Hz 성분만 표시합니다. 두 출력의 같은 주파수 복소 기저를 먼저 합산했습니다.';
status.textContent='기존 native 복소장 재사용 · 이 표시 단계 새 PDE 0 · 원 centered C1 계산은 별도 1회 완료 · full convergence / 새 fat 검증 / 실험 미완료';root.dataset.rendered='true';root.dataset.commonMax=String(max);root.dataset.planeId=p.id;root.dataset.frequency=f;return {plane:p.id,frequency:f,time_ms:tms,common_max_V_m:max,mode,match,scales};}
for(const c of['TIS','C1'])$('shape-'+c).addEventListener('mousemove',event=>{if(!cache.plane)return;const p=cache.plane,tr=cache.transform[c],rect=event.currentTarget.getBoundingClientRect(),u=tr.umin+(event.clientX-rect.left-tr.pad.l)/tr.width*(tr.umax-tr.umin),v=tr.vmin+(event.clientY-rect.top-tr.pad.t)/tr.height*(tr.vmax-tr.vmin);if(u<tr.umin||u>tr.umax||v<tr.vmin||v>tr.vmax)return;
let i=0,j=0;for(let k=1;k<p.u_mm.length;k++)if(Math.abs(p.u_mm[k]-u)<Math.abs(p.u_mm[i]-u))i=k;for(let k=1;k<p.v_mm.length;k++)if(Math.abs(p.v_mm[k]-v)<Math.abs(p.v_mm[j]-v))j=k;const k=j*p.u_mm.length+i;if(p.native_indices[k]<0){$('shape-hover').textContent='팬텀 외부 · native 셀 없음';return;}const xyz=p.kind==='XY'?[p.u_mm[i],p.v_mm[j],p.fixed_mm]:p.kind==='XZ'?[p.u_mm[i],p.fixed_mm,p.v_mm[j]]:[p.fixed_mm,p.u_mm[i],p.v_mm[j]],E=cache.views[c].E.slice(k*3,k*3+3),out=p.kind==='XY'?2:p.kind==='XZ'?1:0;
$('shape-hover').textContent=c+' · native cell '+p.native_indices[k]+' · xyz=['+xyz.map(nice).join(', ')+'] mm · t='+nice(cache.time_ms)+' ms · Ex/Ey/Ez=['+Array.from(E,nice).join(', ')+'] V/m · |E|='+nice(cache.views[c].mag[k])+' V/m · 단면 수직 성분 '+['Ex','Ey','Ez'][out]+'='+nice(E[out])+' V/m. Float32 표시는 원 Float64 정확도 증명이 아닙니다.';});
for(const id of['shape-plane','shape-mode','shape-match','shape-frequency','shape-arrows'])$(id).addEventListener('change',update);$('shape-time').addEventListener('input',update);let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(update,100);});
function syncFromOriginal(){for(const [oldId,newId]of[['mode','shape-mode'],['match','shape-match']]){const original=$(oldId),target=$(newId);if(original&&Array.from(target.options).some(o=>o.value===original.value))target.value=original.value;}update();}
function syncToOriginal(){for(const [oldId,newId]of[['mode','shape-mode'],['match','shape-match']]){const original=$(oldId);if(original&&original.value!==$(newId).value){original.value=$(newId).value;original.dispatchEvent(new Event('change'));}}}
for(const [oldId,newId]of[['mode','shape-mode'],['match','shape-match']]){if($(oldId))$(oldId).addEventListener('change',syncFromOriginal);$(newId).addEventListener('change',syncToOriginal);}
$('shape-proofs').textContent=JSON.stringify({reference_result_commit:P.reference_result_commit,cases:P.cases,proofs:P.proofs,source_sha256:P.source_sha256,holds:P.holds},null,2);
function validateForTest(){try{const must=(ok,msg)=>{if(!ok)throw Error(msg);},p=cache.plane;must(p&&cache.views,'Current actual-data view required');let expectedMax=0,currentComponents=0,maxNormError=0,maxArrowFraction=0;
for(const c of['TIS','C1']){const V=cache.views[c],ax0=p.kind==='YZ'?1:0,ax1=p.kind==='XY'?1:2;for(let k=0;k<p.native_indices.length;k++){if(p.native_indices[k]<0)continue;const components=Array.from(V.E.slice(k*3,k*3+3));must(components.every(Number.isFinite),'Nonfinite actual instantaneous component');const norm=Math.hypot(...components);maxNormError=Math.max(maxNormError,Math.abs(norm-V.mag[k]));must(Number.isFinite(V.mag[k])&&Math.abs(norm-V.mag[k])<=1e-12*Math.max(1,norm),'Full vector/out-of-plane norm mismatch');expectedMax=Math.max(expectedMax,norm);const q=Math.hypot(V.E[k*3+ax0],V.E[k*3+ax1]);if(cache.scale>0)maxArrowFraction=Math.max(maxArrowFraction,q/cache.scale);currentComponents+=3;}}
must(Number.isFinite(cache.scale)&&cache.scale===expectedMax,'Shared unclipped maximum is not actual two-case maximum');must(maxArrowFraction<=1+1e-12,'Shared projected-arrow magnitude denominator failed');
let absent3030=0;for(const plane of P.planes){const zero=instant(plane,'C1','3030',0.0000833333333333,1);for(let k=0;k<plane.native_indices.length;k++)if(plane.native_indices[k]>=0){must(zero.E[k*3]===0&&zero.E[k*3+1]===0&&zero.E[k*3+2]===0&&zero.mag[k]===0,'C1 absent3030Hz is nonzero');absent3030++;}}
let waveformComponents=0,maximumWaveformError=0;const perCase={};for(const c of['TIS','C1']){const ref=P.proofs[c+'_waveform_reference'];must(ref&&ref.native_indices.length===17&&ref.field_V_m.length===17,'Seventeen independent Float64 waveform references required');let maximumError=0;for(let n=0;n<ref.native_indices.length;n++){const native=ref.native_indices[n];let plane=null,index=-1;for(const x of P.planes){const j=x.native_indices.indexOf(native);if(j>=0){plane=x;index=j;break;}}must(plane!==null,'Waveform reference not in an exported native plane');const actual=instant(plane,c,'all',ref.time_s,1);let roundingBound=0;for(const [f,d]of Object.entries(plane.fields[c])){const phase=2*Math.PI*Number(f)*ref.time_s;must(d.precision&&d.precision.passed,'Declared conversion proof required');roundingBound+=(Math.abs(Math.cos(phase))+Math.abs(Math.sin(phase)))*d.precision.maximum_absolute_error_V_m;}for(let a=0;a<3;a++){const value=actual.E[index*3+a],target=ref.field_V_m[n][a],error=Math.abs(value-target);must(Number.isFinite(target)&&Number.isFinite(value)&&error<=roundingBound+1e-10*Math.max(1,Math.abs(target)),'Native Float64 waveform/Float32 display mismatch '+c+'/'+native+'/'+a);maximumError=Math.max(maximumError,error);waveformComponents++;}}perCase[c]={samples:17,components:51,maximum_absolute_error_V_m:maximumError};maximumWaveformError=Math.max(maximumWaveformError,maximumError);}
return {passed:true,finite_current_vector_components:currentComponents,full_vector_norm_maximum_error_V_m:maxNormError,shared_unclipped_maximum_V_m:expectedMax,maximum_projected_arrow_fraction:maxArrowFraction,C1_absent3030_zero_cells:absent3030,waveform_components_checked:waveformComponents,maximum_waveform_error_V_m:maximumWaveformError,waveform_references:perCase};}catch(e){return {passed:false,error:e.message};}}
window.task1FieldShape=Object.freeze({render:update,payload:P,getState:()=>({plane_id:cache.plane?.id,common_max_V_m:cache.scale,time_ms:cache.time_ms}),instantForTest:instant,validateForTest});syncFromOriginal();
})().catch(e=>{document.getElementById('shape-status').textContent='전기장 방향 표시 실패: '+e.message;console.error(e);});
'''


SECTION = r'''
<section id="field-shape" aria-label="실제 native 전기장 방향과 공간 분포">
<h2>전기장의 공간적 형태 · 순간 벡터와 전극 배치</h2>
<p class="shape-note">색은 실제 합성 순간 전기장 <b>|E(t)| [V/m]</b>, 화살표는 그 전기장의 <b>선택한 단면 안 방향</b>입니다. RMS에는 하나의 방향이 없으며 이 화면을 TIS 변조 지도로 해석하지 않습니다. 단면 밖 성분도 색의 크기에 포함하고, 마우스를 올리면 Ex/Ey/Ez를 각각 표시합니다.</p>
<div class="shape-controls">
<label>단면과 실제 native 위치<select id="shape-plane"></select></label>
<label>기존 TIS 구동 기준<select id="shape-mode"></select></label>
<label>단일 전극쌍 RMS 비교 기준<select id="shape-match"></select></label>
<label>표시 주파수<select id="shape-frequency"><option value="all">실제 전체 합성파</option><option value="3000">3000 Hz 성분</option><option value="3030">3030 Hz 성분</option></select></label>
<label>화살표 길이<select id="shape-arrows"><option value="direction">같은 길이 · 방향만</option><option value="magnitude">공통 |E| 상한에 비례</option></select></label>
<label class="shape-time">실제 시간 t · <output id="shape-time-value"></output><input id="shape-time" type="range" min="0" max="33.333333" step="any" value="0.083333333" aria-label="합성 순간 전기장의 시간 ms"></label>
</div>
<p class="shape-note">구동 기준과 RMS 비교 기준 선택은 위의 기존 결과 표와 동기화됩니다. 단면·주파수·시간·화살표 선택은 이 벡터 화면에 적용됩니다.</p><p id="shape-frequency-note" class="shape-note"></p>
<div class="shape-legend"><b id="shape-range"></b><div class="shape-color"></div><div id="shape-ticks" class="shape-ticks"></div></div>
<div class="shape-row">
<article class="shape-card"><h3>TIS · 현재 best1 f35</h3><p id="shape-TIS-meta" class="shape-state"></p><canvas id="shape-TIS" class="shape-map" aria-label="TIS 순간 전기장 단면과 방향"></canvas><canvas id="shape-iso-TIS" class="shape-iso" aria-label="TIS 실제 상면 전극과 원통 팬텀의 등각 투영"></canvas></article>
<article class="shape-card"><h3>중앙 y=0 · 단일 전극쌍</h3><p id="shape-C1-meta" class="shape-state"></p><canvas id="shape-C1" class="shape-map" aria-label="중앙 단일 전극쌍 순간 전기장 단면과 방향"></canvas><canvas id="shape-iso-C1" class="shape-iso" aria-label="단일 전극쌍 실제 상면 전극과 원통 팬텀의 등각 투영"></canvas></article>
</div>
<div id="shape-hover" class="shape-hover">단면에 마우스를 올리면 실제 native 셀의 xyz 좌표와 부호를 포함한 Ex/Ey/Ez가 나타납니다.</div>
<p class="shape-note">표면 z=0, 깊이는 +z입니다. 흰 점선은 층 경계 0.1/5.1/10.1 mm, 노란 선은 해당 단면과 목표 r≤5 mm·깊이15–20 mm 부피의 교차입니다. 그림은 저장된 native 셀과 드문드문 선택한 벡터를 보여주며 연속 장선 추적이나 공간 보간 결과가 아닙니다. 아래 등각 그림은 실제 상면 전극 윤곽과 목표 부피의 위치 설명입니다.</p>
<p class="shape-note">선택 시간에 따라 두 경우의 순간 전기장은 다를 수 있습니다. 기존에 맞춘 것은 목표 ROI 또는 중앙 한 점의 <b>전체 carrier RMS</b>입니다. 같은 RMS가 같은 파형·변조·전류 부담·활성화를 뜻하지 않습니다. 전체 단면 최대에 맞춘 공통 색 범위를 사용하므로 표층 최대가 크면 깊은 영역의 색 차이가 작게 보일 수 있습니다. 층 경계의 큰 장을 깊이 집중으로 해석하지 않습니다.</p>
<p id="shape-status" class="shape-state">저장된 native 복소 벡터를 읽는 중…</p>
<details class="shape-proof"><summary>벡터 출처 · 표시 정밀도 · 검증 범위</summary><pre id="shape-proofs"></pre></details>
</section>
'''


def validate(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('planes'), list) or not payload['planes']:
        raise ValueError('Nonempty declared native vector planes required')
    if payload.get('reference_result_commit') != 'b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe':
        raise ValueError('Original completed centred C1 result commit required')
    modes = payload['analysis']['modes']
    for m in modes.values():
        if not math.isfinite(m['reference_amplitude_scale']) or m['reference_amplitude_scale'] <= 0:
            raise ValueError('Saved positive reference amplitude required')
        for match in m['matches'].values():
            if not math.isfinite(match['required_source_Vpp']) or match['required_source_Vpp'] <= 0:
                raise ValueError('Saved positive C1 matching amplitude required')
    for p in payload['planes']:
        if p['kind'] not in ('XY','XZ','YZ') or len(p['native_indices']) != len(p['u_mm'])*len(p['v_mm']):
            raise ValueError('Exact native plane lattice required')
        for case in ('TIS','C1'):
            for f,d in p['fields'][case].items():
                if f not in ('3000','3030') or d['dtype'] != '<f4' or d['shape'] != [len(p['v_mm']),len(p['u_mm']),3,2]:
                    raise ValueError('Explicit finite-frequency real/imag vector ABI required')
                if len(base64.b64decode(d['data_base64'],validate=True)) != math.prod(d['shape'])*4:
                    raise ValueError('Exact native display descriptor byte count required')
    return payload


def render(base_html: str, shape_payload: dict) -> str:
    """Add a hash-authorized offline extension while preserving frozen scripts."""
    validate(shape_payload)
    if base_html.count('</main>') != 1 or base_html.count('</body>') != 1 or base_html.count('</style>') != 1:
        raise ValueError('Expected one frozen main/body/style insertion anchor')
    if 'id="field-shape"' in base_html:
        raise ValueError('Do not extend an already extended GUI')
    raw=json.dumps(shape_payload,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    packed=base64.b64encode(gzip.compress(raw,compresslevel=9,mtime=0)).decode('ascii')
    digest=base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode('ascii')
    csp=re.search(r'script-src ([^;\"]+)',base_html)
    if csp is None:
        raise ValueError('Frozen strict CSP script directive required')
    value=csp.group(0)+" 'sha256-"+digest+"'"
    result=base_html[:csp.start()]+value+base_html[csp.end():]
    result=result.replace('</style>',CSS+'</style>',1)
    result=result.replace('<main>','<main><p class="note"><a href="#field-shape">새 전기장 형태 보기: 실제 순간 벡터 · 단면 비교 · 전극과 목표 부피의 등각 그림 ↓</a></p>',1)
    result=result.replace('</main>',SECTION+'</main>',1)
    result=result.replace('</body>','<script id="field-shape-data" type="application/octet-stream">'+packed+'</script><script>'+SCRIPT+'</script></body>',1)
    if re.findall(r'<script>(.*?)</script>',base_html,re.S) != re.findall(r'<script>(.*?)</script>',result,re.S)[:-1]:
        raise ValueError('Original executable scripts changed unexpectedly')
    return result
