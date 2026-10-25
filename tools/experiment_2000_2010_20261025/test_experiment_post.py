"""Pure analytic contracts; no research data or native file is opened."""
import unittest
import experiment_interfaces as iface
import experiment_post as post


class MinimumContracts(unittest.TestCase):
 def test_predeclared_layered_slab_and_affine_tolerance(self):
  result=iface.analytic_validation()
  self.assertTrue(result['passed'])
  self.assertEqual(result['absolute_tolerance'],1e-10)
  self.assertEqual(result['relative_tolerance'],1e-10)
 def test_independent_five_percent_flag_is_not_an_export_gate(self):
  proof={'interfaces':[{'interface_depth_mm':.1,'regions':{'all':{'total_normal_current':{'normalized_L2':.06}}}}]}
  result=post._qa(proof)
  self.assertEqual(result['status'],'numerical_flags_failed')
  self.assertFalse(result['rows'][0]['passed'])
  self.assertEqual(proof['interfaces'][0]['regions']['all']['total_normal_current']['normalized_L2'],.06)


if __name__=='__main__':unittest.main()
