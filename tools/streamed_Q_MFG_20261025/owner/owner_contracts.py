"""Inert stdlib contracts for twelve tiny streamed-operator fixtures."""
import ast,math
from pathlib import Path
SUITES=('test_streamed_real_q',)
MODEL_COUNTS=(12,)
EXCLUDED=frozenset(('root-admission.json','synthetic-test-receipt.json','tests-receipt.json'))
KIND='actual_tiny_streamed_real_Q_operator_fixtures_only'
SCOPE='tiny_streamed_real_Q_manufactured_only'
MAX_ELEMENTS=4096
MAX_FIXTURE_FILE_BYTES=4096
MAX_ALL_FIXTURE_BYTES=65536

def require(ok,message):
 if not ok:raise ValueError(message)
def test_methods(path):
 tree=ast.parse(Path(path).read_text(),filename=str(path));return[node.name+'.'+method.name for node in tree.body if isinstance(node,ast.ClassDef)for method in node.body if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))and method.name.startswith('test_')]
def source_paths(directory):
 directory=Path(directory);require(directory.is_dir()and not directory.is_symlink(),'Canonical actual source directory');return sorted(p for p in directory.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in EXCLUDED)
def fixture_path_allowed(path,root):
 p=Path(path);r=Path(root);return p.is_absolute()and r.is_absolute()and p!=r and r in p.parents and p==p.resolve()and r==r.resolve()
def element_count(shape):
 if type(shape)is int:shape=(shape,)
 require(isinstance(shape,(list,tuple))and 0<len(shape)<=3 and all(type(x)is int and 0<=x<=MAX_ELEMENTS for x in shape),'Explicit bounded synthetic allocation shape')
 count=math.prod(shape);require(count<=MAX_ELEMENTS,'At most4096 synthetic allocation elements');return count
def validate_admission(item,sources,model_sources,model_count,owner_count):
 require(type(item)is dict and item.get('schema')=='task1-streamed-Q-MFG-root-admission-v1','Root supplies explicit manufactured admission')
 require(item.get('status')=='admitted'and item.get('root_authorized')is True and item.get('safe_boundary_confirmed')is True,'Root confirms actual ellipse-transfer/lowpost safe boundary')
 require(item.get('scope')==SCOPE and item.get('source_sha256')==sources and item.get('model_source_sha256')==model_sources,'Exact complete canonical frozen source maps')
 require(item.get('expected_model_tests')==model_count==12 and item.get('expected_owner_tests')==owner_count,'Prospective actual source method counts')
 require(item.get('cpu_limit')==4 and item.get('physical_cap_bytes')==8000000000 and item.get('max_cells')==800000,'Unchanged whole-task limits')
 for key in('native_file_reads_authorized','native_restore_authorized','new_PDE_authorized','new_eigen_authorized','candidate_adoption_authorized'):require(item.get(key)is False,'Tiny tests grant no native work '+key)
 return True
def validate_test_receipt(receipt,expected_model,expected_owner,model_sources,expected_events=None):
 require(receipt.get('kind')==KIND,'Actual tiny streamed real-Q operator fixtures only')
 require(receipt.get('model_source_sha256')==model_sources and receipt.get('source_sha256')==model_sources,'Complete canonical model source SHA map')
 require(receipt.get('model_source_test_count')==expected_model==12 and receipt.get('suites')==list(SUITES),'Exactly twelve model methods from the frozen suite')
 for key in('native_RHS','native_field_reads','native_file_reads','native_eigen_solves','native_full_field_exports'):require(type(receipt.get(key))is int and receipt[key]==0,'Zero actual native work '+key)
 for key in('native_Q_loaded','native_eigen_performed','native_restore_performed','field_admission_granted','candidate_adopted'):require(receipt.get(key)is False,'Manufactured tests do not establish '+key)
 require(receipt.get('forbidden_field_calls')==[]and receipt.get('native_IO_attempts')==[],'Caught boundary violations cannot become a test PASS')
 require(receipt.get('IO_audit_installed')is True,'Actual fixture-only file audit must be installed')
 require(type(receipt.get('tests_run'))is int and 0<=receipt['tests_run']<=expected_model+expected_owner,'Actual finite execution count')
 require(receipt.get('expected_total_tests')==expected_model+expected_owner,'Prospectively counted combined tests')
 passed=receipt.get('status')=='passed'
 if passed:
  require(receipt['tests_run']==receipt['expected_total_tests']and receipt.get('model_tests_run')==expected_model and receipt.get('owner_tests_run')==expected_owner,'All discovered principal/owner methods execute')
  require(all(receipt.get(key)==0 for key in('tests_failed','tests_errors','tests_skipped')),'No failed/error/skipped method')
  work=receipt.get('manufactured_work_counts',{})
  for key in('operator_constructors','metadata_validation_calls','forward_attempts','transpose_attempts','slice_attempts','chunk_visits_started','chunk_visits_completed','operator_receipts'):
   require(type(work.get(key))is int and work[key]>0,'Actual small operator API calls recorded '+key)
  io=receipt.get('synthetic_IO',{});require(io.get('read_opens',0)>0 and io.get('write_opens',0)>0 and io.get('maximum_file_bytes',MAX_FIXTURE_FILE_BYTES+1)<=MAX_FIXTURE_FILE_BYTES and io.get('total_regular_fixture_bytes',MAX_ALL_FIXTURE_BYTES+1)<=MAX_ALL_FIXTURE_BYTES,'Only small preserved synthetic fixture files')
  if expected_events is not None:require({row['test_id']for row in receipt['test_events']if row.get('outcome')=='passed'}==set(expected_events),'All prospective method identities pass')
 return dict(scope_passed=True,tests_passed=passed,actual_tests_run=receipt['tests_run'],model_tests=expected_model,owner_tests=expected_owner,native_RHS=0,native_restore_performed=False,field_admission_granted=False)
