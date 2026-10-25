"""Pure analytic contracts; no actualmask/metadata/native/cache IO."""
import unittest
import column_diagnostic as c
class Contracts(unittest.TestCase):
 def test_full_fraction_models_match(self):
  for z in(0j,.0001-.0002j,10.-20.j):
   a=c.column_model(.25,.25,.3+.2j,z);b=c.column_model(.25,.25,.3+.2j,z,model='area_resolved')
   for field in('I','J','Vt','Vc','Ssource','SSC','Scontact'):self.assertAlmostEqual(abs(a[field]-b[field]),0.,places=12)
 def test_zero_z_exposes_footprint_and_preserves_actual_area(self):
  Y=.3+.2j;a=c.column_model(.125,1.,Y,0j);b=c.column_model(.125,1.,Y,0j,model='area_resolved')
  self.assertEqual(a['I'],Y);self.assertEqual(b['I'],.125*Y);self.assertEqual(a['J'],8*Y);self.assertEqual(b['J'],Y)
 def test_complex_power_and_voltage_signs(self):
  for model in('uniform_pixel','area_resolved'):
   r=c.column_model(.125,1.,.3+.2j,.0001-.0002j,model=model)
   self.assertLess(abs(r['Vt']+r['Vc']-1),1e-12);self.assertLess(abs(r['Ssource']-r['SSC']-r['Scontact']),1e-12)
   self.assertGreater(r['SSC'].real,0);self.assertLess(r['SSC'].imag,0);self.assertGreater(r['Scontact'].real,0);self.assertLess(r['Scontact'].imag,0)
 def test_zero_area_and_materially_overfull_are_rejected(self):
  for area in(0.,-1.,1.01):
   with self.assertRaises(ValueError):c.column_model(area,1.,.3+.2j,.1-.2j)
 def test_roundoff_fraction_is_retained(self):
  area=1+1e-12;r=c.column_model(area,1.,.3+.2j,.1-.2j,model='area_resolved')
  self.assertEqual(r['I'],area*(.3+.2j)/(1+(.3+.2j)*(.1-.2j)))
 def test_weighted_quantile_is_area_based(self):
  self.assertEqual(c.weighted_quantile([1.,100.],[.99,.01],.95),1.)
if __name__=='__main__':unittest.main()
