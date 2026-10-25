"""Pure control-alias contracts; no original scientific file or PDE is read."""
import unittest
import peripheral_screen as m

class ControlAliasContracts(unittest.TestCase):
 def fixture(self):
  candidate=dict(candidate_id=m.IDS[0],reuse_first8_case_id=m.IDS[0],mask_sha256='a'*64)
  catalog=dict(gamma_by_frequency={'2000':[1,2,3,4],'2010':[2,3,4,5]},z_by_frequency={'2000':1,'2010':2},common_ROI={'radius_mm':5,'depth_mm':[15,20]},grid={'cells':793860},drives={'2000':{'source_peak_V':.5}},source_resistance_ohm=50.)
  original=dict(geometry=dict(mask_sha256='a'*64),source_physics_proofs=[{'passed':True}],metrics={'value':1},normalizations={'value':2},scalar_arrays=dict(path='/old/scalars.npz',SHA256='b'*64))
  source=dict(spec=dict(catalog=catalog,provisional_field=dict(derived_field_version=m.science.provisional_field.VERSION)),raw_artifacts={m.IDS[0]+'-'+str(f):dict(path='/old/'+str(f)+'.npz',SHA256='c'*64)for f in(2000,2010)})
  return candidate,catalog,original,source
 def test_control_is_full_metric_scalar_raw_alias_without_new_fields(self):
  result=m._control_alias(*self.fixture())
  self.assertEqual(result['actual_new_RHS'],0);self.assertEqual(result['actual_new_metric_evaluations'],0)
  self.assertTrue(result['no_field_reconstruction']);self.assertTrue(result['no_angular_recalculation'])
  self.assertEqual(result['scalar_arrays']['kind'],'immutable_original_scalar_alias')
  self.assertEqual(set(result['original_raw']),{'2000','2010'})
 def test_control_alias_cannot_substitute_a_different_geometry(self):
  a,b,c,d=self.fixture();a['mask_sha256']='d'*64
  with self.assertRaises(ValueError):m._control_alias(a,b,c,d)
 def test_control_alias_never_mutates_original_metrics(self):
  a,b,c,d=self.fixture();result=m._control_alias(a,b,c,d);result['metrics']['value']=99
  self.assertEqual(c['metrics']['value'],1)
 def test_changed_field_ABI_cannot_reuse_original_control_metrics(self):
  a,b,c,d=self.fixture();d['spec']['provisional_field']['derived_field_version']='other-ABI'
  with self.assertRaises(ValueError):m._control_alias(a,b,c,d)

if __name__=='__main__':unittest.main()
