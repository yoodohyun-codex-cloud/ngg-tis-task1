"""Append one authenticated fine E13 display to a completed seven-case GUI.

Import is inert. No original native cases are extracted, ranked or rewritten.
Root alone runs after source-bound manufactured tests and actual failed-R5
functional-limit publication with a complete seven-case payload.
"""
import ast,copy,gc,hashlib,json,math,time
from pathlib import Path
import append_inputs

SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r4-20261025/source')
RUN=Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r4-20261025-run')
SCHEMA='task1-native-GUI-append-E13fine-display-v1'
NEW_ID='E13-tangent-P23-centroids-225-XY102-Z97'
OLD_NATIVE_IDS=('B0-square15-c10-diagonal-XY102-Z97','P23p5-peripheral-polyomino225-XY102-Z97','E13-tangent-P23-centroids-225')
LEGACY_IDS=('B0-square15-c10-diagonal','MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
MAX_JSON_BYTES=8000000;MAX_HTML_BYTES=8200000

def require(ok,message):
 if not ok:raise ValueError(message)
def check(guard,deadline):
 if guard is not None:guard()
 if deadline is not None and time.monotonic()>=deadline:raise TimeoutError('Finite GUI append deadline; preserve original and partial evidence')
def _json_bytes(value):return(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')
def canonical_identity(value):
 """Standard SHA256 of the exact existing producer's canonical JSON bytes."""
 h=hashlib.sha256();size=0
 encoder=json.JSONEncoder(ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))
 for part in encoder.iterencode(value):
  raw=part.encode('utf-8');h.update(raw);size+=len(raw)
 h.update(b'\n');return dict(SHA256=h.hexdigest(),bytes=size+1,serialization='Python JSON sort_keys/ensure_ascii=False/allow_nan=False/compact separators/UTF8+newline')
def new_bytes(path,raw):
 with Path(path).open('xb')as stream:stream.write(raw)
 return dict(path=str(path),SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def new_json(path,value):return new_bytes(path,_json_bytes(value))
def digest(path,guard,deadline):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):check(guard,deadline);h.update(block)
 return h.hexdigest()
def verify_document(d,guard,deadline):
 p=Path(d['path']);require(p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size==d['bytes']and 0<d['bytes']<=MAX_HTML_BYTES,'Canonical bounded actual preceding GUI document')
 require(d.get('readback_passed')is True and append_inputs.fullhex(d.get('publication_commit'),40)and append_inputs.fullhex(d.get('SHA256'),64)and digest(p,guard,deadline)==d['SHA256'],'Actual full preceding R5 document SHA/bytes/readback')
 return p
def require_partial_base(ctx):
 require(ctx.get('base_outcome')=='partial_payload_complete_functional_limit'and ctx.get('previous_index')is None,'Only exact complete-payload functional-limit failure; no invented old HTML/success')
 missing=ctx.get('previous_index_missing');require(type(missing)is dict and missing.get('reason')=='never_created_after_functional_limit','Explicit actual absent previous index and cause')
 require(type(ctx.get('original_absences'))is list and missing.get('path')in ctx['original_absences']and len(ctx['original_absences'])==3,'Actual old index/summary/build-receipt absences remain guarded')
 return missing
def verify_original_absences(ctx,exists=None):
 require_partial_base(ctx);exists=(lambda p:Path(p).exists()or Path(p).is_symlink())if exists is None else exists
 require(all(type(p)is str and not exists(p)for p in ctx['original_absences']),'Original failed producer outputs remain absent, never fabricated or overwritten')
def previous_cases(payload):
 require(type(payload)is dict and payload.get('schema')=='task1-native-GUI-lite-display-v1','Exact original seven-case GUI payload schema')
 sections=payload.get('sections');require(type(sections)is list and len(sections)==2 and [x.get('kind')for x in sections]==['new_native','legacy_reference'],'Original two separate native/legacy sections')
 require(tuple(c.get('id')for c in sections[0].get('cases',[]))==OLD_NATIVE_IDS and tuple(c.get('id')for c in sections[1].get('cases',[]))==LEGACY_IDS,'All seven original cases and original order retained without substitution')
 require([c.get('pad_count')for c in sections[1]['cases']]==[4,8,12,16]and all(c.get('independent_outputs')==2 for s in sections for c in s['cases']),'Physical pad counts and two-output references remain distinct')
 return sections[0]['cases']+sections[1]['cases']
def fingerprints(cases):return [dict(id=c['id'],**canonical_identity(c))for c in cases]
def finite(value,label,nonnegative=True):
 require(type(value)in(int,float)and math.isfinite(value)and(not nonnegative or value>=0),'Actual finite original statistic '+label);return value
def extended_ranges(previous,all_cases):
 """Only original Float64 normalization/probe records, never display pixels."""
 ranges=copy.deepcopy(previous);require(set(('x_mm','y_mm','depth_mm','AM_V_m','RMS_V_m','J_A_m2','bar_value','wave_time_ms','wave_voltage_V')).issubset(ranges),'All original shared manual axes retained')
 for name,pair in ranges.items():require(type(pair)is list and len(pair)==2 and all(type(x)in(int,float)and math.isfinite(x)for x in pair)and pair[0]<pair[1],'Original finite increasing range '+name)
 maxima={name:0. for name in('AM_V_m','RMS_V_m','J_A_m2','bar_value')};wave_peak=0.
 for c in all_cases:
  require(set(c['normalizations'])==set(MODES)and set(c['amplitude_scales'])==set(MODES),'Exactly four separate original normalization rows per case')
  for mode,row in c['normalizations'].items():
   fields=row['absolute_ROI_fields_V_m']['total'];maxima['AM_V_m']=max(maxima['AM_V_m'],finite(fields['maxTIS']['max'],'total normalized AM max'))
   maxima['RMS_V_m']=max(maxima['RMS_V_m'],finite(fields['RMS']['max'],'total normalized carrier RMS max'))
   maxima['J_A_m2']=max(maxima['J_A_m2'],finite(row['electrical']['contact_normal_J_RMS_max_A_m2'],'normalized contact J RMS max'))
   scale=finite(c['amplitude_scales'][mode],'original amplitude scale');require(scale==row['amplitude_scale'],'No double normalization or substitute amplitude')
   if 'probe_summary'in c:
    for p in c['probe_summary']['probes']:
     require(p.get('status')=='calculated_unloaded_only'and type(p.get('unloaded'))is dict,'Actual supplied unloaded probe record, not an invented waveform')
     wave_peak=max(wave_peak,finite(p['unloaded']['envelope_max_exact_V'],'original exact unloaded envelope max')*scale)
  for values in c['bar_values'].values():
   require(set(values)==set(MODES),'Every bar preserves the four original normalized values')
   for value in values.values():maxima['bar_value']=max(maxima['bar_value'],finite(value,'stored normalized bar value'))
 for name,value in maxima.items():
  require(value>0,'Positive original-statistic range source '+name);ranges[name]=[previous[name][0],max(previous[name][1],value)]
 require(wave_peak>0,'Positive exact source-envelope waveform range');ranges['wave_voltage_V']=[min(previous['wave_voltage_V'][0],-wave_peak),max(previous['wave_voltage_V'][1],wave_peak)]
 return ranges,dict(method='Extend original defaults from all eight Float64 normalization/bar records and all four original unloaded-probe envelope records; no native/display reduction',previous=copy.deepcopy(previous),extended=copy.deepcopy(ranges),normalized_source_maxima=maxima,exact_normalized_envelope_max_V=wave_peak,ranges_change_on_selection=False,manual_overrides_preserved_by_unchanged_renderer=True)
def assemble(previous,new_case,*,provenance,holds):
 """Shallow persistent append: all seven original case objects are reused."""
 old=previous_cases(previous);before=fingerprints(old)
 require(new_case.get('id')==NEW_ID and new_case.get('pad_count')==4 and new_case.get('independent_outputs')==2 and new_case.get('grid_version')=='XY102-Z97','Exactly one new actual four-pad/two-output fine E13 display')
 require(NEW_ID not in [c['id']for c in old],'Do not duplicate an existing display case')
 payload=dict(previous);sections=[dict(s)for s in previous['sections']]
 sections[0]['cases']=list(previous['sections'][0]['cases'])+[new_case]
 sections[1]['cases']=list(previous['sections'][1]['cases'])
 sections[0]['title']='Saved native fields + actual160 unloaded probes'
 sections[0]['grid_scope']=previous['sections'][0].get('grid_scope','')+'; appended E13 fine: XY102-Z97, distinct from coarse E13. No cross-grid ranking.'
 payload['sections']=sections;payload['schema']=SCHEMA
 payload['provenance']=dict(previous.get('provenance',{}));require('append_E13_fine'not in payload['provenance'],'Unique append provenance namespace')
 payload['provenance']['append_E13_fine']=copy.deepcopy(provenance)
 payload['holds']=dict(previous.get('holds',{}));require('appended_E13_fine'not in payload['holds'],'Unique inherited uncertainty namespace')
 payload['holds']['appended_E13_fine']=copy.deepcopy(holds)
 all_cases=sections[0]['cases']+sections[1]['cases'];payload['shared_initial_ranges'],range_proof=extended_ranges(previous['shared_initial_ranges'],all_cases)
 after=fingerprints(sections[0]['cases'][:3]+sections[1]['cases']);require(before==after,'All seven original complete case JSON bytes and quantitative values preserved')
 require(fingerprints(previous_cases(previous))==before,'Original input payload object/cases not mutated')
 require(canonical_identity(payload.get('legacy_provisional_top5'))==canonical_identity(previous.get('legacy_provisional_top5')),'Original provisional order preserved; no reranking')
 probes=[c['probe_summary']for c in sections[0]['cases']];counts={k:sum(p[k]for p in probes)for k in('probe_count','calculated_probe_count','unavailable_probe_count','strict_same_layer_bracket_available_probe_count','same_layer_extrapolated_probe_count')}
 require(counts==dict(probe_count=160,calculated_probe_count=160,unavailable_probe_count=0,strict_same_layer_bracket_available_probe_count=80,same_layer_extrapolated_probe_count=80),'Actual original120 plus new40 probe rows/counts, no copied substitutes')
 proof=dict(original_cases=before,old_case_count=7,new_case_count=1,completed_cases=8,old_cases_reextracted=0,old_case_quantitative_values_byte_preserved=True,original_payload_object_unchanged=True,legacy_rank_recomputed=False,probe_counts=counts,shared_range_proof=range_proof)
 return payload,proof
def make_spec(admission=None):
 ctx=append_inputs.make_spec(admission)
 require_partial_base(ctx)
 return dict(schema='task1-native-GUI-append-E13fine-spec-v1',root_admission=ctx['root_admission'],inputs=ctx,metadata_input_sha256=ctx['metadata_input_sha256'],native_input_descriptors=ctx['native_input_descriptors'],expected_cases=8,expected_old_cases_reused=7,expected_new_native_cases=1,expected_new_native_candidate=NEW_ID,expected_requested_probes=160,expected_new_requested_probes=40,expected_new_high_volume_subsets=48,old_case_extractions=0,new_candidate_rankings=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_native_statistic_reductions=0,new_stat_reductions=0,
  base_outcome='partial_payload_complete_functional_limit',previous_index_required=False,previous_GUI_complete_success=False,
  output_functional_bounds=dict(JSON_bytes=MAX_JSON_BYTES,HTML_bytes=MAX_HTML_BYTES,not_a_storage_capacity_guard=True,no_automatic_trimming_or_further_downsampling=True),display_policy=dict(frozen_case_helper='R5 gui_build._case byte-identical; new case only',old_seven_payload_records_reused_verbatim=True,new_case_uses_same_frozen64_point_and_sparse_arrow_display_policy=True,no_new_statistics_or_ranking=True),child_RSS_forecast_bytes=240000000,new_output_forecast_bytes=20000000,forecasts_unmeasured=True,CPU_limit=4,total_RSS_plus_all_owned_task_bytes=8000000000,max_physical_cells=800000,browser_validation_performed=False,candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['metadata_input_sha256'])
def source_test_count():
 count=0
 for p in SOURCE.glob('test_*.py'):
  t=ast.parse(p.read_text(),filename=str(p));count+=sum(isinstance(m,ast.FunctionDef)and m.name.startswith('test_')for c in t.body if isinstance(c,ast.ClassDef)for m in c.body)
 return count
def _check_tests(spec,out):
 p=out/'synthetic-test-receipt.json';require(p.is_file()and not p.is_symlink()and p.stat().st_size<2*1024**2,'Actual protected source-bound MFG receipt before new native reads')
 raw=p.read_bytes();r=json.loads(raw);n=source_test_count()
 require(r.get('status')=='passed'and r.get('model_source_sha256')==spec['inputs']['source_sha256']and type(r.get('model_source_test_count'))is int and r['model_source_test_count']==n and type(r.get('model_tests_run'))is int and r['model_tests_run']==n,'Actual exact new model manufactured tests/source identity')
 require(type(r.get('tests_run'))is int and r['tests_run']==r.get('expected_total_tests')and r['tests_run']>=n and all(type(r.get(k))is int and r[k]==0 for k in('tests_failed','tests_errors','tests_skipped')),'All prospective source-bound model/owner tests passed')
 require(r.get('native_field_reads')==0 and r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('scientific_API_spy_calls')==[],'Manufactured work before native data/fields')
 return dict(path=str(p),SHA256=hashlib.sha256(raw).hexdigest(),tests_run=r['tests_run'],model_tests=n)
def extract_one_case(np,case,extract,guard,deadline,case_builder):
 require(case.get('candidate_id')==NEW_ID and case.get('section')=='new_native','Only the new E13 fine case may enter native extraction')
 return case_builder(np,case,extract,guard,deadline)
def build(spec,guard,deadline_monotonic=None,output_dir=None):
 check(guard,deadline_monotonic);out=Path(output_dir or RUN)
 require(callable(guard)and out==RUN and out==out.resolve()and out.is_dir()and not out.is_symlink()and not(out/'payload.json').exists(),'Unique root-owned append run; no original overwrite')
 require(spec==make_spec(spec['root_admission']),'Exact source-published R5/post/native provenance and finite append-only specification')
 ctx=spec['inputs'];testproof=_check_tests(spec,out)
 verify_original_absences(ctx);previous_path=verify_document(ctx['previous_payload'],guard,deadline_monotonic)
 with previous_path.open('r',encoding='utf-8')as stream:previous=json.load(stream)
 require(canonical_identity(previous)['SHA256']==ctx['previous_payload']['SHA256']and canonical_identity(previous)['bytes']==ctx['previous_payload']['bytes'],'Exact original canonical payload bytes before append, not a recoded numeric approximation')
 old_identity=fingerprints(previous_cases(previous));old_header={k:canonical_identity(v)for k,v in previous.items()if k not in('schema','sections','shared_initial_ranges','provenance','holds')}
 check(guard,deadline_monotonic)
 import numpy as np
 import frozen_gui_build,lite_extract,lite_render
 case=ctx['new_case'];require(case['candidate_id']==NEW_ID and case['section']=='new_native','Single new E13 fine case helper call only')
 display,caseproof=extract_one_case(np,case,lite_extract,guard,deadline_monotonic,frozen_gui_build._case)
 # Metadata links supplement the unchanged helper without altering its values.
 for key in('probe_json','probe_arrays','high_volume'):
  if key in case:display['provenance']['artifacts'].append(frozen_gui_build.artifact(case[key],key))
 payload,proof=assemble(previous,display,provenance=ctx['provenance'],holds=ctx['holds'])
 require(old_identity==proof['original_cases']and all(canonical_identity(payload[k])==value for k,value in old_header.items()),'No old case/global quantitative key overwritten during append')
 proof.update(base_outcome='partial_payload_complete_functional_limit',previous_GUI_complete_success=False,previous_payload_recovered_without_old_extraction=True,previous_payload=ctx['previous_payload'],previous_index=None,previous_index_missing=ctx['previous_index_missing'],original_absences=ctx['original_absences'],previous_GUI_evidence=ctx['previous_GUI_evidence'],new_case_source=case['provenance'],new_case_native_files=ctx['native_input_descriptors'],actual_new_case_extractions=1,new_case_native_arrays_released=True,testproof=testproof,source_sha256=ctx['source_sha256'],new_native_statistic_reductions=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_candidate_rankings=0,browser_validation_performed=False,candidate_adopted=False)
 new_json(out/'new-case-proof.json',dict(caseproof,candidate_id=NEW_ID,new_native_statistic_reductions=0))
 new_json(out/'checkpoint-append-new-case.json',dict(completed_old_cases_reused=7,completed_new_native_extractions=1,native_arrays_released=True,new_PDE_RHS=0,new_Q_loads=0,new_angular_evaluations=0))
 raw=_json_bytes(payload);pdesc=new_bytes(out/'payload.json',raw);require(len(raw)<=MAX_JSON_BYTES,'Functional8MB JSON exceeded; preserve complete payload and fail, no trimming')
 before=canonical_identity(payload);document=lite_render.render(payload);require(canonical_identity(payload)==before and fingerprints(payload['sections'][0]['cases'][:3]+payload['sections'][1]['cases'])==old_identity,'Renderer does not mutate complete payload or any original case')
 html=document.encode('utf-8');require(len(html)<=MAX_HTML_BYTES,'Functional8.2MB HTML exceeded; preserve evidence without omission');hdesc=new_bytes(out/'index.html',html)
 verify_document(ctx['previous_payload'],guard,deadline_monotonic);verify_original_absences(ctx)
 for d in ctx['native_input_descriptors']:frozen_gui_build.verify_native(d,guard,deadline_monotonic)
 require(append_inputs.source_inventory()==ctx['source_sha256'],'Canonical source unchanged after append/render')
 proof.update(payload=pdesc,index=hdesc,complete_payload_identity=before,original_payload_document_bytes_unchanged=True,original_absences_preserved=True);proofdesc=new_json(out/'append-preservation-proof.json',proof)
 summary=dict(schema='task1-native-GUI-append-E13fine-result-v1',status='native_GUI_E13fine_appended_browser_unverified',completed_cases=8,old_cases_reused=7,new_native_cases_extracted=1,new_native_candidate=NEW_ID,legacy_reference_cases=4,new_native_section_cases=4,requested_probes=160,new_requested_probes=40,new_high_volume_subsets=48,strict_same_layer_probes=80,extrapolated_probes=80,unavailable_probes=0,old_case_extractions=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_native_statistic_reductions=0,new_stat_reductions=0,new_candidate_rankings=0,old_case_quantitative_values_byte_preserved=True,original_statistics_overwritten=False,old_GUI_pointers_modified=False,browser_validation_performed=False,experimental_validation=False,full_convergence=False,candidate_adopted=False,Windows_saved_verified=False,payload=pdesc,index=hdesc,append_preservation_proof=proofdesc,payload_JSON_bytes=len(raw),index_HTML_bytes=len(html),source_sha256=ctx['source_sha256'],inherited_holds=payload['holds'])
 summary.update(base_outcome='partial_payload_complete_functional_limit',previous_GUI_complete_success=False,previous_payload_recovered_without_old_extraction=True,previous_index_missing=ctx['previous_index_missing'],original_absences_preserved=True)
 new_json(out/'gui-build-receipt.json',summary);check(guard,deadline_monotonic)
 del payload,previous,display,document,html,raw;gc.collect()
 return dict(summary=summary,arrays={})
