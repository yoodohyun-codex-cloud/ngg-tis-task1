"""Pure manufactured-source contracts; no native files are read."""
import math
import unittest
import estimator_fourier as e


class EstimatorDecomposition(unittest.TestCase):
 def test_equal_biased_sides_cancel_jump_but_side_errors_remain(self):
  row={'upper_J':{'real':2.,'imaginary':3.},'lower_J':{'real':2.,'imaginary':3.},'exact_J':{'real':1.,'imaginary':2.}}
  out=e.decompose(row,1/math.sqrt(2))
  self.assertEqual(out['jump_squared_A2_m4'],0)
  self.assertGreater(out['upper_SC_spatial_RMS_error_A_m2'],0)
  self.assertGreater(out['lower_VS_spatial_RMS_error_A_m2'],0)
  self.assertLess(out['jump_identity_absolute_error_A2_m4'],1e-12)

 def test_opposed_side_errors_reinforce_jump(self):
  row={'upper_J':{'real':2.,'imaginary':0.},'lower_J':{'real':0.,'imaginary':0.},'exact_J':{'real':1.,'imaginary':0.}}
  out=e.decompose(row,1.)
  self.assertEqual(out['jump_squared_A2_m4'],4.)
  self.assertEqual(out['cross_term_signed_A2_m4'],2.)
  self.assertEqual(out['jump_identity_absolute_error_A2_m4'],0.)

 def test_both_meshes_support_identical_two_and_three_point_orders(self):
  f=e.f;gamma=[.003+.02j,.2+.04j,.04+.005j,.3+.07j]
  for grid in e.GRIDS:
   faces,layers,zs=f.make_grid(grid['h_mm'],grid['sc_cells'],grid['bulk_counts'])
   v,_,state=f.exact_profile(2*math.pi*4/.05,gamma,f.THICKNESS,zs)
   for points in(2,3):
    rows=f.fit_interfaces(v,zs,layers,gamma,f.THICKNESS,state,points,1/math.sqrt(2))
    self.assertTrue(all(r['upper_points']==r['lower_points']==points for r in rows))
    self.assertEqual(f.QA_LIMIT,.05)


if __name__=='__main__':unittest.main()
