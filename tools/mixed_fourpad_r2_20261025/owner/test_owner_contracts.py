"""Synthetic accounting fixtures, never scientific data or numerical solves."""
import unittest
from owner_contracts import validate_mixed_summary
def fixture():return dict(status='mixed_fourpad_screen_computed_unadopted',completed_conditions=4,actual_new_driven_RHS=4,actual_new_metric_evaluations=2,actual_alias_conditions=2,new_eigen_solves=0)
class MixedAccounting(unittest.TestCase):
 def test_exact_new_work_and_aliases_are_distinct(self):self.assertTrue(validate_mixed_summary(fixture())['passed'])
 def test_extra_solve_or_repeated_control_count_rejected(self):
  for key,value in(('actual_new_driven_RHS',8),('actual_alias_conditions',0),('new_eigen_solves',1)):
   data=fixture();data[key]=value
   with self.assertRaises(ValueError):validate_mixed_summary(data)
 def test_partial_metrics_never_claim_complete(self):
  data=fixture();data['actual_new_metric_evaluations']=1
  with self.assertRaises(ValueError):validate_mixed_summary(data)
 def test_exact_status_and_integer_counters_required(self):
  data=fixture();data['status']='prepared_only'
  with self.assertRaises(ValueError):validate_mixed_summary(data)
  data=fixture();data['new_eigen_solves']=False
  with self.assertRaises(ValueError):validate_mixed_summary(data)
if __name__=='__main__':unittest.main()
