"""Pure source/admission/MFG/accounting gates for one-case GUI append."""
import ast,math
from pathlib import Path
MODEL_TEST_COUNT=40
MODEL_SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source')
NEW_ID='E13-tangent-P23-centroids-225-XY102-Z97'
EXCLUDED=frozenset(('root-admission.json','synthetic-test-receipt.json','tests-receipt.json'))
FROZEN_MODEL_SHA={'/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/APPEND_BUILD_CONTRACT.md': '385cdc293f4129208d9aee5c7be10aba4bca20a7693260f8ece7f04b493ed219', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/APPEND_INPUT_CONTRACT.md': '6889ea17237aef0fc413a88e7973e6c6abe5f5c47f89d0c3df67d4ea2b76029a', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/append_build.py': '03a186ea6d2fca013baac28ac13182d94eedce2de24b3c3fed616e98ee1d6ffc', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/append_inputs.py': '5b46bb0a20dac1e49247484676641b4d2c9a370738bcb0fc21b98cefb3a99a0f', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/frozen_gui_build.py': 'f802d13334f08fb35611e56afe674f4f21afe030fd77a47aa93bd17013b2e620', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/gui_inputs.py': '1b5f66e4277c2fadde8290afdb4fa677b1d3971ecb0fdf7fa7e671067fcc3dd7', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/lite_extract.py': 'c796ba656d7e37ac7333a97ca86303052a9508d8e8aa4223f251cc398fcf412e', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/lite_render.py': '9cc9acd3b16176e4c4cddc9e0877b6fcdb2972b73b048d6054d47503502213b6', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/test_append_build.py': '735f38381078c320aa401bd5059d26e529a382dac886b3a2286f51069c2a8640', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/test_append_inputs.py': '6e8197fe99adfed0a007c9595c5699535eba086e159951979eaa88c69471b0a2', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/test_lite_extract.py': '3acb90dddcd2e4423a3bf58a130010c0a81021b80bba48417429871fdc10c4e1', '/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source/test_lite_render.py': '70bda6ac1c0404f2a8f8d911f7d563e2e159fb0ac7f5aa284d4d285e8eb7931b'}

def require(ok,message):
 if not ok:raise ValueError(message)
def source_paths(root):return sorted(p for p in Path(root).iterdir()if p.is_file()and p.suffix in('.py','.md','.json','.log')and p.name not in EXCLUDED)
def test_methods(path):
 tree=ast.parse(Path(path).read_text());return [cls.name+'.'+f.name for cls in tree.body if isinstance(cls,ast.ClassDef)for f in cls.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef))and f.name.startswith('test_')]
def validate_admission(a,sources,model_sources,owner_count):
 require(type(a)is dict and a.get('schema')=='task1-native-GUI-append-E13fine-root-admission-v4'and a.get('status')=='selected_partial_payload_append_after_GUI5_readback_recovery','Separate positive append-only admission after actual R5')
 require(a.get('publication_outcome')=='readback_recovered_after_original_publication_timeout'and a.get('prior_recovery_terminal_dead_confirmed')is True,'Separate actual completed readback terminal required, original GUI owner staysfailed')
 require(a.get('base_outcome')=='partial_payload_complete_functional_limit'and a.get('prior_owner_terminal_dead_confirmed')is True,'Only actual particular failed-complete-payload branch with dead original owner')
 require(a.get('root_authorized')is True and a.get('safe_boundary_confirmed')is True,'Actual safe boundary only; no waiting for another worker')
 for key in('previous_append_R4_source_failure_reviewed','prior_append_R4_owner_terminal_dead_confirmed','prior_source_readback_terminal_dead_confirmed','prior_clone_check_terminal_dead_confirmed'):require(a.get(key)is True,'Explicit Root prior SourcePUB failure/recovery review and dead terminal: '+key)
 require(a.get('base_version')=='native-GUI-lite-r5-20261025'and a.get('previous_GUI',{}).get('run')=='/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-20261025-run','Only actual workspace R5, never failed R4')
 require(a.get('source_sha256')==model_sources==FROZEN_MODEL_SHA and a.get('owner_source_sha256')==sources,'Complete canonical frozen40-test model and owner inventories')
 require(a.get('expected_model_tests')==MODEL_TEST_COUNT and type(owner_count)is int and owner_count>0 and type(a.get('expected_owner_tests'))is int and a['expected_owner_tests']==owner_count,'Dynamic actual source test inventory')
 require(a.get('CPU_limit')==4 and a.get('physical_cap_bytes')==8000000000 and a.get('max_cells')==800000,'Unchanged original CPU/RAM/cells')
 require(a.get('child_RSS_forecast_bytes')==240000000 and a.get('new_output_forecast_bytes')==20000000 and a.get('new_TMPFS_output_forecast_bytes')==0 and a.get('new_output_storage')=='existing_workspace_disk','Provisional240M RSS/20Mdisk/0newTMPFS; not a capacity quota')
 for key in('new_PDE_RHS','new_Q_loads','new_eigen_solves','new_angular_evaluations','new_stat_reductions','old_native_extractions'):require(type(a.get(key))is int and a[key]==0,'No '+key)
 require(type(a.get('new_native_extractions'))is int and a['new_native_extractions']==1 and a.get('candidate_ids')==[NEW_ID],'Exactly one new display case')
 for key in('candidate_adopted','browser_authorized','old_GUI_pointers_modified'):require(a.get(key)is False,'No '+key)
 return True

def validate_MFG(r,model_sources,owner_count,expected_events=None):
 require(r.get('schema')=='task1-native-GUI-append-E13fine-manufactured-tests-v1'and r.get('status')=='passed'and r.get('model_source_sha256')==model_sources,'Actual successful exact-source prospective manufactured tests')
 expected=dict(model_source_test_count=MODEL_TEST_COUNT,model_tests_run=MODEL_TEST_COUNT,owner_tests_run=owner_count,tests_run=MODEL_TEST_COUNT+owner_count,expected_total_tests=MODEL_TEST_COUNT+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0)
 require(all(type(r.get(k))is int and r[k]==v for k,v in expected.items()),'Complete dynamic40+owner tests before original document/native bytes')
 require(r.get('scientific_API_spy_calls')==[]and r.get('native_IO_attempts')==[]and r.get('native_Q_loaded')is False and r.get('field_admission_granted')is False and r.get('browser_validation_performed')is False,'Caught native/scientific violations cannot become PASS')
 require(r.get('negative_fixture_counts',{}).get('invalid_admission_before_IO')==1 and r.get('dependencies_initialized_before_mocks')is True and r.get('IO_audit_installed')is True,'Intended invalid-admission-before-data fixture and prewarmed bounded I/O gate')
 events=r.get('test_events',[]);require(type(events)is list and len(events)==MODEL_TEST_COUNT+owner_count and len({e.get('test_id')for e in events})==len(events)and all(e.get('outcome')=='passed'for e in events),'Actual unique complete passed event set')
 if expected_events is not None:require({e['test_id']for e in events}==set(expected_events),'Actual event IDs exactly match independently published inventory')
 return dict(passed=True,model_tests=MODEL_TEST_COUNT,owner_tests=owner_count,actual_tests=MODEL_TEST_COUNT+owner_count,native_field_reads_during_MFG=0)

def validate_summary(s):
 require(s.get('schema')=='task1-native-GUI-append-E13fine-result-v1'and s.get('status')=='native_GUI_E13fine_appended_browser_unverified','Actual one-case append complete, browser remains unverified')
 expected=dict(completed_cases=8,old_cases_reused=7,new_native_cases_extracted=1,legacy_reference_cases=4,new_native_section_cases=4,requested_probes=160,new_requested_probes=40,new_high_volume_subsets=48,strict_same_layer_probes=80,extrapolated_probes=80,unavailable_probes=0,old_case_extractions=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_native_statistic_reductions=0,new_stat_reductions=0,new_candidate_rankings=0)
 require(all(type(s.get(k))is int and s[k]==v for k,v in expected.items())and s.get('new_native_candidate')==NEW_ID,'Exact one-new/seven-reused/eight-total/probe/source accounting')
 require(s.get('base_outcome')=='partial_payload_complete_functional_limit'and s.get('previous_GUI_complete_success')is False and s.get('previous_payload_recovered_without_old_extraction')is True and s.get('original_absences_preserved')is True and s.get('previous_index_missing',{}).get('reason')=='never_created_after_functional_limit','Actual partial recovery truth, no invented old index/GUI success')
 require(s.get('inherited_holds',{}).get('appended_E13_fine',{}).get('previous_GUI_partial_failure',{}).get('publication_outcome')=='readback_recovered_after_original_publication_timeout','Separate actual readback recovery remains visible; no original publication success fabricated')
 require(s.get('old_case_quantitative_values_byte_preserved')is True,'All seven original case canonical-byte identities retained')
 for key in('original_statistics_overwritten','old_GUI_pointers_modified','browser_validation_performed','experimental_validation','full_convergence','candidate_adopted','Windows_saved_verified'):require(s.get(key)is False,'No unsupported overwrite/validation/adoption/storage claim '+key)
 require(type(s.get('payload_JSON_bytes'))is int and 0<s['payload_JSON_bytes']<=8000000 and type(s.get('index_HTML_bytes'))is int and 0<s['index_HTML_bytes']<=8200000,'Functional display bounds only; no automatic omission or storage quota')
 return dict(passed=True,**expected,payload_JSON_bytes=s['payload_JSON_bytes'],index_HTML_bytes=s['index_HTML_bytes'],browser_validation_performed=False,candidate_adopted=False)
def fixture_elements(shape):
 if type(shape)is int:shape=(shape,)
 require(isinstance(shape,(tuple,list))and 0<len(shape)<=4 and all(type(v)is int and v>=0 for v in shape),'Explicit small manufactured shape')
 n=math.prod(shape);require(n<=65536,'No actual native/Q shape in synthetic fixtures');return n
def forecast_physical_bytes(task_temp,research_RSS,child_RSS,new_tmpfs_output):
 require(all(type(v)is int and v>=0 for v in(task_temp,research_RSS,child_RSS,new_tmpfs_output)),'Actual bytes and separately declared forecasts')
 return task_temp+research_RSS+child_RSS+new_tmpfs_output
