"""Synthetic completeness fixtures only; no arrays, cached data or solver."""
import copy,unittest
from owner_contracts import validate_consolidation_summary
def fixture():
 rows=[dict(candidate_id='C'+str(i),candidate_adopted=False,probe_prediction=dict(status='calculated_unloaded_only',probe_count=40,probes=[{}for _ in range(40)]))for i in range(15)]
 return dict(status='fifteen_native_geometries_cached_gui_probe_analysis_complete',canonical_native_geometries=15,new_PDE_RHS=0,actual_new_angular_evaluations=0,candidates=rows,provisional_top5=['C'+str(i)for i in range(5)],baseline_id='C0',mandatory_compare_ids=['C1','C2','C3'],reported_local_candidates=[dict(eligible_for_native_ranking=False)],candidate_adopted=False,no_original_phi_E_or_scalar_overwrite=True)
class ConsolidationAccounting(unittest.TestCase):
 def test_fifteen_geometries_and_six_hundred_unloaded_probes(self):self.assertEqual(validate_consolidation_summary(fixture())['unloaded_probe_count'],600)
 def test_new_solve_angular_evaluation_or_boolean_counter_rejected(self):
  for key,value in(('new_PDE_RHS',1),('actual_new_angular_evaluations',1),('canonical_native_geometries',True)):
   data=fixture();data[key]=value
   with self.assertRaises(ValueError):validate_consolidation_summary(data)
 def test_duplicate_geometry_or_incomplete_probe_payload_rejected(self):
  for change in('duplicate','count','payload'):
   data=fixture()
   if change=='duplicate':data['candidates'][1]['candidate_id']='C0'
   elif change=='count':data['candidates'][1]['probe_prediction']['probe_count']=39
   else:data['candidates'][1]['probe_prediction']['probes'].pop()
   with self.assertRaises(ValueError):validate_consolidation_summary(data)
 def test_unverified_local_rank_adoption_and_source_overwrite_rejected(self):
  for field in('local','adoption','overwrite'):
   data=fixture()
   if field=='local':data['reported_local_candidates'][0]['eligible_for_native_ranking']=True
   elif field=='adoption':data['candidate_adopted']=True
   else:data['no_original_phi_E_or_scalar_overwrite']=False
   with self.assertRaises(ValueError):validate_consolidation_summary(data)
if __name__=='__main__':unittest.main()
