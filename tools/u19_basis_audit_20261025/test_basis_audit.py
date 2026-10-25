"""Pure small contracts; no research native file or publication is opened."""
import unittest
import numpy as np
import basis_audit as b


class CachedBasisContracts(unittest.TestCase):
 def test_diagonal_pad_exchange_is_rotation_not_y_reflection(self):
  rows=[dict(pad=0,x_mm=-1.,y_mm=-1.,area_m2=1.),dict(pad=1,x_mm=1.,y_mm=1.,area_m2=1.),dict(pad=2,x_mm=1.,y_mm=-1.,area_m2=1.),dict(pad=3,x_mm=-1.,y_mm=1.,area_m2=1.)]
  y,p=b.contact_reflection_proof(rows,'y_reflection')
  self.assertEqual(y['status'],'not_applicable');self.assertIsNone(p)
  rotation,p=b.contact_reflection_proof(rows,'xy_rotation180')
  self.assertEqual(rotation['status'],'exact_xy_rotation180_pad_mask_proved')
  self.assertTrue(np.array_equal(p,[1,0,3,2]))
  rows[1]['area_m2']=1.01
  rotation,p=b.contact_reflection_proof(rows,'xy_rotation180')
  self.assertEqual(rotation['status'],'not_applicable');self.assertIsNone(p)

 def test_indexed_mask_area_is_absolute_not_a_fraction(self):
  mask=[dict(pad=0,i=15,j=15,area_m2=2.5e-7)]
  contacts=[dict(pad=0,x_mm=-17.25,y_mm=-17.25,area_m2=2.5e-7)]
  result=b.mask_contact_binding(mask,contacts,.5)
  self.assertEqual(result['status'],'exact_mask_native_contact_geometry_match')
  contacts[0]['area_m2']*=.25e-6
  self.assertEqual(b.mask_contact_binding(mask,contacts,.5)['status'],'geometry_mismatch')

 def test_180_scalar_and_vector_parity_have_both_horizontal_signs(self):
  grid=np.asarray([[-.25,-.25,0,0,1],[-.25,.25,0,0,1],[.25,-.25,0,0,1],[.25,.25,0,0,1]],float)
  geometry=dict(x=np.asarray([-.25,.25]),y=np.asarray([-.25,.25]),lookup=np.asarray([[[0,2],[1,3]]]),ix=np.asarray([0,0,1,1]),iy=np.asarray([0,1,0,1]),iz=np.zeros(4,int))
  permutation=b.grid_y_permutation(grid,geometry,'xy_rotation180')
  a=grid[:,0]+2*grid[:,1];c=-a
  scalar=b.parity_diagnostic(a,c[permutation],np.ones(4),grid,'potential','V')
  self.assertEqual(scalar['absolute_volume_weighted_RMS_difference'],0.)
  e0=np.tile([-1.,-2.,-3.],(4,1));e1=np.tile([1.,2.,-3.],(4,1))
  correct=b.parity_diagnostic(e0,e1[permutation]*[-1,-1,1],np.ones(4),grid,'E','V/m')
  wrong=b.parity_diagnostic(e0,e1[permutation]*[1,-1,1],np.ones(4),grid,'E','V/m')
  self.assertEqual(correct['absolute_volume_weighted_RMS_difference'],0.)
  self.assertGreater(wrong['absolute_volume_weighted_RMS_difference'],0.)
  self.assertFalse(correct['phase_or_gauge_fitted'])

 def test_both_basis_and_complex_cross_term_energy_KCL(self):
  transfer=np.asarray([[.1,-.02],[-.02,.1]],complex)
  density=np.asarray([[.1,-.02,-.04,-.04],[-.02,.1,-.04,-.04]],complex)
  loss=np.zeros((6,2,2),complex);loss[0]=.25*transfer;area=np.ones(4);pads=np.arange(4)
  for c in([1,0],[0,1],[1,1],[1,1j]):
   result,*_=b.conservation(c,transfer,loss,density,area,pads)
   self.assertTrue(result['passed'])
  # Preserve the two diagonal basis powers but corrupt an off-diagonal form.
  broken=loss.copy();broken[0,0,1]+=1e-3;broken[0,1,0]+=1e-3
  diagonal,*_=b.conservation([1,0],transfer,broken,density,area,pads)
  combined,*_=b.conservation([1,1],transfer,broken,density,area,pads)
  self.assertTrue(diagonal['passed']);self.assertFalse(combined['passed'])

 def test_contact_P95_is_area_weighted_not_point_count(self):
  self.assertEqual(b.weighted_quantile([1.,99.],[99.,1.],.95),1.)


if __name__=='__main__':unittest.main()
