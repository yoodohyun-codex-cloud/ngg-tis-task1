"""Synthetic metadata-only no-fallback/scope fixtures, no real input reads."""
import unittest
from owner_contracts import validate_restore,validate_summary,validate_MFG

def summary():return dict(status='four_matched97_metric_cases_and_physical_overlap_computed_unadopted',actual_new_driven_RHS=3,actual_reused_fine_B0_2000_RHS=1,actual_new_coarse_driven_RHS=0,actual_new_metric_evaluations=4,actual_full_angular_evaluations=2,actual_SC4_only_angular_evaluations=2,actual_repeated_original_bulk_angular_evaluations=0,actual_duplicate_full_coarse_scalar_archives=0,new_eigen_solves=0,candidates=[{}]*4,Q_resident_during_postprocessing=False,candidate_adopted=False,coarse_common97_bulk_binding=dict(passed=True,bulk_raw_duplicated=False),holds=dict(old_13_of_14_electrical_failures_per_basis_preserved=True,full_convergence=False))
def restore():return dict(passed=True,passivity_passed=True,physical_gates=dict(passed=True,metrics={str(i):{}for i in range(5)}),actual_new_RHS=0,reused_published_baseline_surface=True,restored_modal_relative_error=1e-12,modal_restore_limit=2e-7)
class FineAccounting(unittest.TestCase):
 def test_exact_three_new_RHS_and_cached_restore_pass(self):self.assertTrue(validate_summary(summary())['passed']);self.assertTrue(validate_restore(restore())['passed'])
 def test_fourth_solve_or_old_bulk_rescan_cannot_pass(self):
  for key,value in(('actual_new_driven_RHS',4),('actual_new_coarse_driven_RHS',1),('actual_repeated_original_bulk_angular_evaluations',2),('actual_duplicate_full_coarse_scalar_archives',2)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_restore_failure_or_hidden_fallback_blocks(self):
  for key,value in(('passed',False),('actual_new_RHS',1),('restored_modal_relative_error',3e-7)):
   p=restore();p[key]=value
   with self.assertRaises(ValueError):validate_restore(p)
 def test_failed_first_manufactured_receipt_never_admits_field(self):
  sources={'canonical/model.py':'a'*64};r=dict(status='passed',model_source_sha256=sources,model_source_test_count=47,model_tests_run=47,tests_run=53,expected_total_tests=53,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loaded=False,field_admission_granted=False)
  self.assertTrue(validate_MFG(r,sources,47)['passed']);r.update(status='failed',tests_failed=1)
  with self.assertRaises(ValueError):validate_MFG(r,sources,47)
if __name__=='__main__':unittest.main()
