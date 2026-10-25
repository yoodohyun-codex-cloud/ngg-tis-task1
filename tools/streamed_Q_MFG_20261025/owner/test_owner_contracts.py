"""Pure owner-contract fixtures; no model imports, arrays or input files."""
import unittest
from unittest.mock import patch
import resource_scope
from owner_contracts import validate_test_receipt,validate_admission,fixture_path_allowed,element_count,SUITES,KIND,SCOPE

def fixture():
 return dict(kind=KIND,suites=list(SUITES),source_sha256={'canonical/source.py':'a'*64},model_source_sha256={'canonical/source.py':'a'*64},model_source_test_count=12,status='passed',tests_run=20,expected_total_tests=20,model_tests_run=12,owner_tests_run=8,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_file_reads=0,native_eigen_solves=0,native_full_field_exports=0,native_Q_loaded=False,native_eigen_performed=False,native_restore_performed=False,field_admission_granted=False,candidate_adopted=False,forbidden_field_calls=[],native_IO_attempts=[],IO_audit_installed=True,manufactured_work_counts={k:1 for k in('operator_constructors','metadata_validation_calls','forward_attempts','transpose_attempts','slice_attempts','chunk_visits_started','chunk_visits_completed','operator_receipts')},synthetic_IO=dict(read_opens=3,write_opens=3,maximum_file_bytes=144,total_regular_fixture_bytes=288))
class ScopeContracts(unittest.TestCase):
 def test_complete_tiny_receipt_cannot_admit_native_restore(self):self.assertFalse(validate_test_receipt(fixture(),12,8,fixture()['model_source_sha256'])['field_admission_granted'])
 def test_native_work_count_skip_or_missing_call_blocks_success(self):
  for key,value in(('native_RHS',1),('native_file_reads',1),('native_Q_loaded',True),('native_restore_performed',True),('tests_run',19),('tests_skipped',1)):
   item=fixture();item[key]=value
   with self.assertRaises(ValueError):validate_test_receipt(item,12,8,item['model_source_sha256'])
  item=fixture();item['manufactured_work_counts']['forward_attempts']=0
  with self.assertRaises(ValueError):validate_test_receipt(item,12,8,item['model_source_sha256'])
 def test_failure_remains_publishable_with_honest_actual_count(self):
  item=fixture();item.update(status='failed',tests_run=3,tests_errors=1,model_tests_run=3,owner_tests_run=0)
  self.assertFalse(validate_test_receipt(item,12,8,item['model_source_sha256'])['tests_passed'])
 def test_fixture_paths_and_allocations_have_fixed_limits(self):
  root='/dev/shm/task1-streamed-Q-MFG-20261025-run/synthetic'
  self.assertTrue(fixture_path_allowed(root+'/test-a/x.f64',root));self.assertFalse(fixture_path_allowed('/tmp/x.f64',root));self.assertFalse(fixture_path_allowed(root+'/../escape.f64',root))
  self.assertEqual(element_count((6,17)),102)
  for shape in((8192,8192),(-1,),True,(4097,)):
   with self.assertRaises(ValueError):element_count(shape)
 def test_positive_admission_binds_both_complete_source_maps(self):
  sources={'model.py':'a'*64,'owner.py':'b'*64};model={'model.py':'a'*64}
  item=dict(schema='task1-streamed-Q-MFG-root-admission-v1',status='admitted',root_authorized=True,safe_boundary_confirmed=True,scope=SCOPE,source_sha256=sources,model_source_sha256=model,expected_model_tests=12,expected_owner_tests=8,cpu_limit=4,physical_cap_bytes=8000000000,max_cells=800000,native_file_reads_authorized=False,native_restore_authorized=False,new_PDE_authorized=False,new_eigen_authorized=False,candidate_adoption_authorized=False)
  self.assertTrue(validate_admission(item,sources,model,12,8));item['source_sha256']={'model.py':'a'*64}
  with self.assertRaises(ValueError):validate_admission(item,sources,model,12,8)
 def test_oversize_fixture_or_caught_boundary_violation_blocks_pass(self):
  for key,value in(('maximum_file_bytes',4097),('total_regular_fixture_bytes',65537)):
   item=fixture();item['synthetic_IO'][key]=value
   with self.assertRaises(ValueError):validate_test_receipt(item,12,8,item['model_source_sha256'])
  item=fixture();item['native_IO_attempts']=[{'path':'/native/Q.f64'}]
  with self.assertRaises(ValueError):validate_test_receipt(item,12,8,item['model_source_sha256'])
class ResearchRSSScopeContracts(unittest.TestCase):
 def test_other_research_families_count_once_without_framework(self):
  def row(pid,parent,tick,argv,rss):return dict(pid=pid,ppid=parent,start_ticks=tick,argv=argv,cwd='/opt/framework',uid=0,rss_bytes=rss)
  rows=[row(10,1,100,['python'],10),row(20,1,200,['python','/dev/shm/task1-browser/source/serve.py'],20),row(21,20,201,['chrome'],30),row(30,1,300,['framework'],40)]
  members,audit,total=resource_scope.classify(rows,{10:100});self.assertEqual(set(members),{10,20,21});self.assertEqual(total,60);self.assertFalse(next(r for r in audit if r['pid']==30)['research_owned'])
 def test_dead_registry_ignored_live_unknown_RSS_blocks(self):
  row=dict(pid=10,ppid=1,start_ticks=100,argv=['python'],cwd='/opt/framework',uid=0,rss_bytes=10);registered=[dict(pid=404,start_ticks=999,registry='retired')]
  def gone(pid):
   if pid==404:raise FileNotFoundError('dead PID')
   return 100
  with patch.object(resource_scope,'collect_processes',return_value=([row],[])),patch.object(resource_scope,'registry_identities',return_value=registered):
   self.assertEqual(resource_scope.observe({10:100},gone)['members'],{10:100})
   with self.assertRaises(ValueError):resource_scope.observe({10:100},lambda pid:100 if pid==10 else 999)
if __name__=='__main__':unittest.main()
