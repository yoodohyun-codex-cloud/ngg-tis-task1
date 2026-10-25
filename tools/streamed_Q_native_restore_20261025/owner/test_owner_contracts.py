"""Pure metadata/shape fixtures, no scientific data or arrays."""
import unittest
from owner_contracts import validate_summary,validate_cached_gates,validate_MFG,fixture_elements

def gates():
 limits=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
 return dict(passed=True,passivity_passed=True,physical_gates=dict(passed=True,metrics={k:dict(passed=True,limit=v,value=0.)for k,v in limits.items()}),actual_new_RHS=0,iterations=0,matvec_count=0,new_Krylov_calls=0,reused_published_baseline_surface=True,modal_restore_passed=True,modal_restore_relative_error=1e-12,modal_restore_limit=2e-7,stored_source_current_restore_passed=True,stored_power_restore_comparison=dict(passed=True))
def summary():
 rows=[dict(frequency_Hz=f,active_output=i,native_Q_read=True,whole_Q_loaded=False,Q_closed_and_profiles_released_before_error_reduction=True,field_reconstruction_saved=False,new_PDE_RHS=0,new_Krylov_calls=0,new_eigen_solves=0,new_angular_evaluations=0,field_error=dict(passed=True),candidate_adopted=False)for i,f in enumerate((2000,2010))]
 return dict(status='two_cached_native_carriers_streamed_Q_restore_computed_unadopted',completed_cached_native_responses=2,actual_native_E_reconstructions=2,actual_native_field_comparisons=2,actual_new_PDE_RHS=0,actual_new_Krylov_calls=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,new_native_phi_or_E_archives=0,new_Q_archives=0,frequencies_Hz=[2000,2010],actual_native_Q_read=True,whole_Q_loaded=False,full_Q_materialized=False,complex_Q_materialized=False,responses=rows,native_restore_verification_passed=True,phase_fit=False,gauge_fit=False,original_results_overwritten=False,full_mesh_convergence=False,experimental_validation=False,physiological_activation_or_safety_claim=False,candidate_adopted=False,Windows_saved_verified=False,same_physical_coordinates_and_grid_verified=True,inherited_holds=dict(old_independent_5percent_interface_failures_preserved=True))
class CachedStreamOwnerContracts(unittest.TestCase):
 def test_completed_comparison_retains_failed_field_equivalence_without_adoption(self):
  s=summary();self.assertTrue(validate_summary(s)['native_field_equivalence_passed']);s['responses'][1]['field_error']['passed']=False;s['native_restore_verification_passed']=False
  self.assertFalse(validate_summary(s)['native_field_equivalence_passed'])
  s['native_restore_verification_passed']=True
  with self.assertRaises(ValueError):validate_summary(s)
 def test_hidden_solve_fullQ_or_duplicate_native_export_cannot_pass(self):
  for key,value in(('actual_new_PDE_RHS',1),('actual_new_Krylov_calls',1),('full_Q_materialized',True),('new_native_phi_or_E_archives',1),('actual_new_angular_evaluations',1)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_all_original_cached_gates_and_no_fallback_are_required(self):
  self.assertTrue(validate_cached_gates(gates())['passed'])
  for key,value in(('actual_new_RHS',1),('passivity_passed',False),('modal_restore_relative_error',3e-7),('stored_source_current_restore_passed',False)):
   p=gates();p[key]=value
   with self.assertRaises(ValueError):validate_cached_gates(p)
  p=gates();p['physical_gates']['metrics']['relative_algebraic_residual']['limit']=1e-5
  with self.assertRaises(ValueError):validate_cached_gates(p)
 def test_bounded_manufactured_arrays_cannot_allocate_native_field_or_fullQ(self):
  self.assertEqual(fixture_elements((5,3)),15)
  for shape in((793848,3),(8184,8184),(False,4)):
   with self.assertRaises(ValueError):fixture_elements(shape)
 def test_actual_local_MFG_source_and_zero_native_activity_are_mandatory(self):
  refs={'canonical/model.py':'a'*64};r=dict(status='passed',model_source_sha256=refs,model_source_test_count=2,model_tests_run=2,owner_tests_run=5,tests_run=7,expected_total_tests=7,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loaded=False,native_field_reads=0,field_admission_granted=False,scientific_API_spy_calls=[])
  self.assertTrue(validate_MFG(r,refs,2,5)['passed']);r['native_Q_loaded']=True
  with self.assertRaises(ValueError):validate_MFG(r,refs,2,5)
if __name__=='__main__':unittest.main()
