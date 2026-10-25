"""Unrun tiny manufactured weighted-volume and scaling contracts."""
import unittest
import high_volume as subject

class WeightedThresholdContracts(unittest.TestCase):
    def fixture(self):
        import numpy as np
        grid=np.asarray([[0.,0.,1.,0.,1.],[1.,0.,2.,1.,1.],[2.,0.,3.,2.,1.],[3.,0.,4.,3.,1.]])
        return np,grid,np.asarray([1.,3.,3.,10.]),np.asarray([.8,.1,.05,0.])
    def test_fractional_physical_volume_not_cell_count_and_hotspot_ties(self):
        np,g,v,w=self.fixture();r=subject.threshold_summary(np,g,v,w,2.)
        self.assertAlmostEqual(r['high_modulation_volume_m3'],.15)
        self.assertAlmostEqual(r['high_modulation_volume_fraction'],.15/.95)
        self.assertEqual(r['hotspot_tie_count'],2);self.assertEqual(r['high_subset_maximum_V_m'],3.)
        self.assertEqual(r['high_subset_native_centre_bounds_mm'],{'minimum':[1.,0.,2.],'maximum':[2.,0.,3.]})
        self.assertEqual(r['layer_high_modulation_volume_m3'],{'1':.1,'2':.05})
    def test_scaling_changes_absolute_subset_without_mutating_original(self):
        np,g,v,w=self.fixture();original=v.copy();r=subject.threshold_summary(np,g,v,w,2.,.5)
        self.assertEqual(r['high_modulation_volume_m3'],0.);self.assertIsNone(r['high_subset_maximum_V_m'])
        np.testing.assert_array_equal(v,original)
        r=subject.threshold_summary(np,g,v,w,2.,2.)
        self.assertAlmostEqual(r['high_modulation_volume_m3'],.95);self.assertEqual(r['high_subset_maximum_V_m'],6.)
    def test_zero_drive_and_empty_ROI_remain_empty_without_nan_or_invented_hotspot(self):
        np,g,v,w=self.fixture();r=subject.threshold_summary(np,g,v,w,2.,0.)
        self.assertEqual(r['high_modulation_volume_fraction'],0.);self.assertEqual(r['hotspot_centres'],[])
        r=subject.threshold_summary(np,g,v,w*0,2.)
        self.assertIsNone(r['high_modulation_volume_fraction']);self.assertIsNone(r['weighted_native_centre_mm'])
    def test_expired_stage_rejects_before_partial_result_and_bad_weights_fail(self):
        np,g,v,w=self.fixture()
        with self.assertRaises(TimeoutError):subject.threshold_summary(np,g,v,w,2.,deadline_monotonic=0.)
        w[0]=-1.
        with self.assertRaises(ValueError):subject.threshold_summary(np,g,v,w,2.)

if __name__=='__main__':unittest.main()
