"""Inert finite GUI-build contracts, no fields/files/native work on import."""
import ast,math
from pathlib import Path
MODEL_TEST_COUNT=16
EXCLUDED=frozenset(('root-admission.json','synthetic-test-receipt.json','tests-receipt.json'))
FROZEN_MODEL_SHA={'lite_extract.py':'c796ba656d7e37ac7333a97ca86303052a9508d8e8aa4223f251cc398fcf412e','lite_render.py':'558c184ef7eaf47aa744ef04ff0313e74bd772430c897037d08d0b10292be7d4','test_lite_extract.py':'3acb90dddcd2e4423a3bf58a130010c0a81021b80bba48417429871fdc10c4e1','test_lite_render.py':'7860eeda63752d5aa97854d0d23ee4c2000f98c7ab3ab5ca5cc4a2036746b110'}

def require(ok,message):
 if not ok:raise ValueError(message)
def source_paths(root):return sorted(p for p in Path(root).iterdir()if p.is_file()and p.suffix in('.py','.md','.json')and p.name not in EXCLUDED)
def test_methods(path):
 tree=ast.parse(Path(path).read_text());return [cls.name+'.'+f.name for cls in tree.body if isinstance(cls,ast.ClassDef)for f in cls.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef))and f.name.startswith('test_')]
def validate_admission(a,sources,model_sources,owner_count):
 require(type(a)is dict and a.get('schema')=='task1-native-GUI-lite-build-root-admission-v1'and a.get('status')=='selected_finite_GUI_build','Explicit positive GUI-only build admission')
 require(a.get('root_authorized')is True and a.get('safe_boundary_confirmed')is True,'Root must confirm actual terminal safe boundary; owner never waits for or interrupts another task')
 require(a.get('source_sha256')==sources and a.get('model_source_sha256')==model_sources,'All canonical frozen model/owner source hashes, no path aliases')
 require(a.get('expected_model_tests')==MODEL_TEST_COUNT and a.get('expected_owner_tests')==owner_count and type(owner_count)is int and owner_count>0,'Exact prospective dynamic MFG counts')
 require(a.get('cpu_limit')==4 and a.get('physical_cap_bytes')==8000000000 and a.get('max_cells')==800000,'Unchanged original CPU/RAM/cell limits')
 for key in('new_PDE_authorized','Q_load_authorized','new_eigen_authorized','angular_scan_authorized','statistics_regeneration_authorized','browser_authorized','candidate_adoption_authorized'):
  require(a.get(key)is False,'GUI build grants no '+key)
 review=a.get('native_restore_review');require(type(review)is dict and type(review.get('status'))is str and review['status']and not any(t in review['status'].lower()for t in('running','pending')),'Native restore status is actual terminal or explicitly unavailable, never an invented PASS')
 return True

def validate_MFG(r,model_sources,owner_count,expected_events=None):
 require(r.get('schema')=='task1-native-GUI-lite-manufactured-tests-v1'and r.get('status')=='passed'and r.get('model_source_sha256')==model_sources,'Actual successful source-bound manufactured GUI tests')
 expected=dict(model_source_test_count=16,model_tests_run=16,owner_tests_run=owner_count,tests_run=16+owner_count,expected_total_tests=16+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0)
 require(all(type(r.get(k))is int and r[k]==v for k,v in expected.items()),'Complete actual 16+owner tests before original native array reads')
 require(r.get('scientific_API_spy_calls')==[]and r.get('native_IO_attempts')==[]and r.get('field_admission_granted')is False and r.get('browser_validation_performed')is False,'No caught native/scientific/boundary violation can become PASS')
 require(r.get('negative_fixture_counts',{}).get('native_suffix_rejection_before_open')==1,'Only exact native-suffix negative fixture rejected before any file open')
 require(r.get('dependencies_initialized_before_mocks')is True and r.get('IO_audit_installed')is True,'Actual existing NumPy.ma/fft/testing prewarm and data-I/O gate')
 if expected_events is not None:require(len(r.get('test_events',[]))==16+owner_count and {e['test_id']for e in r['test_events']if e.get('outcome')=='passed'}==set(expected_events),'All prospective method identities execute once')
 return dict(passed=True,model_tests=16,owner_tests=owner_count,actual_tests=16+owner_count,native_field_reads_during_MFG=0)

def validate_summary(s):
 require(s.get('schema')=='task1-native-GUI-lite-build-result-v1'and s.get('status')=='native_GUI_lite_built_browser_unverified','Actual generated GUI derivative, browser status remains separate')
 counts=dict(completed_cases=7,new_native_cases=3,legacy_reference_cases=4,requested_probes=120,strict_same_layer_probes=60,extrapolated_probes=60,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0)
 require(all(type(s.get(k))is int and s[k]==v for k,v in counts.items()),'Exact mandatory seven native/legacy cases and 120 actual probe accounting')
 require(type(s.get('payload_JSON_bytes'))is int and 0<s['payload_JSON_bytes']<=4900000 and type(s.get('index_HTML_bytes'))is int and 0<s['index_HTML_bytes']<=5000000,'Functional display/memory payload bounds, not a storage quota')
 for key in('browser_validation_performed','candidate_adopted','old_GUI_pointers_modified'):require(s.get(key)is False,'Preserve unverified/old GUI/candidate status '+key)
 return dict(passed=True,**counts,payload_JSON_bytes=s['payload_JSON_bytes'],index_HTML_bytes=s['index_HTML_bytes'],browser_validation_performed=False,candidate_adopted=False)

def fixture_elements(shape):
 if type(shape)is int:shape=(shape,)
 require(isinstance(shape,(tuple,list))and 0<len(shape)<=4 and all(type(v)is int and v>=0 for v in shape),'Explicit synthetic allocation shape')
 n=math.prod(shape);require(n<=65536,'Synthetic arrays at most65536elements, no native volume');return n
