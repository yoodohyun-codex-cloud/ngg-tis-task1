#!/usr/bin/env python3
"""Build an offline top-five layout viewer from caller-supplied display data.

No files are read at import or by render(). No research imports, native reads,
solves, normalization, scoring, scientific gates, or resource-ledger writes.
The caller owns source verification, serialized execution and resource limits.
Float32 canvas values are display-only; catalog Float64 statistics are authority.
"""
from __future__ import annotations
import base64
import hashlib
import html
import json
import math
import os
from pathlib import Path
import struct

CATALOG_SCHEMA = 'task1-top5-layout-catalog-v1'
DISPLAY_SCHEMA = 'task1-top5-native-display-v1'
MODES = ('raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
         'skin_contact_only', 'legacy_composite_full_skin')
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
PRIMARY = 'primary_r5_depth15_20'
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2',
           'contact_voltage_RMS_max_V', 'SC_power_W', 'contact_power_W',
           'bulk_skin_J_vector_RMS_max_A_m2', 'bulk_skin_J_vector_RMS_p95_A_m2',
           'skin_SC_plus_dermis_power_W', 'source_power_W')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(value, *, positive=False):
    return type(value) in (int, float) and math.isfinite(value) and (value > 0 if positive else value >= 0)


def validate_catalog(catalog):
    require(isinstance(catalog, dict) and catalog.get('schema') == CATALOG_SCHEMA, 'Unknown layout catalog schema')
    selected = catalog.get('selected_layouts')
    require(isinstance(selected, list) and len(selected) == 5, 'Exactly five completed nonbaseline layout representatives required')
    rows = [catalog.get('canonical_baseline')] + selected
    require(all(isinstance(row, dict) for row in rows), 'Canonical baseline and five layout rows required')
    ids, geometry = set(), set()
    for row in rows:
        require(isinstance(row.get('id'), str) and row['id'] and row['id'] not in ids, 'Unique layout row ids required')
        require(isinstance(row.get('geometry_key'), str) and row['geometry_key'] and row['geometry_key'] not in geometry,
                'Five distinct physical geometry/wiring layouts, not five drives on one layout, required')
        ids.add(row['id']); geometry.add(row['geometry_key'])
        circuit = row.get('circuit', {})
        require(type(circuit.get('n_pads')) is int and circuit['n_pads'] >= 4 and circuit.get('n_outputs') == 2 and
                circuit.get('n_return_nodes') == 1 and circuit.get('source_resistance_ohm') == 50,
                'Explicit physical pads, two outputs, one common return and 50ohm required')
        require(set(row.get('normalizations', {})) == set(MODES), 'Five separate saved normalizations required')
        for mode in MODES:
            n = row['normalizations'][mode]
            require(finite(n.get('amplitude_scale'), positive=True), 'Positive saved amplitude scale required')
            require(isinstance(n.get('normalized_burdens'), dict) and all(finite(n['normalized_burdens'].get(k)) for k in BURDENS),
                    'Nine separately stored current/contact/skin/power burdens required')
            regions = n.get('regions', {})
            require(all(name in regions for name in (PRIMARY, 'surface_0_5', 'primary_complement', 'total')),
                    'Primary, surface, complete non-target and global regions required')
            for metric in METRICS:
                stats = regions[PRIMARY].get(metric, {})
                require(all(finite(stats.get(k)) for k in ('mean', 'p10', 'CV', 'max')), 'Finite saved ROI statistics required')
    require(catalog.get('candidate_adopted') is not True, 'A diagnostic comparison cannot claim adoption')
    reference = catalog.get('pad_count_reference')
    if reference is not None:
        require(isinstance(reference, dict) and isinstance(reference.get('scope'), str), 'Explicit separate strip-family scope required')
        source = reference.get('source', {})
        require(isinstance(source.get('path'), str) and isinstance(source.get('SHA256'), str) and
                len(source['SHA256']) == 64 and all(c in '0123456789abcdef' for c in source['SHA256']), 'Pad-count source path/SHA required')
        group = reference.get('rows', [])
        require(isinstance(group, list) and [r.get('n_pads') for r in group] == [4, 4, 8, 12, 16] and
                len({r.get('id') for r in group}) == 5, 'Separate original4/strip4/8/12/16 reference rows required')
        for row in group:
            require(row.get('n_outputs') == 2 and isinstance(row.get('return_topology'), str) and
                    'common' in row['return_topology'].lower(), 'Pad count cannot increase independent outputs or change common return')
            require(set(row.get('normalizations', {})) == {'raw_1Vpp', 'skin_contact_only'}, 'Fixed raw/skin8 strip reference required')
            for mode in ('raw_1Vpp', 'skin_contact_only'):
                n = row['normalizations'][mode]
                require(all(finite(n.get(k)) for k in ('mean_V_m', 'P10_V_m', 'source_Vpp_per_output')) and
                        all(finite(n.get('normalized_burdens', {}).get(k)) for k in BURDENS) and
                        isinstance(n.get('source_output_RMS_by_output_mA'), list) and len(n['source_output_RMS_by_output_mA']) == 2 and
                        all(finite(v) for v in n['source_output_RMS_by_output_mA']), 'Stored pad-count ROI/source/burden values required')
    return rows


def _edges(values, name):
    require(isinstance(values, list) and len(values) >= 3 and
            all(type(v) in (int, float) and math.isfinite(v) for v in values) and
            all(b > a for a, b in zip(values, values[1:])), 'Strictly increasing finite native '+name+' required')


def _binary(value, expected_bytes, label):
    require(isinstance(value, str) and len(value) <= (expected_bytes+2)//3*4+4, 'Bounded base64 '+label+' required')
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid base64 '+label) from error
    require(len(decoded) == expected_bytes, 'Native shape/byte count differs: '+label)
    return decoded


def _range(value, label):
    require(isinstance(value, list) and len(value) == 2 and value[0] == 0 and finite(value[1], positive=True),
            'Shared finite 0-based color range required: '+label)


def validate_display(catalog, display):
    rows = validate_catalog(catalog)
    require(isinstance(display, dict) and display.get('schema') == DISPLAY_SCHEMA and display.get('no_new_PDE') is True,
            'Explicit display-only native export required')
    require(display.get('fieldunits') == 'V/m' and display.get('contactunits') == 'A/m2', 'Explicit common V/m and A/m2 units required')
    grid = display.get('grid', {})
    for key in ('x_edges_mm', 'y_edges_mm', 'z_faces_mm'):
        _edges(grid.get(key), key)
    nx, ny, nz = (len(grid[k])-1 for k in ('x_edges_mm', 'y_edges_mm', 'z_faces_mm'))
    require(nx <= 160 and ny <= 160 and nz <= 200, 'Bounded native display grid required')
    depths = grid.get('XY_actual_depths_mm')
    require(isinstance(depths, list) and len(depths) == 5 and all(type(v) in (int, float) and math.isfinite(v) and
            grid['z_faces_mm'][0] <= v <= grid['z_faces_mm'][-1] for v in depths), 'Five actual native XY depths required')
    for key in ('XZ_actual_y_mm', 'YZ_actual_x_mm'):
        require(type(grid.get(key)) in (int, float) and math.isfinite(grid[key]), 'Actual native central-plane coordinate required')
    cases = display.get('cases')
    require(isinstance(cases, list) and len(cases) == 6 and len({c.get('id') for c in cases}) == 6,
            'Six unique native displays, including canonical baseline, required')
    by_id = {c['id']: c for c in cases}
    require(set(by_id) == {r['id'] for r in rows}, 'Display/catalog row join differs')
    for row in rows:
        case = by_id[row['id']]
        require(case.get('geometry_key') == row['geometry_key'], 'Display geometry/wiring join differs')
        require(set(case.get('scales', {})) == set(MODES) and all(case['scales'][m] == row['normalizations'][m]['amplitude_scale'] for m in MODES),
                'Display scales must equal all five saved catalog scales; no rematching')
        centres = case.get('pad_centres')
        require(isinstance(centres, list) and len(centres) == row['circuit']['n_pads'] and
                {p.get('pad') for p in centres} == set(range(row['circuit']['n_pads'])), 'All physical pad identities required')
        for p in centres:
            require(p.get('node') in (-1, 0, 1, 'GND', 'gnd', 'out0', 'out1') and
                    all(type(p.get(k)) in (int, float) and math.isfinite(p[k]) for k in ('x_mm', 'y_mm')) and finite(p.get('area_mm2'), positive=True),
                    'Physical pad role, actual centroid and individual area required')
        outlines = case.get('physical_outlines')
        if outlines is not None:
            require(isinstance(outlines, list) and len(outlines) == len(centres) and
                    {p.get('pad') for p in outlines} == set(range(len(centres))), 'Physical outlines must retain all pad identities')
            def node_role(node):
                return 'out0' if node in (0, 'out0') else 'out1' if node in (1, 'out1') else 'GND'
            by_pad = {p['pad']: p for p in centres}
            for outline in outlines:
                poly = outline.get('polygon_mm')
                require(outline.get('node') in (-1, 0, 1, 'GND', 'gnd', 'out0', 'out1') and
                        node_role(outline['node']) == node_role(by_pad[outline['pad']]['node']), 'Physical outline/source role differs')
                require(isinstance(poly, list) and 3 <= len(poly) <= 20000 and all(isinstance(q, list) and len(q) == 2 and
                        all(type(v) in (int, float) and math.isfinite(v) for v in q) for q in poly),
                        'Finite exact physical polygon vertices required; no hull, rounding or area reconstruction')
                require(finite(outline.get('area_mm2'), positive=True) and
                        math.isclose(outline['area_mm2'], by_pad[outline['pad']]['area_mm2'], rel_tol=1e-10, abs_tol=1e-8),
                        'Physical outline and patch metadata must describe the same pad area')
        mask = _binary(case.get('pad_mask_b64'), nx*ny*2, row['id']+' pad mask')
        labels = {p[0] for p in struct.iter_unpack('<h', mask)}
        require(all(-1 <= p < len(centres) for p in labels) and
                {p for p in labels if p >= 0} == set(range(len(centres))), 'Pad mask must represent every physical pad and no unknown pad')
        require(set(case.get('planes', {})) == set(METRICS), 'Three distinct saved electrical metrics required')
        for metric in METRICS:
            planes = case['planes'][metric]
            require(isinstance(planes.get('xy'), list) and len(planes['xy']) == 5, 'Five unchanged native XY planes required')
            for i, plane in enumerate(planes['xy']):
                _binary(plane, nx*ny*4, row['id']+metric+'xy'+str(i))
            _binary(planes.get('xz'), nx*nz*4, row['id']+metric+'xz')
            _binary(planes.get('yz'), ny*nz*4, row['id']+metric+'yz')
        _binary(case.get('contact_J_RMS', {}).get('values_b64'), nx*ny*4, row['id']+' contact normal J RMS')
    for mode in MODES:
        for metric in METRICS:
            limits = display.get('color_limits', {}).get(mode, {}).get(metric, {})
            for scope in ('global', 'primary_ROI'):
                _range(limits.get(scope), mode+'/'+metric+'/'+scope)
        _range(display.get('contact_color_limits', {}).get(mode), mode+'/contact normal J')
    return rows


SCRIPT = r'''
'use strict';
const payload=JSON.parse(document.getElementById('data').textContent),catalog=payload.catalog,display=payload.display;
const rows=[catalog.canonical_baseline,...catalog.selected_layouts],cases=new Map(display.cases.map(c=>[c.id,c])),grid=display.grid;
const $=id=>document.getElementById(id),fmt=(v,d=6)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('en-US',{maximumSignificantDigits:d}):'—';
const names={raw_1Vpp:'동일 인가전압 · raw 1 Vpp',equal_total_source_output_RMS_sum:'출력별 RMS 전류합 일치',equal_total_power:'총 source 전력 일치',skin_contact_only:'피부·접촉 8개 부담 제한',legacy_composite_full_skin:'과거 복합 제한'};
const metricNames={maxTIS:'기본파 TIS · 2074 표본방향 최대',fixedTIS:'기본파 TIS · (X+Y)/√2 방향',RMS:'전체 carrier 벡터 E RMS'};
const burdenLabels={surface_J_RMS_max_A_m2:'접촉면 normal J 최대 [A/m²]',surface_J_RMS_p95_A_m2:'접촉면 normal J P95 [A/m²]',contact_voltage_RMS_max_V:'접촉 전압 최대 RMS [V]',SC_power_W:'SC 손실 [W]',contact_power_W:'접촉 계면 손실 [W]',bulk_skin_J_vector_RMS_max_A_m2:'SC+dermis 벡터 J 최대 [A/m²]',bulk_skin_J_vector_RMS_p95_A_m2:'SC+dermis 벡터 J P95 [A/m²]',skin_SC_plus_dermis_power_W:'SC+dermis 손실 [W]',source_power_W:'총 source 전력 [W]'};
const capKeys=Object.keys(burdenLabels).filter(k=>k!=='source_power_W'),palette=[[68,1,84],[65,68,135],[42,120,142],[34,168,132],[122,209,81],[253,231,37]];
function friendly(row){const id=row.source_case_id||row.id;if(id.includes('baseline-square15'))return'원래 4개 정방형 · 15×15 mm';if(id.includes('rounded-fullface225'))return'동일면적 모서리 완화형 · 225 mm²/패드';if(id.includes('crossalloc-source225-return225'))return'균등면적 십자형 · 225/225 mm²';if(/cross17p5.*arm10|cross17.5.*arm10/.test(id))return'17.5×10 십자형 · 250 mm²/패드';if(id.includes('crossalloc-source200-return250'))return'자극200 · 귀환250 십자형';if(id.includes('crossalloc-source250-return200'))return'자극250 · 귀환200 십자형';return row.label||row.id;}
function nodeLabel(n){return n===0||n==='out0'?'out0':n===1||n==='out1'?'out1':'GND';}
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function addLink(parent,path,text){if(!path)return;const a=el('a',text);a.href=path;parent.append(a);}
function fill(id,options,selected){for(const[v,t]of options){const o=el('option',t);o.value=v;$(id).append(o);}$(id).value=selected;}
fill('mode',Object.entries(names),'skin_contact_only');fill('metric',Object.entries(metricNames),'maxTIS');fill('plane',[['xy','수평 XY'],['xz','수직 XZ'],['yz','수직 YZ']],'xz');
fill('depth',grid.XY_actual_depths_mm.map((d,i)=>[String(i),`요청 ${[5,10,15,17.5,20][i]} mm → 실제 ${fmt(d)} mm`]),'3');fill('range',[['global','전체 native volume 공통 범위'],['primary_ROI','심부 ROI 색상 확대 · 초과값 있음']],'primary_ROI');
const nx=grid.x_edges_mm.length-1,ny=grid.y_edges_mm.length-1,nz=grid.z_faces_mm.length-1,cache=new Map();
function decode(s,kind){const key=kind+s;if(cache.has(key))return cache.get(key);const raw=atob(s),a=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)a[i]=raw.charCodeAt(i);const v=new DataView(a.buffer),n=kind==='h'?raw.length/2:raw.length/4,out=kind==='h'?new Int16Array(n):new Float32Array(n);for(let i=0;i<n;i++)out[i]=kind==='h'?v.getInt16(i*2,true):v.getFloat32(i*4,true);cache.set(key,out);return out;}
function color(v,max){if(!Number.isFinite(v))return'#e7edf2';const t=Math.max(0,Math.min(1,v/max))*5,i=Math.min(4,Math.floor(t)),f=t-i;return'rgb('+palette[i].map((x,k)=>Math.round(x+(palette[i+1][k]-x)*f)).join(',')+')';}
function canvasSetup(canvas){const w=Math.max(180,canvas.clientWidth),h=canvas.classList.contains('field-map')?260:150,dpr=Math.min(2,window.devicePixelRatio||1);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const c=canvas.getContext('2d');c.scale(dpr,dpr);c.fillStyle='#fff';c.fillRect(0,0,w,h);return[c,w,h];}
function frame(canvas,xe,ye,flipY){const[c,w,h]=canvasSetup(canvas),m={l:43,r:12,t:11,b:31},pw=w-m.l-m.r,ph=h-m.t-m.b,x0=xe[0],x1=xe.at(-1),y0=ye[0],y1=ye.at(-1),X=x=>m.l+(x-x0)/(x1-x0)*pw,Y=y=>m.t+(flipY?(y-y0)/(y1-y0):(y1-y)/(y1-y0))*ph;return{c,w,h,m,pw,ph,X,Y,xe,ye,flipY};}
function axes(f,xlabel,ylabel){const{c,X,Y,xe,ye,m,w,h}=f;c.strokeStyle='#b6c5d2';c.lineWidth=.8;c.strokeRect(m.l,m.t,f.pw,f.ph);c.fillStyle='#536779';c.font='10px system-ui';c.textAlign='center';for(const x of[xe[0],(xe[0]+xe.at(-1))/2,xe.at(-1)])c.fillText(fmt(x,4),X(x),h-17);c.fillText(xlabel,m.l+f.pw/2,h-3);c.textAlign='right';for(const y of[ye[0],(ye[0]+ye.at(-1))/2,ye.at(-1)])c.fillText(fmt(y,4),m.l-4,Y(y)+3);c.save();c.translate(11,m.t+f.ph/2);c.rotate(-Math.PI/2);c.textAlign='center';c.fillText(ylabel,0,0);c.restore();}
let overPattern;
function rectangles(f,values,max,scale=1,mask=null,role=false,pads=[]){const{c,X,Y,xe,ye}=f,cols=xe.length-1;for(let j=0;j<ye.length-1;j++)for(let i=0;i<cols;i++){const at=j*cols+i,v=values[at],pad=mask?mask[at]:null;if(role&&pad<0)continue;c.fillStyle=role?({out0:'#ec854b',out1:'#4383c6',GND:'#bcc8d1'}[nodeLabel(pads.find(p=>p.pad===pad)?.node)]||'#bcc8d1'):color(v*scale,max);const xx=X(xe[i]),yy=Y(ye[j]),yy1=Y(ye[j+1]);c.fillRect(xx,Math.min(yy,yy1),X(xe[i+1])-xx+.15,Math.abs(yy1-yy)+.15);if(!role&&Number.isFinite(v)&&v*scale>max){if(!overPattern){const tile=document.createElement('canvas');tile.width=tile.height=7;const tc=tile.getContext('2d');tc.strokeStyle='rgba(78,49,0,.6)';tc.beginPath();tc.moveTo(0,7);tc.lineTo(7,0);tc.stroke();overPattern=c.createPattern(tile,'repeat');}c.fillStyle=overPattern;c.fillRect(xx,Math.min(yy,yy1),X(xe[i+1])-xx+.15,Math.abs(yy1-yy)+.15);}}}
function outline(f,mask){const{c,X,Y,xe,ye}=f;c.strokeStyle='#193a50';c.lineWidth=.65;for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const p=mask[j*nx+i];if(p<0)continue;const edges=[[i===0||mask[j*nx+i-1]!==p,xe[i],ye[j],xe[i],ye[j+1]],[i===nx-1||mask[j*nx+i+1]!==p,xe[i+1],ye[j],xe[i+1],ye[j+1]],[j===0||mask[(j-1)*nx+i]!==p,xe[i],ye[j],xe[i+1],ye[j]],[j===ny-1||mask[(j+1)*nx+i]!==p,xe[i],ye[j+1],xe[i+1],ye[j+1]]];for(const[yes,x,y,xx,yy]of edges)if(yes){c.beginPath();c.moveTo(X(x),Y(y));c.lineTo(X(xx),Y(yy));c.stroke();}}}
function geometry(canvas,data){const mask=decode(data.pad_mask_b64,'h'),f=frame(canvas,grid.x_edges_mm,grid.y_edges_mm,false),physical=data.physical_outlines;if(physical){canvas.dataset.geometryMethod='exact_physical_polygons';const{c,X,Y}=f;for(const pad of physical){const points=pad.polygon_mm;c.beginPath();c.moveTo(X(points[0][0]),Y(points[0][1]));for(const[x,y]of points.slice(1))c.lineTo(X(x),Y(y));c.closePath();c.fillStyle={out0:'#ec854b',out1:'#4383c6',GND:'#bcc8d1'}[nodeLabel(pad.node)];c.fill();c.strokeStyle='#193a50';c.lineWidth=.8;c.stroke();}}else{canvas.dataset.geometryMethod='native_cell_mask_partial_contact_cell_display';rectangles(f,mask,1,1,mask,true,data.pad_centres);outline(f,mask);}const{c,X,Y}=f;c.strokeStyle='#5c798b';c.lineWidth=.7;c.beginPath();c.ellipse(X(0),Y(0),Math.abs(X(25)-X(0)),Math.abs(Y(25)-Y(0)),0,0,2*Math.PI);c.stroke();c.font='bold 9px system-ui';c.textAlign='center';for(const p of data.pad_centres){c.fillStyle='#102e42';c.fillText(`${p.pad}:${nodeLabel(p.node)}`,X(p.x_mm),Y(p.y_mm));}axes(f,'x [mm]','y [mm]');}
function locate(edges,value){for(let i=0;i<edges.length-1;i++)if(value>=edges[i]&&value<edges[i+1])return i;return value===edges.at(-1)?edges.length-2:-1;}
function hover(canvas,f,values,scale,unit,row,plane,depth,max){canvas.onpointermove=e=>{const box=canvas.getBoundingClientRect(),px=e.clientX-box.left,py=e.clientY-box.top,x=f.xe[0]+(px-f.m.l)/f.pw*(f.xe.at(-1)-f.xe[0]),yy=(py-f.m.t)/f.ph,y=f.flipY?f.ye[0]+yy*(f.ye.at(-1)-f.ye[0]):f.ye.at(-1)-yy*(f.ye.at(-1)-f.ye[0]),i=locate(f.xe,x),j=locate(f.ye,y);if(i<0||j<0){$('hover').textContent='셀 위에 포인터를 올리면 실제 native 좌표와 표시값이 나옵니다.';return;}const v=values[j*(f.xe.length-1)+i]*scale,xx=(f.xe[i]+f.xe[i+1])/2,zz=(f.ye[j]+f.ye[j+1])/2;let xyz=plane==='xy'?`x ${fmt(xx)}, y ${fmt(zz)}, z ${fmt(depth)}`:plane==='xz'?`x ${fmt(xx)}, y ${fmt(grid.XZ_actual_y_mm)}, z ${fmt(zz)}`:`x ${fmt(grid.YZ_actual_x_mm)}, y ${fmt(xx)}, z ${fmt(zz)}`;$('hover').textContent=`${friendly(row)} · ${xyz} mm · ${Number.isFinite(v)?fmt(v,7)+' '+unit:'영역 밖 / 미지원 (NaN)'} · ${display.display_precision?'Float16 근사 표시값; 원통계 Float64':'Float32 표시값; 원통계 Float64'} · ${Number.isFinite(v)?(v>max?'표시 상한 초과, 물리적 포화 아님':'색상 범위 내'):'유효값 없음'}`;};canvas.onclick=canvas.onpointermove;}
function field(canvas,row,data){const metric=$('metric').value,plane=$('plane').value,depth=Number($('depth').value),mode=$('mode').value,range=$('range').value,p=data.planes[metric],values=decode(plane==='xy'?p.xy[depth]:p[plane],'f'),xe=plane==='yz'?grid.y_edges_mm:grid.x_edges_mm,ye=plane==='xy'?grid.y_edges_mm:grid.z_faces_mm,f=frame(canvas,xe,ye,plane!=='xy'),max=display.color_limits[mode][metric][range][1],scale=data.scales[mode];canvas.dataset.vmax=String(max);canvas.dataset.vmin='0';canvas.dataset.mode=mode;canvas.dataset.metric=metric;canvas.dataset.plane=plane;rectangles(f,values,max,scale);const{c,X,Y}=f;c.strokeStyle='rgba(255,255,255,.95)';c.lineWidth=1.3;c.setLineDash([4,3]);if(plane==='xy'){c.beginPath();c.ellipse(X(0),Y(0),Math.abs(X(5)-X(0)),Math.abs(Y(5)-Y(0)),0,0,2*Math.PI);c.stroke();}else{const fixed=plane==='xz'?grid.XZ_actual_y_mm:grid.YZ_actual_x_mm,r=Math.sqrt(Math.max(0,25-fixed*fixed));c.strokeRect(X(-r),Y(15),X(r)-X(-r),Y(20)-Y(15));for(const z of[.1,5.1,10.1]){c.beginPath();c.moveTo(X(xe[0]),Y(z));c.lineTo(X(xe.at(-1)),Y(z));c.stroke();}}c.setLineDash([]);axes(f,plane==='yz'?'y [mm]':'x [mm]',plane==='xy'?'y [mm]':'+z depth [mm]');hover(canvas,f,values,scale,'V/m',row,plane,grid.XY_actual_depths_mm[depth],max);panelScale(canvas,values,scale,max,'V/m');layerLabels(f,plane,grid.XY_actual_depths_mm[depth]);}
function panelScale(canvas,values,scale,max,unit){
 let box=canvas.nextElementSibling;if(!box||!box.classList.contains('panel-scale')){box=el('div',undefined,'panel-scale');canvas.after(box);}
 const valid=Array.from(values).filter(Number.isFinite),over=valid.filter(v=>v*scale>max).length;
 canvas.dataset.overCount=String(over);canvas.dataset.validCount=String(valid.length);
 const plane=canvas.dataset.plane||'xy',depth=canvas.classList.contains('contact-map')?0:grid.XY_actual_depths_mm[Number($('depth').value)],location=plane==='xy'?`XY z=${fmt(depth)} mm`:plane==='xz'?`XZ y=${fmt(grid.XZ_actual_y_mm)} mm`:`YZ x=${fmt(grid.YZ_actual_x_mm)} mm`;
 box.replaceChildren(el('div',`${location} · ${display.display_precision?'Float16 근사':'Float32 표시'} · 공통 색상 범위 0–${fmt(max)} ${unit}`),el('div',undefined,'gradient'));
 const ticks=el('div',undefined,'scale-ticks');for(const fraction of[0,.5,1])ticks.append(el('span',fmt(max*fraction,4)));box.append(ticks);
 box.append(el('div',`▧ 표시 상한 초과 ${valid.length?fmt(100*over/valid.length,4):'—'}% (${over}/${valid.length}) · 현재 표시 단면 유한 셀, 비가중 · 체적 통계 아님`));
 box.append(el('div','상한 초과는 빗금+노랑 · 물리적 포화 아님. 값은 유지; 셀 hover/클릭으로 확인.'));
}
function layerLabels(f,plane,depth){
 const {c,X,Y}=f;c.save();c.font='10px system-ui';c.textAlign='left';
 function label(text,x,y){const w=c.measureText(text).width;c.fillStyle='rgba(255,255,255,.88)';c.fillRect(x-2,y-10,w+4,13);c.fillStyle='#173249';c.fillText(text,x,y);}
 if(plane!=='xy'){for(const[name,z]of[['dermis 진피',2.6],['fat 지방',7.6],['muscle 근육',22.6]])label(name,X(f.xe[0])+4,Y(z));for(const z of[.1,5.1,10.1]){label(`${z} mm`,X(f.xe.at(-1))-42,Y(z)+11);}c.textAlign='left';label('목표 ROI 15–20 mm',X(-5),Y(17.5));}
 else{const name=depth<.1?'SC 각질층':depth<5.1?'dermis 진피':depth<10.1?'fat 지방':'muscle 근육';label(name,X(f.xe[0])+4,f.m.t+14);label(depth>=15&&depth<=20?'목표 ROI r≤5 mm':'r≤5 mm 투영 (목표 깊이 밖)',X(f.xe[0])+4,f.m.t+29);}
 c.restore();
}
function contact(canvas,row,data){const mode=$('mode').value,values=decode(data.contact_J_RMS.values_b64,'f'),mask=decode(data.pad_mask_b64,'h'),f=frame(canvas,grid.x_edges_mm,grid.y_edges_mm,false),max=display.contact_color_limits[mode][1],scale=data.scales[mode];canvas.dataset.vmax=String(max);canvas.dataset.vmin='0';canvas.dataset.mode=mode;rectangles(f,values,max,scale);outline(f,mask);axes(f,'x [mm]','y [mm]');hover(canvas,f,values,scale,'A/m²',row,'xy',0,max);panelScale(canvas,values,scale,max,'A/m²');}
function hotspot(s){const h=s.hotspot||{};return{coords:h.center_xyz_mm||h.position_mm||h.xyz_mm||s.maximum_location_mm||s.max_position_mm||null,layer:h.layer??s.maximum_layer??s.max_layer??'미제공'};}
function sourceVpp(n){if(n.actual_source_Vpp_intervals_V)return JSON.stringify(n.actual_source_Vpp_intervals_V);if(n.source_Vpp_by_output)return JSON.stringify(n.source_Vpp_by_output);return fmt(n.source_Vpp_per_output)+' Vpp / output (저장 정의)';}
function table(headers,records){const box=el('div',undefined,'table-scroll'),t=el('table'),thead=el('thead'),hr=el('tr');for(const h of headers)hr.append(el('th',h));thead.append(hr);const body=el('tbody');for(const r of records){const tr=el('tr');for(const v of r){const td=el('td');if(v instanceof Node)td.append(v);else td.textContent=v;tr.append(td);}body.append(tr);}t.append(thead,body);box.append(t);return box;}
function gateText(row){const checks=row.gate_checks||[];return checks.length?`${checks.filter(c=>c.passed).length}/${checks.length} 통과`:'비교 기준';}
function score(row){return Array.isArray(row.ranking_score)?row.ranking_score[0]:row.max_relative_violation;}
function rowInfo(row,n){const b=n.normalized_burdens,s=n.regions[PRIMARY][$('metric').value];return[fmt(s.mean),fmt(s.p10),fmt(s.CV),fmt(s.max),fmt(n.regions.surface_0_5[$('metric').value].p95),fmt(n.regions.primary_complement[$('metric').value].p95),sourceVpp(n),JSON.stringify(n.source_output_RMS_by_output_mA||[]),fmt(b.source_power_W)];}
const PRIMARY='primary_r5_depth15_20',cards=new Map();
rows.forEach((row,i)=>{const card=el('article',undefined,'case-card'+(i===0?' baseline':''));card.dataset.caseId=row.id;const head=el('div',undefined,'case-head'),name=el('div');name.append(el('span',i===0?'ORIGINAL · 기준':`선별 ${i}`,'eyebrow'),el('h2',friendly(row)));head.append(name,el('span',i===0?'기준':gateText(row),'badge'+(i===0?' neutral':'')));const sub=el('p',undefined,'case-sub'),stats=el('div',undefined,'mini-stats'),top=el('div',undefined,'top-pair');const geo=el('canvas'),j=el('canvas');geo.className='layout-map';j.className='contact-map';for(const[c,t]of[[geo,'z=0 패드 형상·출력 연결'],[j,'z=0 접촉 normal J RMS']]){const fig=el('figure');fig.append(c,el('figcaption',t));top.append(fig);}const main=el('canvas');main.className='field-map';const geometrynote=el('p',undefined,'geometry-note'),caption=el('p',undefined,'map-caption'),globalnote=el('p',undefined,'global-note'),details=el('details');details.append(el('summary','연결·면적·source 및 검증 근거'));const evidence=el('div',undefined,'evidence');details.append(evidence);card.append(head,sub,stats,main,caption,globalnote,top,geometrynote,details);$('cards').append(card);cards.set(row.id,{card,stats,sub,geo,j,main,caption,globalnote,geometrynote,evidence});});
function renderEvidence(row,n,target){target.replaceChildren();const data=cases.get(row.id),pads=data.pad_centres;target.append(el('p',`물리 패드 ${row.circuit.n_pads}개 · 독립 출력 ${row.circuit.n_outputs}개 · 공통 GND ${row.circuit.n_return_nodes}개 · 50 Ω`),el('p','각 패드 면적: '+pads.map(p=>`pad${p.pad} ${fmt(p.area_mm2)} mm²`).join(' / ')));target.append(el('p','실제 source Vpp: '+sourceVpp(n)),el('p','출력별 RMS 전류: '+(n.source_output_RMS_by_output_mA||[]).map(x=>fmt(x)).join(' / ')+' mA'));const checks=row.gate_checks||[];target.append(table(['8개 원래 기준 · 저장 판정','후보','기준','결과'],checks.map(g=>[g.name,fmt(g.candidate),fmt(g.baseline),g.passed?'PASS':'FAIL'])));const ids=el('dl');for(const[k,v]of[['candidate',row.condition_id||row.id],['source case/run',(row.source_case_id||'')+' / '+(row.source_run_id||'')],['source commit',row.source_commit],['config SHA256',row.configuration_sha256],['geometry/wiring key',row.geometry_key]]){ids.append(el('dt',k),el('dd',v||'—'));}target.append(ids);const links=el('p',undefined,'source-links');for(const[k,p]of Object.entries(row._ui_links||{}))addLink(links,p,k+' ↗ ');target.append(links);const proofs=el('details');proofs.append(el('summary','native 지표·접촉 J 재현 확인과 격자 메타데이터'));const pre=el('pre',JSON.stringify({native_stats_proofs:data.native_stats_proofs||null,contact_J_regression:data.contact_J_RMS.regression||data.contact_J_RMS.regression_proof||null,mesh:row.mesh_metadata||null,validation_scope:'대수적 검사/표시 재현과 전체 수렴·실험은 별개; source JSON 영수증 기준'},null,2));proofs.append(pre);target.append(proofs);const bulk=el('p','체적 SC+dermis J 공간지도: 미저장·미제공. 아래 최대/P95 표는 별도 native 벡터 J 통계입니다.','muted');target.append(bulk);}
function renderBurdens(mode){const host=$('burdens');host.replaceChildren();for(const row of rows){const n=row.normalizations[mode],b=n.normalized_burdens,limits=n.baseline_derived_numerical_limits||catalog.canonical_baseline.normalizations.raw_1Vpp.normalized_burdens,box=el('article',undefined,'burden-card');box.append(el('h3',friendly(row)));for(const k of capKeys){const line=el('div',undefined,'burden-line'),ratio=limits[k]>0?b[k]/limits[k]:null,label=el('div',undefined,'burden-label');label.append(el('span',burdenLabels[k]),el('strong',fmt(b[k])+' · '+(ratio===null?'—':fmt(ratio,4)+'×')));const track=el('div',undefined,'track'),bar=el('i');bar.style.width=(ratio===null?0:Math.min(150,ratio*100)/1.5)+'%';if(ratio!==null&&ratio>1+1e-10)bar.className='over';track.append(bar);line.append(label,track);box.append(line);}box.append(el('p',`총 source 전력 ${fmt(b.source_power_W)} W · skin8의 8개 제한에 source 전력은 포함되지 않음`,'source-power'));const caps=n.active_skin_contact_caps||[];box.append(el('p','저장된 활성 제한: '+(caps.join(', ')||'해당 기록 없음'),'muted'));host.append(box);}}
function renderPower(mode){const host=$('signed-power');host.replaceChildren();let found=false;for(const row of rows){const n=row.normalizations[mode],data=cases.get(row.id),pw=n.signed_per_output_power_evidence||data.signed_output_power_evidence?.[mode];if(!pw)continue;found=true;const details=el('details');details.append(el('summary',friendly(row)));const records=[];if(pw.totals)records.push(['그룹 총합',fmt(pw.totals.ideal_source_power_W),fmt(pw.totals.metal_delivered_power_W),fmt(pw.totals.source_resistor_loss_W)]);for(const out of pw.outputs||[]){records.push(['out'+out.output_index,fmt(out.ideal_source_power_W),fmt(out.metal_delivered_power_W),fmt(out.source_resistor_loss_W)]);for(const f of out.spectrum||[])records.push(['out'+out.output_index+' / '+f.frequency_Hz+' Hz',fmt(f.ideal_source_power_W),fmt(f.metal_delivered_power_W),fmt(f.source_resistor_loss_W)]);}if(!records.length)records.push(['원형 영수증',JSON.stringify(pw),'','']);details.append(table(['출력·주파수','signed source W','signed metal W','50 Ω loss W'],records));host.append(details);}if(!found)host.append(el('p','이 선택의 signed 출력별 전력 영수증은 제공되지 않았습니다. 총 source 전력은 부담 표에 보존하며, 전류·전압으로 새로 추정하지 않습니다.'));}
function update(){const mode=$('mode').value,metric=$('metric').value,plane=$('plane').value,depth=Number($('depth').value),range=$('range').value,clim=display.color_limits[mode][metric][range],jc=display.contact_color_limits[mode];$('hover').textContent='셀 hover/클릭: 상한 적용 전 표시값과 초과 여부 확인 (정밀 원본값 아님)';$('depth').disabled=plane!=='xy';$('field-legend').textContent=`공통 ${fmt(clim[0])}–${fmt(clim[1])} V/m · 6개 배치와 모든 plane 동일 · ${range==='primary_ROI'?'심부 ROI 색상 확대: 표시 상한 초과, 물리적 포화 아님':'전체 native volume 범위'}`;$('contact-legend').textContent=`접촉 normal J RMS 공통 ${fmt(jc[0])}–${fmt(jc[1])} A/m² · 6개 배치 동일`;$('mode-note').textContent=`현재 지도·수치표: ${names[mode]}. ${mode==='skin_contact_only'?'원래 square의 피부·접촉 8개 수치 제한을 맞춘 저장 진폭이며 source 전력·1 Vpp 상한이 없습니다.':mode==='equal_total_source_output_RMS_sum'?'두 출력 RMS 전류의 합이며 공통 GND 귀환전류가 아닙니다.':mode==='legacy_composite_full_skin'?'피부·접촉 8개와 source 전력·1 Vpp 상한을 함께 적용한 과거 비교입니다.':'저장된 비교 진폭을 사용합니다.'} source Vpp가 1을 넘는 결과를 동일1Vpp 이득으로 해석하지 않습니다.`;for(const row of rows){const data=cases.get(row.id),v=cards.get(row.id),n=row.normalizations[mode],r=n.regions[PRIMARY][metric],area=data.pad_centres.reduce((a,p)=>a+p.area_mm2,0);v.sub.textContent=`${row.circuit.n_pads} pads / ${row.circuit.n_outputs} outputs / common GND · 접촉 총면적 ${fmt(area)} mm² · A ${fmt(n.amplitude_scale)}`;v.stats.replaceChildren();for(const[label,val]of[['목표 평균',fmt(r.mean)+' V/m'],['목표 P10',fmt(r.p10)+' V/m'],['CV',fmt(r.CV)],['최대 위반율',row===rows[0]?'비교 기준':fmt(score(row)*100,4)+'%']]){const box=el('div');box.append(el('span',label),el('b',val));v.stats.append(box);}v.caption.textContent=plane==='xy'?`native XY: 실제 깊이 ${fmt(grid.XY_actual_depths_mm[depth])} mm (요청 ${[5,10,15,17.5,20][depth]} mm)`:`native ${plane.toUpperCase()}: ${plane==='xz'?'y':'x'}=${fmt(plane==='xz'?grid.XZ_actual_y_mm:grid.YZ_actual_x_mm)} mm · +z 깊이 · 흰 경계 0.1/5.1/10.1 mm`;const global=n.regions.total[metric],gh=hotspot(global);v.caption.textContent+=' · 층 깊이 [mm]: SC 0–0.1 / dermis 0.1–5.1 / fat 5.1–10.1 / muscle 10.1–25.1. 목표 ROI r≤5, z15–20.';v.globalnote.textContent=`전역 최대 ${fmt(global.max)} V/m · ${gh.coords?JSON.stringify(gh.coords)+' mm':'좌표 미제공'} · ${gh.layer}. 표면·층 경계 hotspot은 깊이 집중의 근거가 아닙니다.`;v.geometrynote.textContent=data.physical_outlines?'배치 그림: 정확한 물리 polygon 윤곽. 접촉 J: 부분접촉면은 해당 native 셀로 표시; 정확 형상은 배치 윤곽을 참조합니다.':'배치 그림: native mask 셀 표시(부분접촉은 셀로 표시). 정확 물리 윤곽은 이 export에 미제공입니다. 접촉 J 역시 native patch 셀 표시입니다.';geometry(v.geo,data);field(v.main,row,data);contact(v.j,row,data);renderEvidence(row,n,v.evidence);}const host=$('quantitative');host.replaceChildren(table(['배치','목표 평균 V/m','목표 P10 V/m','CV','목표 최대 V/m','표면0–5 P95 V/m','전체 비표적 P95 V/m','실제 source Vpp','각 output RMS mA','총 source W'],rows.map(row=>[friendly(row),...rowInfo(row,row.normalizations[mode])])));const vols=[];for(const row of rows){const n=row.normalizations[mode];for(const region of[PRIMARY,'surface_0_5','primary_complement','total']){const s=n.regions[region][metric],cuts=s.fixed_baseline_threshold_volume||{},hot=hotspot(s);vols.push([friendly(row),region,fmt(s.p10_over_mean),fmt(s.volume_m3),fmt(cuts.primary_r5_depth15_20_mean?.volume_m3),fmt(cuts.primary_r5_depth15_20_p10?.volume_m3),hot.coords?JSON.stringify(hot.coords):'미제공',hot.layer,fmt(s.max)]);}}$('volume-stats').replaceChildren(table(['배치','영역','P10/평균','표현체적 m³','≥원래ROI평균 체적 m³','≥원래ROIP10 체적 m³','hotspot xyz mm','층','최대 V/m'],vols));renderBurdens(mode);renderPower(mode);}
for(const id of['mode','metric','plane','depth','range'])$(id).addEventListener('change',update);
const compact=catalog.ranked_layouts||catalog.all_rows||[];$('ranking').append(table(['배치','최대 위반율','합계 위반율','목표 P10','실패 항목'],compact.map(row=>[friendly(row),fmt(score(row)*100,4)+'%',fmt((row.ranking_score?.[1]??row.sum_relative_violation)*100,4)+'%',fmt(row.eight_gate_values?.primary_maxTIS_p10??row.gate_values?.[(catalog.gate_names||[]).indexOf('primary_maxTIS_p10')]??row.ranking_metrics?.p10),((row.gate_checks||[]).filter(g=>!g.passed).map(g=>g.name).join(', '))||(row.failed_gate_indices?row.failed_gate_indices.map(i=>(catalog.gate_names||[])[i]).join(', '):JSON.stringify(row.failed_gate_names||row.failed_gates||[]))])));
const padReference=catalog.pad_count_reference,padHost=$('pad-count-reference');if(padReference){const records=padReference.rows.map(row=>{const raw=row.normalizations.raw_1Vpp,skin=row.normalizations.skin_contact_only,b=skin.normalized_burdens;return[row.label||row.id,row.n_pads,row.n_outputs,'common GND',fmt(raw.mean_V_m),fmt(raw.P10_V_m),fmt(skin.mean_V_m),fmt(skin.P10_V_m),fmt(skin.source_Vpp_per_output),JSON.stringify(skin.source_output_RMS_by_output_mA),fmt(b.surface_J_RMS_max_A_m2),fmt(b.surface_J_RMS_p95_A_m2),fmt(b.contact_voltage_RMS_max_V),fmt(b.source_power_W)];});padHost.append(table(['별도 가족/배치','물리패드','독립출력','귀환','raw 평균 V/m','raw P10 V/m','skin8 평균 V/m','skin8 P10 V/m','skin8 source Vpp/output','skin8 outputRMS mA','접촉 Jmax A/m²','접촉 J95 A/m²','접촉 RMS V','총 source W'],records),el('p',padReference.scope,'footnote'));const src=el('p',undefined,'footnote');addLink(src,catalog._ui_pad_count_source,'별도 가족 원본 영수증 ↗');src.append(el('code',' SHA256 '+padReference.source.SHA256));padHost.append(src);}else{padHost.append(el('p','이 catalog에 별도 strip 가족의 수치 영수증이 제공되지 않았습니다. 과거 4/8/12/16-pad 원본 화면 링크를 아래에 보존하며 값을 새로 채우지 않습니다.','footnote'));}
const exclusions=catalog.excluded_rows||catalog.exclusions||[];$('excluded').textContent=JSON.stringify(exclusions,null,2);$('source-overview').textContent=JSON.stringify({schema:catalog.schema,selection:catalog.selection||catalog.ranking_definition||'max eight relative violations → sum → P10 → mean; representative completed drive per layout',native_display_schema:display.schema,source:catalog.source_commit||catalog.implementation_git_commit,display_source_proofs:display.source_proofs||display.input_sha256||'per-case native_stats_proofs',catalog_holds:catalog.holds},null,2);
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(update,100);});window.task1Top5=Object.freeze({render:update,catalog,display});update();
'''

CSS = '''
.panel-scale{font-size:10px;line-height:1.5;margin:3px 0 10px;color:#435b6b}.scale-ticks{display:flex;justify-content:space-between;font-variant-numeric:tabular-nums}.display-warning{padding:12px;border:1px solid #d9ac5a;background:#fff7df;border-radius:8px;font-size:12px}code{overflow-wrap:anywhere;word-break:break-all}

:root{--ink:#173249;--muted:#60798b;--line:#dbe6ec;--paper:#f2f6f8;--brand:#136d87;--amber:#aa681e}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 system-ui,-apple-system,"Noto Sans KR",sans-serif}a{color:#166c91}header{background:linear-gradient(120deg,#102d46,#165d72);color:#fff;padding:34px max(22px,calc((100vw - 1550px)/2)) 30px}.eyebrow{font-size:10px;letter-spacing:.1em;font-weight:750;color:#6b8799}.hero-tag{font-size:11px;letter-spacing:.12em;color:#a8d8e1}h1{font-size:clamp(26px,3vw,40px);line-height:1.2;margin:10px 0 14px}header p{max-width:1000px;color:#d3e5eb;margin:7px 0}.hero-badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.hero-badges span{border:1px solid #75a6b855;background:#ffffff0b;border-radius:20px;padding:5px 11px;font-size:11px}main{max-width:1594px;margin:auto;padding:20px 22px 60px}.controls{position:sticky;top:0;z-index:10;display:flex;flex-wrap:wrap;gap:12px;padding:14px;background:#ffffffed;border:1px solid var(--line);border-radius:12px;box-shadow:0 4px 18px #1732490a;backdrop-filter:blur(9px)}label{display:flex;flex-direction:column;gap:5px;font-size:11px;font-weight:700;color:var(--muted)}select{font:inherit;font-size:12px;padding:9px 28px 9px 10px;max-width:300px;border:1px solid #cbdbe3;border-radius:7px;background:#fff;color:var(--ink)}select:focus{outline:2px solid #4aa5bc}.mode-note{padding:12px 16px;border-left:3px solid #2c91a9;background:#e8f3f6;color:#28596f;font-size:12px;border-radius:3px}.legends{display:grid;grid-template-columns:1.7fr 1fr;gap:16px;margin:16px 0}.legend{background:white;border:1px solid var(--line);padding:13px 16px;border-radius:9px;font-size:11px}.gradient{height:9px;border-radius:7px;margin-top:8px;background:linear-gradient(90deg,rgb(68,1,84),rgb(65,68,135),rgb(42,120,142),rgb(34,168,132),rgb(122,209,81),rgb(253,231,37))}.section-title{display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin:24px 0 10px}.section-title h2{font-size:19px;margin:0}.section-title small{color:var(--muted);font-size:11px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.case-card{min-width:0;border:1px solid var(--line);background:#fff;border-radius:13px;padding:16px;box-shadow:0 3px 12px #17324906}.case-card.baseline{border-top:4px solid #147f9d;padding-top:13px}.case-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}.case-head h2{font-size:15px;line-height:1.4;margin:4px 0 0;overflow-wrap:anywhere}.badge{font-size:10px;color:#935411;background:#fff0da;border:1px solid #f0d2a6;border-radius:15px;padding:4px 8px;white-space:nowrap}.badge.neutral{background:#e9f4f8;color:#15647d;border-color:#b8dbe7}.case-sub{font-size:10px;color:var(--muted);min-height:30px;margin:9px 0}.mini-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:10px 0}.mini-stats div{background:#f2f7fa;border-radius:7px;padding:8px 6px;overflow:hidden}.mini-stats span{display:block;font-size:9px;color:var(--muted);white-space:nowrap}.mini-stats b{display:block;font-size:11px;font-variant-numeric:tabular-nums;white-space:nowrap;margin-top:3px}canvas{display:block;width:100%;height:150px;background:#fff}.field-map{height:260px;border-top:1px solid #edf2f5}.geometry-note{font-size:10px;color:#60798b;border-left:2px solid #bbd3de;padding-left:8px}.global-note{font-size:10px;color:#735726;background:#fff8ed;padding:7px 9px;border-radius:5px;margin:4px 0 9px}.map-caption{font-size:10px;color:var(--muted);margin:0 0 10px}.top-pair{display:grid;grid-template-columns:1fr 1fr;gap:5px;border-top:1px solid #edf2f5;padding-top:7px}figure{margin:0;min-width:0}figcaption{font-size:10px;text-align:center;color:var(--muted)}details{border-top:1px solid var(--line);padding:10px 0;margin-top:12px}summary{font-size:11px;font-weight:700;color:#386c85;cursor:pointer}.evidence{font-size:11px;overflow-wrap:anywhere}.evidence p{margin:7px 0}.evidence dl{font-size:10px}.evidence dd{margin:0 0 6px;font-family:ui-monospace,monospace}.evidence dt{font-weight:750;color:var(--muted)}.source-links{display:flex;flex-wrap:wrap;gap:8px}.role-key{display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin:12px 0}.role-key i{display:inline-block;width:10px;height:10px;margin-right:5px;border:1px solid #193a50}.role-key .out0{background:#ec854b}.role-key .out1{background:#4383c6}.role-key .gnd{background:#bcc8d1}.hover{position:sticky;bottom:0;z-index:11;background:#153c50;color:#e0eef4;border-radius:8px;padding:10px 14px;font-size:11px;margin:14px 0;box-shadow:0 2px 12px #17324920}.table-scroll{overflow:auto;max-width:100%;border:1px solid var(--line);border-radius:9px;background:#fff}table{border-collapse:collapse;width:100%;font-size:11px;white-space:nowrap}th,td{padding:9px 11px;border-bottom:1px solid #e4edf1;text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}th{background:#eaf1f5;font-weight:700}tr:last-child td{border-bottom:0}.burdens{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.burden-card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px}.burden-card h3{font-size:13px;margin:0 0 12px;overflow-wrap:anywhere}.burden-line{margin:9px 0}.burden-label{display:flex;justify-content:space-between;gap:8px;font-size:10px}.burden-label strong{font-variant-numeric:tabular-nums;white-space:nowrap}.track{height:5px;background:#e7eef2;border-radius:5px;overflow:hidden;margin-top:4px}.track i{display:block;height:5px;background:#3a94ae;border-radius:5px}.track i.over{background:#ca843c}.source-power{font-size:10px;padding-top:9px;border-top:1px dashed #cddde5}.muted{color:var(--muted);font-size:11px}.notice{background:#fff4e4;color:#80551d;border:1px solid #eed6b0;border-radius:10px;padding:16px;font-size:12px}.footnote{color:var(--muted);font-size:11px;line-height:1.8}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px;background:#eef4f7;padding:12px;border-radius:7px}.linkrow{display:flex;gap:15px;flex-wrap:wrap;margin-top:15px;font-size:12px}noscript{display:block;padding:20px;background:#fff4e4}@media(max-width:1180px){.cards,.burdens{grid-template-columns:repeat(2,minmax(0,1fr))}.controls{position:relative}.mini-stats b{font-size:12px}}@media(max-width:720px){header{padding:25px 18px}main{padding:14px 12px 36px}.cards,.burdens,.legends{grid-template-columns:1fr}.controls{gap:9px;padding:12px}label{flex:1 1 45%}select{max-width:100%;width:100%;font-size:11px}.case-card{padding:13px}.section-title{display:block}.section-title small{display:block;margin-top:4px}.hover{bottom:5px;font-size:10px}.mini-stats b{font-size:12px}}
'''


def _ui_links(row, output):
    result = {}
    for key in ('native_summary', 'native_registration', 'native_case_record', 'condition_source', 'scalar_archive'):
        ref = row.get(key)
        if isinstance(ref, dict) and isinstance(ref.get('path'), str):
            result[key] = os.path.relpath(Path(ref['path']).resolve(), output.parent)
    probe = row.get('raw_probe_artifact_reference')
    if isinstance(probe, dict) and isinstance(probe.get('path'), str):
        result['unloaded probe40'] = os.path.relpath(Path(probe['path']).resolve(), output.parent)
    return result


def render(catalog: dict, display: dict, output: Path) -> str:
    """Return a self-contained HTML string; the guarded caller writes it.

    Input contracts and payload byte shapes are verified. No file is opened,
    generated, hashed, or changed by this function. Source/hash provenance is
    supplied by the caller and is not promoted into independent verification.
    """
    validate_display(catalog, display)
    output = Path(output).resolve()
    # JSON round-trip creates a caller-independent view without custom encoders,
    # object hooks, NaN/Infinity, native imports or implicit rescaling.
    view_catalog = json.loads(json.dumps(catalog, ensure_ascii=False, allow_nan=False))
    for row in [view_catalog['canonical_baseline'], *view_catalog['selected_layouts']]:
        row['_ui_links'] = _ui_links(row, output)
    if view_catalog.get('pad_count_reference'):
        view_catalog['_ui_pad_count_source'] = os.path.relpath(Path(view_catalog['pad_count_reference']['source']['path']).resolve(), output.parent)
    encoded = json.dumps({'catalog': view_catalog, 'display': display}, ensure_ascii=False,
                         allow_nan=False, separators=(',', ':')).replace('<', '\\u003c').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    repository_docs = Path(__file__).resolve().parents[1]/'docs'
    archived = os.path.relpath(repository_docs/'CLOUD_VOLUME_RESULTS_20261021_v8.html', output.parent)
    fine_groups = os.path.relpath(repository_docs/'CLOUD_GROUPED_FINE_RESULTS_20261021_v2.html', output.parent)
    return '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-__HASH__'; style-src 'unsafe-inline'">
<title>작업 1 · 현재 선별된 전극 배치 5종</title><style>__CSS__</style><body>
<header><div class="hero-tag">TASK 1 · NATIVE FIELD COMPARISON</div><h1>현재 선별된 전극 배치 5종</h1>
<p>원래 4-pad 기준과 서로 다른 형상·위치·배선의 5개 배치를 비교합니다. 배치별 완료된 대표 구동을 포함하므로, 형상 하나의 독립적인 인과 효과를 뜻하지 않습니다.</p>
<p>선정 순서: 8개 수치 기준의 최대 상대 위반율 → 위반율 합계 → 목표 P10 → 평균. 1위도 모든 기준을 통과한 성공 후보가 아닙니다.</p>
<div class="hero-badges"><span>고정 D50 mm · 층 0.1 / 5 / 5 / 15 mm</span><span>물리 패드 수 ≠ 독립 출력 수</span><span>계산 완료 · 전체 수렴 / 실험 / 채택 보류</span></div></header>
<main><section class="controls" aria-label="저장된 결과 선택">
<label for="mode">비교 정규화<select id="mode"></select></label><label for="metric">전기장 지표<select id="metric"></select></label><label for="plane">단면<select id="plane"></select></label><label for="depth">XY 실제 깊이<select id="depth"></select></label><label for="range">공통 색상 범위<select id="range"></select></label></section>
<p id="mode-note" class="mode-note" aria-live="polite"></p><p class="display-warning"><b>표시 상한 초과, 물리적 포화 아님</b> — 노랑 끝색과 빗금은 색상 상한을 넘는 값입니다. 실제 배열을 clipping하지 않습니다. 전체 분포 범위와 심부 ROI 색상 확대는 동일 데이터를 다른 공통 눈금으로 표시합니다. ROI 확대는 공간 자르기가 아닙니다.<br>maxTIS: 기본파 변조의 2074 표본방향 최대 (연속 최대의 표본 하한). fixedTIS: 기본파 (X+Y)/√2 고정방향 변조. carrier RMS: 전체 carrier 벡터 E RMS; TIS 변조와 다릅니다. 지도는 근사 표시값이고 원 Float64 통계와 구분합니다. 단면 셀 통계는 지방 전체 체적 최소나 물리 검증 결과가 아닙니다.</p><div class="legends"><div class="legend"><span id="field-legend"></span><div class="gradient"></div></div><div class="legend"><span id="contact-legend"></span><div class="gradient"></div></div></div>
<div class="section-title"><h2>실제 패드 배치와 공간 분포</h2><small>r ≤ 5 mm · 깊이 15–20 mm 목표 ROI 고정 / 각 지도 동일 단위·범위</small></div>
<div class="role-key"><span><i class="out0"></i>out0</span><span><i class="out1"></i>out1</span><span><i class="gnd"></i>공통 GND 귀환</span><span>물리 polygon 제공 시 정확 윤곽 우선 · 없으면 native mask 셀 표시 · bounding box 대체 없음 · 모서리 완화형은 매끈한 원이 아닌 실제 계단 윤곽</span></div><section id="cards" class="cards"></section>
<div id="hover" class="hover" role="status">셀 위에 포인터를 올리면 실제 native 좌표와 표시값이 나옵니다.</div>
<p class="footnote">지도는 Float32LE native cell 표시값이며 보간하지 않습니다. XZ/YZ는 실제 비균일 z face 간격으로 그립니다. 정량 값은 아래 원래 Float64 통계를 사용합니다. 목표 ROI 표시 clipping은 데이터를 바꾸지 않습니다. NaN은 영역 밖·미지원이며 0이 아닙니다. 표면 층 경계의 최대값을 깊이 집중으로 해석하지 않습니다. XY의 실제 native 깊이는 요청한 20 mm와 다를 수 있고, exact20 mm 차동 프로브는 별도입니다.</p>
<div class="section-title"><h2>목표 집중도와 비표적 절대값</h2><small>maxTIS / fixedTIS 변조와 전체 carrier E RMS는 서로 다른 물리량</small></div><section id="quantitative"></section>
<details><summary>고정 기준 이상 체적 · 균일도 · 전역 hotspot</summary><div id="volume-stats"></div><p class="footnote">원래 기준 ROI 평균/P10 cutoff를 고정한 체적입니다. 생리적 활성 체적이 아닙니다. fractional ROI·실제 표현 체적·가중 ECDF를 유지하며 analytic cylinder로 재정규화하지 않았습니다. total 행의 hotspot은 전역 최대입니다.</p></details>
<div class="section-title"><h2>피부·접촉 부담을 각각 확인</h2><small>막대는 original 기준 대비 표시 비율 · 수치 기준은 인체 안전 한계가 아님</small></div><section id="burdens" class="burdens"></section>
<p class="footnote">접촉 J 지도에서 부분접촉면은 해당 native 셀로 표시하며 정확 형상은 배치 윤곽을 참조합니다. 접촉면 normal J는 면적 가중 통계이고 SC+dermis 체적 벡터 J는 체적 가중 통계입니다. 서로 대체하지 않습니다. SC·dermis·접촉 계면·source 저항 손실을 분리합니다. 과거 skin_power_W=SC+contact 별칭을 전체 피부 손실로 사용하지 않습니다. 체적 J 공간지도는 제공되지 않아 최대/P95 표만 표시합니다.</p>
<details><summary>signed 출력별·주파수별 전력과 그룹 총합</summary><div id="signed-power"></div><p class="footnote">음수와 비활성 주파수 0을 보존합니다. 실제 전원의 sink/compliance·공통 접지·동기 위상·계측 부하가 실험 검증됐다는 뜻은 아닙니다.</p></details>
<div class="section-title"><h2>패드 수 확장 대조 · 별도 strip 가족</h2><small>고정 raw / skin8 두 열 · 위 정규화 선택과 독립</small></div><section id="pad-count-reference"></section><p class="footnote">원래 정방형4 + strip4/8/12/16의 총 접촉면적900 mm² 가족을 별도로 비교합니다. 모두 독립 출력2개·공통GND이며, 패드 수가 증가해도 전원 수가 늘지 않습니다. 패드 분할과 형상·배치 효과도 함께 포함하므로 패드 개수만의 고립된 인과 효과는 아닙니다. 이 표는 raw와skin8을 항상 함께 보존하며 위 지도의다른 정규화로 재계산하지 않습니다.</p>
<details><summary>전체 배치 순위와 제외 근거</summary><p class="footnote">순위는 skin8 정규화의 maxTIS 8개 기준에 고정되며, 위 지도 지표나 모드를 바꿔도 다시 정렬하지 않습니다. 완료되고 비교 가능한 배치별 대표 구동만 선별했습니다. 8·12·16-pad 과거 결과는 독립 출력 증가로 간주하지 않으며, 현재 다섯 배치와 별도 원본 화면에 보존합니다.</p><div id="ranking"></div><pre id="excluded"></pre></details>
<section class="notice"><b>검증 범위</b><p>현재 값은 전기적 수치 프록시입니다. 선별1 모서리 완화형의 대표 구동은 f35이며, 과거 e7 구동의 SC4 진단 통과를 f35에 이전하지 않습니다. 대수적 보존 검사, 공간 통계 재현, 격자·가장자리·접촉 수렴, 실험 검증과 채택은 별개입니다. PBS 계면 모델은 실제 피부에서 검증된 접촉값이 아닙니다. 2074 방향 maxTIS는 연속 방향 최대의 표본 하한입니다. TIS 변조와 단일 주파수 RMS를 같은 생리량으로 취급하지 않습니다.</p><p>40개 차동 프로브는 깊이 5·10·15·20 mm, 중심과 두 축 ±5 mm의 probe 중심, X/Y 방향·팁 간격 5 mm의 무부하 예측입니다. ETA5001/DSOX1202A의 실제 port impedance·설정·대역폭·부하 예측은 별도 검증 전까지 보류합니다.</p></section>
<details><summary>소스 · 선택 계약 · 저장 출처</summary><pre id="source-overview"></pre><p class="footnote">이 화면은 caller가 검증한 catalog와 display export를 내장합니다. 화면 생성은 native 해시의 독립 재검증·시뮬레이션 재현·실험 검증이 아닙니다. 원본 source 링크는 로컬 저장소 파일일 수 있어 HTML 복사본이나 GitHub에서 열리지 않을 수 있습니다. 새 PDE·정규화·순위·gate 계산은 브라우저에서 수행하지 않습니다.</p></details>
<div class="linkrow"><a href="__ARCHIVE__">과거 44조건 · 4/8/12/16-pad</a><a href="__GROUPS__">fine grouped pad 비교</a></div><noscript>이 화면은 오프라인 JavaScript로 내장된 저장값과 지도만 선택합니다. 외부 네트워크는 사용하지 않습니다.</noscript>
</main><script id="data" type="application/json">__DATA__</script><script>__SCRIPT__</script></body></html>'''.replace('__HASH__', script_hash).replace('__CSS__', CSS).replace('__ARCHIVE__', html.escape(archived, quote=True)).replace('__GROUPS__', html.escape(fine_groups, quote=True)).replace('__SCRIPT__', SCRIPT).replace('__DATA__', encoded)
