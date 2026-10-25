"""Small metadata fixtures only; no real data, source imports or arrays."""
import copy,unittest
from owner_contracts import validate_summary,validate_MFG,fixture_elements
def summary():
 proofs=[dict(frequency_Hz=f,passed=True,passivity_passed=True,physical_gates=dict(passed=True),actual_new_RHS=1)for f in(2000,2010)]
 rows=[dict(candidate_id=c,control_alias=True,new_PDE_RHS=0,new_angular_metric_evaluations=0)for c in('B0','P23')]+[dict(candidate_id='new',control_alias=False,source_physics_proofs=proofs)]
 return dict(status='single_centroid_area_matched_ellipse_screen_computed_unadopted',completed_conditions=3,actual_new_driven_RHS=2,actual_new_angular_metric_evaluations=1,actual_immutable_control_aliases=2,actual_control_RHS_repeated=0,actual_control_angular_metrics_repeated=0,new_eigen_solves=0,candidates=rows,Q_resident_during_metrics=False,originals_overwritten=False,candidate_adopted=False,holds=dict(old_13_of_14_XY_contact_failures_preserved=True,fractional_contact_and_edge_peak_uncertainty=True,full_convergence=False))
def mfg():return dict(status='passed',model_source_sha256={'canonical/model.py':'a'*64},model_source_test_count=2,model_tests_run=2,owner_tests_run=4,tests_run=6,expected_total_tests=6,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loaded=False,native_field_reads=0,field_admission_granted=False,scientific_API_spy_calls=[])
class FiniteEllipseContracts(unittest.TestCase):
 def test_exact_two_new_and_two_alias_counts_pass(self):self.assertTrue(validate_summary(summary())['passed'])
 def test_extra_solve_control_work_or_resident_Q_blocks(self):
  for key,value in(('actual_new_driven_RHS',3),('actual_control_RHS_repeated',1),('actual_control_angular_metrics_repeated',1),('Q_resident_during_metrics',True)):
   value_summary=summary();value_summary[key]=value
   with self.assertRaises(ValueError):validate_summary(value_summary)
  value_summary=summary();value_summary['candidates'][0]['new_PDE_RHS']=1
  with self.assertRaises(ValueError):validate_summary(value_summary)
 def test_failed_physics_or_dropped_hold_cannot_pass(self):
  value_summary=summary();value_summary['candidates'][2]['source_physics_proofs'][0]['passed']=False
  with self.assertRaises(ValueError):validate_summary(value_summary)
  value_summary=summary();value_summary['holds']['old_13_of_14_XY_contact_failures_preserved']=False
  with self.assertRaises(ValueError):validate_summary(value_summary)
 def test_failed_skipped_changed_source_or_native_test_work_blocks(self):
  value=mfg();self.assertTrue(validate_MFG(value,value['model_source_sha256'],2,4)['passed'])
  for key,bad in(('tests_failed',1),('tests_skipped',1),('model_source_sha256',{}),('native_Q_loaded',True),('scientific_API_spy_calls',['cache'])):
   value=mfg();value[key]=bad
   with self.assertRaises(ValueError):validate_MFG(value,{'canonical/model.py':'a'*64},2,4)
 def test_manufactured_array_cap_precedes_native_size_allocation(self):
  self.assertEqual(fixture_elements((4,5)),20)
  for shape in((7860,),(7860,7860),(False,4),(-1,4)):
   with self.assertRaises(ValueError):fixture_elements(shape)
if __name__=='__main__':unittest.main()
