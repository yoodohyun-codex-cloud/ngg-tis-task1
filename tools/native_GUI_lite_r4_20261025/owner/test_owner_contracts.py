"""Source-only pure fixtures; no actual tests executed by source author."""
import unittest
from owner_contracts import fixture_elements,validate_summary,validate_MFG

def summary():return dict(schema='task1-native-GUI-lite-build-result-v1',status='native_GUI_lite_built_browser_unverified',completed_cases=7,new_native_cases=3,legacy_reference_cases=4,requested_probes=120,strict_same_layer_probes=60,extrapolated_probes=60,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0,payload_JSON_bytes=4000000,index_HTML_bytes=4050000,browser_validation_performed=False,candidate_adopted=False,old_GUI_pointers_modified=False)
class GUIOwnerContracts(unittest.TestCase):
 def test_build_does_not_imply_browser_or_adoption(self):self.assertFalse(validate_summary(summary())['browser_validation_performed'])
 def test_missing_reference_and_wrong_probe_counts_block(self):
  for key,value in(('legacy_reference_cases',3),('strict_same_layer_probes',61),('new_Q_loads',1),('old_GUI_pointers_modified',True)):
   s=summary();s[key]=value
   with self.assertRaises(ValueError):validate_summary(s)
 def test_functional_size_cap_is_not_silent_data_omission(self):
  s=summary();s['index_HTML_bytes']=5000001
  with self.assertRaises(ValueError):validate_summary(s)
 def test_array_bound_is_explicit_and_does_not_reinterpret_cell_cap(self):
  self.assertEqual(fixture_elements((96,5)),480)
  for shape in((793848,5),(-1,),True):
   with self.assertRaises(ValueError):fixture_elements(shape)
 def test_failed_or_caught_native_call_cannot_be_mfg_pass(self):
  with self.assertRaises(ValueError):validate_MFG(dict(status='failed'),{},1)
