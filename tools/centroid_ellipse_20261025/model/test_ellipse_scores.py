"""Scalar multiobjective comparison keeps absolute losses and uncertainty."""
import unittest
import ellipse_post as post
class EllipseScores(unittest.TestCase):
 def test_ratio_only_improvement_is_not_hidden_by_min4(self):
  base=dict(target_mean=1.,target_P10=.8,target_to_surface_mean=.1,target_to_offtarget_mean=.2)
  value=dict(target_mean=.5,target_P10=.4,target_to_surface_mean=.2,target_to_offtarget_mean=.4)
  result=post.score(value,base);self.assertEqual(result['robust_minimum_four_ratio'],.5);self.assertTrue(result['ratio_only_improvement_with_absolute_loss'])
  value['target_mean']=1.;result=post.score(value,base);self.assertTrue(result['ratio_only_improvement_with_absolute_loss']);self.assertFalse(result['absolute_target_losses']['target_mean']);self.assertTrue(result['absolute_target_losses']['target_P10'])
 def test_missing_ratios_are_unranked_and_strict_tradeoffs_retained(self):
  values={'A':dict(mean=1.,p10=1.),'B':dict(mean=2.,p10=.5),'C':dict(mean=.5,p10=.5),'missing':dict(mean=None,p10=1.)}
  result=post.pareto(values);self.assertEqual(result['A']['status'],'provisional_nondominated');self.assertEqual(result['B']['status'],'provisional_nondominated');self.assertEqual(result['C']['status'],'provisional_dominated');self.assertEqual(result['missing']['status'],'not_ranked_missing_objective')
 def test_tiny_partial_contact_peak_is_disclosed_without_correction(self):
  import numpy as np
  face=.0005**2;grid=np.asarray([[0.,0.,0.,0.,1.],[1.,0.,0.,0.,1.],[0.,1.,0.,0.,1.],[1.,1.,0.,0.,1.]])
  common=dict(contact_area_m2=face*np.asarray([1.,.01,.5,1.]),contact_pad=np.arange(4),contact_xy_index=np.arange(4))
  raw0=dict(common,contact_normal_J_peak_A_m2=np.asarray([1.,10.,2.,1.],complex),contact_drop_peak_V=np.asarray([1.,10.,2.,1.],complex));raw1=dict(common,contact_normal_J_peak_A_m2=np.zeros(4,complex),contact_drop_peak_V=np.zeros(4,complex))
  result=post.partial_contact_diagnostics(np,grid,[raw0,raw1]);self.assertEqual(result['maximum_J_RMS_site']['physical_pad'],1);self.assertAlmostEqual(result['maximum_J_RMS_site']['fraction_of_full_surface_face'],.01);self.assertAlmostEqual(result['maximum_J_RMS_site']['contact_normal_J_RMS_A_m2'],10/np.sqrt(2));self.assertTrue(result['no_correction_factor_applied']);self.assertFalse(result['minimum_fraction_used_as_cutoff'])
if __name__=='__main__':unittest.main()
