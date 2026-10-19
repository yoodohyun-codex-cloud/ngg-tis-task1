"""Bounded synthetic checks; no existing simulation or PDE is run."""
from pathlib import Path
import json
import math
import tempfile
import unittest

import numpy as np
from explore_tis import MATERIALS
from single_vs_tis import (build_comparison, evaluate_single_basis,
                          loaded_terminal_vpp_bounds, scale_metrics)


class LoadedVoltageVppTests(unittest.TestCase):
    def test_sinusoidal_vpp_contains_2sqrt2_rms(self):
        phasor = .4*np.exp(.137j)
        lower, upper, metadata = loaded_terminal_vpp_bounds([2000], [[phasor]])
        expected = 2*math.sqrt(2)*(abs(phasor)/math.sqrt(2))
        self.assertLessEqual(lower[0], expected+1e-14)
        self.assertGreaterEqual(upper[0], expected-1e-14)
        self.assertLess(upper[0]-lower[0], .002)
        self.assertEqual(metadata['samples'], 64)
        self.assertEqual(metadata['period_s'], .0005)

    def test_asymmetric_multitone_range_is_not_twice_absolute_peak(self):
        # cos(t)+0.5cos(2t): max1.5, min-0.75, Vpp2.25; 2maxabs=3.
        lower, upper, metadata = loaded_terminal_vpp_bounds([1, 2], [[1.], [.5]])
        self.assertLessEqual(lower[0], 2.25+1e-14)
        self.assertGreaterEqual(upper[0], 2.25-1e-14)
        self.assertLess(upper[0], 2.253)
        self.assertLess(upper[0], 3)
        self.assertEqual(metadata['period_s'], 1)
        self.assertEqual(metadata['samples'], 128)

    def test_vpp_brackets_and_registered_metrics_scale_linearly(self):
        spectrum = np.array([[.7+.2j, .1j], [.3j, -.4]])
        lo, hi, _ = loaded_terminal_vpp_bounds([2000, 2010], spectrum)
        scaled_lo, scaled_hi, _ = loaded_terminal_vpp_bounds([2000, 2010], spectrum*7.3)
        np.testing.assert_allclose(scaled_lo, lo*7.3, rtol=1e-13)
        np.testing.assert_allclose(scaled_hi, hi*7.3, rtol=1e-13)
        base = {'source_load_voltage_Vpp_lower_by_output_V': lo.tolist(),
                'source_load_voltage_Vpp_upper_by_output_V': hi.tolist(),
                'max_source_load_voltage_Vpp_lower_V': float(lo.max()),
                'max_source_load_voltage_Vpp_upper_V': float(hi.max())}
        result = scale_metrics(base, 7.3)
        np.testing.assert_allclose(result['source_load_voltage_Vpp_upper_by_output_V'], hi*7.3)
        self.assertAlmostEqual(result['max_source_load_voltage_Vpp_lower_V'], lo.max()*7.3)


class SingleVsTisTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.profile = {'thickness_nm': 0, 'selected_fit': {'Rs_ohm': 0}, 'warnings': [],
                        'points': [{'frequency_Hz': f, 'Z_real_ohm': 10., 'Z_imag_ohm': -5.,
                                    'source_range': 'synthetic_test'}
                                   for f in (1, 10000)]}
        self.grid = [(x, y, z, 3, 1e-9) for z in (19., 21.)
                     for y in (-.3125, .3125) for x in (-.3125, .3125)]
        self.single_folder = self.make_basis('single', 1)
        self.tis_folder = self.make_basis('tis', 2)
        self.single = self.row('single', 1, .5)
        self.tis = self.row('tis', 2, 2.)
        self.paths = {name: {'basis_dir': str(folder), 'config_path': str(folder/'config.properties')}
                      for name, folder in (('single', self.single_folder), ('tis', self.tis_folder))}

    def make_basis(self, name, channels):
        folder = self.root/name
        folder.mkdir()
        (folder/'BASIS_COMPLETE').touch()
        (folder/'validation.json').write_text(json.dumps(dict(
            channels=channels, cells=len(self.grid), max_residual=1e-9,
            max_power_error=1e-9, max_current_error=1e-9)))
        (folder/'config.properties').write_text(''.join(f'{k}={v}\n' for k, v in MATERIALS.items()))
        np.savetxt(folder/'grid.csv', np.array(self.grid), delimiter=',', comments='',
                   header='x_mm,y_mm,z_mm,layer,volume_m3')
        frequencies = (2000, 6000) if channels == 1 else (2000, 2010, 6000, 6030)
        for f in frequencies:
            source = np.eye(channels, dtype='<c16')*.002
            loss = np.zeros((6, channels, channels), dtype='<c16')
            sc = .00001 if channels == 1 else .0001
            contact = .5*(.002/(225e-6))**2*.001*(2*225e-6) if channels == 1 else .00002
            for c in range(channels):
                loss[0, c, c] = sc
                loss[4, c, c] = contact
                loss[5, c, c] = .0001
                loss[3, c, c] = .0005-sc-contact-.0001
            source.tofile(folder/f'source-{f}.bin')
            loss.tofile(folder/f'loss-{f}.bin')
            if channels == 1:
                contacts = 'pad,x_mm,y_mm,area_m2\n0,-10,-10,0.000225\n1,10,-10,0.000225\n'
                (folder/f'contacts-{f}.csv').write_text(contacts)
                np.array([.002/225e-6, -.002/225e-6], dtype='<c16').tofile(folder/f'density-{f}.bin')
                field = np.zeros((1, len(self.grid), 3, 2), dtype='<f8')
                field[0, :, 0, 0] = np.array(self.grid)[:, 0]/.3125
                field[0, :, 0, 1] = 1
                field.tofile(folder/f'field-{f}.bin')
        return folder

    def row(self, identity, channels, response):
        sc = .00001 if channels == 1 else .0002
        contact = .5*(.002/(225e-6))**2*.001*(2*225e-6) if channels == 1 else .00004
        return dict(id=identity, basis_id=identity, h_mm=.625, thickness_nm=0,
                    layout='synthetic-'+identity, pad_size_mm=15, pad_count=channels*2,
                    output_channels=channels, xy_mm=[[-10, -10], [10, -10]]*channels,
                    waveform='sine', carrier_Hz=2000, beat_Hz=10,
                    carrier_group=[0] if channels == 1 else [0, 1],
                    phase_deg=[0.]*channels, boundary_mode='measured_minus_Rs',
                    target20_total_E_RMS_V_m=response,
                    target20_modulation_V_m=0 if channels == 1 else 3.9,
                    surface_J_RMS_max_A_m2=1 if channels == 1 else 8,
                    surface_J_RMS_p95_A_m2=.8 if channels == 1 else 6,
                    contact_voltage_RMS_max_V=.02 if channels == 1 else .08,
                    SC_power_W=sc, contact_power_W=contact,
                    source_power_W=.0005*channels,
                    max_source_current_RMS_mA=math.sqrt(2))

    def test_same_actual_rms_and_no1vpp_cap_and_single_zero_tis(self):
        report = build_comparison([self.tis], [self.single], self.paths)
        pair = report['comparisons'][0]
        self.assertEqual(pair['status'], 'complete')
        self.assertEqual(pair['match']['required_single_source_Vpp'], 4)
        self.assertEqual(pair['metrics_at_match']['single']['target20_total_E_RMS_V_m'], 2)
        self.assertEqual(pair['metrics_at_match']['single']['target20_modulation_V_m'], 0)
        self.assertFalse(pair['match']['envelope_match_possible'])
        self.assertFalse(pair['verification']['source_voltage_cap_applied'])
        self.assertIn('source_load_voltage_Vpp_upper_by_output_V', pair['metrics_at_match']['single'])
        self.assertFalse(report['differential_probe_assumptions']['actual_connection_confirmed'])
        self.assertIsNone(report['differential_probe_assumptions']['actual_hardware_model'])
        self.assertEqual(pair['metrics_at_match']['tis']['source_Vpp'], 1)
        self.assertEqual(pair['markers']['single_1Vpp']['source_Vpp'], 1)
        # Preserve a single-pair advantage instead of forcing TIS to win.
        self.assertEqual(pair['burden_ratios']['surface_J_RMS_max_A_m2'], .5)
        self.assertAlmostEqual(pair['burden_ratios']['SC_power_W'], .8)
        self.assertFalse(pair['compatibility']['total_electrode_area_cm2']['matched'])
        self.assertFalse(pair['compatibility']['total_electrode_area_cm2']['required'])

    def test_linear_quadratic_laws_and_curves_share_field_abscissa(self):
        report = build_comparison([self.tis], [self.single], self.paths, [0, 1, 2, 5])
        pair = report['comparisons'][0]
        scaled = pair['metrics_at_match']['single']
        self.assertEqual(scaled['surface_J_RMS_p95_A_m2'], .8*4)
        self.assertEqual(scaled['contact_voltage_RMS_max_V'], .02*4)
        self.assertAlmostEqual(scaled['source_power_W'], .0005*16)
        for target, tis, single in zip(pair['curves']['target_E_RMS_V_m'],
                                       pair['curves']['tis'], pair['curves']['single']):
            self.assertAlmostEqual(tis['target20_total_E_RMS_V_m'], target)
            self.assertAlmostEqual(single['target20_total_E_RMS_V_m'], target)
        self.assertGreater(max(v['source_Vpp'] for v in pair['curves']['single']), 1)
        self.assertEqual(scale_metrics(self.single, 0)['source_power_W'], 0)

    def test_zero_response_rejected_and_mesh_coating_mismatch_held(self):
        zero = build_comparison([self.tis], [dict(self.single, target20_total_E_RMS_V_m=0)], self.paths)
        self.assertEqual(zero['comparisons'][0]['status'], 'invalid_response')
        for changed in (dict(h_mm=1.25), dict(thickness_nm=50)):
            result = build_comparison([self.tis], [dict(self.single, **changed)], self.paths)
            self.assertEqual(result['comparisons'][0]['status'], 'held_incompatible')
        paths = {key: {'basis_dir': value['basis_dir']} for key, value in self.paths.items()}
        self.assertEqual(build_comparison([self.tis], [self.single], paths)['comparisons'][0]['status'],
                         'held_incompatible')

    def test_single_basis_evaluates_f_and3f_without_unused_beat_files(self):
        design = dict(channels=1, carrier_Hz=2000, size_mm=15,
                      xy_mm=[[-10, -10], [10, -10]], layout='test', h_mm=.625)
        sine = evaluate_single_basis(self.single_folder, design, self.profile, 'sine')
        square = evaluate_single_basis(self.single_folder, design, self.profile, 'square_3h')
        self.assertEqual(sine['basis_frequencies_Hz'], [2000])
        self.assertEqual(square['basis_frequencies_Hz'], [2000, 6000])
        self.assertAlmostEqual(sine['target20_total_E_RMS_V_m'], 1/math.sqrt(2))
        self.assertAlmostEqual(square['target20_total_E_RMS_V_m'], math.sqrt(.625))
        self.assertEqual(square['target20_modulation_V_m'], 0)
        self.assertTrue(square['electrical_verification']['contact_density_power_matches_loss'])
        self.assertFalse((self.single_folder/'source-2010.bin').exists())

    def test_failed_source_cache_and_contact_balance_are_not_accepted(self):
        self.single['max_source_current_RMS_mA'] = 99
        report = build_comparison([self.tis], [self.single], self.paths)
        self.assertEqual(report['single_controls'][0]['status'], 'validation_failed')
        np.array([.002/225e-6, 0], dtype='<c16').tofile(self.single_folder/'density-2000.bin')
        design = dict(channels=1, carrier_Hz=2000, size_mm=15,
                      xy_mm=[[-10, -10], [10, -10]], layout='test')
        with self.assertRaisesRegex(ValueError, 'conservation'):
            evaluate_single_basis(self.single_folder, design, self.profile, 'sine')


if __name__ == '__main__':
    unittest.main()
