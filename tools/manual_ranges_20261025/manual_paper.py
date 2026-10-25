"""Pure patch of the reviewed paper figure for persistent user-selected viewports.

Only presentation and time sampling change. Native phasors, physical statistics,
projection/RMS/envelope formulae and existing numerical provenance are retained.
The parent owns data access, source pins, the execution lock and actual browser.
"""
from __future__ import annotations


def once(text,before,after):
    if text.count(before)!=1:
        raise ValueError('One reviewed paper anchor required: '+before[:100])
    return text.replace(before,after,1)


def function(script,name,replacement):
    marker='function '+name+'('
    if script.count(marker)!=1:
        raise ValueError('One reviewed function required: '+name)
    start=script.index(marker);stop=script.find('\nfunction ',start+len(marker))
    if stop<0:
        raise ValueError('Following reviewed function required: '+name)
    return script[:start]+replacement.strip()+script[stop:]


TICKS=r'''
function ticksMap(g,tr,kind){g.font='9px system-ui';g.fillStyle='#355c72';g.textAlign='center';for(const v of[tr.u0,(tr.u0+tr.u1)/2,tr.u1])g.fillText(nice(v,4),tr.x(v),tr.pad.t+tr.height+15);g.textAlign='right';for(const v of[tr.v0,(tr.v0+tr.v1)/2,tr.v1])g.fillText(nice(v,4),tr.pad.l-5,tr.y(v)+3);}
'''

MAP=r'''
function drawMap(c,m,p,V,max){const id='paper-map-'+c+'-'+m,{el,g,w,h}=cv(id),ue=p.u_edges_mm,ve=p.v_edges_mm,range=MR.get(id,{xMin:ue[0],xMax:ue.at(-1),yMin:ve[0],yMax:ve.at(-1),cMin:0,cMax:TASK1_LOCKED_E},{kind:'EMap',xLabel:p.u_label,yLabel:p.v_label,axisX:p.kind==='YZ'?'y':'x',axisY:p.kind==='XY'?'y':'z',colour:true,colorUnit:'V/m'}),tr=setupAxes(g,w,h,range.xMin,range.xMax,range.yMin,range.yMax,[p.u_label,p.v_label]),nu=p.u_mm.length,nv=p.v_mm.length;
el.dataset.xMin=String(range.xMin);el.dataset.xMax=String(range.xMax);el.dataset.yMin=String(range.yMin);el.dataset.yMax=String(range.yMax);el.dataset.vmin=String(range.cMin);el.dataset.vmax=String(range.cMax);el.dataset.scaleMode='manual';el.dataset.axisOrientation=p.kind==='XY'?'y_up':'depth_down';el.dataset.colorTransform=window.task1FixedScales.transform();if(p.kind==='XY'){const yy=tr.y;tr.y=v=>tr.pad.t+tr.height-(yy(v)-tr.pad.t);tr.up=true;}
let low=0,high=0,total=0,hidden=0;g.save();g.beginPath();g.rect(tr.pad.l,tr.pad.t,tr.width,tr.height);g.clip();for(let j=0;j<nv;j++)for(let i=0;i<nu;i++){const k=j*nu+i;if(p.native_indices[k]<0)continue;const value=V[k];total++;if(value<range.cMin)low++;if(value>range.cMax)high++;if(p.u_mm[i]<range.xMin||p.u_mm[i]>range.xMax||p.v_mm[j]<range.yMin||p.v_mm[j]>range.yMax)hidden++;if(ue[i+1]<range.xMin||ue[i]>range.xMax||ve[j+1]<range.yMin||ve[j]>range.yMax)continue;const x0=tr.x(ue[i]),x1=tr.x(ue[i+1]),y0=tr.y(ve[j]),y1=tr.y(ve[j+1]);g.fillStyle=color(value,range.cMax,range.cMin);g.fillRect(x0,Math.min(y0,y1),Math.max(.2,x1-x0+.15),Math.max(.2,Math.abs(y1-y0)+.15));if((value<range.cMin||value>range.cMax)&&k%5===0){g.beginPath();g.strokeStyle=value>range.cMax?'rgba(255,255,255,.8)':'rgba(8,29,43,.7)';g.lineWidth=.7;g.moveTo(x0,Math.min(y0,y1));g.lineTo(x1,Math.max(y0,y1));g.stroke();}}
g.restore();boundaries(g,tr,p);frame(g,tr);ticksMap(g,tr,p.kind);state.maps[id]={...tr,plane:p,case:c,metric:m,values:V,manualRange:range};MR.note(id,{low,high,total,viewportHidden:hidden,message:'색 범위 밖은 표시 잘림이며 실제 plateau가 아닙니다. Hover는 원 표시값입니다.'});}
'''

LAYOUT=r'''
function drawLayout(c){const id='paper-layout-'+c,{el,g,w,h}=cv(id),range=MR.get(id,{xMin:-25,xMax:25,yMin:-25,yMax:25},{kind:'layout',xLabel:'x [mm]',yLabel:'y [mm]',axisX:'x',axisY:'y',colour:false}),s=Math.min((w-60)/(range.xMax-range.xMin),(h-44)/(range.yMax-range.yMin)),pw=(range.xMax-range.xMin)*s,ph=(range.yMax-range.yMin)*s,left=(w-pw)/2,top=(h-ph)/2-3,tr={pad:{l:left,t:top},width:pw,height:ph,u0:range.xMin,u1:range.xMax,v0:range.yMin,v1:range.yMax,x:v=>left+(v-range.xMin)*s,y:v=>top+(range.yMax-v)*s};
el.dataset.xMin=String(range.xMin);el.dataset.xMax=String(range.xMax);el.dataset.yMin=String(range.yMin);el.dataset.yMax=String(range.yMax);el.dataset.scaleMode='manual';el.dataset.axisOrientation='y_up';g.fillStyle='#f4f8fa';g.fillRect(left,top,pw,ph);g.save();g.beginPath();g.rect(left,top,pw,ph);g.clip();g.beginPath();g.fillStyle='#edf4f7';g.strokeStyle='#94afbf';g.ellipse(tr.x(0),tr.y(0),25*s,25*s,0,0,2*Math.PI);g.fill();g.stroke();g.beginPath();g.strokeStyle='#d5a257';g.setLineDash([3,3]);g.arc(tr.x(0),tr.y(0),5*s,0,2*Math.PI);g.stroke();g.setLineDash([]);let hidden=0;for(const p of P.cases[c].physical_outlines){const q=p.polygon_mm,pc=P.cases[c].pad_centres.find(v=>v.pad===p.pad),node=p.node??pc?.node;g.beginPath();q.forEach((v,i)=>i?g.lineTo(tr.x(v[0]),tr.y(v[1])):g.moveTo(tr.x(v[0]),tr.y(v[1])));g.closePath();g.fillStyle=node===0||node==='out0'?'#db975e':node===1||node==='out1'?'#5f9ccb':'#b6c2cb';g.fill();g.strokeStyle='#68889b';g.stroke();if(pc){g.fillStyle='#173b4f';g.font='9px system-ui';g.textAlign='center';g.fillText(String(node),tr.x(pc.x_mm),tr.y(pc.y_mm)+3);if(pc.x_mm<range.xMin||pc.x_mm>range.xMax||pc.y_mm<range.yMin||pc.y_mm>range.yMax)hidden++;}}g.restore();frame(g,tr);ticksMap(g,tr,'XY');g.font='10px system-ui';g.fillStyle='#33576e';g.textAlign='left';g.fillText('z=0 · x → / y ↑ · 팬텀 D50 mm 유지 / 표시 좌표만 조절',8,h-2);MR.note(id,{viewportHidden:hidden,message:'표시 확대는 팬텀·전극 형상을 변경하지 않습니다.'});}
'''

WAVE_VALUES=r'''
function waveValues(c,point,direction,scale,max_ms){const id='paper-wave-'+c+'-'+point.id,range=MR.get(id,{xMin:0,xMax:max_ms,yMin:-TASK1_LOCKED_E,yMax:TASK1_LOCKED_E},{kind:'wave',xLabel:'시간 [ms]',yLabel:'고정방향 E [V/m]',axisX:'time',axisY:'E',colour:false}),a=projection(rawVector(central,c,3000,point.local_index,scale),direction),b=projection(rawVector(central,c,3030,point.local_index,scale),direction),span=range.xMax-range.xMin,desired=Math.max(1001,Math.ceil(span/1000*3030*20)+1),n=Math.min(40001,desired),x=new Float64Array(n),one=new Float64Array(n),two=new Float64Array(n),sum=new Float64Array(n),upper=new Float64Array(n),lower=new Float64Array(n);for(let i=0;i<n;i++){const ms=range.xMin+span*i/(n-1),t=ms/1000;x[i]=ms;one[i]=toneReal(a,3000,t);two[i]=toneReal(b,3030,t);sum[i]=one[i]+two[i];upper[i]=envelope(a,b,t);lower[i]=-upper[i];}return{x,one,two,sum,upper,lower,a,b,max:amplitude(a)+amplitude(b),scalarRMS:Math.hypot(amplitude(a),amplitude(b))/Math.sqrt(2),AM:fixedAM(a,b),manualRange:range,samplingLimited:desired>40001,requestedSampleCount:desired};}
'''

WAVE_DRAW=r'''
function drawWave(c,point,wave,ymax){const id='paper-wave-'+c+'-'+point.id,{el,g,w,h}=cv(id),range=wave.manualRange,tr=setupAxes(g,w,h,range.xMin,range.xMax,range.yMax,range.yMin,['시간 [ms]','고정방향 E [V/m]']);el.dataset.xMin=String(range.xMin);el.dataset.xMax=String(range.xMax);el.dataset.yMin=String(range.yMin);el.dataset.yMax=String(range.yMax);el.dataset.vmin=String(range.yMin);el.dataset.vmax=String(range.yMax);el.dataset.timeFirst=String(wave.x[0]);el.dataset.timeLast=String(wave.x.at(-1));el.dataset.sampleCount=String(wave.x.length);el.dataset.scaleMode='manual';g.fillStyle='white';g.fillRect(tr.pad.l,tr.pad.t,tr.width,tr.height);g.save();g.beginPath();g.rect(tr.pad.l,tr.pad.t,tr.width,tr.height);g.clip();line(g,tr,wave.x,wave.one,'#aab4bd',.9);line(g,tr,wave.x,wave.two,'#80abc5',.9);line(g,tr,wave.x,wave.sum,'#ba442e',.9);line(g,tr,wave.x,wave.upper,'#253c4a',1.5,[4,3]);line(g,tr,wave.x,wave.lower,'#253c4a',1.5,[4,3]);g.restore();frame(g,tr);g.font='9px system-ui';g.fillStyle='#355c72';g.textAlign='center';for(const v of[range.xMin,(range.xMin+range.xMax)/2,range.xMax])g.fillText(nice(v,4),tr.x(v),tr.pad.t+tr.height+15);g.textAlign='right';for(const v of[range.yMin,(range.yMin+range.yMax)/2,range.yMax])g.fillText(nice(v,4),tr.pad.l-4,tr.y(v)+3);$('paper-wave-'+c+'-'+point.id+'-caption').textContent='방향 '+$('paper-direction').value+' · 전체 carrier projection RMS '+nice(wave.scalarRMS)+' V/m · envelope 변조깊이 '+nice(wave.AM)+' V/m · xyz=['+point.xyz_mm.map(v=>nice(v,6)).join(', ')+'] mm · 실제 표시 시간 '+nice(wave.x[0],7)+'–'+nice(wave.x.at(-1),7)+' ms';let low=0,high=0;for(const value of wave.sum){if(value<range.yMin)low++;if(value>range.yMax)high++;}MR.note(id,{low,high,total:wave.sum.length,message:'합성파 표본의 y축 잘림 수입니다. RMS/AM은 시간 창의 표본 통계로 다시 계산하지 않습니다.'+(wave.samplingLimited?' 긴 시간 창의 표시 표본 상한40001에 도달했습니다. Carrier 세부는 시간 축을 확대해 확인하세요.':'')});}
'''

PROFILE=r'''
function drawProfile(metric,profile){const id='paper-profile-'+metric,{el,g,w,h}=cv(id),all=[...profile.curves.TIS[metric],...profile.curves.C1[metric]].filter(Number.isFinite),max=Math.max(0,...all),range=MR.get(id,{xMin:profile.axis==='z'?0:-25,xMax:profile.axis==='z'?25.1:25,yMin:0,yMax:TASK1_LOCKED_E},{kind:'profile',xLabel:profile.axis+' [mm]',yLabel:'세기 [V/m]',axisX:'coord',axisY:'E',colour:false}),tr=setupAxes(g,w,h,range.xMin,range.xMax,range.yMax,range.yMin,[profile.axis+' [mm]','세기 [V/m]']);el.dataset.xMin=String(range.xMin);el.dataset.xMax=String(range.xMax);el.dataset.yMin=String(range.yMin);el.dataset.yMax=String(range.yMax);el.dataset.vmin=String(range.yMin);el.dataset.vmax=String(range.yMax);el.dataset.coordinateMin=String(range.xMin);el.dataset.coordinateMax=String(range.xMax);el.dataset.scaleMode='manual';g.fillStyle='white';g.fillRect(tr.pad.l,tr.pad.t,tr.width,tr.height);g.save();g.beginPath();g.rect(tr.pad.l,tr.pad.t,tr.width,tr.height);g.clip();const xz=state.selected.kind!=='XY';if(xz){g.fillStyle='rgba(234,183,89,.14)';g.fillRect(tr.x(15),tr.y(range.yMax),tr.x(20)-tr.x(15),tr.y(range.yMin)-tr.y(range.yMax));}for(const c of['TIS','C1'])line(g,tr,profile.x,profile.curves[c][metric],caseColors[c],1.8);g.restore();frame(g,tr);g.font='9px system-ui';g.fillStyle='#355c72';g.textAlign='center';for(const v of[range.xMin,(range.xMin+range.xMax)/2,range.xMax])g.fillText(nice(v,4),tr.x(v),tr.pad.t+tr.height+15);g.textAlign='right';for(const v of[range.yMin,(range.yMin+range.yMax)/2,range.yMax])g.fillText(nice(v,4),tr.pad.l-5,tr.y(v)+3);let low=0,high=0,total=0,hidden=0;for(const c of['TIS','C1'])for(let i=0;i<profile.x.length;i++){const value=profile.curves[c][metric][i];if(!Number.isFinite(value))continue;total++;if(value<range.yMin)low++;if(value>range.yMax)high++;if(profile.x[i]<range.xMin||profile.x[i]>range.xMax)hidden++;}state.profiles[metric]={maximum_V_m:max,display_minimum_V_m:range.yMin,display_maximum_V_m:range.yMax,coordinate_min:range.xMin,coordinate_max:range.xMax,coordinates:profile.coordinates,points:profile.x.length};MR.note(id,{low,high,total,viewportHidden:hidden,message:'계산된 선 표본의 표시 범위입니다. 부피 ROI 통계는 변경하지 않습니다.'});}
'''


def patch_paper(script):
    """Patch the already fixed+color-synchronized paper SCRIPT, fail on drift."""
    if 'const TASK1_LOCKED_E=window.task1FixedScaleContract.electric_field.upper_V_m;'not in script:
        raise ValueError('Reviewed fixed-range paper source required')
    script=once(script,"'use strict';","'use strict';\nconst MR=window.task1ManualRanges;if(!MR)throw Error('Manual range helper required');")
    script=once(script,'function color(v,max){const q=window.task1FixedScales.colorFraction(v,max),','function color(v,max,min=0){const q=window.task1FixedScales.colorFraction(v,max,min),')
    for name,source in [('ticksMap',TICKS),('drawMap',MAP),('drawLayout',LAYOUT),('waveValues',WAVE_VALUES),('drawWave',WAVE_DRAW),('drawProfile',PROFILE)]:
        script=function(script,name,source)
    old="const ticks=$('paper-ticks-'+metric);ticks.replaceChildren(...[0,.25,.5,.75,1].map(v=>{const e=document.createElement('span'),x=$('paper-color').value==='log'?Math.expm1(v*Math.log1p(max)):v*max;e.textContent=nice(x,3);return e;}));$('paper-range-'+metric).textContent=metricNames[metric]+' · 0–'+nice(max)+' V/m · '+($('paper-color').value==='log'?'log1p 색 변환':'선형 색')+' · 전체 지원 조건 고정 / 자동 조정 없음';"
    new="const common=MR.snapshot().groups.EColour||{},cMin=Number.isFinite(common.cMin)?common.cMin:0,cMax=Number.isFinite(common.cMax)?common.cMax:TASK1_LOCKED_E,ticks=$('paper-ticks-'+metric);ticks.replaceChildren(...[0,.25,.5,.75,1].map(v=>{const e=document.createElement('span'),x=window.task1FixedScales.colorValueAtFraction(v,cMax,cMin);e.textContent=nice(x,3);return e;}));$('paper-range-'+metric).textContent=metricNames[metric]+' · 공통 기본색 '+nice(cMin)+'–'+nice(cMax)+' V/m · 개별 수동 범위는 각 그래프 아래 눈금·색 막대를 확인하세요';"
    script=once(script,old,new)
    # The viewport may extend beyond saved data. Never select the nearest native
    # edge cell for a cursor that is actually outside the native grid extent.
    old="if(u<tr.u0||u>tr.u1||v<tr.v0||v>tr.v1)return;let i=0,j=0;"
    new="if(u<tr.u0||u>tr.u1||v<tr.v0||v>tr.v1)return;if(u<p.u_edges_mm[0]||u>p.u_edges_mm.at(-1)||v<p.v_edges_mm[0]||v>p.v_edges_mm.at(-1)){$('paper-hover').textContent='저장된 native 격자 범위 밖 · 표시 좌표만 확대됨';return;}let i=0,j=0;"
    script=once(script,old,new)
    script=once(script," · 색 변환과 무관한 원 표시값 / clipping 없음'"," · 색 변환·사용자 범위와 무관한 원 표시값'")
    old='profile:state.profile,profile_limits:state.profiles};}'
    new="profile:state.profile,profile_limits:state.profiles,manual_wave_windows:Object.fromEntries(Object.entries(state.waves||{}).flatMap(([point,cases])=>Object.entries(cases).map(([c,w])=>[c+'-'+point,{first_ms:w.x[0],last_ms:w.x.at(-1),samples:w.x.length,range:w.manualRange,sampling_limited:w.samplingLimited}])))};}"
    script=once(script,old,new)
    return script
