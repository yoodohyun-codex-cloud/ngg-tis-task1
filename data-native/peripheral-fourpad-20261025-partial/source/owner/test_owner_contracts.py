"""Small metadata fixtures; no physical geometry, masks, PDE or arrays."""
import unittest
from owner_contracts import IDS,prepared_counts
def fixture(blocked=()):
 rows=[]
 for i,cid in enumerate(IDS):
  row=dict(candidate_id=cid,status='source_recipe_geometry_ready_root_selection_pending',reuse_first8_case_id=cid if i<2 else None,mask_path=cid+'.csv',mask_sha256='a'*64)
  if i in blocked:row.update(status='recipe_blocked',blocker='synthetic exact-orbit/connectivity failure',mask_path=None)
  rows.append(row)
 return dict(candidates=rows)
class ProspectiveCounts(unittest.TestCase):
 def test_all_ready_is_exact_six_new_RHS_and_three_metrics(self):
  c=prepared_counts(fixture());self.assertEqual((c['expected_completed_conditions'],c['expected_new_driven_RHS'],c['expected_new_metric_evaluations']),(5,6,3))
 def test_one_blocked_preserves_reason_and_selects_remaining_before_execution(self):
  c=prepared_counts(fixture((2,)));self.assertEqual((c['expected_completed_conditions'],c['expected_new_driven_RHS'],c['expected_new_metric_evaluations']),(4,4,2));self.assertEqual(c['recipe_blockers'][0]['candidate_id'],IDS[2]);self.assertFalse(c['force_blocked_shape'])
 def test_zero_ready_does_not_admit_any_new_PDE(self):
  c=prepared_counts(fixture((2,3,4)));self.assertFalse(c['permits_new_PDE']);self.assertEqual(c['expected_new_driven_RHS'],0);self.assertEqual(c['expected_control_alias_conditions'],2)
 def test_blocked_control_and_missing_ready_mask_are_rejected(self):
  with self.assertRaises(ValueError):prepared_counts(fixture((0,)))
  c=fixture();c['candidates'][2]['mask_path']=None
  with self.assertRaises(ValueError):prepared_counts(c)
if __name__=='__main__':unittest.main()
