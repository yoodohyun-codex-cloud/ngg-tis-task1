"""Synthetic instrument network/waveform checks only; no research data or PDE."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('task1_instrument_prediction', TOOLS/'task1_instrument_prediction.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def complex_value(record):
    return complex(record['real'], record['imaginary'])


class InstrumentNetworkTests(unittest.TestCase):
    def setUp(self):
        self.config = M.read(M.DEFAULT_CONFIG)

    def test_differential_spec_is_two_ground_shunts_not_an_extra_parallel_branch(self):
        M.validate_config(self.config)
        response = M.input_admittances(3000, self.config)
        each = 1/4e6+1j*2*np.pi*3000*7e-12
        self.assertAlmostEqual(complex_value(response['each_tip_to_reference_ground_admittance']), each)
        self.assertAlmostEqual(complex_value(response['differential_port_admittance']), each/2)
        self.assertAlmostEqual(complex_value(response['differential_port_impedance']), 2/each)
        self.assertAlmostEqual(complex_value(response['common_mode_pair_admittance']), 2*each)
        # Adding an independent 8Mohm shunt would incorrectly double this G.
        self.assertAlmostEqual(response['differential_port_admittance']['real'], 1/8e6)
        invalid = copy.deepcopy(self.config)
        invalid['probe']['between_inputs']['capacitance_F'] = 7e-12
        with self.assertRaisesRegex(ValueError, 'no extra branch'):
            M.validate_config(invalid)

    def test_scope_R_C_and_tolerance_are_downstream_not_added_to_phantom(self):
        response = M.input_admittances(9090, self.config)
        scope = response['downstream_scope_input']
        self.assertFalse(scope['phantom_parallel_load'])
        self.assertEqual(len(scope['user_tolerance_corners']), 4)
        self.assertEqual({corner['resistance_ohm'] for corner in scope['user_tolerance_corners']}, {980000., 1020000.})
        self.assertTrue(np.allclose(sorted({corner['capacitance_F'] for corner in scope['user_tolerance_corners']}), [13e-12, 19e-12]))
        expected = 1/(1/1e6+1j*2*np.pi*9090*16e-12)
        self.assertAlmostEqual(complex_value(scope['nominal_impedance']), expected)
        self.assertAlmostEqual(response['differential_port_admittance']['real'], 1/8e6)

    def test_missing_port_impedance_holds_actual_loaded_prediction(self):
        prediction = M.loading_prediction()
        self.assertEqual(prediction['status'], 'held_missing_native_port_response')
        self.assertIsNone(prediction['loaded_Vpp_V'])
        self.assertIsNone(prediction['loaded_RMS_V'])
        self.assertIn('-Z_port', prediction['equations']['first_order_tip_change'])
        self.assertFalse(prediction['full_PDE_probe_loading_recomputed'])

    def test_first_order_formula_and_exact_supplied_port_solve_differ_as_expected(self):
        v0 = np.array([1+.1j, .2-.3j])
        z = np.diag([1000., 2000.])
        y = np.array([1e-6, 1e-6])
        result = M.loading_prediction(v0, z, y)
        loaded = np.array([complex_value(item) for item in result['exact_linear_port_voltages']])
        first = np.array([complex_value(item) for item in result['first_order_change']])
        np.testing.assert_allclose(loaded, v0/(1+np.array([.001, .002])))
        np.testing.assert_allclose(first, -np.array([.001, .002])*v0)
        self.assertLessEqual(np.linalg.norm(loaded-v0-first), result['first_order_remainder_norm_upper_V'])
        self.assertFalse(result['actual_tip_model_validated'])
        self.assertFalse(result['full_PDE_probe_loading_recomputed'])

    def test_same_open_differential_voltage_does_not_determine_common_mode_loading(self):
        z, y = np.diag([1000., 5000.]), [1e-4, 1e-4]
        a = M.loading_prediction([.5, -.5], z, y)
        b = M.loading_prediction([10.5, 9.5], z, y)
        self.assertNotAlmostEqual(complex_value(a['exact_linear_port_differential_voltage']),
                                  complex_value(b['exact_linear_port_differential_voltage']))
        with self.assertRaisesRegex(ValueError, '2x2 port Z'):
            M.loading_prediction([1, 0], np.eye(3), y)

    def test_one_pole_is_explicit_assumption_with_correct_complex_phase(self):
        transfer = M.assumed_one_pole_transfer([15e6], self.config)[0]
        self.assertAlmostEqual(transfer, (.5-.5j)/(1+.75j))
        self.assertLess(transfer.imag, 0.)
        self.assertFalse(self.config['illustrative_filter_option']['enabled_by_default'])
        self.assertIn('do not determine', self.config['illustrative_filter_option']['status'])

    def test_user_provenance_urls_and_unknown_actual_hardware_settings_preserved(self):
        self.assertFalse(self.config['provenance']['independent_manufacturer_verification_performed'])
        self.assertEqual(self.config['provenance']['urls'], [
            'https://en.tw-eta.com/index.php?c=show&id=121',
            'https://go.keysight.com/us/en/assets/7018-06411/data-sheets/5992-3484.pdf'])
        self.assertIsNone(self.config['probe']['actual_attenuation_switch'])
        self.assertIsNone(self.config['scope']['actual_bandwidth_option_Hz'])
        self.assertFalse(self.config['recommended_start_configuration']['external_50ohm_termination'])


class InstrumentWaveformTests(unittest.TestCase):
    def setUp(self):
        self.config = M.read(M.DEFAULT_CONFIG)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        frequencies = [100, 110, 300, 330]
        phasors = [complex(.003, .001), complex(.002, -.001), complex(.0004, -.0002), complex(.0003, .0001)]
        self.stats = M.spectral_report(frequencies, phasors, [100, 110])
        spectrum = [dict(frequency_Hz=f, real_V=value.real, imaginary_V=value.imag) for f, value in zip(frequencies, phasors)]
        centers = [('centre', 0, 0), ('x_plus', 5, 0), ('x_minus', -5, 0), ('y_plus', 0, 5), ('y_minus', 0, -5)]
        rows = []
        for depth in (5, 10, 15, 20):
            for name, x, y in centers:
                for axis in ('X', 'Y'):
                    offset = np.array([2.5, 0., 0.]) if axis == 'X' else np.array([0., 2.5, 0.])
                    center = np.array([x, y, depth], float)
                    rows.append(dict(id=f'd{depth}-{name}-{axis}', status='complete',
                        depth_from_skin_surface_mm=depth, position=name, axis=axis,
                        centre_mm=center.tolist(), plus_mm=(center+offset).tolist(), minus_mm=(center-offset).tolist(),
                        tip_gap_mm=5., plus_centre_pitch_mm=5., spectrum=spectrum,
                        RMS_V=self.stats['RMS_V'], Vpp_lower_V=self.stats['Vpp_lower_V'], Vpp_upper_V=self.stats['Vpp_upper_V'],
                        fundamental_fixed_axis_envelope=dict(frequencies_Hz=[100, 110])))
        self.row = rows[0]
        probe40 = dict(status='complete', counts=dict(complete=40), expected_waveform_count=40,
            provenance=dict(source_run_id='synthetic-run', source_condition_id='synthetic-case', source_candidate_id='synthetic-case-square_3h'),
            coordinate_system=dict(unit='mm', surface_z_mm=0., depth_axis='+z'),
            measurement_grid=dict(depths_mm=[5., 10., 15., 20.], plus_centre_pitch_mm=5., tip_gap_mm=5.), measurements=rows)
        self.probes_path = self.root/'probes.json'
        self.probes_path.write_text(json.dumps(dict(status='complete', conditions=[dict(id='synthetic-case-square_3h', waveform='square_3h', probe40=probe40)])))
        summary = dict(status='complete', id='synthetic-case',
            conditions=[dict(id='synthetic-case-square_3h', waveform='square_3h', source_Vpp_per_output=1.)],
            artifacts=dict(probes_json='probes.json', files={'probes.json': dict(SHA256=M.sha(self.probes_path))}))
        self.summary_path = self.root/'summary.json'
        self.summary_path.write_text(json.dumps(summary))

    def test_both_matched_attenuation_options_preserve_displayed_voltage(self):
        result = M.probe_prediction(self.row, self.config)
        self.assertEqual(len(result['scenarios']), 1)
        options = result['scenarios'][0]['matched_options']
        self.assertEqual([item['hardware_attenuation'] for item in options], [50, 500])
        self.assertAlmostEqual(options[0]['BNC_RMS_V']/options[1]['BNC_RMS_V'], 10.)
        for option in options:
            self.assertAlmostEqual(option['displayed_input_referred_RMS_V'], self.stats['RMS_V'])
            self.assertAlmostEqual(option['BNC_Vpp_lower_V']*option['scope_probe_factor'], self.stats['Vpp_lower_V'])
            self.assertFalse(option['probe_output_impedance_loading_effect_included'])
        self.assertEqual(result['actual_loaded_prediction']['status'], 'held_missing_native_port_response')

    def test_optional_filter_retains_phases_and_remains_unloaded_unvalidated(self):
        result = M.probe_prediction(self.row, self.config, illustrative_one_pole=True, include_plots=True)
        base, assumed = result['scenarios']
        self.assertEqual(len(result['scenarios']), 2)
        self.assertLess(assumed['tip_equivalent_output']['RMS_V'], base['tip_equivalent_output']['RMS_V'])
        self.assertFalse(assumed['phantom_input_loading_included'])
        self.assertFalse(assumed['actual_instrument_transfer_validated'])
        self.assertIn('assumed_not_measured', assumed['status'])
        spectrum = assumed['tip_equivalent_output']['spectrum']
        original = self.row['spectrum'][0]
        expected = complex(original['real_V'], original['imaginary_V'])*M.assumed_one_pole_transfer([original['frequency_Hz']], self.config)[0]
        self.assertAlmostEqual(complex_value(spectrum[0]['peak_voltage']), expected)
        self.assertTrue(base['time_plot']['display_samples_do_not_replace_Vpp_bounds'])
        self.assertLessEqual(len(base['time_plot']['time_ms']), 1025)
        self.assertTrue(assumed['tip_equivalent_output']['fundamental_envelope']['third_harmonics_excluded'])

    def test_40_probe_result_retains_run_candidate_hashes_and_does_not_claim_loading(self):
        report = M.build_prediction(self.summary_path)
        self.assertEqual(report['conditions'][0]['complete_probes'], 40)
        self.assertEqual(report['conditions'][0]['source_run_id'], 'synthetic-run')
        self.assertEqual(report['conditions'][0]['candidate_id'], 'synthetic-case-square_3h')
        self.assertEqual(report['summary_sha256'], M.sha(self.summary_path))
        self.assertEqual(len(report['input_network_frequency_response']), 4)
        self.assertFalse(report['actual_hardware_settings_verified'])
        self.assertIsNone(report['actual_loaded_prediction']['loaded_Vpp_V'])
        self.assertEqual(report['new_PDE'], 0)

    def test_changed_probe_hash_and_wrong_center_gap_semantics_are_rejected(self):
        self.probes_path.write_text(self.probes_path.read_text()+' ')
        with self.assertRaisesRegex(ValueError, 'SHA differs'):
            M.build_prediction(self.summary_path)
        summary = M.read(self.summary_path)
        probes = M.read(self.probes_path)
        probes['conditions'][0]['probe40']['measurements'][0]['plus_mm'][0] = 5.
        self.probes_path.write_text(json.dumps(probes))
        summary['artifacts']['files']['probes.json']['SHA256'] = M.sha(self.probes_path)
        self.summary_path.write_text(json.dumps(summary))
        with self.assertRaisesRegex(ValueError, 'tip endpoints differ'):
            M.build_prediction(self.summary_path)


class InstrumentCLIGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root_patch = patch.object(M, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.run = self.root/'data-native/cloud-synthetic'
        folder = self.run/'postprocess/synthetic-case'
        folder.mkdir(parents=True)
        (self.run/'configs').mkdir()
        (self.run/'cases').mkdir()
        config = self.run/'configs/synthetic-case.properties'
        config.write_text('channels=2\n')
        digest = M.sha(config)
        self.summary = folder/'summary.json'
        self.summary.write_text(json.dumps(dict(status='complete', id='synthetic-case',
            mesh_metadata=dict(config_sha256=digest))))
        self.record = self.run/'cases/synthetic-case.json'
        self.original_record = dict(id='synthetic-case', status='complete', config_sha256=digest,
            postprocess_sha256=M.sha(self.summary), postprocess_path=str(self.summary))
        self.record.write_text(json.dumps(self.original_record))
        (self.run/'preregistration.json').write_text(json.dumps(dict(cases=[dict(id='synthetic-case',
            config_sha256=digest, config_file=str(config))])))
        (self.run/'controller.json').write_text('{"status":"complete","phase":"finished"}')
        (self.run/'summary.json').write_text('{"status":"complete"}')
        self.supplement = self.root/'docs/cloud-restart-20261020/instruments/synthetic.json'

    def test_supplement_and_matching_raw_audit_outputs_allowed_other_destinations_rejected(self):
        run, eligibility = M.validate_actual_request(self.summary, self.supplement)
        self.assertEqual(run, self.run)
        self.assertTrue(eligibility['output_is_git_supplement'])
        _, raw = M.validate_actual_request(self.summary, self.run/'audit/synthetic.json')
        self.assertFalse(raw['output_is_git_supplement'])
        with self.assertRaisesRegex(ValueError, 'unique output'):
            M.validate_actual_request(self.summary, self.root/'docs/elsewhere.json')
        with self.assertRaisesRegex(ValueError, 'unique output'):
            M.validate_actual_request(self.summary, self.root/'data-native/cloud-other/audit/other.json')
        self.supplement.parent.mkdir(parents=True)
        self.supplement.write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'unique output'):
            M.validate_actual_request(self.summary, self.supplement)

    def test_complete_case_inside_failed_terminal_run_retains_error_status(self):
        (self.run/'controller.json').write_text('{"status":"error","phase":"stopped"}')
        (self.run/'summary.json').write_text('{"status":"error"}')
        _, eligible = M.validate_actual_request(self.summary, self.supplement)
        self.assertEqual(eligible['source_run_original_terminal_status'], 'error')
        self.assertFalse(eligible['failed_run_promoted_to_complete'])
        self.assertEqual(M.read(self.run/'summary.json')['status'], 'error')

    def test_postprocessed_case_without_complete_execution_record_is_ineligible(self):
        record = dict(self.original_record, status='error')
        self.record.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'must both be complete'):
            M.validate_actual_request(self.summary, self.supplement)
        self.record.unlink()
        with self.assertRaisesRegex(ValueError, 'complete case execution record'):
            M.validate_actual_request(self.summary, self.supplement)

    def test_postprocess_SHA_path_and_config_must_match_completed_record(self):
        for changes, message in [({'postprocess_sha256': '0'*64}, 'SHA/path'),
                                  ({'postprocess_path': str(self.summary.parent/'other.json')}, 'SHA/path'),
                                  ({'config_sha256': '0'*64}, 'config/native')]:
            with self.subTest(changes=changes):
                self.record.write_text(json.dumps(dict(self.original_record, **changes)))
                with self.assertRaisesRegex(ValueError, message):
                    M.validate_actual_request(self.summary, self.supplement)

    def test_global_running_state_is_ineligible_even_with_complete_case(self):
        (self.run/'controller.json').write_text('{"status":"running","phase":"solving"}')
        (self.run/'summary.json').write_text('{"status":"running"}')
        with self.assertRaisesRegex(ValueError, 'matching terminal statuses'):
            M.validate_actual_request(self.summary, self.supplement)

    def test_new_output_must_preserve_reserve_after_payload_bytes(self):
        with patch.object(M.shutil, 'disk_usage', return_value=SimpleNamespace(free=M.DISK_RESERVE+9)):
            with self.assertRaisesRegex(ValueError, '2GiB disk reserve'):
                M.check_disk_reserve(self.supplement, additional_bytes=10)
        with patch.object(M.shutil, 'disk_usage', return_value=SimpleNamespace(free=M.DISK_RESERVE+10)):
            M.check_disk_reserve(self.supplement, additional_bytes=10)


if __name__ == '__main__':
    unittest.main()
