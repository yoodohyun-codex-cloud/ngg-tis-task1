"""Small independent result-accounting fixtures, never scientific data reads."""
import copy,unittest
from owner_contracts import validate_pair_gui_summary,validate_ecdf_artifacts,BASELINE,PAIRS,MODES
def fixture():
 rows=[]
 for i,cid in enumerate((BASELINE,)+PAIRS):
  point,roi=(4.,5.)if i==0 else(2.,1.);scales=[1.,1. if i==0 else 2.,1. if i==0 else 5.]
  modes={name:dict(amplitude_scale=a,required_source_high_impedance_Vpp=a,centre_vector_RMS_V_m=point*a,target_volume_RMS_V_m=roi*a)for name,a in zip(MODES,scales)}
  rows.append(dict(candidate_id=cid,is_TIS=i==0,physical_pads=4 if i==0 else 2,independent_outputs=2 if i==0 else 1,contact_area_mm2=900. if i==0 else 450.,frequencies_Hz=[2000,2010]if i==0 else[2000],candidate_adopted=False,modes=modes,centre_vector_RMS_V_m=point,target_volume_RMS_V_m=roi,regression_proofs=[dict(passed=True)],single_carrier_10Hz_envelope_AM_V_m=None if i==0 else 0.,saved_single_pair_comparison=dict(geometry=dict(physical_pads=2,connected_sources=1,pads=[dict(center_mm=[-12.5,0.]),dict(center_mm=[12.5,0.])]))))
 return dict(status='cached_three_geometry_single_pair_GUI_r2_prepared_unadopted',new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,originals_overwritten=False,browser_validation_performed=False,candidate_adopted=False,candidates=rows,baseline_id=BASELINE,comparison_modes=list(MODES),grid_binding=dict(original_weights_changed=False),ECDF_diagnostics_saved_before_regressions=True,original_producer_stats_and_electrical_preserved=True,regression_limit_unchanged='1e-10+2e-7*abs(saved)')
class PairGUIAccounting(unittest.TestCase):
 def test_two_physically_distinct_RMS_match_criteria(self):
  result=validate_pair_gui_summary(fixture());self.assertEqual(result['comparison_geometries'],3);self.assertEqual(result['separate_single_pair_matches'],4)
  definitions={'sources':{'fixture':dict(SHA256='a'*64,function_AST_SHA256='b'*64)}};audit=dict(status='actual_original_source_and_function_SHA_verified',ECDF_helper_SHA256='c'*64,regression_limit_unchanged='1e-10+2e-7*abs(saved)',sources=[dict(producer='fixture',passed=True,source_SHA256='a'*64,function_AST_SHA256='b'*64)]);measure=dict(producer_matches_saved_with_unchanged_limit=True);diags={cid:dict(candidate_id=cid,schema='task1-actual-ECDF-producer-and-canonical-diagnostic-v1',source_definitions=definitions,all_numeric_values_computed_from_actual_pinned_native_fields=True,regression_tolerance_changed=False,diagnostic_written_before_any_metric_regression=True,regions={str(i):dict(p10=measure,p95=measure)for i in range(6)},contact_normal_J_P95=measure,skin_vector_J_P95=measure)for cid in(BASELINE,)+PAIRS};self.assertTrue(validate_ecdf_artifacts(fixture(),audit,diags,definitions,'c'*64)['passed']);diags.pop(PAIRS[0])
  with self.assertRaises(ValueError):validate_ecdf_artifacts(fixture(),audit,diags,definitions,'c'*64)
 def test_pad_count_does_not_imply_another_source(self):
  data=fixture();data['candidates'][1]['independent_outputs']=2
  with self.assertRaises(ValueError):validate_pair_gui_summary(data)
 def test_centre_match_cannot_substitute_for_ROI_match(self):
  data=fixture();data['candidates'][1]['modes'][MODES[2]]=copy.deepcopy(data['candidates'][1]['modes'][MODES[1]])
  with self.assertRaises(ValueError):validate_pair_gui_summary(data)
 def test_y0_return_and_zero_single_frequency_AM_remain_explicit(self):
  for change in('return','AM'):
   data=fixture()
   if change=='return':data['candidates'][1]['saved_single_pair_comparison']['geometry']['pads'][1]['center_mm'][1]=2.
   else:data['candidates'][1]['single_carrier_10Hz_envelope_AM_V_m']=1.
   with self.assertRaises(ValueError):validate_pair_gui_summary(data)
 def test_new_work_incomplete_geometry_or_invalid_validation_claim_rejected(self):
  for change in('counter','missing','browser','overwrite','adopt','proof','ECDF'):
   data=fixture()
   if change=='counter':data['new_PDE_RHS']=True
   elif change=='missing':data['candidates'].pop()
   elif change=='browser':data['browser_validation_performed']=True
   elif change=='overwrite':data['originals_overwritten']=True
   elif change=='adopt':data['candidate_adopted']=True
   elif change=='ECDF':data['ECDF_diagnostics_saved_before_regressions']=False
   else:data['candidates'][1]['regression_proofs'][0]['passed']=False
   with self.assertRaises(ValueError):validate_pair_gui_summary(data)
if __name__=='__main__':unittest.main()
