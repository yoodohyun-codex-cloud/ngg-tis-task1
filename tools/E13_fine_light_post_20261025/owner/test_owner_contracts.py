"""Pure synthetic metadata and bounded protected fixtures; no actual datasets."""
import unittest
from owner_contracts import validate_summary,validate_MFG,fixture_elements,owned_auxiliary_bytes,CANDIDATE_ID

def summary():
 row=dict(candidate_id=CANDIDATE_ID,requested_probes=40,calculated_probes=38,unavailable_probes=2,strict_same_layer_bracket_available_probes=28,same_layer_extrapolated_probes=10,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,actual_threshold_subsets=48,candidate_adopted=False)
 return dict(status='E13_fine_cached_highvolume_and40probe_postbatch_computed_unadopted',actual_new_PDE_RHS=0,actual_new_Q_loads=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,old_case_repeats=0,completed_native_geometries=1,candidates=[row],requested_probes=40,calculated_probes=38,unavailable_probes=2,strict_same_layer_bracket_available_probes=28,same_layer_extrapolated_probes=10,expected_threshold_subsets_per_geometry=48,actual_threshold_subsets=48,original_statistics_recomputed=False,original_results_overwritten=False,old600probe_predictions_preserved=True,hardware_loading_validated=False,experimental_validation=False,full_convergence=False,physiological_activation_or_safety_claim=False,candidate_adopted=False,Windows_saved_verified=False,inherited_holds=dict(old_independent_5percent_interface_failures_preserved=True,prior_fine14_of18_and16_of18_failures_preserved=True,SC_XY_contact_edge_material_uncertainty_preserved=True),E13_publication_recovery=dict(original_numerical_owner_status='failed_preserved',old_numerical_owner_rewritten=False,recovery_only_not_new_numerical_success=True))
def mfg():return dict(status='passed',model_source_sha256={'canonical/model.py':'a'*64},model_source_test_count=2,model_tests_run=2,owner_tests_run=7,tests_run=9,expected_total_tests=9,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loaded=False,native_field_reads=0,field_admission_granted=False,scientific_API_spy_calls=[])
class E13FineLightOwnerContracts(unittest.TestCase):
 def test_actual_partial_availability_and_strict_extrap_counts_remain_separate(self):self.assertTrue(validate_summary(summary(),1)['passed'])
 def test_only_one_E13fine_case_and_48subsets_no_hidden_work_or_repeat(self):
  for key,value in(('actual_new_PDE_RHS',1),('actual_new_Q_loads',1),('actual_new_angular_evaluations',1),('old_case_repeats',1),('completed_native_geometries',2),('actual_threshold_subsets',47),('strict_same_layer_bracket_available_probes',38)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s,1)
  s=summary();s['candidates'][0]['candidate_id']='coarse-E13'
  with self.assertRaises(ValueError):validate_summary(s,1)
  s=summary();s['candidates'][0]['calculated_probes']=40
  with self.assertRaises(ValueError):validate_summary(s,1)
 def test_prior_failure_recovery_and_contact_holds_cannot_be_relabelled(self):
  for key in('old_independent_5percent_interface_failures_preserved','prior_fine14_of18_and16_of18_failures_preserved','SC_XY_contact_edge_material_uncertainty_preserved'):
   s=summary();s['inherited_holds'][key]=False
   with self.assertRaises(ValueError):validate_summary(s,1)
  s=summary();s['E13_publication_recovery']['original_numerical_owner_status']='passed'
  with self.assertRaises(ValueError):validate_summary(s,1)
  s=summary();s['hardware_loading_validated']=True
  with self.assertRaises(ValueError):validate_summary(s,1)
 def test_manufactured_FFT_vector_allowed_native_field_and_Q_shape_rejected(self):
  self.assertEqual(fixture_elements(65536),65536);self.assertEqual(fixture_elements((810,5)),4050)
  for shape in((793848,),(7860,7860),(False,4),(-1,4)):
   with self.assertRaises(ValueError):fixture_elements(shape)
 def test_failed_skipped_or_changed_source_MFG_never_admits_real_native_read(self):
  r=mfg();self.assertTrue(validate_MFG(r,r['model_source_sha256'],2,7)['passed'])
  for key,value in(('tests_errors',1),('tests_skipped',1),('model_source_sha256',{}),('native_field_reads',1),('scientific_API_spy_calls',['load'])):
   r=mfg();r[key]=value
   with self.assertRaises(ValueError):validate_MFG(r,{'canonical/model.py':'a'*64},2,7)
 def test_prewarmed_numpy_unique_and_native_size_constructor_bound(self):
  import numpy as np
  self.assertEqual(np.unique([2,1,2]).tolist(),[1,2])
  with self.assertRaises(ValueError):np.arange(65537)
 def test_auxiliary_accounting_includes_tmp_namespace_and_rejects_omission(self):
  sizes={'shm':200,'legacy':14341};result=owned_auxiliary_bytes(sizes.__getitem__,{'/dev/shm':['shm'],'/tmp':['legacy']})
  self.assertEqual(result['total_bytes'],14541);self.assertEqual(result['by_namespace_bytes']['/tmp'],14341)
  with self.assertRaises(ValueError):owned_auxiliary_bytes(sizes.__getitem__,{'/dev/shm':['shm']})
if __name__=='__main__':unittest.main()
