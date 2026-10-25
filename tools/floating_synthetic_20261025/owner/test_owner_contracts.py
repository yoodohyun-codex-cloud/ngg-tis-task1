"""Pure synthetic scope fixtures; no original data or scientific import."""
import copy,unittest
from unittest.mock import patch
import resource_scope
from owner_contracts import validate_test_receipt,SUITES,REQUIRED_CONTROLS

def fixture():return dict(kind='actual_small_synthetic_matrix_algebra_only',suites=list(SUITES),source_sha256={'canonical/source.py':'a'*64},status='passed',tests_run=15,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_Q_loaded=False,native_eigen_performed=False,field_admission_granted=False,forbidden_field_calls=[],test_events=[{'test_id':'synthetic.'+name,'outcome':'passed'}for name in REQUIRED_CONTROLS])
class ScopeContracts(unittest.TestCase):
 def test_complete_small_matrix_receipt_never_admits_a_field_run(self):self.assertFalse(validate_test_receipt(fixture(),15,fixture()['source_sha256'])['field_admission_granted'])
 def test_field_work_or_false_count_cannot_be_a_success(self):
  for key,value in(('native_RHS',2),('native_Q_loaded',True),('field_admission_granted',True),('tests_run',14),('tests_skipped',1)):
   item=fixture();item[key]=value
   with self.assertRaises(ValueError):validate_test_receipt(item,15,item['source_sha256'])
 def test_assertion_failures_remain_publishable_failures_not_a_pass(self):
  item=fixture();item.update(status='failed',tests_failed=1)
  self.assertFalse(validate_test_receipt(item,15,item['source_sha256'])['tests_passed'])
class ResearchRSSScopeContracts(unittest.TestCase):
 def test_other_research_families_count_once_but_framework_does_not(self):
  def row(pid,parent,tick,argv,rss):return dict(pid=pid,ppid=parent,start_ticks=tick,argv=argv,cwd='/opt/framework',uid=0,rss_bytes=rss)
  records=[row(10,1,100,['python'],10),row(20,1,200,['python','/dev/shm/task1-browser/source/serve.py'],20),row(21,20,201,['chrome'],30),row(30,1,300,['unrelated-framework'],40),row(40,1,400,['orphan'],50)]
  members,audit,total=resource_scope.classify(records,{10:100},registered=[dict(pid=40,start_ticks=399,registry='stale')])
  self.assertEqual(set(members),{10,20,21});self.assertEqual(total,60);self.assertFalse(next(r for r in audit if r['pid']==30)['research_owned'])
 def test_observe_ignores_dead_registry_but_rejects_live_missing_RSS(self):
  record=dict(pid=10,ppid=1,start_ticks=100,argv=['python'],cwd='/opt/framework',uid=0,rss_bytes=10)
  registered=[dict(pid=404,start_ticks=999,registry='retired-registration')]
  def gone(pid):
   if pid==404:raise FileNotFoundError('dead PID')
   return 100
  with patch.object(resource_scope,'collect_processes',return_value=([record],[])),patch.object(resource_scope,'registry_identities',return_value=registered):
   self.assertEqual(resource_scope.observe({10:100},gone)['members'],{10:100})
   with self.assertRaises(ValueError):resource_scope.observe({10:100},lambda pid:100 if pid==10 else 999)
if __name__=='__main__':unittest.main()
