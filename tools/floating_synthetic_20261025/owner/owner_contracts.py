"""Pure scope and source-AST discovery for the finite synthetic review."""
import ast
from pathlib import Path
SUITES=('frozen_test_floating_cem','test_p23_comparison')
REQUIRED_CONTROLS=('test_two_distinct_gauges_and_complex_uniform_shift','test_ground_leak_fault_is_detectable_and_constant_mode_is_rejected','test_both_basis_reduced_vs_independent_full_mna_power_and_inactive_port')

def require(ok,message):
 if not ok:raise ValueError(message)
def test_methods(path):
 tree=ast.parse(Path(path).read_text(),filename=str(path))
 return [node.name+'.'+item.name for node in tree.body if isinstance(node,ast.ClassDef)for item in node.body if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef))and item.name.startswith('test_')]
def proposal_source_names(path,include_frozen=False):
 tree=ast.parse(Path(path).read_text(),filename=str(path));values={}
 for node in tree.body:
  if isinstance(node,ast.Assign):
   for name in node.targets:
    if isinstance(name,ast.Name)and name.id in('FROZEN_SOURCES','OWN_SOURCES'):values[name.id]=ast.literal_eval(node.value)
 require(set(values)=={'FROZEN_SOURCES','OWN_SOURCES'},'Literal frozen proposal source inventory, no field-model call')
 names=tuple(values['FROZEN_SOURCES'])+tuple(values['OWN_SOURCES'])
 return(names,values['FROZEN_SOURCES'])if include_frozen else names
def validate_test_receipt(receipt,expected_tests,source_sha256):
 require(receipt.get('kind')=='actual_small_synthetic_matrix_algebra_only','Never label tiny algebra as a phantom solve')
 require(receipt.get('suites')==list(SUITES)and receipt.get('source_sha256')==source_sha256,'Actual frozen suite and canonical source identities')
 require(receipt.get('native_RHS')==0 and receipt.get('native_field_reads')==0 and receipt.get('native_Q_loaded')is False and receipt.get('native_eigen_performed')is False and receipt.get('field_admission_granted')is False,'Native field/admission work is excluded')
 require(receipt.get('forbidden_field_calls')==[],'No field-model API may be called by synthetic tests')
 require(type(receipt.get('tests_run'))is int and 0<=receipt['tests_run']<=expected_tests,'Actual discovered execution count')
 passed=receipt.get('status')=='passed'
 if passed:
  require(receipt['tests_run']==expected_tests and all(receipt.get(k)==0 for k in('tests_failed','tests_errors','tests_skipped')),'All prospectively counted tests must actually pass without skips')
  successful={row['test_id'].rsplit('.',1)[-1]for row in receipt.get('test_events',[])if row.get('outcome')=='passed'}
  require(set(REQUIRED_CONTROLS)<=successful,'Gauge, deliberate ground-leak and50vs100ohm assertions must actually run and pass')
 return dict(scope_passed=True,tests_passed=passed,actual_tests_run=receipt['tests_run'],native_RHS=0,field_admission_granted=False)
