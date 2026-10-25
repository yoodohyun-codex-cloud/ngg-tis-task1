"""Pure synthetic accounting and already-audited ownership-scope fixtures."""
import unittest
from unittest.mock import patch
import resource_scope
from owner_contracts import validate_test_receipt,SUITES
def fixture():return dict(kind='actual_manufactured_MMS_overlay_projection_contracts_only',suites=list(SUITES),source_sha256={'canonical/source.py':'a'*64},model_source_sha256={'canonical/source.py':'a'*64},model_source_test_count=47,status='passed',tests_run=52,expected_total_tests=52,model_tests_run=47,owner_tests_run=5,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_eigen_solves=0,native_full_field_exports=0,native_Q_loaded=False,native_eigen_performed=False,field_admission_granted=False,candidate_adopted=False,forbidden_field_calls=[],native_IO_attempts=[])
class ScopeContracts(unittest.TestCase):
 def test_complete_small_fixture_receipt_never_admits_a_field_run(self):self.assertFalse(validate_test_receipt(fixture(),47,5,fixture()['model_source_sha256'])['field_admission_granted'])
 def test_field_work_or_false_count_cannot_be_a_success(self):
  for key,value in(('native_RHS',2),('native_Q_loaded',True),('field_admission_granted',True),('tests_run',51),('tests_skipped',1)):
   item=fixture();item[key]=value
   with self.assertRaises(ValueError):validate_test_receipt(item,47,5,item['model_source_sha256'])
 def test_failed_assertions_remain_a_publishable_failure(self):
  item=fixture();item.update(status='failed',tests_failed=1)
  self.assertFalse(validate_test_receipt(item,47,5,item['model_source_sha256'])['tests_passed'])
class ResearchRSSScopeContracts(unittest.TestCase):
 def test_other_research_families_count_once_but_framework_does_not(self):
  def row(pid,parent,tick,argv,rss):return dict(pid=pid,ppid=parent,start_ticks=tick,argv=argv,cwd='/opt/framework',uid=0,rss_bytes=rss)
  rows=[row(10,1,100,['python'],10),row(20,1,200,['python','/dev/shm/task1-browser/source/serve.py'],20),row(21,20,201,['chrome'],30),row(30,1,300,['framework'],40)]
  members,audit,total=resource_scope.classify(rows,{10:100});self.assertEqual(set(members),{10,20,21});self.assertEqual(total,60);self.assertFalse(next(r for r in audit if r['pid']==30)['research_owned'])
 def test_dead_registry_is_ignored_and_live_missing_RSS_fails_closed(self):
  row=dict(pid=10,ppid=1,start_ticks=100,argv=['python'],cwd='/opt/framework',uid=0,rss_bytes=10);registered=[dict(pid=404,start_ticks=999,registry='retired')]
  def gone(pid):
   if pid==404:raise FileNotFoundError('dead PID')
   return 100
  with patch.object(resource_scope,'collect_processes',return_value=([row],[])),patch.object(resource_scope,'registry_identities',return_value=registered):
   self.assertEqual(resource_scope.observe({10:100},gone)['members'],{10:100})
   with self.assertRaises(ValueError):resource_scope.observe({10:100},lambda pid:100 if pid==10 else 999)
if __name__=='__main__':unittest.main()
