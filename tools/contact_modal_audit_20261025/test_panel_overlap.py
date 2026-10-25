"""Pure synthetic unit-test SOURCE; finite owner alone may execute it."""
import json
import math
import unittest
import panel_overlap as p


def numpy_for_test():
    import numpy as np
    return np


class PanelOverlapTests(unittest.TestCase):
    def test_constant_complex_field_on_unequal_physical_partitions(self):
        np=numpy_for_test()
        result=p.compare([-.0005,0.,.0005],[2.+3j,2.+3j],
                         [-.0005,-.0001,.0002,.0005],[2.+3j]*3,.2-.1j,np)
        s=result['summary'];a=result['arrays']
        self.assertAlmostEqual(s['overlap_length_m'],.001,places=15)
        self.assertEqual(s['overlap_links'],4)
        self.assertAlmostEqual(s['primary_pairwise']['absolute_spatial_peak_L2_A_m2'],0.)
        self.assertAlmostEqual(s['secondary_B_averaged_on_A']['absolute_spatial_peak_L2_A_m2'],0.)
        self.assertAlmostEqual(s['a']['spatial_complex_peak_RMS_A_m2'],math.sqrt(13.))
        np.testing.assert_allclose(a['old_covered_fraction'],1.,rtol=0,atol=1e-12)
        np.testing.assert_allclose(a['new_covered_fraction'],1.,rtol=0,atol=1e-12)
        self.assertFalse(s['automatic_gate_applied'])
        json.dumps(s,allow_nan=False)

    def test_fine_discontinuity_cancels_under_secondary_average_only(self):
        np=numpy_for_test()
        result=p.compare([-.0005,.0005],[0.],[-.0005,0.,.0005],[1.,-1.],1.,np)
        s=result['summary']
        self.assertAlmostEqual(s['primary_pairwise']['absolute_spatial_peak_L2_A_m2'],1.)
        self.assertAlmostEqual(s['secondary_B_averaged_on_A']['absolute_spatial_peak_L2_A_m2'],0.)
        self.assertAlmostEqual(s['within_A_B_variation_squared_A2_m4'],1.)
        self.assertAlmostEqual(s['projection_Pythagorean_closure_A2_m4'],0.)
        self.assertAlmostEqual(s['denominator_A_m2'],1.)

    def test_complex_norms_use_conjugation_and_rms_divides_by_sqrt_two(self):
        np=numpy_for_test()
        s=p.compare([-.0005,0.,.0005],[1j,1j],
                    [-.0005,.0005],[-1j],.2-.1j,np)['summary']
        self.assertAlmostEqual(s['a']['integral_abs_q_squared_A2_m3'],.001)
        self.assertAlmostEqual(s['a']['integral_q_squared_NONCONJUGATE_A2_m3']['real'],-.001)
        self.assertAlmostEqual(s['primary_pairwise']['absolute_spatial_peak_L2_A_m2'],2.)
        self.assertAlmostEqual(s['primary_pairwise']['absolute_temporal_RMS_difference_A_m2'],math.sqrt(2.))
        self.assertAlmostEqual(s['a']['length_weighted_J95_peak_A_m2'],1.)
        self.assertAlmostEqual(s['a']['length_weighted_J95_temporal_RMS_A_m2'],1./math.sqrt(2.))
        self.assertAlmostEqual(s['a']['active_contact_power_per_width_W_per_m'],.0001)
        self.assertAlmostEqual(s['a']['reactive_contact_power_per_width_var_per_m'],-.00005)

    def test_contact_power_difference_is_B_minus_A_and_per_unit_width(self):
        np=numpy_for_test()
        s=p.compare([-.0005,.0005],[1.],[-.0005,.0005],[2.],3.-4j,np)['summary']
        self.assertAlmostEqual(s['B_minus_A_integral_abs_q_squared_A2_m3'],.003)
        self.assertAlmostEqual(s['B_minus_A_active_contact_power_per_width_W_per_m'],.0045)
        self.assertAlmostEqual(s['B_minus_A_complex_contact_power_per_width_VA_per_m']['imaginary'],-.006)

    def test_J95_is_length_weighted_not_panel_count_weighted(self):
        np=numpy_for_test();edges=[-.0005,.00046,.0005]
        s=p.compare(edges,[1.,100.],edges,[1.,100.],1.,np)['summary']
        self.assertAlmostEqual(s['a']['length_weighted_J95_peak_A_m2'],1.)
        self.assertAlmostEqual(s['a']['panel_max_peak_A_m2'],100.)
        self.assertAlmostEqual(s['a']['spatial_complex_peak_RMS_A_m2'],math.sqrt(.96+.04*10000.))

    def test_zero_fields_disclose_denominator_floor(self):
        np=numpy_for_test()
        s=p.compare([-.0005,.0005],[0j],[-.0005,0.,.0005],[0j,0j],1.,np)['summary']
        self.assertTrue(s['denominator_floor_used'])
        self.assertEqual(s['denominator_A_m2'],1e-300)
        self.assertEqual(s['primary_pairwise']['normalized_L2'],0.)
        json.dumps(s,allow_nan=False)

    def test_missing_or_nonmatching_physical_coverage_is_rejected(self):
        np=numpy_for_test()
        for edges_a,qa,edges_b,qb in(
            ([-.0004,.0005],[1.],[-.0005,.0005],[1.]),
            ([-.0004,.0004],[1.],[-.0004,.0004],[1.]),
            ([-.0005,0.,-.0001,.0005],[1.,1.,1.],[-.0005,.0005],[1.]),
            ([-.0005,0.,.0005],[1.],[-.0005,.0005],[1.])):
            with self.subTest(edges_a=edges_a),self.assertRaises(ValueError):
                p.compare(edges_a,qa,edges_b,qb,1.,np)


if __name__=='__main__':unittest.main()
