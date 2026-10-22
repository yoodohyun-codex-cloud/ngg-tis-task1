#!/usr/bin/env python3
"""Bounded, source-bound display export; no PDE, E/phi decode or adoption.

Prepare a unique catalog and source manifest, then display saved scalar cells and
derive contact-normal RMS J from the existing complex current-density basis.
Scientific tables remain the original float64 results; float32 is display only.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import threading
import time
import shutil

for _var in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_var] = '1'
import numpy as np
import task1_resource_policy as policy
import task1_bounded_continuation as bounded

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
MAX_ADDED = 12*1024**2
METRICS = ('maxTIS','fixedTIS','RMS')
MODES = ('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
PRIMARY = 'primary_r5_depth15_20'
DEPTHS = (5.,10.,15.,17.5,20.)
EXPECTED = ('rounded-fullface225-xy80','crossalloc-source225-return225-xy80','cross17p5-arm10-xy80','crossalloc-source200-return250-xy80','crossalloc-source250-return200-xy80')


def require(ok, message):
    if not ok: raise ValueError(message)


def now(): return datetime.now(timezone.utc).isoformat()


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''): h.update(chunk)
    return h.hexdigest()


def write_new(path, value, *, compact=False):
    with Path(path).open('x') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=None if compact else 2,separators=(',',':')if compact else None,allow_nan=False);stream.write('\n')


def descriptor(value):
    require(isinstance(value,dict) and 'path' in value,'Source descriptor with explicit path required')
    path=Path(value['path']);digest=value.get('SHA256',value.get('sha256'))
    require(path.is_absolute() and path==path.resolve() and path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink(),'Canonical existing source required')
    require(isinstance(digest,str) and sha(path)==digest,'Bound source SHA mismatch: '+str(path))
    return path,digest


def axes_and_indices(grid, meta):
    grid=np.asarray(grid,float)
    require(grid.shape==(meta['cells'],5) and np.isfinite(grid).all(),'Exact native five-column grid required')
    x,y,z=(np.unique(grid[:,k]) for k in range(3));h=float(meta['h_xy_mm']);faces=np.asarray(meta['z_faces_mm'],float)
    require(meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40] and meta['cells']==351680,'Original comparable fine SC2 grid required')
    require(len(faces)==len(z)+1 and np.all(np.diff(faces)>0) and np.allclose(z,(faces[:-1]+faces[1:])/2,rtol=0,atol=1e-8),'Use actual nonuniform depth faces')
    require(np.allclose(np.diff(x),h,rtol=0,atol=1e-8) and np.allclose(np.diff(y),h,rtol=0,atol=1e-8),'Uniform native XY centers required')
    ix,iy,iz=(np.searchsorted(axis,grid[:,k])for k,axis in enumerate((x,y,z)))
    require(len(np.unique((iz*len(y)+iy)*len(x)+ix))==len(grid),'Duplicate native cell')
    return dict(x=x,y=y,z=z,ix=ix,iy=iy,iz=iz,x_edges=np.r_[x-h/2,x[-1]+h/2],y_edges=np.r_[y-h/2,y[-1]+h/2],z_faces=faces)


def encode_f32(values):
    return base64.b64encode(np.asarray(values,dtype='<f4').tobytes(order='C')).decode('ascii')


def aggregate_rss_bytes():
    """Count this display process and live descendants, including Chromium."""
    entries={}
    for folder in Path('/proc').iterdir():
        if not folder.name.isdigit():continue
        try:
            fields=(folder/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]in('Z','X'):continue
            entries[int(folder.name)]=(int(fields[1]),int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
        except(OSError,ValueError,IndexError):continue
    owned={os.getpid()}
    while True:
        children={pid for pid,(parent,_)in entries.items()if parent in owned}
        if children<=owned:break
        owned.update(children)
    return sum(entries.get(pid,(0,0))[1]for pid in owned)


def scalar_planes(values, axes):
    x,y,z,ix,iy,iz=(axes[k] for k in ('x','y','z','ix','iy','iz'))
    result={'xy':[]};chosen=[int(np.argmin(abs(z-d))) for d in DEPTHS]
    for k in chosen:
        image=np.full((len(y),len(x)),np.nan);use=iz==k;image[iy[use],ix[use]]=values[use];result['xy'].append(encode_f32(image))
    image=np.full((len(z),len(x)),np.nan);use=iy==int(np.argmin(abs(y)));image[iz[use],ix[use]]=values[use];result['xz']=encode_f32(image)
    image=np.full((len(z),len(y)),np.nan);use=ix==int(np.argmin(abs(x)));image[iz[use],iy[use]]=values[use];result['yz']=encode_f32(image)
    return result


def weighted_primary_proof(values, weights, saved):
    use=weights>0;v,w=values[use],weights[use];order=np.argsort(v,kind='stable');cum=np.cumsum(w[order])
    actual=dict(mean=float(v@w/w.sum()),p10=float(v[order[min(int(np.searchsorted(cum,.1*cum[-1],side='left')),len(v)-1)]]),max=float(v.max()),volume_m3=float(w.sum()))
    for key,value in actual.items():
        require(math.isclose(value,float(saved[key]),rel_tol=1e-10,abs_tol=1e-25 if key=='volume_m3' else 1e-12),'Saved native scalar/primary statistic mismatch: '+key)
    return dict(passed=True,actual=actual,saved={k:saved[k]for k in actual},scope='Saved scalar archive and fractional primary weights; not a new mesh/convergence gate')


def add_pad_count_reference(catalog):
    path=ROOT/'docs/GROUPED_FINE_RESULTS_20261021.result-brief.json';digest=sha(path);source=json.loads(path.read_text());rows=[]
    for case in source['cases']:
        modes={}
        for mode,n in case['normalizations'].items():
            require(mode in ('raw_1Vpp','skin_contact_only'),'Only stored grouped display modes may be shown')
            s=n['primary_ROI']['maxTIS'];modes[mode]=dict(mean_V_m=s['mean'],P10_V_m=s['p10'],source_Vpp_per_output=n['source_Vpp_per_output'],normalized_burdens=n['normalized_burdens'],source_output_RMS_by_output_mA=n['source_output_RMS_by_output_mA'])
        rows.append(dict(id=case['case_id'],label=case['label'],n_pads=case['circuit']['n_pads'],n_outputs=case['circuit']['n_outputs'],return_topology=case['circuit']['return_topology'],normalizations=modes))
    require(len(rows)==5 and [r['n_pads']for r in rows]==[4,4,8,12,16] and all(r['n_outputs']==2 for r in rows),'Preserve original4-square plus4/8/12/16 strip two-output controls')
    require(sha(path)==digest,'Grouped reference changed while reading')
    catalog['pad_count_reference']=dict(source=dict(path=str(path),SHA256=digest),rows=rows,scope='Stored original4-square plus distinct strip4/8/12/16; all2outputs/commonGND/50ohm,total900mm2. These are not the five selected layouts. Raw and skin8 only; no new normalization.')
    catalog.setdefault('input_sha256',{})[str(path)]=digest


def export_case(row, contact_module, pins, axes_cache, roi_reference, guard):
    guard();gp,gd=descriptor(row['grid']);vp,vd=descriptor(row['scalar_archive']);meta=row['mesh_metadata']
    pins.update({str(gp):gd,str(vp):vd});require(vp.stat().st_size<=96*1024**2,'Bounded scalar NPZ required')
    if gd not in axes_cache:
        with (gzip.open(gp,'rt') if gp.suffix=='.gz' else gp.open()) as stream:grid=np.loadtxt(stream,delimiter=',',skiprows=1)
        axes_cache[gd]=axes_and_indices(grid,meta)
    axes=axes_cache[gd];planes={};maxima={};primarymax={};proof={}
    with np.load(vp,allow_pickle=False) as archive:
        weights=np.asarray(archive['region_target_m3'],float);total=np.asarray(archive['region_total_m3'],float);surface=np.asarray(archive['region_surface_0_5_m3'],float)
        require(all(a.shape==(meta['cells'],) and np.isfinite(a).all() and np.all(a>=0) for a in (weights,total,surface)) and np.any(weights>0) and np.all(total>0),'Finite native ROI weights required')
        if not roi_reference:roi_reference.update(target=weights.copy(),total=total.copy(),surface=surface.copy())
        else:require(all(np.array_equal(a,roi_reference[k]) for a,k in ((weights,'target'),(total,'total'),(surface,'surface'))),'All six cases must preserve exact native ROI masks and volume weights')
        for metric in METRICS:
            values=np.asarray(archive[metric],float);require(values.shape==(meta['cells'],) and np.isfinite(values).all() and np.all(values>=0),'Finite nonnegative saved scalar cells required')
            proof[metric]=weighted_primary_proof(values,weights,row['normalizations']['raw_1Vpp']['regions'][PRIMARY][metric]);planes[metric]=scalar_planes(values,axes);maxima[metric]=float(values.max());primarymax[metric]=float(values[weights>0].max())
    contact=contact_module.export_contact(row,required_pins=pins)
    require(contact['regression']['passed'],'Contact map must reproduce existing raw and normalized Jmax/J95')
    pins.update(contact['input_sha256']);x,y=axes['x'],axes['y'];jx=np.searchsorted(x,contact['x_mm']);jy=np.searchsorted(y,contact['y_mm'])
    require(np.all(jx<len(x)) and np.all(jy<len(y)) and np.allclose(x[jx],contact['x_mm'],rtol=0,atol=1e-8) and np.allclose(y[jy],contact['y_mm'],rtol=0,atol=1e-8),'Contact patch coordinates must match actual native surface cells')
    require(len(np.unique(jy*len(x)+jx))==len(jx),'Multiple patches per displayed contact cell require a reviewed subcell renderer')
    jimage=np.full((len(y),len(x)),np.nan);mask=np.full((len(y),len(x)),-1,dtype='<i2');jimage[jy,jx]=contact['raw_J_RMS_A_m2'];mask[jy,jx]=contact['pad']
    centres=[];circuit=row['circuit']
    for pad in sorted(set(int(p) for p in contact['pad'])):
        use=contact['pad']==pad;w=contact['area_m2'][use];centres.append(dict(pad=pad,node=circuit['pad_to_node'][str(pad)],x_mm=float(contact['x_mm'][use]@w/w.sum()),y_mm=float(contact['y_mm'][use]@w/w.sum()),area_mm2=float(w.sum()*1e6)))
    scales={m:float(row['normalizations'][m]['amplitude_scale'])for m in MODES};require(scales['raw_1Vpp']==1,'Stored raw whole-waveform normalization must be exactly one')
    outlines=[]
    for pad in row['case'].get('design',{}).get('pads',[]):
        if isinstance(pad.get('polygon_mm'),list):
            p=int(pad['pad']);outlines.append(dict(pad=p,node=circuit['pad_to_node'][str(p)],polygon_mm=pad['polygon_mm']))
    guard();return dict(id=row['id'],geometry_key=row['geometry_key'],scales=scales,planes=planes,raw_scalar_maxima=maxima,raw_primary_ROI_maxima=primarymax,pad_mask_b64=base64.b64encode(mask.tobytes()).decode('ascii'),pad_centres=centres,physical_outlines=outlines,contact_J_RMS=dict(values_b64=encode_f32(jimage),raw_max_A_m2=float(np.max(contact['raw_J_RMS_A_m2'])),regression=contact['regression'],definition='Area-patch contact-normal RMS current density, not SC/dermis vector J; partial-face patches occupy their native display cell'),native_stats_proofs=proof,contact_source_proof={k:v for k,v in contact.items()if k not in ('x_mm','y_mm','area_m2','pad','raw_J_RMS_A_m2')})


def make_display(catalog,contact_module,pins,guard):
    axes_cache={};roi={};rows=[catalog['canonical_baseline'],*catalog['selected_layouts']];cases=[]
    require(len(rows)==6 and len({r['geometry_key']for r in rows})==6,'One baseline plus five distinct physical layouts required')
    for row in rows:cases.append(export_case(row,contact_module,pins,axes_cache,roi,guard))
    require(len(axes_cache)==1,'Exactly shared native grid bytes required for six-panel comparison')
    a=next(iter(axes_cache.values()));limits={};jlimits={}
    for mode in MODES:
        limits[mode]={metric:{'global':[0.,max(c['raw_scalar_maxima'][metric]*c['scales'][mode]for c in cases)],'primary_ROI':[0.,max(c['raw_primary_ROI_maxima'][metric]*c['scales'][mode]for c in cases)]}for metric in METRICS}
        jlimits[mode]=[0.,max(c['contact_J_RMS']['raw_max_A_m2']*c['scales'][mode]for c in cases)]
    return dict(schema='task1-top5-native-display-v1',cases=cases,grid=dict(x_edges_mm=a['x_edges'].tolist(),y_edges_mm=a['y_edges'].tolist(),z_faces_mm=a['z_faces'].tolist(),XY_requested_depths_mm=list(DEPTHS),XY_actual_depths_mm=[float(a['z'][np.argmin(abs(a['z']-d))])for d in DEPTHS],XZ_actual_y_mm=float(a['y'][np.argmin(abs(a['y']))]),YZ_actual_x_mm=float(a['x'][np.argmin(abs(a['x']))])),color_limits=limits,contact_color_limits=jlimits,fieldunits='V/m',contactunits='A/m2',display_precision='Float32LE maps only; scientific tables and proof use original float64',outside_mask='NaN; no interpolation or phantom-size enlargement',bulk_J_spatial_map='unavailable; saved SC/dermis vector Jmax/J95 tables only',no_new_PDE=True,no_new_E_or_phi_decode=True)


def implementation():
    names=['tools/task1_top5_build.py','tools/task1_top5_catalog.py','tools/task1_top5_dashboard.py','tools/task1_top5_contact_export.py','tools/task1_resource_policy.py','tools/task1_bounded_continuation.py','tools/task1_candidate_screen.py','tests/test_task1_top5_build.py','tests/test_task1_top5_catalog.py','tests/test_task1_top5_dashboard.py','tests/test_task1_top5_contact_export.py']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for name in names:
        p=ROOT/name;require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT),'Commit all display implementation/tests before actual use: '+name);refs[str(p)]=sha(p)
    return dict(source_commit=commit,implementation_sha256=refs)


def browser_check(html_path,output,guard):
    from playwright.sync_api import sync_playwright
    errors=[];external=[]
    with sync_playwright() as engine:
        browser=engine.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--disable-dev-shm-usage','--disk-cache-size=0','--media-cache-size=0','--disable-gpu-shader-disk-cache'])
        try:
            page=browser.new_page(viewport=dict(width=1540,height=1100),device_scale_factor=1)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request:external.append(request.url)if request.url.startswith(('http:','https:'))else None)
            # This managed Chromium blocks file: navigation. Loading our own
            # already authorized artifact into memory needs no server or route.
            page.set_content(html_path.read_text(),wait_until='load',timeout=45000);page.wait_for_timeout(300);guard()
            require(page.locator('.case-card').count()==6,'Browser must render six original/candidate cards')
            require(page.locator('.field-map').count()==6 and page.locator('.contact-map').count()==6,'All six actual scalar/contact maps required')
            initial=page.locator('#field-legend').inner_text();require(initial.strip(),'Shared field legend required')
            page.screenshot(path=str(output/'desktop.png'),full_page=False)
            for mode in MODES:
                page.select_option('#mode',mode);page.wait_for_timeout(30);require(page.locator('#mode').input_value()==mode,'Normalization selection failed')
            page.select_option('#mode','raw_1Vpp');page.select_option('#metric','RMS');page.select_option('#plane','xy');page.select_option('#depth','4');page.select_option('#range','global');page.wait_for_timeout(100)
            require(page.locator('#field-legend').inner_text().strip(),'Carrier-RMS shared legend must remain available')
            canvas=page.locator('.field-map').first
            pixels=canvas.evaluate('(c)=>{const d=c.getContext("2d").getImageData(0,0,c.width,c.height).data;let n=0;for(let i=3;i<d.length;i+=4)if(d[i])n++;return n;}')
            require(pixels>100,'Native field map is blank')
            page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100)
            require(page.evaluate('document.documentElement.scrollWidth')<=392,'Dashboard must fit mobile viewport')
            page.screenshot(path=str(output/'mobile.png'),full_page=False)
            require(not errors and not external,'Offline dashboard produced JS errors or external requests: '+str(errors+external))
            return dict(status='passed',real_chromium=True,source='SHA-bound offline HTML loaded as memory DOM; managed file navigation unavailable',cards=6,field_canvases=6,contact_canvases=6,normalizations_tested=list(MODES),carrier_RMS_XY_depth20_selected=True,native_map_nonempty_pixels=pixels,mobile_width=390,mobile_overflow=False,JS_errors=errors,external_requests=external,scientific_convergence_claimed=False)
        finally:browser.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--prepare',type=Path);group.add_argument('--plan',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs') and not output.exists(),'Unique new docs output directory required')
    import task1_top5_catalog as catalog_module
    import task1_top5_contact_export as contact_module
    import task1_top5_dashboard as dashboard
    with ExitStack() as stack:
        stack.enter_context(bounded.dual_lock(ROOT/'.task1-loop.lock'));stack.enter_context(bounded.dual_lock(ROOT/'.task1-execution.lock'))
        ledger=policy.load_ledger(ROOT/'runtime/task1-budget.json');cap=120 if args.prepare else 600
        require(policy.remaining_seconds(ledger)>=cap,'Existing approved remaining finite budget required');require(shutil.disk_usage(ROOT).free>=2*GIB+MAX_ADDED,'Preserve 2GiB reserve plus bounded display artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();status='failed_preserved';error=None;state={};stop=threading.Event();thread=None;previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        def guard():
            require(time.monotonic()-started<cap,'Finite display deadline exceeded');require(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,aggregate_rss_bytes())<3*GIB,'3GiB aggregate RSS cap exceeded');require(shutil.disk_usage(ROOT).free>=2*GIB,'Original2GiB free reserve exhausted')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=MAX_ADDED,'Display artifacts exceed12MiB bound')
        def checkpoint(phase):
            guard();state.update(pid=os.getpid(),proc_start_ticks=bounded.ticks(os.getpid()),phase=phase,status='running',updated_utc=now(),elapsed_seconds=time.monotonic()-started)
            if output.exists():bounded.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:guard();bounded.write(output/'heartbeat.json',dict(state,updated_utc=now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as exc:state['guard_failure']=type(exc).__name__+': '+str(exc);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupt(signum,frame):raise TimeoutError('Controlled finite display signal '+str(signum)+('; '+state['guard_failure']if state.get('guard_failure')else''))
        for s in previous:signal.signal(s,interrupt)
        signal.setitimer(signal.ITIMER_REAL,cap)
        try:
            code=implementation()
            if args.prepare:
                require(not args.prepare.exists() and not args.prepare.with_name(args.prepare.name+'.failure.json').exists() and args.prepare.parent.is_dir(),'Unique unattempted existing-parent plan required')
                catalog=catalog_module.collect(ROOT)
                add_pad_count_reference(catalog)
                require(tuple(r['source_case_id']for r in catalog['selected_layouts'])==EXPECTED,'Catalog differs from independent all-evidence ranking; review before display')
                pins=dict(code['implementation_sha256']);pins.update(catalog.get('input_sha256',catalog.get('source_refs',{})))
                for row in [catalog['canonical_baseline'],*catalog['selected_layouts']]:
                    pins.update(row['source_refs'])
                    for key in ('grid','scalar_archive'):
                        path,digest=descriptor(row[key]);pins[str(path)]=digest
                    pins.update(contact_module.required_contact_paths(row))
                pins.update(policy.policy_refs(ledger))
                for path,digest in pins.items():require(sha(path)==digest,'Pinned display input mismatch: '+path)
                plan=dict(schema='task1-top5-display-plan-v1',status='prepared_not_executed',created_utc=now(),output_directory=str(output),catalog=catalog,input_sha256=pins,**code,resources=dict(max_seconds=600,max_added_bytes=MAX_ADDED,CPU_count=1,RSS_bytes=3*GIB,minimum_free_bytes=2*GIB,cumulative_seconds=policy.effective_limit(ledger)),new_PDE=0,new_E_phi_decode=False,candidate_adopted=False)
                require(len(json.dumps(catalog,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())<=2*1024**2,'Catalog must remain within2MiB compact bound')
                guard();write_new(args.prepare,plan,compact=True);status='prepared_not_executed'
            else:
                plan_sha=sha(args.plan);plan=json.loads(args.plan.read_text());require(plan['schema']=='task1-top5-display-plan-v1' and plan['output_directory']==str(output),'Exact prepared display output required');require(plan['implementation_sha256']==code['implementation_sha256'],'Display implementation drift')
                for path,digest in plan['input_sha256'].items():require(sha(path)==digest,'Pinned display input drift: '+path)
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();catalog=plan['catalog'];write_new(output/'catalog.json',catalog,compact=True);checkpoint('decode_saved_scalar_and_contact_display')
                pins=dict(plan['input_sha256']);display=make_display(catalog,contact_module,pins,guard);checkpoint('render_offline_dashboard')
                rendered=dashboard.render(catalog,display,output/'index.html')
                require(isinstance(rendered,str) and not (output/'index.html').exists(),'Pure dashboard renderer must return one new offline HTML document')
                with (output/'index.html').open('x') as stream:stream.write(rendered)
                guard();checkpoint('real_browser_interaction_checks');browser=browser_check(output/'index.html',output,guard);write_new(output/'browser-validation.json',browser)
                require(sha(args.plan)==plan_sha,'Prepared plan changed during display')
                for path,digest in pins.items():require(sha(path)==digest,'Consumed display source changed: '+path)
                guard();manifest=dict(schema='task1-top5-display-manifest-v1',status='export_ready_pending_final_checks',created_utc=now(),**code,plan=dict(path=str(args.plan.resolve()),SHA256=plan_sha),input_sha256=pins,inputs_unchanged=True,case_ids=[r['id']for r in [catalog['canonical_baseline'],*catalog['selected_layouts']]],selected_layouts=[r['source_case_id']for r in catalog['selected_layouts']],display_grid=display['grid'],color_limits=display['color_limits'],contact_color_limits=display['contact_color_limits'],contact_regression={r['id']:r['contact_J_RMS']['regression']for r in display['cases']},native_scalar_primary_proofs={r['id']:r['native_stats_proofs']for r in display['cases']},browser_validation=browser,new_PDE=0,new_E_phi_decode=False,new_contact_RMS_display_from_existing_basis=True,scientific_tables_unchanged=True,float32_maps_only=True,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,resources=dict(CPU_count=1,wall_seconds=time.monotonic()-started,max_seconds=600,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_added_bytes=MAX_ADDED,cumulative_budget_seconds=policy.effective_limit(ledger)),artifacts={p.name:dict(bytes=p.stat().st_size,SHA256=sha(p))for p in output.iterdir()if p.is_file()and p.name!='heartbeat.json'})
                write_new(output/'manifest.json',manifest)
                guard()
                manifest['status']='display_export_complete_unadopted';bounded.write(output/'manifest.json',manifest);guard();status=manifest['status']
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc);failed_from_status=status;status='failed_preserved'
            failure=dict(status=status,failed_from_status=failed_from_status,error=error,resource_guard_failure=state.get('guard_failure'),phase=state.get('phase'),new_PDE=0,old_evidence_preserved=True,automatic_retry=False)
            manifest_path=output/'manifest.json'
            if manifest_path.exists():
                partial_manifest=json.loads(manifest_path.read_text());partial_manifest.update(status=status,failed_from_manifest_status=partial_manifest.get('status'),error=error);bounded.write(manifest_path,partial_manifest)
            if output.exists():write_new(output/'failure.json',failure)
            elif args.prepare and not args.prepare.with_name(args.prepare.name+'.failure.json').exists():write_new(args.prepare.with_name(args.prepare.name+'.failure.json'),failure)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='top5_display_prepare'if args.prepare else'top5_display_export',status=status,error=error,seconds=elapsed,finished_utc=now()));bounded.write(ROOT/'runtime/task1-budget.json',ledger)
            if output.exists():bounded.write(output/'heartbeat.json',dict(state,status=status,error=error,updated_utc=now(),elapsed_seconds=elapsed))
            for s,h in previous.items():signal.signal(s,h)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
