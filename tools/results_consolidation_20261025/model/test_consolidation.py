"""Pure four-ratio ranking contracts, no datasets/arrays are read."""
import unittest
import consolidation as m

class FourRatioContracts(unittest.TestCase):
 def reference(self):return dict(target_AM_mean_V_m=1.,target_AM_P10_V_m=.5,target_to_surface_mean_ratio=.1,target_to_offtarget_mean_ratio=.2)
 def test_all_four_gains_required_for_minimum_score_above_one(self):
  result=m.four_ratios(1.2,.6,8.,8.,self.reference())
  self.assertEqual(result['four_ratios_to_B0']['target_mean'],1.2)
  self.assertEqual(result['four_ratios_to_B0']['target_P10'],1.2)
  self.assertAlmostEqual(result['four_ratios_to_B0']['target_to_surface_mean'],1.5)
  self.assertAlmostEqual(result['four_ratios_to_B0']['target_to_offtarget_mean'],.75)
  self.assertAlmostEqual(result['robust_minimum_four_ratio'],.75)
 def test_ratio_only_gain_with_target_loss_cannot_score_as_improvement(self):
  result=m.four_ratios(.8,.4,2.,2.,self.reference())
  self.assertEqual(result['robust_minimum_four_ratio'],.8)
 def test_missing_zero_reference_is_unrankable_not_an_epsilon_success(self):
  reference=self.reference();reference['target_AM_P10_V_m']=0.
  self.assertIsNone(m.four_ratios(1.,.5,5.,5.,reference)['robust_minimum_four_ratio'])

if __name__=='__main__':unittest.main()
