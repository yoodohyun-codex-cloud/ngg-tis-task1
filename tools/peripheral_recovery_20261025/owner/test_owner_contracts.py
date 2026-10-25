"""Synthetic counter/identity fixtures, not scientific data or PDE tests."""
import unittest
from owner_contracts import validate_recovery_summary
def fixture():
 return dict(status='peripheral_recovery_computed_without_P23_PDE_repeat',completed_conditions=4,actual_new_driven_RHS=2,actual_reused_saved_RHS=2,actual_new_metric_evaluations=2,actual_alias_conditions=2,new_P23_RHS=0,new_P12_RHS=2,new_eigen_solves=0,recipe_blockers=[dict(candidate_id='P24-peripheral-polyomino225')])
class RecoveryAccounting(unittest.TestCase):
 def test_exact_reuse_and_new_work_are_separate(self):self.assertTrue(validate_recovery_summary(fixture())['passed'])
 def test_any_repeated_P23_RHS_is_rejected(self):
  data=fixture();data['new_P23_RHS']=2
  with self.assertRaises(ValueError):validate_recovery_summary(data)
 def test_missing_metrics_and_new_work_mislabeled_as_reuse_are_rejected(self):
  for key,value in(('actual_new_metric_evaluations',1),('actual_new_driven_RHS',4),('actual_reused_saved_RHS',0)):
   data=fixture();data[key]=value
   with self.assertRaises(ValueError):validate_recovery_summary(data)
 def test_blocker_and_integer_counter_identity_are_preserved(self):
  data=fixture();data['recipe_blockers']=[]
  with self.assertRaises(ValueError):validate_recovery_summary(data)
  data=fixture();data['new_P23_RHS']=False
  with self.assertRaises(ValueError):validate_recovery_summary(data)
if __name__=='__main__':unittest.main()
