"""Synthetic completion/accounting fixtures only; no scientific inputs."""
import ast,copy,unittest
from pathlib import Path
from owner_contracts import validate_single_pair_summary,IDS,MATCHES

def fixture():
 rows=[]
 for cid in IDS:
  rows.append(dict(candidate_id=cid,geometry=dict(physical_pads=2,connected_sources=1,pads=[{'center_mm':[-12.5,0]},{'center_mm':[12.5,0]}]),actual_new_driven_RHS=1,source_physics_proof=dict(passed=True,physical_topology=dict(passed=True,connected_sources=1,no_logical1_or3_contact_patches=True)),single_carrier_envelope_AM_10Hz_V_m=0,carrier_RMS_is_not_TIS_modulation=True,separate_RMS_matches_to_selected_TIS={key:dict(required_source_high_impedance_Vpp=2.,equal_RMS_does_not_imply_equal_TIS_modulation_or_activation=True)for key in MATCHES}))
 return dict(status='calculated_provisional_single_pair_comparison_unadopted',actual_new_driven_RHS=2,new_eigen_solves=0,existing_PDE_repeated=False,TIS_angular_computation_performed=False,Q_resident_during_metrics=False,candidate_adopted=False,selected_TIS_reference={'candidate_id':'P23p5-peripheral-polyomino225'},candidates=rows,Q_release_boundaries=[dict(candidate_id=cid,raw_frame_returned=True,Q_passed_to_metrics=False)for cid in IDS])
class SinglePairAccounting(unittest.TestCase):
 def test_two_physical_single_source_cases_are_complete(self):self.assertTrue(validate_single_pair_summary(fixture())['passed'])
 def test_extra_RHS_or_eigen_work_cannot_be_complete(self):
  for key,value in(('actual_new_driven_RHS',4),('new_eigen_solves',1),('new_eigen_solves',False)):
   d=fixture();d[key]=value
   with self.assertRaises(ValueError):validate_single_pair_summary(d)
 def test_second_attached_source_or_y_shift_rejected(self):
  for key in('source','y'):
   d=fixture()
   if key=='source':d['candidates'][0]['geometry']['connected_sources']=2
   else:d['candidates'][0]['geometry']['pads'][0]['center_mm'][1]=-5
   with self.assertRaises(ValueError):validate_single_pair_summary(d)
 def test_Q_release_and_physical_pass_are_mandatory(self):
  d=fixture();d['Q_release_boundaries'][0]['Q_passed_to_metrics']=True
  with self.assertRaises(ValueError):validate_single_pair_summary(d)
  d=fixture();d['candidates'][0]['source_physics_proof']['physical_topology']['passed']=False
  with self.assertRaises(ValueError):validate_single_pair_summary(d)
 def test_centre_and_ROI_matches_cannot_be_collapsed(self):
  d=fixture();d['candidates'][0]['separate_RMS_matches_to_selected_TIS'].pop(MATCHES[1])
  with self.assertRaises(ValueError):validate_single_pair_summary(d)
class PublicationNamespaceContracts(unittest.TestCase):
 def test_guardian_and_worker_require_identical_publication_prefix(self):
  prefixes=[]
  for filename in('guardian.py','worker.py'):
   tree=ast.parse(Path(__file__).with_name(filename).read_text())
   value=next(node.value.value for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='REMOTE'for t in node.targets))
   prefixes.append(value)
  self.assertEqual(prefixes,['data-native/single-pair-refresh-20261025/']*2)
if __name__=='__main__':unittest.main()
