"""Pure signs/normalization/admission contracts; no cache or NumPy/SciPy IO."""
import json,unittest
import layer_dtn_cem as c
class Contracts(unittest.TestCase):
 def test_physical_top_contact_has_no_half_SC_cell(self):
  area=2.5e-7;z=5e-5-1e-4j
  self.assertEqual(c.contact_conductance(area,z),area/z)
 def test_common_ground_and_inactive_output_signs(self):
  # All four pads included; output1 stays connected to its50ohm and0V ideal.
  phi=[.1+.02j,.03-.01j,.02+.01j,.04+.02j];metal=[.3+.02j,.01-.03j];z=.2-.1j
  surface,metalrows,qpad=c.contact_equations([0j]*4,phi,metal,[0,1,2,3],[0,1,2,3],[1.]*4,z)
  for p in range(4):self.assertEqual(surface[p],(phi[p]-(metal[p]if p<2 else 0))/z)
  self.assertEqual(metalrows[1],metal[1]/50-qpad[1])
 def test_loaded_current_gate_cannot_be_hidden_by_source_rhs(self):
  errors={k:0. for k in('relative_algebraic_residual','relative_loaded_current_residual','relative_all_pad_KCL','relative_output_pad_current','relative_complex_power_error')}
  errors['relative_algebraic_residual']=1e-10;errors['relative_loaded_current_residual']=1e-5
  self.assertFalse(c.screen_errors(errors)['passed'])
 def test_contact_power_conjugation(self):
  z=.2-.1j;drop=.1+.03j;g=1/z;I=g*drop
  power=.5*drop*I.conjugate();expected=.5*z*abs(I)**2
  self.assertLess(abs(power-expected),1e-15);self.assertGreater(power.real,0);self.assertLess(power.imag,0)
 def test_unadmitted_reference_is_rejected(self):
  with self.assertRaises((ValueError,KeyError)):c.validate_admission(json.dumps({'schema':'task1-layer-dtn-xy102-cem-root-admission-v1','status':'proposed'}).encode())
class FractionalMaskContracts(unittest.TestCase):
 def test_exact_rational_partition_across_partial_pixels(self):
  F=c.Fraction;rect=(F(1,5),F(4,5),F(1,7),F(6,7));area=F(0)
  for i in range(3):
   for j in range(4):area+=c.rectangle_intersection(F(i,3),F(i+1,3),F(j,4),F(j+1,4),*rect)
  self.assertEqual(area,(rect[1]-rect[0])*(rect[3]-rect[2]))
 def test_touching_boundary_and_disjoint_pixels_have_zero_contact(self):
  F=c.Fraction
  self.assertEqual(c.rectangle_intersection(F(0),F(1),F(0),F(1),F(1),F(2),F(0),F(1)),0)
  self.assertEqual(c.rectangle_intersection(F(0),F(1),F(0),F(1),F(2),F(3),F(2),F(3)),0)
 def test_partial_patch_is_not_rescaled_to_full_pixel(self):
  F=c.Fraction
  area=c.rectangle_intersection(F(0),F(1),F(0),F(1),F(1,2),F(3,2),F(1,3),F(4,3))
  self.assertEqual(area,F(1,3))
if __name__=='__main__':unittest.main()
