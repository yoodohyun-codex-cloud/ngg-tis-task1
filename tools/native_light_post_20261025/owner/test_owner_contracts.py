"""Pure small metadata/shape fixtures; no actual datasets, imports or arrays."""
import unittest
from owner_contracts import validate_summary,validate_MFG,fixture_elements

def summary():
 rows=[dict(candidate_id=c,requested_probes=40,calculated_probes=38,unavailable_probes=2,strict_same_layer_bracket_available_probes=28,same_layer_extrapolated_probes=10,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,candidate_adopted=False)for c in('fineB0','fineP23')]
 return dict(status='cached_native_highvolume_and40probe_postbatch_computed_unadopted',actual_new_PDE_RHS=0,actual_new_Q_loads=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,completed_native_geometries=2,candidates=rows,requested_probes=80,calculated_probes=76,unavailable_probes=4,strict_same_layer_bracket_available_probes=56,same_layer_extrapolated_probes=20,expected_threshold_subsets_per_geometry=48,original_statistics_recomputed=False,original_results_overwritten=False,old600probe_predictions_preserved=True,hardware_loading_validated=False,experimental_validation=False,full_convergence=False,physiological_activation_or_safety_claim=False,candidate_adopted=False,Windows_saved_verified=False,inherited_holds=dict(old_13_of_14_electrical_failures_per_basis_preserved=True,old_independent_5percent_interface_failures_preserved=True))
def mfg():return dict(status='passed',model_source_sha256={'canonical/model.py':'a'*64},model_source_test_count=2,model_tests_run=2,owner_tests_run=5,tests_run=7,expected_total_tests=7,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loaded=False,native_field_reads=0,field_admission_granted=False,scientific_API_spy_calls=[])
class LightOwnerContracts(unittest.TestCase):
 def test_actual_partial_availability_and_strict_extrap_counts_remain_separate(self):self.assertTrue(validate_summary(summary(),2)['passed'])
 def test_hidden_scientific_work_or_count_relabelling_blocks(self):
  for key,value in(('actual_new_PDE_RHS',1),('actual_new_Q_loads',1),('actual_new_angular_evaluations',1),('strict_same_layer_bracket_available_probes',76)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s,2)
  s=summary();s['candidates'][0]['calculated_probes']=40
  with self.assertRaises(ValueError):validate_summary(s,2)
 def test_dropped_failure_or_loaded_hardware_claim_cannot_pass(self):
  s=summary();s['inherited_holds']['old_13_of_14_electrical_failures_per_basis_preserved']=False
  with self.assertRaises(ValueError):validate_summary(s,2)
  s=summary();s['hardware_loading_validated']=True
  with self.assertRaises(ValueError):validate_summary(s,2)
 def test_manufactured_FFT_vector_allowed_native_field_and_Q_shape_rejected(self):
  self.assertEqual(fixture_elements(65536),65536);self.assertEqual(fixture_elements((810,5)),4050)
  for shape in((793848,),(7860,7860),(False,4),(-1,4)):
   with self.assertRaises(ValueError):fixture_elements(shape)
 def test_failed_or_skipped_or_changed_source_MFG_never_admits_real_native_read(self):
  r=mfg();self.assertTrue(validate_MFG(r,r['model_source_sha256'],2,5)['passed'])
  for key,value in(('tests_errors',1),('tests_skipped',1),('model_source_sha256',{}),('native_field_reads',1),('scientific_API_spy_calls',['load'])):
   r=mfg();r[key]=value
   with self.assertRaises(ValueError):validate_MFG(r,{'canonical/model.py':'a'*64},2,5)
if __name__=='__main__':unittest.main()
