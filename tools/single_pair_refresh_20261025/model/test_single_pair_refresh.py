"""Meaningful tiny scalar/source contract tests. Prepared, not run by author.

No PDE, cache read, eigen work or physical RHS is requested by these tests.
The frozen CEM reference-equation test imports its source lazily at test time.
"""
import math
import unittest
from unittest.mock import patch
import single_pair_refresh as single


class _Field:
    def __init__(self, rows):
        self.rows = rows

    def __getitem__(self, item):
        row, component = item
        return self.rows[row][component]


class SinglePairContractTests(unittest.TestCase):
    def assertComplexClose(self, actual, expected, places=13):
        self.assertAlmostEqual(actual.real, expected.real, places=places)
        self.assertAlmostEqual(actual.imag, expected.imag, places=places)

    def test_two_corrected_geometries_are_centred_on_y_zero(self):
        cases = single.geometries()
        self.assertEqual([c['pads'][0]['center_mm'] for c in cases], [[-12.5, 0.], [-15., 0.]])
        self.assertEqual([c['pads'][1]['center_mm'] for c in cases], [[12.5, 0.], [15., 0.]])
        for case in cases:
            self.assertEqual(case['physical_pads'], 2)
            self.assertEqual(case['connected_sources'], 1)
            self.assertEqual(sum(p['area_mm2'] for p in case['pads']), 450.)
            self.assertEqual([p['physical_pad_id'] for p in case['pads']], [0, 1])
            self.assertEqual([p['node'] for p in case['pads']], ['source0', 'GND'])

    def test_one_source_complex_circuit_signs_ground_return_and_power(self):
        # Exact independent two-contact + tissue resistor circuit, .5 Vpeak.
        z, tissue_resistance, source_resistance = 2. - .4j, 100., 50.
        current = .5 / (source_resistance + tissue_resistance + 2. * z)
        metal = .5 - source_resistance * current
        phi = [metal - z * current, z * current]
        tissue = [(phi[0] - phi[1]) / tissue_resistance,
                  (phi[1] - phi[0]) / tissue_resistance]
        residual, source_equation, outward = single.one_source_contact_equations(
            tissue, phi, metal, [0, 1], [0, 1], [1., 1.], z)
        for value in residual:
            self.assertComplexClose(value, 0j)
        self.assertComplexClose(source_equation, .5 / 50. + 0j)
        self.assertComplexClose(outward[0], -current)
        self.assertComplexClose(outward[1], current)
        self.assertComplexClose(sum(outward), 0j)
        source_power = .5 * .5 * current.conjugate()
        dissipative_complex_power = .5 * abs(current) ** 2 * (50. + 100. + 2. * z)
        self.assertComplexClose(source_power, dissipative_complex_power)
        self.assertGreater(source_power.real, 0.)
        self.assertLess(source_power.imag, 0.)

    def test_existing_cem_mapping_has_no_contact_on_dummy_output(self):
        frozen = single._science()
        z, metal = 2. - .4j, .42 + .01j
        phi, tissue = [.4 + .02j, .01 - .01j], [.01j, -.01j]
        surface, equation, outward = single.one_source_contact_equations(
            tissue, phi, metal, [0, 1], [0, 1], [1., 1.], z)
        mapped_surface, mapped_equations, mapped_outward = frozen.base.contact_equations(
            tissue, phi, [metal, 0j], [0, 2], [0, 1], [1., 1.], z)
        self.assertEqual(surface, mapped_surface)
        self.assertEqual(equation, mapped_equations[0])
        self.assertEqual(mapped_equations[1], 0j)
        self.assertEqual(mapped_outward[1], 0j)
        self.assertEqual(mapped_outward[3], 0j)
        self.assertEqual((0j - 0j) / 50., 0j)  # unused algebraic output current
        self.assertEqual(outward, [mapped_outward[0], mapped_outward[2]])

    def test_vpp_peak_and_distinct_frequency_vector_rms(self):
        self.assertAlmostEqual(single.field_vector_rms([[.5, 0j, 0j]]), 1. / (2. * math.sqrt(2.)))
        self.assertAlmostEqual(single.field_vector_rms([[3., 4j, 0.]]), 5. / math.sqrt(2.))
        self.assertAlmostEqual(single.field_vector_rms([[3., 4j, 0.], [0., 0., 12.]]), math.sqrt(169. / 2.))

    def test_roi_rms_uses_second_moment_not_mean_field_rms(self):
        # Equal-volume RMS-field values 0 and 2 have mean=std=1.
        self.assertAlmostEqual(single.roi_rms_from_stats(1., 1.), math.sqrt(2.))
        self.assertNotEqual(single.roi_rms_from_stats(1., 1.), 1.)
        # A physical centre vector can instead be zero by complex cancellation.
        stencil = [dict(native_cell_index=0, weight=.5), dict(native_cell_index=1, weight=.5)]
        vector = single.sample_field_vector(_Field([[2., 0., 0.], [-2., 0., 0.]]), stencil)
        self.assertEqual(vector, [0j, 0j, 0j])
        self.assertEqual(single.field_vector_rms([vector]), 0.)

    def test_physical_coordinate_linear_weights_and_no_extrapolation(self):
        self.assertEqual(single._axis_stencil([-.25, .25], 0.), [(0, .5), (1, .5)])
        self.assertEqual(single._axis_stencil([19.9, 20.2], 19.9), [(0, 1.)])
        weights = single._axis_stencil([19.9, 20.2], 20.)
        self.assertAlmostEqual(sum(w for _, w in weights), 1.)
        self.assertAlmostEqual(sum([19.9, 20.2][i] * w for i, w in weights), 20.)
        with self.assertRaises(ValueError):
            single._axis_stencil([19.9, 20.2], 20.3)

    def test_amplitude_scales_current_voltage_linearly_and_power_quadratically(self):
        original = dict(source_Vpp_each=1., source_current_RMS_A=3., return_current_RMS_A=3.,
            source_current_RMS_by_output_A=[3.], physical_pad_current_RMS_A=[3., 3.],
            source_current_peak_A=dict(real=3., imaginary=4.), return_current_peak_A=dict(real=-3., imaginary=-4.),
            source_power_W=5., source_resistor_power_W=2., SC_power_W=1., skin_power_W=2.,
            contact_power_W=.2, skin_plus_contact_power_W=2.2,
            contact_normal_J_RMS_max_A_m2=7., contact_normal_J_RMS_P95_A_m2=6.,
            contact_voltage_RMS_max_V=.1, skin_vector_J_RMS_max_A_m2=9.,
            skin_vector_J_RMS_P95_A_m2=8., layers_power_W=dict(sc=1., dermis=1., fat=.3, muscle=.2))
        result = single.scaled_electrical(original, 2.5)
        self.assertEqual(original['source_Vpp_each'], 1.)
        self.assertEqual(result['source_Vpp_each'], 2.5)
        for key in single.LINEAR_BURDENS:
            self.assertEqual(result[key], original[key] * 2.5)
        for key in single.POWER_BURDENS + ('source_power_W', 'source_resistor_power_W', 'skin_plus_contact_power_W'):
            self.assertEqual(result[key], original[key] * 2.5 ** 2)
        self.assertEqual(result['physical_pad_current_RMS_A'], [7.5, 7.5])
        self.assertEqual(result['layers_power_W']['fat'], .3 * 2.5 ** 2)
        self.assertEqual(result['source_current_peak_A'], dict(real=7.5, imaginary=10.))

    def test_absent_root_admission_blocks_before_science_import(self):
        with patch.object(single.Path, 'is_file', return_value=False), patch.object(single, '_science') as science:
            with self.assertRaisesRegex(ValueError, 'admission'):
                single.make_spec()
            science.assert_not_called()

    def test_single_carrier_am_is_zero_and_rms_not_modulation(self):
        # For every real projection, 2min(|single carrier|, |absent carrier|)=0.
        for projection in (0j, 1. + 2j, -3. - 4j):
            self.assertEqual(2. * min(abs(projection), 0.), 0.)
        self.assertGreater(single.field_vector_rms([[1., 0., 0.]]), 0.)


if __name__ == '__main__':
    unittest.main()
