"""Pure tiny source tests; no native/cache/reference solve is executed here."""
import math
import unittest
import numpy as np
import cem_compare as c


class ReferenceComparisonContracts(unittest.TestCase):
 def test_explicit_XY_order_is_mapped_without_gauge_or_spatial_fit(self):
  grid=np.asarray([[-.25,-.25,.025,0,1],[.25,-.25,.025,0,1],[-.25,-.25,.2,1,1],[.25,-.25,.2,1,1]],float)
  xy=np.asarray([[.25,-.25],[-.25,-.25]])
  mapping=c.coordinate_map(grid,xy,[.025,.2],[0,1])
  self.assertTrue(np.array_equal(mapping,[1,0,3,2]))
  with self.assertRaises(ValueError):c.coordinate_map(grid,xy,[.025,200],[0,1])
  with self.assertRaises(ValueError):c.coordinate_map(grid,xy,[.025,.2],[0,1.5])

 def test_harmonic_face_flux_has_correct_sign_units_and_layer_continuity(self):
  faces=np.asarray([0.,.05,.1,2.6,5.1,7.6,10.1,17.6,25.1]);z=(faces[:-1]+faces[1:])/2
  gamma=np.asarray([.002+.01j,.2+.002j,.04+.0002j,.3+.02j]);boundaries=np.asarray([0.,.1,5.1,10.1,25.1]);current=.3+.2j
  values=[]
  for depth,layer in zip(z,np.repeat(np.arange(4),2)):
   integral=sum((boundaries[i+1]-boundaries[i])/1000/gamma[i]for i in range(layer))+(depth-boundaries[layer])/1000/gamma[layer]
   values.append(1-current*integral)
  layout=dict(lookup=np.arange(8).reshape(8,1),faces_mm=faces,layer_counts=np.asarray([2,2,2,2]))
  result=c.shared_flux(np.asarray(values),layout,gamma)
  self.assertEqual(result.shape,(3,1))
  self.assertTrue(np.allclose(result,current,rtol=1e-10,atol=1e-10))

 def test_constant_complex_offset_is_preserved_as_difference(self):
  reference=np.asarray([1.+0j,2.+0j]);actual=reference+.1+.2j
  result=c.complex_error(actual,reference,np.asarray([1.,3.]),np.asarray([[0,0,0],[1,0,0]]),'V')
  self.assertAlmostEqual(result['absolute_difference_spatial_complex_RMS'],math.sqrt(.05))
  self.assertFalse(result['phase_or_gauge_fitted'])
  self.assertEqual(result['status'],'secondary_diagnostic_not_gated')


if __name__=='__main__':unittest.main()
