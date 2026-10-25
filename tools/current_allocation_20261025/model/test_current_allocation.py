"""Pure tradeoff/Pareto tests; no stored research arrays or PDE are used."""
import unittest
import current_allocation as m

class AllocationAnalysisContracts(unittest.TestCase):
 def point(self,mean,p10,surface,off):return dict(target_AM_mean_V_m=mean,target_AM_P10_V_m=p10,surface_AM_mean_V_m=surface,off_target_AM_mean_V_m=off,target_to_surface_mean_ratio=mean/surface,target_to_offtarget_mean_ratio=mean/off)
 def test_relative_multiplier_catalog_has_two_exact_aliases(self):
  self.assertEqual(len(m.GEOMETRIES)*len(m.RELATIVE_MULTIPLIERS),10)
  self.assertEqual(sum(r==1 for r in m.RELATIVE_MULTIPLIERS)*len(m.GEOMETRIES),2)
  self.assertEqual(len({m.condition_id(g,r)for g in m.GEOMETRIES for r in m.RELATIVE_MULTIPLIERS}),10)
 def test_pareto_dominance_requires_all_target_and_nontarget_objectives(self):
  a=self.point(2,1,1,1);b=self.point(1,.5,2,2)
  self.assertTrue(m.dominates(a,b));self.assertFalse(m.dominates(b,a))
  trade=self.point(3,.4,.5,.5)
  self.assertFalse(m.dominates(trade,a));self.assertFalse(m.dominates(a,trade))
 def test_equal_points_do_not_dominate_each_other(self):
  a=self.point(1,.5,2,3)
  self.assertFalse(m.dominates(a,dict(a)))
 def test_ratio_gain_with_absolute_target_loss_is_explicit(self):
  a=self.point(.8,.3,.4,.4);b=self.point(1,.5,1,1)
  result=m.tradeoffs(a,b)
  self.assertTrue(result['ratio_gain_with_absolute_target_loss'])
  self.assertEqual(result['target_mean_change'],-1)
  self.assertEqual(result['target_P10_change'],-1)
 def test_numerical_pareto_tolerance_does_not_turn_roundoff_into_improvement(self):
  a=self.point(1,.5,2,3);b=self.point(1+1e-14,.5,2,3)
  self.assertFalse(m.dominates(b,a))

if __name__=='__main__':unittest.main()
