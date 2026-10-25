"""Pure synthetic contracts only; author has not executed these tests."""
import unittest
import pair_gui_inputs as inputs
import pair_gui_post as post
import pair_gui_render as render
class PairGUIContracts(unittest.TestCase):
 def test_ROI_mean_and_second_moment_RMS_remain_distinct(self):
  raw=dict(mean=3.,std=4.,rms=5.,p10=1.,p95=8.,min=0.,max=9.,volume_m3=2.)
  result=post.scale_stats(raw,2.);self.assertEqual(result['mean'],6.);self.assertEqual(result['rms'],10.);self.assertEqual(result['volume_m3'],2.);self.assertEqual(raw['rms'],5.)
 def test_burden_ratios_do_not_insert_zero_denominators(self):
  e={'source_power_W':4.,'skin_vector_J_RMS_max_A_m2':3.};r={'source_power_W':2.,'skin_vector_J_RMS_max_A_m2':0.};ratios=post.relative_burdens(e,r);self.assertEqual(ratios['source_power_W'],2.);self.assertIsNone(ratios['skin_vector_J_RMS_max_A_m2']);self.assertIsNone(ratios['contact_power_W'])
 def test_regression_failure_is_preserved_as_error(self):
  self.assertTrue(post.regression(2.,2.,'synthetic')['passed'])
  with self.assertRaises(ValueError):post.regression(3.,2.,'synthetic')
 def test_nonfinite_or_complex_payloads_are_rejected_before_output(self):
  for value in(float('nan'),float('inf'),complex(1,2)):
   with self.assertRaises((TypeError,ValueError)):post.encoded(dict(value=value))
 def test_renderer_escapes_embedded_script_without_fetch_or_native_decode(self):
  html=render.build(dict(marker='</script><img src=x>'),dict());self.assertIn('\\u003c/script\\u003e',html);self.assertNotIn('<img src=x>',html);self.assertNotIn('fetch(',html)
 def test_fixed_modes_and_correct_new_single_pair_ids(self):
  self.assertEqual(post.MODES,('fixed_1Vpp','same_centre20mm_vector_RMS','same_target_volume_RMS'));self.assertEqual(inputs.PAIR_IDS,('single-pair-square15-c12.5-y0','single-pair-square15-c15-y0'));self.assertEqual(post.DEPTHS,(5.,10.,15.,17.5,20.))
if __name__=='__main__':unittest.main()
