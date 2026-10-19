"""Independent waveform/circuit report fixtures; no research modules or PDE."""
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np


SPEC = importlib.util.spec_from_file_location('task1_waveform_check',
    Path(__file__).resolve().parents[1]/'tools/task1_waveform_check.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class WaveformTests(unittest.TestCase):
    def test_arbitrary_complex_phase_and_harmonics_remain_distinct(self):
        report = M.two_carrier_check([3000, 3030, 9000, 9090], [1j, .6, .5, -.3j], [3000, 3030])
        self.assertAlmostEqual(report['exact_width'], 1.2)
        actual = M.temporal_convergence([3000, 3030, 9000, 9090], [1j, .6, .5, -.3j])
        self.assertEqual(len(actual['levels']), 3)
        self.assertNotAlmostEqual(report['exact_width'], actual['levels'][-1]['all_frequency_analytic_envelope_width_lower'], places=2)
        self.assertFalse(actual['physical_mesh_and_instrument_convergence'])

    def test_same_frequency_complex_cancellation_precedes_RMS(self):
        result = M.signed_statistics([100, 100, 300], [1j, -1j, .4])
        self.assertAlmostEqual(result['spectral_RMS'], .4/math.sqrt(2))
        self.assertLess(result['RMS_relative_error'], 2e-12)

    def test_single_carrier_nonzero_RMS_but_zero_fundamental_TIS(self):
        result = M.two_carrier_check([3000, 9000], [2j, .5], [3000])
        self.assertEqual(result['exact_width'], 0)
        self.assertGreater(M.signed_statistics([3000, 9000], [2j, .5])['spectral_RMS'], 0)
        with self.assertRaises(ValueError):
            M.two_carrier_check([100, 101, 102], [1, 2, 3], [100, 101, 102])

    def test_polarized_complex_vector_direction_and_actual_vector_RMS(self):
        a, b = np.array([1j, 0, 0]), np.array([.5, 0, 0])
        c = dict(id='synthetic', waveform='sine', actual_fundamental_Hz=[2000, 2010],
            metrics=dict(target20_modulation_V_m=1., target20_total_E_RMS_V_m=math.sqrt(.625),
                centre_field_spectrum=[dict(frequency_Hz=f, real_V_m=v.real.tolist(), imaginary_V_m=v.imag.tolist())
                                       for f, v in [(2000, a), (2010, b)]]))
        result = M.field_check(c)
        self.assertAlmostEqual(result['saved_direction_max_TIS_V_m'], 1)
        self.assertEqual(result['direction_count'], 2074)
        c['metrics']['target20_modulation_V_m'] = 0
        with self.assertRaises(ValueError):
            M.field_check(c)

    def test_actual_waveform_extrema_bracket_contains_known_sine(self):
        result = M.signed_statistics([123], [1+.7j])
        expected = 2*abs(1+.7j)
        self.assertLessEqual(result['signed_Vpp_lower'], expected+1e-14)
        self.assertGreaterEqual(result['signed_Vpp_upper'], expected-1e-14)

    def test_bulk_skin_total_and_conductive_J_remain_distinct(self):
        grid = np.array([(0, 3.), (1, 1.), (2, 1.)], dtype=[('layer', 'i4'), ('volume_m3', 'f8')])
        field = np.array([[2, 0, 0], [4, 0, 0], [9, 0, 0]], complex)
        result = M.bulk_skin_current_density({2000: field}, grid, {2000: {0: 1+1j, 1: 1+1j, 2: 1+1j}})
        sc = result['regions']['SC']
        self.assertAlmostEqual(sc['total']['J_vector_RMS_max_A_m2'], 2)
        self.assertAlmostEqual(sc['conductive']['J_vector_RMS_max_A_m2'], math.sqrt(2))
        skin = result['regions']['skin_SC_plus_dermis']['total']
        self.assertAlmostEqual(skin['J_vector_RMS_p95_A_m2'], 4)
        self.assertAlmostEqual(skin['J_vector_RMS_volume_mean_A_m2'], 2.5)
        self.assertAlmostEqual(skin['region_energy_RMS_A_m2'], math.sqrt(7))


class C1Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.tis = self.fixture('tis', 2, [2., 4.], 3.)
        self.c1 = self.fixture('c1', 1, [1., 1.], .5)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self, name, channels, values, center):
        folder = self.root/name
        folder.mkdir()
        config = folder/'config.properties'
        config.write_text('sc.sigma=0.0002\nsc.epsilon_r=110000\nz.3000.re=0.0001\nz.3000.im=-0.0001\n')
        native = folder/'volume.npz'
        np.savez_compressed(native, RMS=np.asarray(values), region_target_m3=np.array([1., 3.]))
        metric = {key: 2. for key in (*M._LINEAR_METRICS, *M._POWER_METRICS)}
        metric.update(target20_modulation_V_m=1. if channels == 2 else 0.,
                      target20_total_E_RMS_V_m=center, source_current_RMS_by_output_mA=[2.]*channels)
        condition = dict(id=name+'-square_3h', waveform='square_3h', actual_fundamental_Hz=[3000, 3030] if channels == 2 else [3000],
            source_Vpp_per_output=1., metrics=metric, native_volume_archive='volume.npz',
            volume_metrics=dict(regions=dict(target=dict(statistics=dict(RMS=dict(mean=float(np.asarray(values)@np.array([1., 3.])/4)))))))
        meta = dict(h_xy_mm=1.25, radius_mm=25., total_depth_mm=25.1, sc_cells=2,
            bulk_layer_counts=[14, 14, 40], z_faces_mm=[0., .1, 5.1, 10.1, 25.1],
            tissue_boundaries_mm=[0., .1, 5.1, 10.1, 25.1], source_peak_V=.5, source_resistance_ohm=50.,
            phasor_convention='peak,+jomega_t', field_reconstruction='same synthetic fixture', channels=channels,
            config_sha256=M.sha256(config))
        summary = dict(id=name, status='complete', mesh_metadata=meta, source_normalization=dict(source_Vpp=1., source_resistance_ohm=50.),
            input_sha256={str(config): M.sha256(config)}, conditions=[condition],
            artifacts=dict(files={'volume.npz': dict(SHA256=M.sha256(native))}))
        path = folder/'summary.json'
        path.write_text(json.dumps(summary))
        return path

    def test_same_point_vs_ROI_energy_vs_mean_local_RMS(self):
        report = M.c1_report(self.tis, self.c1)
        matches = {row['criterion']: row for row in report['pairs']}
        self.assertAlmostEqual(matches['centre20_vector_E_RMS']['required_single_open_circuit_Vpp'], 6)
        self.assertAlmostEqual(matches['ROI_energy_E_RMS']['required_single_open_circuit_Vpp'], math.sqrt(13))
        self.assertAlmostEqual(matches['ROI_mean_local_E_RMS']['required_single_open_circuit_Vpp'], 3.5)
        center = matches['centre20_vector_E_RMS']['single_metrics_at_match']
        self.assertEqual(center['source_power_W'], 72.)
        self.assertEqual(center['surface_J_RMS_max_A_m2'], 12.)
        self.assertEqual(center['target20_modulation_V_m'], 0.)
        self.assertFalse(matches['centre20_vector_E_RMS']['envelope_or_physiological_equivalence'])

    def test_changed_contact_config_is_rejected(self):
        path = self.c1.parent/'config.properties'
        path.write_text(path.read_text().replace('0.0001', '0.0002'))
        with self.assertRaisesRegex(ValueError, 'config missing or changed'):
            M.c1_report(self.tis, self.c1)

    def test_native_volume_hash_and_derived_wave_alias_are_rejected(self):
        summary = json.loads(self.c1.read_text())
        self.c1.parent.joinpath('volume.npz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'archive SHA'):
            M.c1_report(self.tis, self.c1)
        condition = summary['conditions'][0]
        condition['waveform'] = 'sine'
        with self.assertRaisesRegex(ValueError, 'square_3h only'):
            M._roi_energy_rms(self.c1, summary, condition)


if __name__ == '__main__':
    unittest.main()
