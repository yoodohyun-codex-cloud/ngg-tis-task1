"""Pure source discovery and synthetic47 accounting, no model or data imports."""
import ast
from pathlib import Path
SUITES=('test_cached_metrics','test_fine_fields','test_fine_inputs','test_fine_post','test_fine_screen_contract','test_fine_solver','test_physical_overlap','test_physical_projector','test_provisional_field','test_screen_metrics')
MODEL_COUNTS=(2,2,5,7,1,3,5,10,5,7)
EXCLUDED=frozenset(('root-admission.json','synthetic-test-receipt.json','tests-receipt.json'))
def require(ok,message):
 if not ok:raise ValueError(message)
def test_methods(path):
 tree=ast.parse(Path(path).read_text(),filename=str(path));return[node.name+'.'+method.name for node in tree.body if isinstance(node,ast.ClassDef)for method in node.body if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))and method.name.startswith('test_')]
def source_paths(directory):
 directory=Path(directory);require(directory.is_dir()and not directory.is_symlink(),'Canonical actual source directory');return sorted(p for p in directory.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in EXCLUDED)
def validate_test_receipt(receipt,expected_model,expected_owner,model_sources,expected_events=None):
 require(receipt.get('kind')=='actual_manufactured_MMS_overlay_projection_contracts_only','Tiny manufactured/source contracts only')
 require(receipt.get('model_source_sha256')==model_sources and receipt.get('source_sha256')==model_sources,'Complete canonical source inventory must match the future fine-field contract')
 require(receipt.get('model_source_test_count')==expected_model==47 and receipt.get('suites')==list(SUITES),'Exactly47 frozen model test definitions')
 for key in('native_RHS','native_field_reads','native_eigen_solves','native_full_field_exports'):require(type(receipt.get(key))is int and receipt[key]==0,'No native research work '+key)
 for key in('native_Q_loaded','native_eigen_performed','field_admission_granted','candidate_adopted'):require(receipt.get(key)is False,'Manufactured tests cannot admit or adopt a native field '+key)
 require(receipt.get('forbidden_field_calls')==[]and receipt.get('native_IO_attempts')==[],'Synthetic scope forbids native input/cache/field APIs even if a test catches the exception')
 require(type(receipt.get('tests_run'))is int and 0<=receipt['tests_run']<=expected_model+expected_owner,'Actual total execution count')
 require(receipt.get('expected_total_tests')==expected_model+expected_owner,'Prospectively counted combined tests, never a fabricated run count')
 passed=receipt.get('status')=='passed'
 if passed:
  require(receipt['tests_run']==receipt['expected_total_tests']and receipt.get('model_tests_run')==expected_model and receipt.get('owner_tests_run')==expected_owner,'Every principal and separate owner test actually executed')
  require(all(receipt.get(key)==0 for key in('tests_failed','tests_errors','tests_skipped')),'All tests pass without errors, failures or skips')
  if expected_events is not None:require({row['test_id']for row in receipt['test_events']if row.get('outcome')=='passed'}==set(expected_events),'Every prospectively discovered method must actually pass')
 return dict(scope_passed=True,tests_passed=passed,actual_tests_run=receipt['tests_run'],model_tests=expected_model,owner_tests=expected_owner,native_RHS=0,field_admission_granted=False)
