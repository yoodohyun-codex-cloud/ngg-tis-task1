"""Synthetic cached-array contracts; root alone runs, no file/PDE access."""
import math,unittest
import allocation_electrical as a
class AllocationContracts(unittest.TestCase):
 def test_relative_multiplier_is_not_absolute_equal_current_target(self):
  w=a.weights_for_relative_multiplier(2.,1.,.5);self.assertEqual((w['a0'],w['a1']),(.5,1.));self.assertEqual(w['achieved_absolute_active_current_ratio_I0_over_I1'],1.);self.assertEqual(w['relative_multiplier_achieved'],.5)
 def test_ratio_one_is_exact_original_weights_even_if_baseline_currents_differ(self):
  w=a.weights_for_relative_multiplier(2.,3.,1.);self.assertEqual((w['a0'],w['a1']),(1.,1.));self.assertTrue(w['relative_multiplier_one_exact_original_alias']);self.assertEqual(w['achieved_absolute_active_current_ratio_I0_over_I1'],2/3)
 def test_positive_bounded_inverse_side(self):
  w=a.weights_for_relative_multiplier(2.,1.,2.);self.assertEqual((w['a0'],w['a1']),(1.,.5));self.assertEqual(w['relative_multiplier_achieved'],2.)
 def test_invalid_ratios_rejected(self):
  for ratio in(0.,-1.,float('nan'),float('inf')):
   with self.assertRaises(ValueError):a.weights_for_relative_multiplier(1.,2.,ratio)
 def fixture(self,np):
  raw0=dict(source_current_peak_A=np.asarray([2+1j,.5-.2j]),contact_normal_J_peak_A_m2=np.asarray([3+4j,1-2j]),contact_drop_peak_V=np.asarray([.2+.1j,.1-.2j]),contact_area_m2=np.asarray([99.,1.]),contact_pad=np.asarray([0,1]),layer_complex_power_W=np.asarray([1-.2j,2-.3j,3-.4j,4-.5j]))
  raw1=dict(source_current_peak_A=np.asarray([.2+.3j,1-2j]),contact_normal_J_peak_A_m2=np.asarray([1+1j,8+6j]),contact_drop_peak_V=np.asarray([.1-.1j,.3+.2j]),contact_area_m2=np.asarray([99.,1.]),contact_pad=np.asarray([0,1]),layer_complex_power_W=np.asarray([2-.4j,4-.6j,6-.8j,8-1j]))
  p0=dict(frequency_Hz=2000,source_complex_power_W=a.pair(11-2j),contact_complex_power_W=a.pair(.5-.1j),source_resistor_power_W=.5)
  p1=dict(frequency_Hz=2010,source_complex_power_W=a.pair(22-4j),contact_complex_power_W=a.pair(1-.2j),source_resistor_power_W=1.)
  return raw0,raw1,p0,p1
 def test_unequal_weights_scale_each_signed_power_separately(self):
  import numpy as np
  r0,r1,p0,p1=self.fixture(np);e,d=a.synthesize(np,r0,r1,p0,p1,.5,1.)
  self.assertEqual(e['source_power_W'],.25*11+22);self.assertEqual(e['SC_power_W'],.25*1+2);self.assertEqual(e['skin_power_W'],.25*3+6);self.assertEqual(e['contact_power_W'],.25*.5+1)
  self.assertLess(e['source_complex_power_W']['imaginary'],0);self.assertEqual(e['source_Vpp_by_frequency'],{'2000':.5,'2010':1.});self.assertTrue(e['unequal_source_Vpp'])
 def test_induced_output_currents_scale_coherently_before_RMS(self):
  import numpy as np
  r0,r1,p0,p1=self.fixture(np);e,d=a.synthesize(np,r0,r1,p0,p1,.5,1.);truth=np.sqrt((abs(.5*r0['source_current_peak_A'])**2+abs(r1['source_current_peak_A'])**2)/2)
  np.testing.assert_allclose(e['source_current_RMS_by_output_A'],truth,rtol=1e-14,atol=0);self.assertEqual(d[0]['scaled_source_current_peak_A'][1],a.pair(.5*r0['source_current_peak_A'][1]))
 def test_contact_RMS_and_area_weighted_P95_not_unweighted(self):
  import numpy as np
  r0,r1,p0,p1=self.fixture(np);e,d=a.synthesize(np,r0,r1,p0,p1,.5,1.);J=np.sqrt((abs(.5*r0['contact_normal_J_peak_A_m2'])**2+abs(r1['contact_normal_J_peak_A_m2'])**2)/2)
  self.assertAlmostEqual(e['contact_normal_J_RMS_max_A_m2'],float(max(J)));self.assertEqual(e['contact_normal_J_RMS_P95_A_m2'],float(min(J)))
 def test_cached_inputs_are_not_modified(self):
  import numpy as np
  r0,r1,p0,p1=self.fixture(np);before=r0['contact_normal_J_peak_A_m2'].copy();a.synthesize(np,r0,r1,p0,p1,.5,1.);np.testing.assert_array_equal(before,r0['contact_normal_J_peak_A_m2'])
 def test_mismatched_contact_order_rejected(self):
  import numpy as np
  r0,r1,p0,p1=self.fixture(np);r1['contact_pad']=r1['contact_pad'][::-1]
  with self.assertRaises(ValueError):a.synthesize(np,r0,r1,p0,p1,1.,1.)
if __name__=='__main__':unittest.main()
