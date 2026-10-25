"""Structured-scaler regressions, using synthetic metadata only."""
import copy,unittest
import screen_metrics as metrics

class StructuredScalingContracts(unittest.TestCase):
 def test_signed_power_pairs_layers_frequency_maps_and_pad_ids(self):
  e=dict(source_Vpp_each=1.,source_Vpp_by_frequency={'2000':.5,'2010':1.},source_peak_V_by_frequency={'2000':.25,'2010':.5},active_source_current_RMS_by_frequency_A={'2000':.2,'2010':.3},source_current_RMS_by_output_A=[.4,.5],source_complex_power_W=dict(real=2.,imaginary=-3.),contact_complex_power_W=dict(real=.2,imaginary=-.1),layer_complex_power_W=[dict(real=.5,imaginary=-.25)]*4,layers_power_W={'sc':.5,'dermis':.5,'fat':.5,'muscle':.5},source_power_W=2.,SC_power_W=.5,skin_power_W=1.,contact_power_W=.2,source_resistor_power_W=.1,physical_pad_current_RMS_A=[dict(physical_pad_id=9,current_RMS_A=.15)],achieved_absolute_active_current_ratio_I0_over_I1=2/3,independent_outputs=2)
  original=copy.deepcopy(e);result=metrics._scaled_electrical(e,3.)
  self.assertEqual(result['source_complex_power_W'],dict(real=18.,imaginary=-27.))
  self.assertAlmostEqual(result['contact_complex_power_W']['imaginary'],-.9)
  self.assertEqual(result['layer_complex_power_W'][0],dict(real=4.5,imaginary=-2.25))
  self.assertEqual(result['layers_power_W']['sc'],4.5)
  self.assertEqual(result['source_Vpp_by_frequency'],{'2000':1.5,'2010':3.})
  self.assertEqual(result['source_peak_V_by_frequency'],{'2000':.75,'2010':1.5})
  self.assertAlmostEqual(result['active_source_current_RMS_by_frequency_A']['2000'],.6)
  self.assertEqual(result['source_current_RMS_by_output_A'],[1.2000000000000002,1.5])
  self.assertEqual(result['physical_pad_current_RMS_A'][0]['physical_pad_id'],9)
  self.assertAlmostEqual(result['physical_pad_current_RMS_A'][0]['current_RMS_A'],.45)
  self.assertEqual(result['achieved_absolute_active_current_ratio_I0_over_I1'],2/3)
  self.assertEqual(result['independent_outputs'],2);self.assertEqual(e,original)

if __name__=='__main__':unittest.main()
