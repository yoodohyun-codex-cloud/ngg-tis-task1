"""Synthetic native-potential contracts; no PDE or old field cache is used."""
from pathlib import Path
import json
import math
import tempfile
import unittest

import numpy as np
from depth_probe_comparison import evaluate_depth_probe


class DepthProbeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.grid = np.array([(x, y, z, 3, 1e-9) for z in (18, 19, 20, 21, 22)
                              for y in range(-4, 5) for x in range(-4, 5)], float)
        np.savetxt(self.folder/'grid.csv', self.grid, delimiter=',', comments='',
                   header='x_mm,y_mm,z_mm,layer,volume_m3')
        (self.folder/'BASIS_COMPLETE').touch()

    def make_basis(self, gradients, row, offset=.23+.07j):
        channels = row['output_channels']
        (self.folder/'validation.json').write_text(json.dumps(dict(
            channels=channels, cells=len(self.grid), max_residual=1e-9,
            max_power_error=1e-9, max_current_error=1e-9)))
        xyz = self.grid[:, :3]/1000
        xyz[:, 2] -= .020
        for frequency, gradient in gradients.items():
            gradient = np.asarray(gradient, complex)
            phi = np.asarray(offset+gradient@xyz.T, dtype='<c16')
            field = np.broadcast_to(-gradient[:, None, :], (channels, len(xyz), 3))
            phi.tofile(self.folder/f'potential-{frequency}.bin')
            np.asarray(field, dtype='<c16').tofile(self.folder/f'field-{frequency}.bin')
            np.asarray(np.eye(channels)*.002, dtype='<c16').tofile(self.folder/f'source-{frequency}.bin')
            loss = np.zeros((6, channels, channels), dtype='<c16')
            loss[3] = np.eye(channels)*.0005
            loss.tofile(self.folder/f'loss-{frequency}.bin')

    @staticmethod
    def single_row():
        return dict(id='synthetic-C1', output_channels=1, carrier_group=[0], phase_deg=[0.],
                    carrier_Hz=3000, beat_Hz=0, waveform='sine',
                    target20_total_E_RMS_V_m=1., max_source_current_RMS_mA=math.sqrt(2),
                    source_power_W=.0005)

    def test_linear_complex_potential_difference_and_sign(self):
        row = self.single_row()
        self.make_basis({3000: [[1+2j, 3-1j, .4j]]}, row)
        result = evaluate_depth_probe(self.folder, row, plot_duration_s=None)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(result['verification']['phi_E_consistency']['passed'])
        # coeff=-j; Δphi_X=.005*(1+2j) before drive phase.
        x = result['axes']['X']
        spectrum = x['spectrum'][0]
        self.assertAlmostEqual(spectrum['delta_potential_re_V'], .010, places=14)
        self.assertAlmostEqual(spectrum['delta_potential_im_V'], -.005, places=14)
        self.assertAlmostEqual(x['RMS_V'], math.sqrt(.010**2+.005**2)/math.sqrt(2), places=14)
        expected = 2*math.sqrt(.010**2+.005**2)
        self.assertLessEqual(x['Vpp_lower_V'], expected+1e-14)
        self.assertGreaterEqual(x['Vpp_upper_V'], expected-1e-14)
        # Endpoints±2.5mm require interpolation between original integer centres.
        self.assertEqual(x['spacing_mm'], 5)

    def test_endpoint_swap_changes_complex_sign_but_not_rms_or_vpp(self):
        row = self.single_row()
        self.make_basis({3000: [[2+.3j, 0, 0]]}, row)
        normal = evaluate_depth_probe(self.folder, row, plot_duration_s=None)['axes']['X']
        reversed_result = evaluate_depth_probe(self.folder, row,
            points={'X': {'plus_mm': [-2.5, 0, 20], 'minus_mm': [2.5, 0, 20]}},
            plot_duration_s=None)['axes']['X']
        self.assertAlmostEqual(normal['spectrum'][0]['delta_potential_re_V'],
                               -reversed_result['spectrum'][0]['delta_potential_re_V'])
        self.assertAlmostEqual(normal['RMS_V'], reversed_result['RMS_V'])
        self.assertAlmostEqual(normal['Vpp_lower_V'], reversed_result['Vpp_lower_V'])

    def test_zero_difference_gauge_invariance_and_linear_scaling(self):
        row = self.single_row()
        gradient = {3000: [[1+1j, 0, .4j]]}
        self.make_basis(gradient, row, offset=.2)
        a = evaluate_depth_probe(self.folder, row)
        self.assertEqual(a['axes']['Y']['RMS_V'], 0)
        self.assertEqual(a['axes']['Y']['Vpp_upper_V'], 0)
        self.make_basis(gradient, row, offset=4+3j)
        b = evaluate_depth_probe(self.folder, row, amplitude=1.488314342157298)
        for key in ('RMS_V', 'Vpp_lower_V', 'Vpp_upper_V', 'absolute_peak_lower_V'):
            self.assertAlmostEqual(b['axes']['X'][key], a['axes']['X'][key]*1.488314342157298,
                                   places=12)
        self.assertTrue(b['axes']['X']['time_plot']['Vpp_from_full_period_not_plot'])
        self.assertEqual(b['axes']['X']['time_plot']['duration_s'], .002)

    def test_asymmetric_range_full_period_differs_from_short_plot(self):
        row = dict(id='synthetic-C2', output_channels=2, carrier_group=[0, 1], phase_deg=[0, 0],
                   carrier_Hz=1, beat_Hz=1, waveform='sine', source_power_W=.001,
                   max_source_current_RMS_mA=math.sqrt(2))
        self.make_basis({1: [[200j, 0, 0], [0, 0, 0]],
                         2: [[0, 0, 0], [100j, 0, 0]],
                         3: np.zeros((2, 3)), 6: np.zeros((2, 3))}, row)
        result = evaluate_depth_probe(self.folder, row)
        self.assertEqual(result['status'], 'complete')
        axis = result['axes']['X']
        self.assertLessEqual(axis['Vpp_lower_V'], 2.25+1e-12)
        self.assertGreaterEqual(axis['Vpp_upper_V'], 2.25-1e-12)
        self.assertLess(axis['Vpp_upper_V'], 2*axis['absolute_peak_lower_V'])
        plot = axis['time_plot']['voltage_V']
        self.assertLess(max(plot)-min(plot), axis['Vpp_lower_V'])
        self.assertEqual(axis['full_period']['period_s'], 1)

    def test_missing_native_potential_or_inconsistent_E_is_not_replaced(self):
        row = self.single_row()
        missing = evaluate_depth_probe(self.folder, row)
        self.assertEqual(missing['status'], 'unavailable')
        self.assertEqual(missing['axes'], {})
        self.make_basis({3000: [[1, 0, 0]]}, row)
        path = self.folder/'field-3000.bin'
        field = np.fromfile(path, dtype='<c16').reshape(1, len(self.grid), 3)
        field[..., 0] += .1
        field.tofile(path)
        result = evaluate_depth_probe(self.folder, row)
        self.assertEqual(result['status'], 'validation_failed')
        self.assertFalse(result['verification']['phi_E_consistency']['passed'])
        self.assertEqual(result['axes'], {})


if __name__ == '__main__':
    unittest.main()
