"""Seven-case bounded GUI derivative of authenticated saved native results.

No scientific/file work occurs at import. NumPy and the byte-frozen renderer
are imported only in the root-owned build after source-bound MFG passed.
"""
import copy
import csv
import gc
import hashlib
import importlib
import json
import math
import sys
import time
from pathlib import Path
from fractions import Fraction

import gui_inputs

SCHEMA='task1-native-GUI-lite-display-v1'
MAX_JSON_BYTES=4900000
MAX_HTML_BYTES=5000000
WAVE_POINTS=64
ARROW_SUBSET_STRIDE=4

def require(ok,message):
    if not ok:raise ValueError(message)

def check(guard,deadline):
    if guard is not None:guard()
    if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite GUI derivative incomplete; partial files preserved')

def make_spec(admission=None):
    ctx=gui_inputs.make_spec(admission)
    return dict(schema='task1-native-GUI-lite-build-spec-v1',inputs=ctx,metadata_input_sha256=ctx['metadata_input_sha256'],native_input_descriptors=ctx['native_input_descriptors'],expected_cases=7,new_native_cases=3,legacy_reference_cases=4,expected_probe_rows=120,strict_probe_rows=60,explicit_same_layer_extrapolated_rows=60,
        display_policy=dict(original_wave_points_per_curve=128,selected_wave_points_per_curve=WAVE_POINTS,selection='integer floor k*(127)//63 for k0..63, includes first/last; stored actual values only, no interpolation',arrow_subset_stride=ARROW_SUBSET_STRIDE,arrow_selection='Every fourth original signed 2000Hz phase0 arrow produced by frozen extractor; no vector changes',original_probe_metrics_and_native_fields_unchanged=True),
        output_functional_bounds=dict(JSON_bytes=MAX_JSON_BYTES,HTML_bytes=MAX_HTML_BYTES,not_a_storage_capacity_guard=True),child_RSS_forecast_bytes=340000000,new_output_forecast_bytes=12000000,forecast_unmeasured=True,
        new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_native_statistic_reductions=0,new_stat_reductions=0,new_candidate_ranking=False,browser_validation_performed=False,candidate_adopted=False)

def required_inputs(admission=None):return dict(make_spec(admission)['metadata_input_sha256'])

def _json_bytes(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')

def write_bytes(path,raw):
    # Serialize fully before opening an exclusive destination; no empty JSON.
    with Path(path).open('xb')as stream:stream.write(raw)
    return dict(path=str(path),SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def new_json(path,value):return write_bytes(path,_json_bytes(value))

def _digest(path,guard,deadline):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for part in iter(lambda:stream.read(1024**2),b''):check(guard,deadline);h.update(part)
    return h.hexdigest()

def verify_native(d,guard,deadline):
    check(guard,deadline);p=Path(d['path'])
    require(d.get('readback_passed')is True and gui_inputs.fullhex(d.get('publication_commit'),40)and gui_inputs.fullhex(d.get('SHA256'),64),'Full actual source/result readback proof before any native open')
    require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size==d['bytes']and d['bytes']<=gui_inputs.MAX_NATIVE,'Exact native path and byte count')
    require(_digest(p,guard,deadline)==d['SHA256'],'Full native SHA before/after decode');return p

def load(np,d,keys,guard,deadline):
    p=verify_native(d,guard,deadline)
    with np.load(p,allow_pickle=False)as archive:
        require(set(keys).issubset(archive.files),'Stored native ABI absent; never reconstruct missing fields')
        # Access only explicit keys; no archive-wide materialization/copy.
        result={key:archive[key]for key in keys}
    require(all(np.isfinite(v).all()for v in result.values()if v.dtype.kind not in('U','S')),'Finite actual saved native arrays')
    verify_native(d,guard,deadline);return result

def stored_indices(length,count=WAVE_POINTS):
    require(type(length)is int and type(count)is int and length==128 and 2<=count<=128,'Original128 points and explicit finite display selection')
    return [k*(length-1)//(count-1)for k in range(count)]

def subset_display(display):
    for quantity,planes in display['planes'].items():
        if quantity=='contact_J':continue
        for plane in planes.values():
            if 'arrows'in plane:
                original=plane['arrows'];plane['arrows']=original[::ARROW_SUBSET_STRIDE]
                plane['arrow_display_subset']=dict(source_arrow_count=len(original),selected_arrow_count=len(plane['arrows']),original_extractor_stride=8,selected_every_nth_source_arrow=ARROW_SUBSET_STRIDE,original_vectors_unchanged=True)
    return display

def compact_norms(rows):
    """Select published Float64 records; no multiplication/reduction/ranking."""
    result={}
    for mode,row in rows.items():
        result[mode]=dict(status=row['status'],amplitude_scale=row['amplitude_scale'],absolute_ROI_fields_V_m={region:{q:{k:stats[k]for k in('mean','p10','p95','max')if k in stats}for q,stats in values.items()if q in('maxTIS','RMS')}for region,values in row['absolute_ROI_fields_V_m'].items()},electrical=copy.deepcopy(row.get('electrical',{})))
    return result

def bar_values(rows):
    names=dict(target_AM_mean=('target','mean'),target_AM_P10=('target','p10'),surface_AM_mean=('surface_0_5','mean'),offtarget_AM_mean=('off_target','mean'))
    return {metric:{mode:row['absolute_ROI_fields_V_m'][region]['maxTIS'][stat]for mode,row in rows.items()}for metric,(region,stat)in names.items()}

def artifact(d,label):
    return dict(label=label,fixed_commit=d['publication_commit'],repo_relative_path=d['publication_target'],SHA256=d['SHA256'],bytes=d['bytes'])

def _geometry(np,case,extract,guard,deadline):
    geom=case['geometry'];kind=geom['kind'];out=[]
    if kind=='rectangles':
        for pad in geom['pads']:
            b=pad.get('bounds_mm')
            if b is None:
                x,y=pad['center_mm'];w,h=pad['width_mm'],pad['height_mm'];b=[x-w/2,x+w/2,y-h/2,y+h/2]
            area=Fraction(pad['exact_area_numerator'],pad['exact_area_denominator'])*1000000 if'exact_area_numerator'in pad else Fraction(str(pad['analytic_area_m2']))*1000000
            out.append(extract.rectangle_union_outline([b],pad['pad'],pad['node'],declared_area_mm2=area))
        return out
    if kind=='polyomino':
        d=geom['mask'];p=verify_native(d,guard,deadline);rects={i:[]for i in range(4)};seen=set();h=geom['spacing_mm']
        with p.open('r',newline='',encoding='utf-8')as stream:
            rows=csv.DictReader(stream);require(rows.fieldnames==['pad','i','j','area_m2'],'Published whole-face donor CSV ABI')
            for row in rows:
                check(guard,deadline);pad,i,j=int(row['pad']),int(row['i']),int(row['j']);require(pad in rects and(pad,i,j)not in seen and abs(float(row['area_m2'])-h*h*1e-6)<=1e-20,'Original full physical donor patches only; no fractional-square inference')
                seen.add((pad,i,j));x=-25+i*h;y=-25+j*h;rects[pad].append([x,x+h,y,y+h])
        verify_native(d,guard,deadline)
        for pad in geom['pads']:
            require(len(rects[pad['pad']])==pad['full_cells'],'Exact actual donor physical support, holes retained')
            out.append(extract.rectangle_union_outline(rects[pad['pad']],pad['pad'],pad['node'],declared_area_mm2=225))
        return out
    require(kind=='ellipse','No bbox/square fallback for unknown physical geometry')
    record=geom['record'];proof=record['preflight_and_contact'];require(proof['passed']is True and proof['unresolved_potential_positive_support_omitted']is False and proof['area_rescaled']is False,'Published complete physical ellipse support proof')
    for pad in proof['preflight']['pads']:
        x,y=pad['analytic_centroid_mm'];r=math.hypot(x,y);a=pad['tangential_semimajor_mm'];b=225/(math.pi*a);radial=(x/r,y/r);tangent=(-y/r,x/r)
        polygon=[]
        for k in range(256):
            angle=2*math.pi*k/256;polygon.append([x+a*math.cos(angle)*tangent[0]+b*math.sin(angle)*radial[0],y+a*math.cos(angle)*tangent[1]+b*math.sin(angle)*radial[1]])
        pid=pad['physical_pad_id'];out.append(dict(pad_id=pid,node='out0'if pid==0 else'out1'if pid==1 else'GND',polygon_xy_mm=polygon,holes_xy_mm=[],physical_geometry_source='Actual published analytic ellipse equation and exact centroid;256 chord display only, no replacement of certified fractional contact support',analytic_area_mm2=pad['analytic_area_mm2'],analytic_centroid_mm=pad['analytic_centroid_mm'],tangential_semimajor_mm=a,radial_semiminor_mm_formula='225/(pi*13)',display_boundary_chords=256,contact_fraction_diagnostics=copy.deepcopy(next(p for p in proof['pads']if p['physical_pad_id']==pid)),geometry_rescaled=False,contact_J_map_unavailable=True))
    return out

def probe_payload(np,case,guard,deadline):
    pred=case['probe_record'];a=load(np,case['probe_arrays'],('representative_probe_ids','carrier_excerpt_time_s','representative_carrier_excerpt_V','envelope_time_s','representative_envelope_V'),guard,deadline)
    ids=[str(x)for x in a['representative_probe_ids']];require(len(ids)==40 and len(set(ids))==40,'Forty original waveform identities')
    require(a['representative_carrier_excerpt_V'].shape==a['representative_envelope_V'].shape==(40,128)and a['carrier_excerpt_time_s'].shape==a['envelope_time_s'].shape==(128,),'Actual original128 excerpt+envelope points perprobe')
    index=stored_indices(128);rows=[]
    keys=('probe_id','centre_xyz_mm','differential_axis','tip_spacing_mm','negative_tip_xyz_mm','positive_tip_xyz_mm','polarity','negative_tip_sampling','positive_tip_sampling','status','same_layer_extrapolation_used','strict_same_layer_bracket_available')
    for row in pred['probes']:
        selected={k:copy.deepcopy(row[k])for k in keys};selected['unloaded']=copy.deepcopy(row['unloaded']);i=ids.index(row['probe_id'])
        selected['waveform']=dict(carrier_excerpt_time_s=[float(a['carrier_excerpt_time_s'][j])for j in index],carrier_excerpt_V=[float(a['representative_carrier_excerpt_V'][i,j])for j in index],envelope_time_s=[float(a['envelope_time_s'][j])for j in index],envelope_V=[float(a['representative_envelope_V'][i,j])for j in index],display_source_point_count_each=128,display_selected_point_count_each=len(index),display_original_indices=index,interpolation_performed=False,source_metrics_unchanged=True)
        rows.append(selected)
    result={key:copy.deepcopy(pred[key])for key in('probe_count','calculated_probe_count','unavailable_probe_count','strict_same_layer_bracket_available_probe_count','same_layer_extrapolated_probe_count','waveform_window','interpolation_policy','probe_loaded_prediction','experimental_validation')};result['probes']=rows
    del a;gc.collect();return result

def _case(np,case,extract,guard,deadline):
    g=load(np,case['grid'],('grid','z_faces_m'),guard,deadline);s=load(np,case['scalars'],('AM_max2074','carrier_RMS'),guard,deadline)
    e=load(np,case['E2000'],('E_peak_V_m',),guard,deadline);outlines=_geometry(np,case,extract,guard,deadline)
    display=subset_display(extract.extract_case(np,g['grid'],g['z_faces_m']*1000,s,E_peak_2000=e['E_peak_V_m'],contact_J=None,pad_outlines=outlines,guard=guard,deadline_monotonic=deadline))
    identity=dict(native_cells=int(len(g['grid'])),stored_grid_SHA256=case['grid']['SHA256'],stored_scalar_SHA256=case['scalars']['SHA256'],stored_E2000_SHA256=case['E2000']['SHA256'],native_quantitative_metrics_recomputed=False,contact_J_map_status='unavailable_no_original_stored_contact_RMS_map',no_contact_J_from_bulk_E=True)
    del e,s,g;gc.collect();check(guard,deadline)
    norms=compact_norms(case['normalizations']);r=case['record'];stats=dict(regions={region:{q:copy.deepcopy(v)for q,v in rr['statistics'].items()if q in('maxTIS','RMS')}for region,rr in r['metrics']['regions'].items()if region in('total','target','surface_0_5','off_target')},electrical=copy.deepcopy(r['metrics']['electrical']))
    provenance={k:copy.deepcopy(v)for k,v in case['provenance'].items()if k in('source_run_id','result_commit','source_commit','field_version','material_input_SHA256','contact_input_SHA256')}
    provenance['artifacts']=[artifact(case[k],k)for k in('grid','scalars','E2000')]
    result=dict(id=case['candidate_id'],label=case['label'],pad_count=case['pad_count'],independent_outputs=2,grid_version=case['grid_variant'],display=display,stats=stats,normalizations=norms,amplitude_scales={k:row['amplitude_scale']for k,row in case['normalizations'].items()},bar_values=bar_values(case['normalizations']),holds=copy.deepcopy(r['metrics'].get('holds',{})),provenance=provenance)
    if 'high_volume_record'in case:
        # Copy already-published numerical classifications; never re-threshold
        # display pixels or native scalar arrays to manufacture new statistics.
        result['stats']['published_native_high_volume_record']=copy.deepcopy(case['high_volume_record'])
    if case['section']=='new_native':result['probe_summary']=probe_payload(np,case,guard,deadline)
    return result,identity

def _check_test_receipt(spec,out):
    p=out/'synthetic-test-receipt.json';require(p.is_file(),'Actual source-published protected MFG PASS before native byte opens')
    receipt=json.loads(p.read_bytes());require(receipt.get('status')=='passed'and all(receipt.get(k)==0 for k in('tests_failed','tests_errors','tests_skipped'))and receipt.get('tests_run')==receipt.get('expected_total_tests')and receipt.get('tests_run',0)>=16,'All prospective actual tests passed, not AST-only count')
    require(receipt.get('model_source_sha256')==spec['inputs']['model_source_sha256'],'Actual frozen model test receipt source inventory')
    owner=receipt.get('owner_source_sha256',receipt.get('source_sha256'));require(owner==spec['inputs']['source_sha256'],'Actual integration/owner test receipt complete canonical inventory')
    return dict(path=str(p),SHA256=hashlib.sha256(p.read_bytes()).hexdigest(),tests_run=receipt['tests_run'])

def build(spec,guard,deadline_monotonic=None,output_dir=None):
    check(guard,deadline_monotonic);out=Path(gui_inputs.OUT if output_dir is None else output_dir);require(out==gui_inputs.OUT and out.is_dir(),'Exact unique new GUI output directory created by sole owner')
    ctx=spec['inputs'];testproof=_check_test_receipt(spec,out)
    # Imports are after MFG PASS and source inventory validation by owner.
    import numpy as np
    model_path=str(gui_inputs.MODEL)
    if model_path not in sys.path:sys.path.insert(0,model_path)
    extract=importlib.import_module('lite_extract');renderer=importlib.import_module('lite_render')
    require(gui_inputs.source_inventory(gui_inputs.MODEL)==ctx['model_source_sha256'],'Frozen renderer/extractor unchanged before build')
    payload=dict(schema=SCHEMA,repository='yoodohyun-codex-cloud/ngg-tis-task1',title='TIS · native fields and unloaded probes · fixed ranges',coordinate_system=dict(x_y='mm horizontal',depth_mm='0 at physical top,+z into phantom',layer_interfaces_mm=[0,.1,5.1,10.1,25.1]),normalization_modes=[dict(id=m,label=m)for m in gui_inputs.MODES],bar_metrics=[dict(id=key,label=label,unit='V/m')for key,label in(('target_AM_mean','Target AM mean'),('target_AM_P10','Target AM P10'),('surface_AM_mean','Surface AM mean'),('offtarget_AM_mean','Off-target AM mean'))],shared_initial_ranges=copy.deepcopy(ctx['manual_ranges']),sections=[dict(kind='new_native',title='New saved native fields + actual120 probes',grid_scope='Fine B0/P23:XY102-Z97; E13:coarseXY100-Z101. Different grids explicitly labelled; no cross-grid ranking',cases=[]),dict(kind='legacy_reference',title='Original B0 and4/8/12/16 physical-pad references',grid_scope='Original XY100-Z101; two independent outputs throughout',cases=[])],legacy_provisional_top5=copy.deepcopy(ctx['legacy_provisional_top5']['ordered_ids']),holds=copy.deepcopy(ctx['holds']),provenance=dict(publications={k:dict(commit=v['commit'],receipt_SHA256=v['SHA256'])for k,v in ctx['publication_proofs'].items()},legacy_top5_original_provenance=dict(result_commit=ctx['legacy_provisional_top5']['publication']['publication_commit'],summary_SHA256=ctx['legacy_provisional_top5']['publication']['SHA256'],scope='Original published provisional order preserved; no native maps added and no reranking'),body=ctx['body'],field_version=ctx['field_version'],material_contact_metadata=ctx['material_contact_metadata'],native_restore_review=ctx['native_restore_review'],display_policy=spec['display_policy'],browser_validation_performed=False,Windows_saved_verified=False))
    caseproofs=[];pdir=out/'case-proofs';pdir.mkdir(exist_ok=False)
    for c in ctx['cases']:
        check(guard,deadline_monotonic)
        before=[dict(path=d['path'],SHA256=d['SHA256'],bytes=d['bytes'],publication_commit=d['publication_commit'],publication_target=d['publication_target'],readback_passed=True,full_SHA_before_verified=True,full_SHA_after_verified=True)for d in(c['grid'],c['scalars'],c['E2000'])]
        if 'mask'in c:verify_native(c['mask'],guard,deadline_monotonic)
        if 'fractional_mask'in c:verify_native(c['fractional_mask'],guard,deadline_monotonic);before.append(dict(c['fractional_mask'],full_SHA_before_verified=True))
        display,proof=_case(np,c,extract,guard,deadline_monotonic)
        if 'mask'in c:verify_native(c['mask'],guard,deadline_monotonic)
        if 'fractional_mask'in c:verify_native(c['fractional_mask'],guard,deadline_monotonic);before[-1]['full_SHA_after_verified']=True
        for key in('probe_arrays','mask'):
            if key in c:before.append(dict(c[key],full_SHA_before_verified=True,full_SHA_after_verified=True))
        if c['geometry']['kind']=='polyomino':before.append(dict(c['geometry']['mask'],full_SHA_before_verified=True,full_SHA_after_verified=True))
        proof['native_file_proofs']=before;section=payload['sections'][0 if c['section']=='new_native'else 1];section['cases'].append(display)
        proof.update(candidate_id=c['candidate_id'],actual_new_PDE_RHS=0,actual_new_Q_loads=0,actual_new_angular_evaluations=0,original_statistics_recomputed=False,large_native_arrays_released_before_next_case=True)
        caseproofs.append(new_json(pdir/(c['candidate_id']+'.json'),proof));new_json(out/('checkpoint-GUI-%02d.json'%len(caseproofs)),dict(completed_cases=len(caseproofs),candidate_id=c['candidate_id'],native_arrays_released=True));gc.collect()
    raw=_json_bytes(payload);payload_desc=write_bytes(out/'payload.json',raw)
    require(len(raw)<=MAX_JSON_BYTES,'Functional display JSON4.9MB bound exceeded; payload preserved, no automatic science/case omission')
    document=renderer.render(payload);html_raw=document.encode('utf-8');require(len(html_raw)<=MAX_HTML_BYTES,'Functional HTML5MB bound; preserve payload, no silent reduction')
    html_desc=write_bytes(out/'index.html',html_raw);check(guard,deadline_monotonic)
    require(gui_inputs.source_inventory(gui_inputs.MODEL)==ctx['model_source_sha256'],'Frozen model unchanged after build')
    summary=dict(schema='task1-native-GUI-lite-build-result-v1',status='native_GUI_lite_built_browser_unverified',completed_cases=7,new_native_cases=3,legacy_reference_cases=4,requested_probes=120,strict_same_layer_probes=60,extrapolated_probes=60,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_native_statistic_reductions=0,new_stat_reductions=0,new_candidate_rankings=0,browser_validation_performed=False,candidate_adopted=False,old_GUI_pointers_modified=False,original_statistics_overwritten=False,payload_JSON_bytes=len(raw),index_HTML_bytes=len(html_raw),payload=payload_desc,index=html_desc,case_proofs=caseproofs,actual_test_receipt=testproof,holds=ctx['holds'],native_restore_review=ctx['native_restore_review'],Windows_saved_verified=False)
    new_json(out/'gui-build-receipt.json',summary);return dict(summary=summary,arrays={})
