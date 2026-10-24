"""Small synthetic physics/display fixtures; no actual native/API/CLI reads."""
import base64
import copy
import math
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_best1_pair_native as native


class BestPairNativeTest(unittest.TestCase):
    def test_peak_complex_vector_is_not_multiplied_by_an_extra_half(self):
        field=np.array([[3+4j,0,0],[1j,2,2j]],complex)
        np.testing.assert_allclose(native.pure_sine_rms(field),[5/math.sqrt(2),3/math.sqrt(2)])
        np.testing.assert_allclose(native.pure_sine_rms(-1j*field),native.pure_sine_rms(field))
        np.testing.assert_allclose(native.pure_sine_rms(field*2),2*native.pure_sine_rms(field))
        with self.assertRaises(ValueError):native.pure_sine_rms(np.ones((2,2)))

    def test_interpolate_complex_vector_before_norm_not_scalar_RMS(self):
        grid=np.array([[x,y,z,3,1]for z in(19.,21.)for y in(-1.,1.)for x in(-1.,1.)])
        field=np.zeros((8,3),complex);field[:,0]=grid[:,0]
        np.testing.assert_allclose(native._sample_complex(field,grid),[0,0,0],atol=1e-15)
        self.assertGreater(native.pure_sine_rms(field).mean(),.7)

    def test_fractional_volume_energy_RMS_is_not_mean_local_RMS(self):
        result=native.weighted_stats(np.array([0.,3.]),np.array([3.,1.]))
        self.assertEqual(.75,result['mean']);self.assertEqual(1.5,result['energy_RMS_V_m'])
        self.assertAlmostEqual(result['energy_RMS_V_m'],math.hypot(result['mean'],result['std']))
        self.assertEqual(0.,result['p10']);self.assertEqual(3.,result['p95']);self.assertEqual(4.,result['volume_m3'])
        with self.assertRaises(ValueError):native.weighted_stats(np.array([1.,2.]),np.array([1.,-1.]))

    def test_equal_ROI_energy_does_not_imply_equal_spatial_RMS_shape(self):
        tis=np.array([1.,3.]);c1=np.array([3.,1.]);weights=np.ones(2)
        self.assertEqual(native.weighted_stats(tis,weights)['energy_RMS_V_m'],native.weighted_stats(c1,weights)['energy_RMS_V_m'])
        result=native.scalar_shape_comparison(tis,c1,weights,1.,1.)
        self.assertEqual(2.,result['weighted_RMS_difference_V_m']);self.assertEqual(0.,result['target_fraction_within_10_percent_of_TIS'])
        self.assertAlmostEqual(2/math.sqrt(5),result['relative_RMS_difference_to_TIS_ROI_energy'])
        self.assertFalse(result['vector_or_waveform_equality']);self.assertTrue(result['numerical_10_percent_comparison_not_activation_threshold'])
        matched=native.scalar_shape_comparison(tis,tis*2,weights,1.,.5)
        self.assertEqual(0.,matched['weighted_RMS_difference_V_m']);self.assertEqual(1.,matched['target_fraction_within_10_percent_of_TIS'])

    def test_zero_reference_cell_only_matches_an_actual_zero(self):
        result=native.scalar_shape_comparison(np.array([0.,1.]),np.array([1.,1.]),np.ones(2),1.,1.)
        self.assertEqual(.5,result['target_fraction_within_10_percent_of_TIS'])
        with self.assertRaises(ValueError):native.scalar_shape_comparison(np.ones(2),np.ones(2),np.ones(2),0.,1.)

    def test_float16_error_is_checked_against_original_float64_and_nan_preserved(self):
        values=np.array([0.,1e-8,3.6457357391300533,1346.400298562412,np.nan]);before=values.copy()
        half,proof=native.half_values(values);use=np.isfinite(values)
        self.assertTrue(proof['passed']);self.assertTrue(np.isnan(half[-1]));np.testing.assert_equal(values,before)
        self.assertTrue(np.all(abs(half.astype(float)[use]-values[use])<=native.ABSOLUTE+native.RELATIVE*abs(values[use])))
        with np.errstate(over='ignore'),self.assertRaises(ValueError):native.half_values(np.array([70000.]))

    def test_two_physical_pads_keep_one_output_and_450_square_mm(self):
        case=dict(circuit=dict(n_pads=2,n_outputs=1,pad_to_node={'0':'out0','1':'GND'}),expected_pad_areas_m2=[225e-6]*2,
                  design=dict(pads=[dict(pad=i,polygon_mm=[[i,0],[i+1,0],[i+1,1]])for i in range(2)]))
        axes=dict(x=np.array([-10.,10.]),y=np.array([-10.,10.]))
        before=copy.deepcopy(case)
        result,proof=native._contact_display(np.array([0,1]),np.array([-10.,10.]),np.array([-10.,-10.]),
            np.array([225e-6]*2),np.array([10.,20.]),case,axes)
        self.assertEqual(450.,sum(p['area_mm2']for p in result['pad_centres']))
        self.assertEqual(['out0','GND'],[p['node']for p in result['pad_centres']])
        np.testing.assert_array_equal(np.frombuffer(base64.b64decode(result['pad_mask_b64']),dtype='<i2'),[0,1,-1,-1])
        self.assertTrue(proof['passed']);self.assertEqual(case,before)


if __name__=='__main__':unittest.main()
