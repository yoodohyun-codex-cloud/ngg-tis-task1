"""Pure manufactured contracts; root executes, no native arrays or Git."""
import math,unittest
import vs_estimator as v
class GradedGeometryContracts(unittest.TestCase):
 def test_fixed_symmetric_VS_faces_preserve_layer_thickness(self):
  faces,layers,z=v.make_grid(v.GRIDS[2]);widths=[b-a for a,b,l in zip(faces[:-1],faces[1:],layers)if l==1]
  self.assertEqual(len(widths),18);self.assertAlmostEqual(sum(widths),.005,places=14)
  self.assertAlmostEqual(faces[8],.0001,places=14);self.assertAlmostEqual(faces[26],.0051,places=14)
  for a,b in zip(widths,reversed(widths)):self.assertAlmostEqual(a,b,places=14)
  self.assertTrue(all(d>0 for d in widths));self.assertTrue(all(max(a/b,b/a)<=1.15+1e-10 for a,b in zip(widths[:-1],widths[1:])))
 def test_graded_discrete_network_matches_independent_Thomas_solution(self):
  faces,layers,z=v.make_grid(v.GRIDS[2]);gamma=[.003+.02j,.2+.04j,.04+.005j,.3+.07j];k=2*math.pi/.05
  a=v.f.solve_fvm(k,gamma,faces,layers);b=v.discrete_admittance_profile(k,gamma,faces,layers)
  self.assertTrue(all(abs(x-y)<=1e-10+1e-10*abs(y)for x,y in zip(a,b)))
 def test_graded_zero_mode_has_exact_constant_potential_and_zero_flux(self):
  faces,layers,z=v.make_grid(v.GRIDS[2]);gamma=[.003+.02j,.2+.04j,.04+.005j,.3+.07j]
  values=v.f.solve_fvm(0,gamma,faces,layers);self.assertTrue(all(abs(x-1)<=1e-10 for x in values))
  states=v.discrete_interface_states(values,gamma,faces,layers);self.assertTrue(all(abs(current)<=1e-10 for _,current in states))
if __name__=='__main__':unittest.main()
