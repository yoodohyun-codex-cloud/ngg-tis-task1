import math,unittest
import contact_edge_fv as f
class Contracts(unittest.TestCase):
 def test_full_fraction_closures_identical(self):
  g=1+.25j;z=1e-4-2e-5j
  self.assertEqual(f.contact_conductance(.1,.1,.01,g,z,'physical_area_robin'),f.contact_conductance(.1,.1,.01,g,z,'wholepixel_halfcell_lumping'))
 def test_partial_halfcell_closures_are_distinct(self):
  g=1+.25j;z=1e-4-2e-5j
  actual=f.contact_conductance(.025,.1,.01,g,z,'physical_area_robin');lumped=f.contact_conductance(.025,.1,.01,g,z,'wholepixel_halfcell_lumping')
  self.assertEqual(actual,.025/(z+.01/(2*g)));self.assertEqual(lumped,.025/(z+.25*.01/(2*g)));self.assertGreater(abs(lumped),abs(actual))
 def test_physical_interval_overlap(self):
  self.assertEqual(f.overlap_length(0,1,.5,2),.5);self.assertEqual(f.overlap_length(0,1,1,2),0.)
 def test_zero_and_high_mode_depth_integrals_stable(self):
  phi,ez=f.depth_average_factors(0,0,.0001,.0001);self.assertEqual(phi,.00005);self.assertEqual(ez,1.)
  phi,ez=f.depth_average_factors(1e8,0,.0001,.0001);self.assertTrue(math.isfinite(phi)and math.isfinite(ez));self.assertGreater(phi,0);self.assertGreater(ez,0)
 def test_constant_depth_average_closed_form(self):
  k=100.;t=.0001;a=.00002;b=.00006;ph,ez=f.depth_average_factors(k,a,b,t)
  expected_phi=(math.cosh(k*(t-a))-math.cosh(k*(t-b)))/(k*k*(b-a)*math.cosh(k*t));expected_ez=(math.sinh(k*(t-a))-math.sinh(k*(t-b)))/(k*(b-a)*math.cosh(k*t))
  self.assertAlmostEqual(ph,expected_phi,places=12);self.assertAlmostEqual(ez,expected_ez,places=12)
 def test_exact_aligned_contact_cannot_have_roundoff_ghosts(self):
  for nx in(40,80,160):
   e,w,a=f.exact_mesh_records(nx,'aligned','physical_area_robin');ef,wf,af=f.exact_mesh_records(nx,'aligned','boundary_fitted')
   self.assertEqual(e,ef);self.assertEqual(w,wf);self.assertEqual(a,af);self.assertTrue(all(v==0 or v==h for h,v in zip(w,a)))
 def test_boundary_fitted_inserts_real_edges_without_rescaling(self):
  e,w,a=f.exact_mesh_records(4,'half_cell','physical_area_robin');ef,wf,af=f.exact_mesh_records(4,'half_cell','boundary_fitted')
  self.assertEqual(len(ef),len(e)+2);self.assertEqual(sum(a),sum(af));self.assertTrue(any(0<v<h for h,v in zip(w,a)));self.assertTrue(all(v==0 or v==h for h,v in zip(wf,af)))
if __name__=='__main__':unittest.main()
