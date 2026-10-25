"""Pure scalar contracts; no NumPy/eigen/material-file reads on test import."""
import math,unittest
import weighted_dtn_mms as m
class Contracts(unittest.TestCase):
 def test_zero_modes_distinguish_bottom_conditions(self):
  t=.0001
  self.assertEqual(m.profile(0,t/4,t,'Dirichlet0'),(.75,1/t));self.assertEqual(m.profile(0,t/4,t,'Neumann0'),(1.,0.))
 def test_modal_profiles_obey_endpoints(self):
  t=.0001
  for k in(1e-8,125.,250.,1e6):
   for bc in m.PLAN['bottoms']:
    F,G=m.profile(k,0,t,bc);self.assertAlmostEqual(F,1.,places=12)
    fb,gb=m.profile(k,t,t,bc)
    if bc=='Dirichlet0':self.assertAlmostEqual(fb,0.,places=12)
    else:self.assertAlmostEqual(gb,0.,places=12)
 def test_uniform_depth_closed_forms(self):
  k=125.;t=.0001;z=.00004
  f,g=m.profile(k,z,t,'Dirichlet0');self.assertAlmostEqual(f,math.sinh(k*(t-z))/math.sinh(k*t),places=12);self.assertAlmostEqual(g,k*math.cosh(k*(t-z))/math.sinh(k*t),places=8)
  f,g=m.profile(k,z,t,'Neumann0');self.assertAlmostEqual(f,math.cosh(k*(t-z))/math.cosh(k*t),places=12);self.assertAlmostEqual(g,k*math.sinh(k*(t-z))/math.cosh(k*t),places=12)
 def test_relocated_faces_positive_and_physical(self):
  for n in m.PLAN['grids']:
   faces=m.moved_faces(n);self.assertEqual(len(faces),n+1);self.assertTrue(all(a<b for a,b in zip(faces[:-1],faces[1:])));self.assertEqual(faces[-1]-faces[0],m.Fraction(1,20))
   for f in(m.Fraction(-7,400),m.Fraction(-1,400),m.Fraction(1,400),m.Fraction(7,400)):self.assertIn(f,faces)
 def test_gauss_weights_cover_physical_depth(self):
  self.assertAlmostEqual(sum(w for p,w in m.GAUSS5),2.,places=14);self.assertAlmostEqual(sum(w for p,w in m.GAUSS8),2.,places=14)
if __name__=='__main__':unittest.main()
