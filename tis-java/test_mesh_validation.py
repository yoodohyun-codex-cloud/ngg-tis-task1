"""Mesh-diagnostic guards and planning; no phantom PDE or live-run writes."""
from copy import deepcopy
import hashlib
import itertools
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import mesh_validation as validation


MODEL_CONFIG = """sc.sigma=0.0002
sc.epsilon_r=110000
dermis.sigma=0.2
dermis.epsilon_r=10000
fat.sigma=0.04
fat.epsilon_r=1000
muscle.sigma=0.3
muscle.epsilon_r=100000
h_mm=0.625
size_mm=15
channels=2
frequencies=2000,2010,6000,6030
pad.0.x_mm=-10
pad.0.y_mm=-10
pad.1.x_mm=10
pad.1.y_mm=10
pad.2.x_mm=10
pad.2.y_mm=-10
pad.3.x_mm=-10
pad.3.y_mm=10
z.2000.re=0.0010246703091681638
z.2000.im=-0.0022333986363121724
z.2010.re=0.0010212321657819615
z.2010.im=-0.0022243456968300194
z.6000.re=0.0004695171459649714
z.6000.im=-0.0010523036506919845
z.6030.re=0.00046797038115104785
z.6030.im=-0.0010490350554579028
"""


class MeshPlanningTests(unittest.TestCase):
    def setUp(self):
        # A planning/guard regression must never start the phantom solver.
        process = mock.patch.object(validation.subprocess, 'Popen',
                                    side_effect=AssertionError('PDE launch in unit test'))
        process.start()
        self.addCleanup(process.stop)

    def test_independent_xy_and_sc_counts_match_cylindrical_cell_centres(self):
        expected = ((.625, 2, 80, 5024, 70, 351680, 1962.5),
                    (.625, 4, 80, 5024, 72, 361728, 1962.5),
                    (.625, 8, 80, 5024, 76, 381824, 1962.5),
                    (.5, 2, 100, 7860, 70, 550200, 1965.0),
                    (50 / 120, 2, 120, 11304, 70, 791280, 1962.5))
        for h, sc, nx, nxy, nz, cells, area in expected:
            with self.subTest(h_xy_mm=h, sc_cells=sc):
                metadata = validation.mesh_metadata(h, sc)
                self.assertEqual(metadata['h_xy_mm'], h)
                self.assertEqual(metadata['nx'], nx)
                self.assertEqual(metadata['nxy'], nxy)
                self.assertEqual(metadata['nz'], nz)
                self.assertEqual(metadata['cells'], cells)
                self.assertEqual(metadata['sc_cells'], sc)
                self.assertEqual(metadata['layer_counts'], [sc, 14, 14, 40])
                self.assertAlmostEqual(metadata['cross_section_mm2'], area, places=10)
                self.assertLessEqual(cells, 800000)

    def test_invalid_meshes_do_not_bypass_tiling_or_cell_limit(self):
        for h, sc in ((0, 2), (-.625, 2), (math.nan, 2), (math.inf, 2),
                      (.6, 2), (.25, 2), (.625, 3), (50 / 120, 8)):
            with self.subTest(h_xy_mm=h, sc_cells=sc):
                with self.assertRaises(ValueError):
                    validation.mesh_metadata(h, sc)

    def test_diagnostic_configuration_changes_only_requested_mesh_controls(self):
        original = validation.parse_properties(MODEL_CONFIG)
        for h, sc in ((.625, 2), (.625, 4), (.625, 8), (.5, 2), (50 / 120, 2)):
            with self.subTest(h_xy_mm=h, sc_cells=sc):
                text = validation.make_config(MODEL_CONFIG, h, sc)
                configured = validation.parse_properties(text)
                self.assertAlmostEqual(float(configured.pop('h_mm')), h)
                self.assertEqual(int(configured.pop('validation.sc_cells')), sc)
                self.assertEqual(int(configured.pop('validation.max_cells')), 800000)
                preserved = dict(original)
                preserved.pop('h_mm')
                # Exact equality covers every layer, boundary, pad, frequency,
                # source count and any future original model property.
                self.assertEqual(configured, preserved)
        self.assertEqual(validation.parse_properties(MODEL_CONFIG), original)

    def test_fixed_ten_case_plan_has_both_geometries_at_each_mesh(self):
        plan = validation.case_plan()
        self.assertEqual(len(plan), 10)
        self.assertEqual(len({job['id'] for job in plan}), 10)
        expected = [(.625, 2, 351680), (.625, 4, 361728),
                    (.625, 8, 381824), (.5, 2, 550200),
                    (50 / 120, 2, 791280)]
        for index, (h, sc, cells) in enumerate(expected):
            pair = plan[2 * index:2 * index + 2]
            self.assertEqual([job['geometry'] for job in pair], ['reference', 'leader'])
            self.assertEqual(len({job['mesh_id'] for job in pair}), 1)
            for job in pair:
                self.assertEqual((job['h_xy_mm'], job['sc_cells'], job['cells']),
                                 (h, sc, cells))
                self.assertIn(job['axis'], ('baseline', 'sc', 'xy'))

    def test_hash_guard_detects_changed_or_missing_inputs_without_rewriting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.java'
            original = b'// retained diagnostic source\n'
            path.write_bytes(original)
            hashes = {str(path.resolve()): hashlib.sha256(original).hexdigest()}
            frozen = deepcopy(hashes)
            validation.assert_hashes_unchanged(hashes)
            self.assertEqual(path.read_bytes(), original)
            path.write_bytes(original + b'// changed\n')
            changed = path.read_bytes()
            with self.assertRaises(ValueError):
                validation.assert_hashes_unchanged(hashes)
            self.assertEqual(path.read_bytes(), changed)
            path.unlink()
            with self.assertRaises((ValueError, FileNotFoundError)):
                validation.assert_hashes_unchanged(hashes)
            self.assertEqual(hashes, frozen)


class NumericalGateTests(unittest.TestCase):
    def setUp(self):
        process = mock.patch.object(validation.subprocess, 'Popen',
                                    side_effect=AssertionError('PDE launch in unit test'))
        process.start()
        self.addCleanup(process.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.contacts = []
        # Two pieces per pad make the expected area independent of contact
        # row count, and require summing fractional overlaps per pad.
        for frequency in (2000, 2010, 6000, 6030):
            path = self.directory / f'contacts-{frequency}.csv'
            self.write_contacts(path)
            self.contacts.append(path)
        self.good = dict(max_residual=1e-9, max_power_error=2e-9,
                         max_current_error=3e-9, channels=2, cells=351680)

    def write_contacts(self, path, *, area=225e-6, pads=4):
        rows = ['pad,x_mm,y_mm,area_m2']
        for pad in range(pads):
            rows.extend((f'{pad},0,0,{area * .25:.17g}',
                         f'{pad},1,0,{area * .75:.17g}'))
        path.write_text('\n'.join(rows) + '\n')

    def test_valid_conservation_and_fractional_contact_areas_pass_without_changes(self):
        before = {path: path.read_bytes() for path in self.contacts}
        gates = deepcopy(self.good)
        validation.check_numerical_gates(gates, self.contacts, 15)
        self.assertEqual(gates, self.good)
        self.assertEqual({path: path.read_bytes() for path in self.contacts}, before)

    def test_each_conservation_gate_and_nonfinite_value_is_rejected(self):
        limits = {'max_residual': 2e-7, 'max_power_error': 2e-7,
                  'max_current_error': 2e-6}
        for key, limit in limits.items():
            for bad in (limit * 1.001, math.nan, math.inf, -math.inf):
                with self.subTest(key=key, value=bad):
                    values = dict(self.good, **{key: bad})
                    with self.assertRaises(ValueError):
                        validation.check_numerical_gates(values, self.contacts, 15)

    def test_contact_area_loss_nonfinite_and_missing_pad_are_rejected(self):
        for area in (225e-6 * .99, 225e-6 * 1.01, math.nan, math.inf, -225e-6):
            with self.subTest(area=area):
                self.write_contacts(self.contacts[-1], area=area)
                with self.assertRaises(ValueError):
                    validation.check_numerical_gates(self.good, self.contacts, 15)
        self.write_contacts(self.contacts[-1], pads=3)
        with self.assertRaises(ValueError):
            validation.check_numerical_gates(self.good, self.contacts, 15)


class ConvergenceReviewTests(unittest.TestCase):
    @staticmethod
    def complete_results():
        values = dict(target20_modulation_V_m=3.0,
                      target20_total_E_RMS_V_m=1.5,
                      surface_J_RMS_max_A_m2=12.0,
                      surface_J_RMS_p95_A_m2=9.0,
                      contact_voltage_RMS_max_V=.03,
                      SC_power_W=2e-6, contact_power_W=14e-6)
        return [dict(job, status='complete', validation={}, resources={},
                     metrics=[dict(values, waveform=wave)
                              for wave in ('sine', 'square_3h', 'triangle_3h')])
                for job in validation.case_plan()]

    def test_both_independent_axes_and_all_three_waveforms_are_required(self):
        results = self.complete_results()
        original = deepcopy(results)
        review = validation.review_convergence(results)
        self.assertEqual(review['status'], 'passed')
        self.assertTrue(review['all_passed'])
        self.assertEqual(len(review['rows']), 12)
        self.assertEqual({(row['geometry'], row['axis'], row['waveform'])
                          for row in review['rows']},
                         {(geometry, axis, wave)
                          for geometry in ('reference', 'leader')
                          for axis in ('xy', 'sc')
                          for wave in ('sine', 'square_3h', 'triangle_3h')})
        self.assertTrue(all(row['passed'] for row in review['rows']))
        self.assertEqual(results, original)

    def test_stable_target_does_not_hide_unconverged_surface_current(self):
        results = self.complete_results()
        final_xy = next(result for result in results
                        if result['geometry'] == 'leader'
                        and result['axis'] == 'xy' and result['h_xy_mm'] < .5)
        square = next(row for row in final_xy['metrics']
                      if row['waveform'] == 'square_3h')
        square['surface_J_RMS_max_A_m2'] *= 1.1
        review = validation.review_convergence(results)
        self.assertEqual(review['status'], 'unconverged')
        self.assertFalse(review['all_passed'])
        failed = [row for row in review['rows'] if not row['passed']]
        self.assertEqual(len(failed), 1)
        changes = failed[0]['changes']
        self.assertTrue(changes['target20_modulation_V_m']['passed'])
        self.assertTrue(changes['target20_total_E_RMS_V_m']['passed'])
        self.assertFalse(changes['surface_J_RMS_max_A_m2']['passed'])
        self.assertAlmostEqual(changes['surface_J_RMS_max_A_m2']
                               ['relative_change_percent'], 10.0)
        self.assertEqual(changes['surface_J_RMS_max_A_m2']['limit_percent'], 5)

    def test_missing_case_or_waveform_cannot_claim_convergence(self):
        for missing in ('case', 'waveform'):
            with self.subTest(missing=missing):
                results = self.complete_results()
                if missing == 'case':
                    results.pop()
                else:
                    results[-1]['metrics'].pop()
                review = validation.review_convergence(results)
                self.assertEqual(review['status'], 'incomplete')
                self.assertFalse(review['all_passed'])

    def test_adjacent_trends_retain_first_step_even_when_final_step_passes(self):
        results = self.complete_results()
        for result in results:
            if result['mesh_id'] in ('sc4', 'xy100'):
                for row in result['metrics']:
                    row['surface_J_RMS_max_A_m2'] = 13.2
            elif result['mesh_id'] in ('sc8', 'xy120'):
                for row in result['metrics']:
                    row['surface_J_RMS_max_A_m2'] = 13.21
        original = deepcopy(results)
        trends = validation.adjacent_trends(results)
        review = validation.review_convergence(results)
        self.assertEqual(len(trends), 24)
        self.assertTrue(review['all_passed'])
        for geometry in ('reference', 'leader'):
            for axis, intermediate, final in (('sc', 'sc4', 'sc8'),
                                               ('xy', 'xy100', 'xy120')):
                for wave in ('sine', 'square_3h', 'triangle_3h'):
                    with self.subTest(geometry=geometry, axis=axis, waveform=wave):
                        steps = [row for row in trends if row['geometry'] == geometry
                                 and row['axis'] == axis and row['waveform'] == wave]
                        self.assertEqual([(row['previous_case'], row['current_case'])
                                          for row in steps],
                                         [(f'baseline-{geometry}', f'{intermediate}-{geometry}'),
                                          (f'{intermediate}-{geometry}', f'{final}-{geometry}')])
                        self.assertAlmostEqual(steps[0]['relative_changes_percent']
                                               ['surface_J_RMS_max_A_m2'], 10)
                        last = next(row for row in review['rows']
                                    if row['geometry'] == geometry and row['axis'] == axis
                                    and row['waveform'] == wave)
                        for metric, change in last['changes'].items():
                            self.assertAlmostEqual(steps[1]['relative_changes_percent'][metric],
                                                   change['relative_change_percent'])
        self.assertEqual(results, original)

    def test_geometry_comparison_uses_same_waveform_even_with_reordered_rows(self):
        results = self.complete_results()
        reference_factors = {'sine': 1, 'square_3h': 2, 'triangle_3h': 4}
        leader_gains = {'sine': 1.1, 'square_3h': 1.2, 'triangle_3h': 1.3}
        for result in results:
            for row in result['metrics']:
                wave = row['waveform']
                factor = reference_factors[wave]
                if result['geometry'] == 'leader':
                    factor *= leader_gains[wave]
                for metric in validation.THRESHOLDS:
                    row[metric] *= factor
            if result['geometry'] == 'leader':
                result['metrics'].reverse()
        original = deepcopy(results)
        pairs = validation.geometry_comparisons(results)
        self.assertEqual(len(pairs), 15)
        for pair in pairs:
            with self.subTest(mesh_id=pair['mesh_id'], waveform=pair['waveform']):
                self.assertEqual(pair['reference_case'], f"{pair['mesh_id']}-reference")
                self.assertEqual(pair['leader_case'], f"{pair['mesh_id']}-leader")
                expected_percent = (leader_gains[pair['waveform']] - 1) * 100
                for change in pair['relative_changes_percent'].values():
                    self.assertAlmostEqual(change, expected_percent)
        self.assertEqual(results, original)


class PreregistrationTests(unittest.TestCase):
    @staticmethod
    def registered_specification():
        return dict(
            schema_version=1,
            baseline_cases={'leader': '03522-1', 'reference': '02342-0'},
            resource_limits=dict(
                max_cells=800000, max_cases=10, max_diagnostic_java_processes=1,
                per_case_wall_seconds=600, total_wall_seconds=6600,
                max_RSS_bytes=3 * 1024 ** 3, java_heap='2g', java_active_processors=1,
                java_gc='SerialGC', minimum_free_disk_bytes=2 * 1024 ** 3),
            convergence_relative_limits=dict(
                target20_modulation_V_m=.01, target20_total_E_RMS_V_m=.01,
                surface_J_RMS_max_A_m2=.05, surface_J_RMS_p95_A_m2=.05,
                contact_voltage_RMS_max_V=.05, SC_power_W=.02, contact_power_W=.02),
            solver_validation_limits=dict(
                max_residual=2e-7, max_power_error=2e-7,
                max_current_error=2e-6, max_relative_electrode_area_error=1e-10))

    def test_registered_specification_is_accepted_without_mutation(self):
        specification = self.registered_specification()
        original = deepcopy(specification)
        validation.validate_preregistration(specification)
        self.assertEqual(specification, original)

    def test_widening_any_resource_cap_is_rejected(self):
        widened = dict(max_cells=800001, max_cases=11,
                       max_diagnostic_java_processes=2, per_case_wall_seconds=601,
                       total_wall_seconds=6601, max_RSS_bytes=3 * 1024 ** 3 + 1,
                       java_heap='3g', java_active_processors=2, java_gc='ParallelGC',
                       minimum_free_disk_bytes=2 * 1024 ** 3 - 1)
        for key, value in widened.items():
            with self.subTest(resource_limit=key):
                specification = self.registered_specification()
                specification['resource_limits'][key] = value
                with self.assertRaises(ValueError):
                    validation.validate_preregistration(specification)

    def test_changed_convergence_and_numerical_thresholds_are_rejected(self):
        registered = self.registered_specification()
        for group in ('convergence_relative_limits', 'solver_validation_limits'):
            for key, value in registered[group].items():
                for changed in (value * 2, math.nan, math.inf):
                    with self.subTest(group=group, metric=key, changed=changed):
                        specification = deepcopy(registered)
                        specification[group][key] = changed
                        with self.assertRaises(ValueError):
                            validation.validate_preregistration(specification)


class ResourceGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.log = Path(temporary.name) / 'mock-diagnostic.log'
        self.command = ['java', '-cp', '/private/classes', 'ValidationBasis']
        # Every process and signal is mocked, including the timeout escalation.
        self.process = mock.Mock(pid=987654321, returncode=0)
        self.process.poll.return_value = 0
        for target, options in (
            ('subprocess.Popen', {'return_value': self.process}),
            ('os.killpg', {}),
            ('process_rss_bytes', {'return_value': 1024}),
            ('available_disk_bytes', {'return_value': 10 * validation.GIB}),
            ('time.sleep', {}),
            ('time.monotonic', {'side_effect': itertools.chain([10.0, 10.1],
                                                             itertools.repeat(10.2))}),
        ):
            patcher = mock.patch('mesh_validation.' + target, **options)
            instance = patcher.start()
            self.addCleanup(patcher.stop)
            setattr(self, target.rsplit('.', 1)[-1], instance)

    def test_completed_process_records_bounded_resources(self):
        record = validation.run_guarded(self.command, self.log)
        self.assertEqual(record['status'], 'complete')
        self.assertEqual(record['returncode'], 0)
        self.assertEqual(record['command'], self.command)
        self.assertEqual(record['peak_rss_bytes'], 1024)
        self.assertAlmostEqual(record['wall_seconds'], .2)
        self.Popen.assert_called_once()
        self.assertTrue(self.Popen.call_args.kwargs['start_new_session'])
        self.killpg.assert_not_called()

    def test_timeout_rss_total_deadline_and_disk_stop_only_diagnostic_process(self):
        settings = (
            ('case_timeout', dict(timeout_s=1), [10., 12., 12.1], 1024,
             10 * validation.GIB),
            ('total_timeout', dict(total_deadline=10.05), [10., 10.1, 10.2],
             1024, 10 * validation.GIB),
            ('rss_limit', dict(rss_limit_bytes=1024), [10., 10.1, 10.2],
             1025, 10 * validation.GIB),
            ('disk_reserve', {}, [10., 10.1, 10.2], 1024,
             validation.RESOURCE_LIMITS['minimum_free_bytes'] - 1),
        )
        for reason, options, clock, rss, free in settings:
            with self.subTest(reason=reason):
                self.monotonic.side_effect = itertools.chain(clock, itertools.repeat(clock[-1]))
                self.process_rss_bytes.return_value = rss
                self.available_disk_bytes.return_value = free
                self.process.returncode = -15
                self.process.poll.return_value = -15
                self.killpg.reset_mock()
                with self.assertRaises(validation.ValidationStop) as caught:
                    validation.run_guarded(self.command, self.log, **options)
                self.assertEqual(caught.exception.resources['status'], reason)
                self.assertGreaterEqual(caught.exception.resources['peak_rss_bytes'], rss)
                self.killpg.assert_called_once_with(self.process.pid, validation.signal.SIGTERM)
                self.process.wait.assert_called_with(timeout=3)

    def test_unresponsive_diagnostic_is_killed_after_termination_timeout(self):
        self.monotonic.side_effect = itertools.chain([10., 12.], itertools.repeat(12.1))
        self.process.returncode = -9
        self.process.poll.return_value = -9
        self.process.wait.side_effect = [validation.subprocess.TimeoutExpired(self.command, 3), -9]
        with self.assertRaises(validation.ValidationStop) as caught:
            validation.run_guarded(self.command, self.log, timeout_s=1)
        self.assertEqual(caught.exception.resources['status'], 'case_timeout')
        self.assertEqual(self.killpg.call_args_list,
                         [mock.call(self.process.pid, validation.signal.SIGTERM),
                          mock.call(self.process.pid, validation.signal.SIGKILL)])
        self.assertEqual(self.process.wait.call_args_list,
                         [mock.call(timeout=3), mock.call(timeout=5)])

    def test_caller_cannot_extend_preregistered_case_timeout(self):
        self.monotonic.side_effect = itertools.chain([10., 611.], itertools.repeat(611.1))
        self.process.returncode = -15
        self.process.poll.return_value = -15
        with self.assertRaises(validation.ValidationStop) as caught:
            validation.run_guarded(self.command, self.log, timeout_s=1000000)
        self.assertEqual(caught.exception.resources['status'], 'case_timeout')

    def test_watchdog_exception_kills_child_and_preserves_original_reason(self):
        self.process.poll.return_value = None
        alarm = validation.ValidationStop('driver_rss_limit',
                                          dict(status='driver_rss_limit',
                                               driver_peak_rss_bytes=3 * validation.GIB + 1))
        self.process_rss_bytes.side_effect = alarm

        def reaped_after_kill(*, timeout):
            self.assertEqual(timeout, 5)
            self.process.returncode = -9
            self.process.poll.return_value = -9
            return -9

        self.process.wait.side_effect = reaped_after_kill
        with self.assertRaises(validation.ValidationStop) as caught:
            validation.run_guarded(self.command, self.log)
        self.assertIs(caught.exception, alarm)
        self.assertEqual(alarm.resources['status'], 'driver_rss_limit')
        self.assertEqual(alarm.resources['driver_peak_rss_bytes'], 3 * validation.GIB + 1)
        self.assertGreaterEqual(alarm.resources['java_wall_seconds'], 0)
        self.killpg.assert_called_once_with(self.process.pid, validation.signal.SIGKILL)
        self.process.wait.assert_called_once_with(timeout=5)


if __name__ == '__main__':
    unittest.main()
