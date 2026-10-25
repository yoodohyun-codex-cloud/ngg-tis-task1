"""Tiny metadata-only scope fixtures; the published15 MNA tests are reused."""
import unittest
from owner_contracts import validate_summary,FLOATING

def fixture():
 controls=[dict(actual_new_RHS=0,actual_new_metric_evaluations=0,no_field_reconstruction=True,no_angular_recalculation=True)for _ in range(2)]
 new=dict(candidate_id=FLOATING,actual_new_RHS=2,actual_new_metric_evaluations=1,Q_or_profiles_or_solver_resident_during_metrics=False,actual_hardware_wiring_claimed=False,source_physics_proofs=[dict(passed=True,pair_pad_indices=[[0,2],[1,3]],driven_output=i,source_output_order_preserved=True)for i in(0,1)])
 return dict(status='hypothetical_floating_P23_comparison_computed_unadopted',actual_new_driven_RHS=2,actual_new_metric_evaluations=1,immutable_common_control_aliases=2,completed_conditions=3,new_common_return_RHS=0,new_B0_RHS=0,new_eigen_solves=0,actual_hardware_wiring_claimed=False,physical_mask_changed=False,candidate_adopted=False,common_return_and_hypothetical_floating_separately_named=True,spec=dict(physical_pairs=[[0,2],[1,3]],frequency_output_assignment=[[2000,0],[2010,1]]),candidates=controls+[new])
class FloatingAccounting(unittest.TestCase):
 def test_exact_hypothetical_work_and_aliases_pass(self):self.assertTrue(validate_summary(fixture())['passed'])
 def test_repeated_control_or_extra_RHS_rejected(self):
  for key,value in(('actual_new_driven_RHS',4),('new_common_return_RHS',2),('new_eigen_solves',1)):
   s=fixture();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_changed_wiring_assignment_or_hardware_claim_rejected(self):
  s=fixture();s['actual_hardware_wiring_claimed']=True
  with self.assertRaises(ValueError):validate_summary(s)
  s=fixture();s['spec']['physical_pairs']=[[0,1],[2,3]]
  with self.assertRaises(ValueError):validate_summary(s)
 def test_Q_resident_metrics_or_false_physics_proof_rejected(self):
  s=fixture();s['candidates'][-1]['Q_or_profiles_or_solver_resident_during_metrics']=True
  with self.assertRaises(ValueError):validate_summary(s)
  s=fixture();s['candidates'][-1]['source_physics_proofs'][1]['passed']=False
  with self.assertRaises(ValueError):validate_summary(s)
if __name__=='__main__':unittest.main()
