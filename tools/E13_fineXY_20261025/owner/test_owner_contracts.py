"""Small metadata-only owner contracts; no native files/arrays or model APIs."""
import unittest
from owner_contracts import fixture_elements,owned_auxiliary_bytes,validate_MFG,validate_physical_proof,validate_summary

def summary():
 return dict(status='two_E13_matched97_metric_cases_and_physical_overlap_computed_unadopted',candidates=[{}, {}, {}],new_E13_metric_cases=[dict(grid_variant='XY102-Z97'),dict(grid_variant='XY100-Z97')],actual_new_driven_RHS=2,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=2,actual_full_angular_evaluations=1,actual_SC4_only_angular_evaluations=1,actual_repeated_original_bulk_angular_evaluations=0,actual_duplicate_full_coarse_scalar_archives=0,actual_immutable_fine_B0_aliases=1,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0,Q_resident_during_postprocessing=False,originals_overwritten=False,candidate_adopted=False,same_grid_fine_design_comparisons=dict(primary='Original coarse B0',secondary='FineB0'),holds=dict(old_independent_5percent_interface_failures_preserved=True,prior_fine14_of18_and16_of18_failures_preserved=True,full_convergence=False,physiological_activation_or_safety_claim=False,experimental_validation=False,candidate_adopted=False))

def proof(new=0):
 limits=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
 return dict(passed=True,passivity_passed=True,physical_gates=dict(passed=True,metrics={k:dict(value=0.,limit=v,passed=True)for k,v in limits.items()}),actual_new_RHS=new,reused_published_baseline_surface=not bool(new),iterations=0,matvec_count=0,new_Krylov_calls=0,modal_restore_relative_error=1e-12,modal_restore_limit=2e-7)

class E13OwnerContracts(unittest.TestCase):
 def test_two_new_fine_only_and_original_bulk_baseline_work_cannot_repeat(self):
  self.assertTrue(validate_summary(summary())['passed'])
  for key,value in(('actual_new_driven_RHS',3),('actual_new_coarse_driven_RHS',1),('actual_control_RHS_repeated',1),('actual_repeated_original_bulk_angular_evaluations',1),('actual_immutable_fine_B0_aliases',0),('actual_full_angular_evaluations',2)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_old_failures_and_unadopted_status_are_never_cleared(self):
  s=summary();s['holds']['prior_fine14_of18_and16_of18_failures_preserved']=False
  with self.assertRaises(ValueError):validate_summary(s)
  s=summary();s['candidate_adopted']=True
  with self.assertRaises(ValueError):validate_summary(s)
 def test_cached_coarse_gate_cannot_relax_modal_or_use_fallback(self):
  self.assertTrue(validate_physical_proof(proof(),0)['passed']);self.assertTrue(validate_physical_proof(proof(1),1)['passed'])
  for key,value in(('actual_new_RHS',1),('iterations',1),('new_Krylov_calls',1),('modal_restore_relative_error',3e-7),('passivity_passed',False)):
   p=proof();p[key]=value
   with self.assertRaises(ValueError):validate_physical_proof(p,0)
 def test_both_task_namespaces_and_small_auxiliary_bytes_are_counted(self):
  sizes={'main':1000,'aux':14341};result=owned_auxiliary_bytes(lambda p:sizes[p],{'/dev/shm':['main'],'/tmp':['aux']});self.assertEqual(result['total_bytes'],15341);self.assertEqual(result['by_namespace_bytes']['/tmp'],14341)
  with self.assertRaises(ValueError):owned_auxiliary_bytes(lambda p:0,{'/dev/shm':[]})
 def test_source_bound_zero_native_MFG_and_array_bounds_are_required(self):
  sources={'canonical/model.py':'a'*64};r=dict(status='passed',model_source_sha256=sources,model_source_test_count=40,model_tests_run=40,owner_tests_run=5,tests_run=45,expected_total_tests=45,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loaded=False,native_field_reads=0,field_admission_granted=False,scientific_API_spy_calls=[])
  self.assertTrue(validate_MFG(r,sources,40,5)['passed']);r['native_Q_loaded']=True
  with self.assertRaises(ValueError):validate_MFG(r,sources,40,5)
  self.assertEqual(fixture_elements((4,3)),12)
  with self.assertRaises(ValueError):fixture_elements((8184,8184))

if __name__=='__main__':unittest.main()
