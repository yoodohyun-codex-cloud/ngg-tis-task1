"""Source-only, offline report renderer; caller supplies actual validated arrays.

No read/write/import-time numerical work. Native fields are never modified.
Render-time map extraction selects native centres, without interpolation.
"""
from __future__ import annotations
import html
import json
import math

METRICS={
 'total_E_RMS_V_m':('전체 4주파수 전기장 RMS','V/m','RMS','baseline_total_RMS'),
 'fundamental_E_RMS_V_m':('기본파 전기장 RMS','V/m',None,None),
 'harmonic_E_RMS_V_m':('3차 고조파 전기장 RMS','V/m',None,None),
 'fundamental_maxTIS_2074_V_m':('기본파 최대 방향 변조 (2074 방향)','V/m','maxTIS','baseline_cached_maxTIS_2074'),
 'X_fundamental_TIS_V_m':('X 기본파 변조','V/m','X_TIS','baseline_X_TIS'),
 'Y_fundamental_TIS_V_m':('Y 기본파 변조','V/m','Y_TIS','baseline_Y_TIS'),
 'Z_fundamental_TIS_V_m':('Z 기본파 변조','V/m','Z_TIS','baseline_Z_TIS'),
 'total_Jtotal_RMS_A_m2':('전도 + 변위 전류밀도 RMS','A/m²',None,None),
 'total_Jconduction_RMS_A_m2':('전도 전류밀도 RMS','A/m²',None,None),
 **{'carrier_'+str(f)+'_E_RMS_V_m':(str(f)+' Hz 전기장 RMS','V/m',None,None) for f in (3000,3030,9000,9090)},
}


def _finite(value):
 return isinstance(value,(int,float)) and math.isfinite(float(value))


def build_report(summary,arrays,grid,*,baseline_arrays=None,run_id='task1-all-layer-sensitivity-20261025-run',source_commit=None,result_commit=None):
 """Return {html, markdown}; no IO. grid is actual matching N×5 native grid.

 Caller must ensure grid and all arrays are the exact hash-pinned post inputs.
 baseline_arrays may be cached original volume.npz arrays, not a fresh solve.
 Missing baseline metrics stay explicitly unavailable; no field is invented.
 """
 baseline_arrays={} if baseline_arrays is None else baseline_arrays
 n=len(grid)
 if n!=summary['model']['cells']:raise ValueError('Actual grid length mismatch')
 present={k:v for k,v in METRICS.items()if k in arrays}
 for name in present:
  if len(arrays[name])!=n:raise ValueError('Native scalar length mismatch: '+name)
 axes=[sorted({float(row[k])for row in grid})for k in range(3)]
 if not all(axes):raise ValueError('Actual nonempty native coordinates required')
 nearest=lambda axis,value:min(axes[axis],key=lambda x:(abs(x-value),x))
 # Fixed physical request; actual centre is published separately for every map.
 planes=[('XZ','y',nearest(1,0),0,2,1),('YZ','x',nearest(0,0),1,2,0)]
 planes += [('XY '+str(z)+' mm','z',nearest(2,z),0,1,2)for z in(.025,.075,2.5,5,7.5,10,15,17.5,20)]
 maps=[]
 for label,fixed,value,a,b,axis in planes:
  ids=[i for i,row in enumerate(grid)if float(row[axis])==value]
  x=axes[a];y=axes[b];xi={v:i for i,v in enumerate(x)};yi={v:i for i,v in enumerate(y)}
  cells=[[xi[float(grid[i][a])],yi[float(grid[i][b])],int(i)]for i in ids]
  y_bounds=None
  if b==2:
   representatives={float(grid[i][2]):i for i in ids}
   h_m=float(summary['model']['h_xy_mm'])*1e-3
   y_bounds=[[z-float(grid[representatives[z]][4])/(h_m*h_m)*500,z+float(grid[representatives[z]][4])/(h_m*h_m)*500]for z in y]
  mapobj=dict(label=label,fixed_axis=fixed,actual_fixed_mm=value,x_axis='xyz'[a],y_axis='xyz'[b],x=x,y=y,y_bounds=y_bounds,cells=cells,new={},baseline={})
  for name,meta in present.items():
   values=[float(arrays[name][i])for i in ids]
   if not all(math.isfinite(v)for v in values):raise ValueError('Nonfinite actual scalar map')
   mapobj['new'][name]=values
   oldname=meta[2]
   if oldname and oldname in baseline_arrays:
    old=baseline_arrays[oldname]
    if len(old)!=n:raise ValueError('Cached baseline scalar length mismatch')
    values=[float(old[i])for i in ids]
    if not all(math.isfinite(v)for v in values):raise ValueError('Nonfinite cached baseline scalar')
    mapobj['baseline'][name]=values
  maps.append(mapobj)
 metric_meta={name:dict(label=meta[0],unit=meta[1],baseline_statistic=meta[3])for name,meta in present.items()}
 # Source-statistical range is derived from full volumes, never from a slice.
 ranges={}
 for name,meta in metric_meta.items():
  values=[summary['statistics']['total'][name]['max']]
  oldkey=meta['baseline_statistic']
  if oldkey:values.append(summary['comparison_to_original_same_drive']['total'][oldkey]['max'])
  ranges[name]=dict(min=0,max=max(float(v)for v in values)or 1)
 feedback=[dict(feedback_id=i,source_adoption_commit=source_commit or '3b9fd031f42226201f1578307cebd4b67466332a',actual_run_id=run_id,
  status='Source response only; see explicit held gates. This table does not mark an entire feedback item validated or close it.',
  validation_result='See actual native_gates / independent diagnostics / validation_holds; no material calibration or candidate adoption')
  for i in('T1-F004','T1-F001','T1-F002','T1-F006','T1-F007','T1-F010:FAT-20261024')]
 payload=dict(schema='task1-whole-layer-field-view-v1',run_id=run_id,case_id=summary['case_id'],source_commit=source_commit,result_commit=result_commit,feedback_mapping=feedback,
  summary=summary,metrics=metric_meta,maps=maps,ranges=ranges,
  extraction='Nearest native planes; original cell-constant values; no interpolation, clipping, smoothing or artificial gradient in data',
  baseline='Previously calculated square15 four-pad native cache; no comparator PDE rerun',
  native_grid_shape=[n,5])
 encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('<','\\u003c')
 title='전 층 가정 민감도: SC εr 110000 → 1100'
 document=TEMPLATE.replace('__TITLE__',html.escape(title)).replace('__DATA__',encoded)
 def num(v):return '미계산'if v is None else format(float(v),'.6g')
 e=summary['electrical'];t=summary['statistics']['target'];base=summary['comparison_to_original_same_drive']['target']
 rows=['| 지표 | 기존 4패드 | 새 4패드 민감도 |','|---|---:|---:|',
  '| 목표 ROI 전체 전기장 RMS mean (V/m) | '+num(base['baseline_total_RMS']['mean'])+' | '+num(t['total_E_RMS_V_m']['mean'])+' |',
  '| 목표 ROI 전체 전기장 RMS P10 (V/m) | '+num(base['baseline_total_RMS']['p10'])+' | '+num(t['total_E_RMS_V_m']['p10'])+' |',
  '| 목표 ROI 기본파 max2074 mean (V/m) | '+num(base['baseline_cached_maxTIS_2074']['mean'])+' | '+num(t.get('fundamental_maxTIS_2074_V_m',{}).get('mean'))+' |',
  '| 접촉 정상방향 J RMS max (A/m²) | '+num(summary['baseline_cached_electrical_metrics']['surface_J_RMS_max_A_m2'])+' | '+num(e['contact_normal_J_RMS_max_A_m2'])+' |',
  '| 총 실제 전원 전력 (W) | '+num(summary['baseline_cached_electrical_metrics']['source_power_W'])+' | '+num(e['source_power_W'])+' |']
 md='새 PDE 조건 1개 / RHS 8개를 계산한 SC 유전율 단일 인자 가정 민감도입니다. 네 층 물성의 논문 교정·실험 검증 또는 후보 채택 결과로 해석하지 않습니다.\n\n'+'\n'.join(rows)+'\n\n'+(
  '동일1Vpp에서 접촉Jmax가 감소하더라도 SC실손실 증가와 목표 절대변조 감소를 함께 보아야 합니다. 동일Jmax 전압 환산은 수치 비교이며 구동 제안이 아닙니다. SC+contact 형태의 과거 skin_power_W를 SC+dermis로 비교하지 않습니다.\n\n'
  '기본파 3000/3030 Hz 방향 변조와 전체 4주파수 RMS를 구분합니다. 2074 방향 검색 상태: '+summary['maximum_direction_search']['status']+'. '
  '잔차·전력·전류·면적·공유 flux 보존 검사는 독립 potential-gradient 진단 및 SC/XY/bulk/edge 수렴 검증을 대신하지 않습니다. '
  'SC 2셀 및 기존 XY/접촉 실패를 유지하며, 물성·접촉·실험·생리 활성화·안전 검증은 보류입니다.\n\n'
  '뷰는 원시 Float64 필드를 변경하지 않습니다. 색상 범위·축 범위·클리핑 개수는 별도 표시하며 사용자 설정은 이 HTML의 localStorage에만 저장합니다. '
  '소스 commit: '+str(source_commit)+'; 결과 commit: '+str(result_commit)+'; run: '+run_id+'; case: '+summary['case_id']+'.\n'
 )
 return dict(html=document,markdown=md,report_json=payload)


build=build_report


TEMPLATE='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>body{font:14px system-ui;margin:0;background:#f3f5f7;color:#162334}header,main{max-width:1450px;margin:auto;padding:20px}h1{font-size:23px;margin:0 0 10px}h2{font-size:17px}section,.panel{background:white;padding:16px;border:1px solid #dce2e7;border-radius:9px;margin:12px 0}.notice{background:#fff7db;border-color:#e8d596}.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:end}label{display:inline-flex;flex-direction:column;gap:5px;font-size:12px}input{width:90px}select,input,button{font:inherit;padding:6px;border:1px solid #b4c0cd;border-radius:4px}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{margin:0;min-width:0}canvas{display:block;max-width:100%;width:100%;height:auto;background:#f6f7f8}p{line-height:1.6}small,.small{font-size:12px;color:#566578}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:7px;text-align:right;border-bottom:1px solid #e4e8ed}th:first-child,td:first-child{text-align:left}.scroll{overflow:auto}.mono{font:12px ui-monospace,monospace;overflow-wrap:anywhere;white-space:pre-wrap}button{cursor:pointer;background:#fff}summary{cursor:pointer}@media(max-width:850px){.row{grid-template-columns:1fr}header,main{padding:12px}}</style>
<header><h1>__TITLE__</h1><div id="identity" class="mono"></div><p>지름 50 mm · SC 0.1 / dermis 5 / fat 5 / muscle 15 mm · 윗면 4패드 / 독립 출력 2개 · 패드 2·3 공통 귀환 · 50 Ω · 기본파 3000/3030 Hz 및 3차 9000/9090 Hz</p></header>
<main><section class="notice"><b>계산된 가정 민감도 · 미채택</b><p>새 조건은 SC εr만 110000 → 1100으로 바꿉니다. 모든 층의 σ/εr은 검증된 개별 팬텀 물성이 아닌 가정입니다. 잔차와 보존 gate 통과는 전체 수렴·실험·활성화·안전 검증을 뜻하지 않습니다. SC 2셀, 기존 XY/접촉 실패, PBS 접촉 불확실성을 유지합니다. 실제 Windows 저장은 이 뷰로 확인할 수 없습니다.</p></section>
<section><div class="controls"><label>물리량<select id="metric"></select></label><label>절단면<select id="plane"></select></label><label>비교 조건<select id="normal"><option value="fixed_source_Vpp">동일 전원 Vpp</option><option value="equal_total_source_real_power">동일 총 실제 전원 전력</option><option value="equal_contact_normal_J_RMS_max">동일 접촉 정상 Jmax</option><option value="equal_sum_of_output_RMS_currents_bookkeeping">동일 출력 RMS 전류 합</option></select></label><button id="reset">이 물리량 공통 범위 복원</button><label><input type="checkbox" id="separate">개별 색 범위 사용</label></div><p id="scope" class="small"></p><p id="range-error" class="small" role="alert" style="color:#9b3228"></p><div class="controls" id="limits"></div><p class="small">축과 색 범위를 직접 입력할 수 있습니다. 기본 색 범위는 두 조건의 전체 부피 최대값을 함께 포함합니다. 개별 색 범위 선택 시 두 그림의 색 자체는 직접 비교하지 마세요. 원시 값은 변경하지 않으며 범위 밖 값과 잘린 셀 수를 아래에 표시합니다.</p></section>
<div class="row"><div class="panel"><h2>기존 4패드 기준 · SC εr 110000</h2><canvas id="baseline" width="700" height="600"></canvas><p id="baseline-info" class="small"></p></div><div class="panel"><h2>새 4패드 민감도 · SC εr 1100</h2><canvas id="new" width="700" height="600"></canvas><p id="new-info" class="small"></p></div></div>
<section><h2>목표와 비표적의 절대값 · 같은 세로축</h2><div class="controls"><label>그래프 Y 최소<input id="bar-min" type="number" step="any"></label><label>그래프 Y 최대<input id="bar-max" type="number" step="any"></label></div><canvas id="bars" width="1300" height="430"></canvas><p class="small">목표: 중심 r ≤ 5 mm, z 15–20 mm. 표층: z 0–5 mm. 비표적: 전체 − 목표. 기존 동일 격자의 원래 부피 가중 마스크와 inverse weighted ECDF를 그대로 사용합니다. 변조 cutoff를 생리적 역치로 사용하지 않습니다.</p></section>
<section class="notice"><h2>낮은 접촉 Jmax와 SC 손실을 함께 비교</h2><p id="burden-tradeoff"></p></section><section><h2>피부·접촉·전력 부담</h2><p id="normal-note"></p><div id="burden" class="scroll"></div></section>
<section><h2>전체 층 및 ROI 통계 · 원시 Float64 기반</h2><div id="stats" class="scroll"></div><p class="small">min/P10/median/P90/max/mean/std는 부피 가중 원시 셀 값입니다. 경계에서 높은 E가 나타나도 깊이 선택성으로 판정하지 않습니다. 표시 범위 클리핑은 통계에 적용하지 않습니다. 계면 독립 진단은 gate가 아닌 진단값이며 γE/σE 출력은 저장 E에서 유도한 값입니다.</p></section>
<section><h2>피드백 연결 · 소스 반영과 결과 검증 분리</h2><div id="feedback" class="scroll"></div><p class="small">각 ID는 응답 소스와 실제 실행을 연결합니다. 피드백 전체의 검증 완료·물성 교정·후보 채택을 의미하지 않습니다. 보류 gate는 아래에 그대로 유지합니다.</p></section><section><details><summary>검증 상태 · 물성 · 실행 식별자</summary><pre id="proof" class="mono"></pre></details></section></main>
<script id="payload" type="application/json">__DATA__</script><script>
'use strict';const D=JSON.parse(document.getElementById('payload').textContent),S=D.summary,$=id=>document.getElementById(id),fmt=v=>v===null||v===undefined?'미계산':Number(v).toPrecision(6),savekey='task1-whole-layer-view-ranges-v1';let state={};try{state=JSON.parse(localStorage.getItem(savekey)||'{}')}catch(e){}let limits={};const persist=()=>{try{localStorage.setItem(savekey,JSON.stringify(state))}catch(e){}};
for(const [k,m]of Object.entries(D.metrics)){let o=document.createElement('option');o.value=k;o.textContent=m.label+' ['+m.unit+']';$('metric').append(o)}for(let i=0;i<D.maps.length;i++){let o=document.createElement('option');o.value=i;o.textContent=D.maps[i].label;$('plane').append(o)}
const B=S.baseline_cached_electrical_metrics,N=S.electrical,eqJ=S.separate_linear_normalizations.find(x=>x.name==='equal_contact_normal_J_RMS_max'),oldAM=S.comparison_to_original_same_drive.target.baseline_cached_maxTIS_2074.mean,newAM=S.statistics.target.fundamental_maxTIS_2074_V_m?.mean;
$('burden-tradeoff').textContent='동일 1 Vpp에서 목표 기본파 max2074 평균 '+fmt(oldAM)+' → '+fmt(newAM)+' V/m, 접촉 Jmax '+fmt(B.surface_J_RMS_max_A_m2)+' → '+fmt(N.contact_normal_J_RMS_max_A_m2)+' A/m²입니다. 그러나 SC 실제 손실은 '+fmt(B.SC_power_W)+' → '+fmt(N.layers_power_W.sc)+' W ('+fmt(N.layers_power_W.sc/B.SC_power_W)+'배)입니다. 접촉 Jmax 감소를 전체 피부 부담 개선으로 판정하지 않습니다. 동일 Jmax 환산 '+fmt(eqJ.source_Vpp_each)+' Vpp에서 SC 손실 '+fmt(eqJ.SC_power_W)+' W는 수치 비교이며 실험 구동 제안이 아닙니다.';
$('identity').textContent='run '+D.run_id+' | case '+D.case_id+' | source '+(D.source_commit||'미기입')+' | result '+(D.result_commit||'미기입');$('proof').textContent=JSON.stringify({native_gates:S.native_gates,material:S.actual_material_lookup_audit,maximum_direction:S.maximum_direction_search,validation_holds:S.validation_holds,independent_interfaces:S.independent_interface_potential_gradient_diagnostics,model:S.model,comparator:S.comparator,input_sha256:S.input_sha256},null,2);
function current(){let key=$('metric').value,p=D.maps[+$('plane').value],k=key+'|'+p.label;if(!state[k])state[k]={xmin:p.x[0]-.3125,xmax:p.x.at(-1)+.3125,ymin:p.y_axis==='z'?0:p.y[0]-.3125,ymax:p.y_axis==='z'?25.1:p.y.at(-1)+.3125,cmin:D.ranges[key].min,cmax:D.ranges[key].max,bmin:D.ranges[key].min,bmax:D.ranges[key].max,nmin:D.ranges[key].min,nmax:D.ranges[key].max,barmin:0,barmax:D.ranges[key].max,separate:false};return{key,p,v:state[k]}}
function scale(){return S.separate_linear_normalizations.find(r=>r.name===$('normal').value)}
function setRange(field,value){let {v}=current(),next={...v,[field]:value};if(!(Number.isFinite(value)&&Math.abs(value)<=1e9)){ $('range-error').textContent='유한한 눈금 값을 입력하세요.';return false}for(let[lo,hi]of[['xmin','xmax'],['ymin','ymax'],['cmin','cmax'],['bmin','bmax'],['nmin','nmax'],['barmin','barmax']])if(!(Number.isFinite(next[hi]-next[lo])&&next[hi]>next[lo])){$('range-error').textContent='최대값은 최소값보다 커야 합니다. 이전 적용 범위를 유지합니다.';return false}Object.assign(v,next);$('range-error').textContent='';persist();draw();return true}
function form(){let{key,p,v}=current();$('limits').replaceChildren();for(let[field,label]of [['xmin',p.x_axis+' 최소 mm'],['xmax',p.x_axis+' 최대 mm'],['ymin',p.y_axis+' 최소 mm'],['ymax',p.y_axis+' 최대 mm'],...v.separate?[['bmin','기존 색 최소'],['bmax','기존 색 최대'],['nmin','새 색 최소'],['nmax','새 색 최대']]:[['cmin','공통 색 최소'],['cmax','공통 색 최대']]]){let l=document.createElement('label');l.textContent=label;let e=document.createElement('input');e.type='number';e.step='any';e.value=v[field];e.dataset.field=field;e.onchange=()=>{setRange(field,Number(e.value))};l.append(e);$('limits').append(l)}$('separate').checked=v.separate;$('bar-min').value=v.barmin;$('bar-max').value=v.barmax;draw()}
const palette=t=>{t=Math.max(0,Math.min(1,t));let stops=[[20,25,80],[37,99,170],[37,181,167],[217,223,84],[245,115,45],[153,15,41]],z=t*(stops.length-1),i=Math.min(Math.floor(z),stops.length-2),a=z-i;return'rgb('+stops[i].map((v,j)=>Math.round(v+(stops[i+1][j]-v)*a)).join(',')+')'};
function map(which,key,p,v,factor){let canvas=$(which),ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;ctx.clearRect(0,0,W,H);ctx.fillStyle='#f7f9fa';ctx.fillRect(0,0,W,H);let a=p[which][key],info=$(which+'-info');if(!a){ctx.fillStyle='#566578';ctx.font='19px system-ui';ctx.fillText('이 물리량의 기존 원시 지도 미제공',65,180);info.textContent='미계산/미제공 값을 대신 만들지 않습니다.';return}let cmin=v.separate?(which==='new'?v.nmin:v.bmin):v.cmin,cmax=v.separate?(which==='new'?v.nmax:v.bmax):v.cmax;if(!(v.xmax>v.xmin&&v.ymax>v.ymin&&cmax>cmin)){info.textContent='최대값은 최소값보다 커야 합니다.';return}let L=65,T=25,R=80,B=65,pw=W-L-R,ph=H-T-B,xx=x=>L+(x-v.xmin)/(v.xmax-v.xmin)*pw,yy=y=>p.y_axis==='z'?T+(y-v.ymin)/(v.ymax-v.ymin)*ph:T+ph-(y-v.ymin)/(v.ymax-v.ymin)*ph;ctx.save();ctx.beginPath();ctx.rect(L,T,pw,ph);ctx.clip();let below=0,above=0,min=Infinity,max=-Infinity;for(let i=0;i<a.length;i++){let value=a[i]*factor;min=Math.min(min,value);max=Math.max(max,value);if(value<cmin)below++;if(value>cmax)above++;let[x,y,id]=p.cells[i],xc=p.x[x],yc=p.y[y],dx=p.x.length>1?Math.min(x?xc-p.x[x-1]:p.x[1]-xc,x+1<p.x.length?p.x[x+1]-xc:xc-p.x[x-1]):.625,low=p.y_bounds?p.y_bounds[y][0]:(y?(.5*(yc+p.y[y-1])):yc-.3125),high=p.y_bounds?p.y_bounds[y][1]:(y+1<p.y.length?.5*(yc+p.y[y+1]):yc+.3125);ctx.fillStyle=palette((value-cmin)/(cmax-cmin));let xa=xx(xc-dx/2),xb=xx(xc+dx/2),ya=yy(low),yb=yy(high);ctx.fillRect(Math.min(xa,xb),Math.min(ya,yb),Math.abs(xb-xa)+.3,Math.abs(yb-ya)+.3)}
// Target outline and physical interfaces are annotations, never field edits.
ctx.strokeStyle='rgba(20,20,20,.8)';ctx.lineWidth=1;ctx.setLineDash([5,4]);if(p.y_axis==='z'){for(let depth of[.1,5.1,10.1,15,20]){ctx.beginPath();ctx.moveTo(L,yy(depth));ctx.lineTo(L+pw,yy(depth));ctx.stroke()}ctx.strokeStyle='white';ctx.lineWidth=2;let roiHalf=Math.sqrt(Math.max(0,25-p.actual_fixed_mm*p.actual_fixed_mm));ctx.strokeRect(xx(-roiHalf),yy(15),xx(roiHalf)-xx(-roiHalf),yy(20)-yy(15))}else if(p.fixed_axis==='z'&&p.actual_fixed_mm>=15&&p.actual_fixed_mm<=20){ctx.strokeStyle='white';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(xx(0),yy(0),5/(v.xmax-v.xmin)*pw,5/(v.ymax-v.ymin)*ph,0,0,2*Math.PI);ctx.stroke()}ctx.restore();ctx.setLineDash([]);ctx.strokeStyle='#202c3e';ctx.strokeRect(L,T,pw,ph);ctx.font='13px system-ui';ctx.fillStyle='#202c3e';ctx.textAlign='center';for(let i=0;i<=5;i++){let x=v.xmin+(v.xmax-v.xmin)*i/5,y=v.ymin+(v.ymax-v.ymin)*i/5;ctx.fillText(x.toFixed(1),xx(x),H-B+22);ctx.textAlign='right';ctx.fillText(y.toFixed(1),L-8,yy(y)+4);ctx.textAlign='center'}ctx.fillText(p.x_axis+' (mm)',L+pw/2,H-10);ctx.save();ctx.translate(15,T+ph/2);ctx.rotate(-Math.PI/2);ctx.fillText(p.y_axis+(p.y_axis==='z'?' 깊이 (+ 아래)':'')+' (mm)',0,0);ctx.restore();for(let j=0;j<ph;j++){ctx.fillStyle=palette(1-j/ph);ctx.fillRect(L+pw+18,T+j,14,1)}ctx.textAlign='left';ctx.fillStyle='#202c3e';ctx.fillText(fmt(cmax),L+pw+35,T+9);ctx.fillText(fmt(cmin),L+pw+35,T+ph);info.textContent='실제 '+p.fixed_axis+'='+fmt(p.actual_fixed_mm)+' mm · native 셀 '+a.length+'개 · 원시 ×배율 min/max '+fmt(min)+' / '+fmt(max)+' '+D.metrics[key].unit+' · 색 하한 미만 '+below+' / 상한 초과 '+above+' 셀 (전체 선택 절단면 기준)';}
function stat(region,key,isnew){if(isnew)return S.statistics[region]?.[key];let oldkey=D.metrics[key].baseline_statistic;return oldkey?S.comparison_to_original_same_drive[region]?.[oldkey]:null}
function bars(key,v,factor){let c=$('bars'),ctx=c.getContext('2d'),w=c.width,h=c.height;ctx.clearRect(0,0,w,h);let items=[['목표 mean','target','mean'],['목표 P10','target','p10'],['표층 P95','surface_0_5','p95'],['비표적 P95','off_target','p95']],lo=v.barmin,hi=v.barmax;if(!(hi>lo))return;let L=85,T=30,B=80,pw=w-L-30,ph=h-T-B,y=q=>T+ph-(q-lo)/(hi-lo)*ph;ctx.font='15px system-ui';ctx.textAlign='right';for(let i=0;i<=5;i++){let a=lo+(hi-lo)*i/5;ctx.fillStyle='#566578';ctx.fillText(fmt(a),L-10,y(a)+4);ctx.strokeStyle='#e0e5eb';ctx.beginPath();ctx.moveTo(L,y(a));ctx.lineTo(w-20,y(a));ctx.stroke()}ctx.save();ctx.beginPath();ctx.rect(L,T,pw,ph);ctx.clip();for(let i=0;i<items.length;i++){let[label,r,q]=items[i],x=L+pw*(i+.5)/items.length;for(let j=0;j<2;j++){let s=stat(r,key,!!j);if(!s)continue;let a=s[q]*(j?factor:1),xx=x+(j?8:-60),yy=y(a),zero=y(0);ctx.fillStyle=j?'#c5652e':'#246e9e';ctx.fillRect(xx,Math.min(yy,zero),52,Math.abs(yy-zero));}}ctx.restore();ctx.textAlign='center';ctx.fillStyle='#162334';for(let i=0;i<items.length;i++){let x=L+pw*(i+.5)/items.length;ctx.fillText(items[i][0],x,h-42);let b=stat(items[i][1],key,false),n=stat(items[i][1],key,true);ctx.font='12px system-ui';ctx.fillText('기존 '+fmt(b?.[items[i][2]])+' / 새 '+fmt(n? n[items[i][2]]*factor:null),x,h-20);ctx.font='15px system-ui'}ctx.textAlign='left';ctx.fillText('파랑 기존 · 주황 새 · '+D.metrics[key].unit,L,18)}
function table(headers,rows){let t=document.createElement('table'),tr=document.createElement('tr');for(let h of headers){let e=document.createElement('th');e.textContent=h;tr.append(e)}t.append(tr);for(let row of rows){tr=document.createElement('tr');for(let value of row){let e=document.createElement('td');e.textContent=value;tr.append(e)}t.append(tr)}return t}
$('feedback').replaceChildren(table(['피드백 ID','소스 반영 commit','실제 run','상태'],D.feedback_mapping.map(x=>[x.feedback_id,x.source_adoption_commit,x.actual_run_id,x.status])));
function draw(){let{key,p,v}=current(),s=scale(),f=s.common_source_amplitude_scale,m=D.metrics[key];$('scope').textContent=D.extraction+' · '+m.label+' · '+m.unit+' · 새 조건 진폭 배율 '+fmt(f);map('baseline',key,p,v,1);map('new',key,p,v,f);bars(key,v,f);$('normal-note').textContent=s.interpretation+' 기본파 변조와 전체 RMS/전류/전력은 서로 다른 물리량입니다.';let b=S.baseline_cached_electrical_metrics,e=S.electrical,erows=[['각 출력 전원 Vpp','1',fmt(f)],['출력 RMS 전류 mA',b.source_current_RMS_by_output_mA.map(fmt).join(' / '),s.source_current_RMS_by_output_mA.map(fmt).join(' / ')],['총 실제 전원 전력 W',fmt(b.source_power_W),fmt(s.source_power_W)],['접촉 정상 J RMS max A/m²',fmt(b.surface_J_RMS_max_A_m2),fmt(s.contact_normal_J_RMS_max_A_m2)],['접촉 정상 J RMS P95 A/m²',fmt(b.surface_J_RMS_p95_A_m2),fmt(s.contact_normal_J_RMS_P95_A_m2)],['최대 접촉 전압 RMS V',fmt(b.contact_voltage_RMS_max_V),fmt(s.contact_voltage_RMS_max_V)],['SC 손실 W',fmt(b.SC_power_W),fmt(s.SC_power_W)],['dermis 손실 W','원본 요약 참조',fmt(e.layers_power_W.dermis*f*f)],['fat 손실 W','원본 요약 참조',fmt(e.layers_power_W.fat*f*f)],['muscle 손실 W','원본 요약 참조',fmt(e.layers_power_W.muscle*f*f)],['접촉 손실 W',fmt(b.contact_power_W),fmt(e.contact_power_W*f*f)],['50 Ω 손실 W',fmt(b.source_resistor_power_W),fmt(e.source_resistor_power_W*f*f)]];$('burden').replaceChildren(table(['항목','기존 4패드','새 4패드'],erows));let rows=[];for(let region of ['sc','dermis','fat','muscle','target','surface_0_5','subsurface_5_10','off_target','remaining','total']){for(let isnew of[false,true]){let a=stat(region,key,isnew);if(!a)continue;let factor=isnew?f:1;rows.push([region+(isnew?' 새':' 기존'),...['min','p10','median','p90','max','mean','std'].map(q=>fmt(a[q]*factor)),fmt(a.volume_m3*1e9)])}}$('stats').replaceChildren(table(['층/ROI','min','P10','median','P90','max','mean','std','부피 mm³'],rows));}
$('metric').onchange=form;$('plane').onchange=form;$('normal').onchange=draw;$('separate').onchange=()=>{current().v.separate=$('separate').checked;persist();form()};$('reset').onclick=()=>{let{key,p}=current();delete state[key+'|'+p.label];persist();form()};for(let[id,key]of[['bar-min','barmin'],['bar-max','barmax']])$(id).onchange=()=>{setRange(key,Number($(id).value))};form();window.task1WholeLayerView=Object.freeze({getState:()=>({metric:$('metric').value,plane:current().p.label,normal:$('normal').value,range:JSON.parse(JSON.stringify(current().v))}),setRange});
</script></html>'''
