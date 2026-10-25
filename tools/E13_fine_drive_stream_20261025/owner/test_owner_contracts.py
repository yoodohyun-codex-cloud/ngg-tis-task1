"""Pure finite baseline/ratio/MFG/resource fixtures; no dataset or I/O."""
import copy,unittest
from owner_contracts import physical_forecast,publication_forecast,fixture_elements,validate_MFG,validate_summary

def summary():
 return dict(status='e13_fine_streamed_allocation_complete_unadopted',completed_conditions=3,baseline_verification_conditions=1,actual_new_metric_evaluations=2,actual_directional_metric_evaluations=3,duplicate_baseline_arrays=0,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,baseline_agreement_passed=True,baseline_multiplier=1.,ratio_multipliers=[.8,1.25],baseline_saved_float_maps=['AM_max2074','carrier_RMS','Jtotal_vector_RMS'],unavailable_saved_float_maps=['AM_x','AM_y','AM_z','carrier0_RMS','carrier1_RMS'],baseline_scalar_summary_count=8,candidate_adopted=False,original_results_overwritten=False,output_artifacts=[])
def mfg():
 events=[dict(test_id='synthetic.'+str(i),outcome='passed')for i in range(4)]
 return dict(schema='task1-E13-fine-drive-stream-manufactured-tests-v1',status='passed',model_source_sha256={'synthetic.py':'a'*64},model_source_test_count=2,model_tests_run=2,owner_tests_run=2,tests_run=4,expected_total_tests=4,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0,native_Q_loaded=False,field_admission_granted=False,scientific_API_spy_calls=[],native_IO_attempts=[],test_events=events)
class DriveOwnerContracts(unittest.TestCase):
 def test_baseline_QA_and_two_metrics_are_distinct_from_new_field_work(self):
  out=validate_summary(summary());self.assertEqual(out['actual_directional_metric_evaluations'],3);self.assertEqual(out['new_PDE_RHS'],0)
 def test_failed_baseline_wrong_ratios_duplicate_baseline_or_hidden_field_work_blocks(self):
  for key,value in(('baseline_agreement_passed',False),('baseline_multiplier',.8),('ratio_multipliers',[1.,.8]),('duplicate_baseline_arrays',1),('baseline_saved_float_maps',['AM_max2074']),('unavailable_saved_float_maps',[]),('baseline_scalar_summary_count',3),('completed_conditions',2),('new_PDE_RHS',1),('new_Q_loads',1),('candidate_adopted',True)):
   row=summary();row[key]=value
   with self.assertRaises(ValueError):validate_summary(row)
 def test_actual_complete_unique_test_events_before_native_access(self):
  row=mfg();ids=[x['test_id']for x in row['test_events']];self.assertTrue(validate_MFG(row,row['model_source_sha256'],2,2,ids)['passed'])
  for key,value in(('tests_errors',1),('tests_skipped',1),('native_field_reads',1),('scientific_API_spy_calls',['Q']),('native_IO_attempts',['read'])):
   row=mfg();row[key]=value
   with self.assertRaises(ValueError):validate_MFG(row,row['model_source_sha256'],2,2,ids)
  row=mfg();row['test_events'][1]['test_id']=row['test_events'][0]['test_id']
  with self.assertRaises(ValueError):validate_MFG(row,row['model_source_sha256'],2,2,ids)
 def test_NUM_and_complete_PUB_forecasts_count_different_components(self):
  self.assertEqual(physical_forecast(7600000000,40000000),7895000000)
  self.assertEqual(publication_forecast(7600000000,40000000),7905000000)
  self.assertGreater(physical_forecast(7720000000,40000000),8000000000)
  self.assertGreater(publication_forecast(7710000000,40000000),8000000000)
 def test_negative_or_bool_bytes_cannot_shrink_resource_forecast(self):
  for values in((-1,0),(0,False)):
   with self.assertRaises(ValueError):physical_forecast(*values)
   with self.assertRaises(ValueError):publication_forecast(*values)
 def test_small_manufactured_shape_limit_cannot_admit_native_or_Q_arrays(self):
  self.assertEqual(fixture_elements((128,3)),384);self.assertEqual(fixture_elements(65536),65536)
  for value in((793848,3),(8184,8184),(-1,),True):
   with self.assertRaises(ValueError):fixture_elements(value)
if __name__=='__main__':unittest.main()
