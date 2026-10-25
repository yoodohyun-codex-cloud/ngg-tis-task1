"""Pure append/resource/MFG fixtures; no actual source, payload or native reads."""
import copy,unittest
from types import SimpleNamespace
from owner_contracts import validate_summary,validate_MFG,fixture_elements,forecast_physical_bytes,MODEL_TEST_COUNT,NEW_ID
from temporary_accounting import counted_bytes

def summary():return dict(schema='task1-native-GUI-append-E13fine-result-v1',status='native_GUI_E13fine_appended_browser_unverified',base_outcome='partial_payload_complete_functional_limit',previous_GUI_complete_success=False,inherited_holds=dict(appended_E13_fine=dict(previous_GUI_partial_failure=dict(publication_outcome='readback_recovered_after_original_publication_timeout'))),previous_payload_recovered_without_old_extraction=True,original_absences_preserved=True,previous_index_missing=dict(reason='never_created_after_functional_limit'),completed_cases=8,old_cases_reused=7,new_native_cases_extracted=1,new_native_candidate=NEW_ID,legacy_reference_cases=4,new_native_section_cases=4,requested_probes=160,new_requested_probes=40,new_high_volume_subsets=48,strict_same_layer_probes=80,extrapolated_probes=80,unavailable_probes=0,old_case_extractions=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_native_statistic_reductions=0,new_stat_reductions=0,new_candidate_rankings=0,old_case_quantitative_values_byte_preserved=True,original_statistics_overwritten=False,old_GUI_pointers_modified=False,browser_validation_performed=False,experimental_validation=False,full_convergence=False,candidate_adopted=False,Windows_saved_verified=False,payload_JSON_bytes=5000000,index_HTML_bytes=5100000)
def mfg(owner=7):
 n=MODEL_TEST_COUNT+owner
 return dict(schema='task1-native-GUI-append-E13fine-manufactured-tests-v1',status='passed',model_source_sha256={'synthetic/model.py':'a'*64},model_source_test_count=MODEL_TEST_COUNT,model_tests_run=MODEL_TEST_COUNT,owner_tests_run=owner,tests_run=n,expected_total_tests=n,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_Q_loaded=False,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0,scientific_API_spy_calls=[],native_IO_attempts=[],field_admission_granted=False,browser_validation_performed=False,negative_fixture_counts={'invalid_admission_before_IO':1},dependencies_initialized_before_mocks=True,IO_audit_installed=True,test_events=[dict(test_id='synthetic.'+str(i),outcome='passed')for i in range(n)])
class Entry:
 def __init__(self,n=None):self.n=n
 def is_file(self):return True
 def stat(self):
  if self.n is None:raise FileNotFoundError('Synthetic vanished sibling')
  return SimpleNamespace(st_size=self.n)
class Directory:
 def __init__(self,children):self.children=children
 def is_file(self):return False
 def rglob(self,_):return iter(self.children)
class AppendOwnerContracts(unittest.TestCase):
 def test_append_keeps_seven_quantitative_records_and_browser_status_separate(self):self.assertFalse(validate_summary(summary())['browser_validation_performed'])
 def test_old_case_reextraction_new_work_or_wrong_probe_scope_blocks(self):
  for key,value in(('previous_GUI_complete_success',True),('base_outcome','complete_success'),('old_cases_reused',6),('new_native_cases_extracted',2),('strict_same_layer_probes',79),('new_Q_loads',1),('old_case_extractions',1),('new_candidate_rankings',1),('old_case_quantitative_values_byte_preserved',False),('old_GUI_pointers_modified',True)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_functional_display_bound_is_fail_preserve_not_omission_or_storage_quota(self):
  for key,value in(('payload_JSON_bytes',8000001),('index_HTML_bytes',8200001)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_all_passed_unique_source_events_and_no_caught_native_IO_are_required(self):
  r=mfg();self.assertTrue(validate_MFG(r,r['model_source_sha256'],7)['passed'])
  for key,value in(('tests_skipped',1),('tests_errors',1),('native_IO_attempts',['read']),('scientific_API_spy_calls',['Q']),('native_Q_loaded',True),('model_source_sha256',{})):
   r=mfg();r[key]=value
   with self.assertRaises(ValueError):validate_MFG(r,{'synthetic/model.py':'a'*64},7)
  r=mfg();r['test_events'][1]['test_id']=r['test_events'][0]['test_id']
  with self.assertRaises(ValueError):validate_MFG(r,r['model_source_sha256'],7)
 def test_disk_output_does_not_hide_actual_tmp_or_relax_8GB_physical_budget(self):
  total=forecast_physical_bytes(7610000000,40000000,240000000,0);self.assertEqual(total,7890000000)
  self.assertGreater(forecast_physical_bytes(7800000000,40000000,240000000,0),8000000000)
  self.assertEqual(forecast_physical_bytes(7610000000+14341,40000000,240000000,0)-total,14341)
  with self.assertRaises(ValueError):forecast_physical_bytes(1,2,3,False)
 def test_manufactured_array_cap_does_not_reinterpret_physical_cell_limit(self):
  self.assertEqual(fixture_elements((96,5)),480);self.assertEqual(fixture_elements(65536),65536)
  for shape in((793848,5),(8184,8184),(-1,),True):
   with self.assertRaises(ValueError):fixture_elements(shape)
 def test_vanished_entry_does_not_erase_other_owned_auxiliary_bytes(self):
  self.assertEqual(counted_bytes(Directory([Entry(13),Entry(),Entry(29)])),42)
  self.assertEqual(counted_bytes(Entry()),0);self.assertEqual(counted_bytes(Entry(14341)),14341)
if __name__=='__main__':unittest.main()
