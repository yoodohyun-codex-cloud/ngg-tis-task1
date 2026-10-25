"""Manufactured-only tests. No native files, old modules, PDE, or data IO.

The largest fixture/projection has 8*2074=16592 elements; waveform vectors
contain8192 elements. These tests are supplied for the sole owner to execute.
"""
import copy
import unittest

import numpy as np
import stream_metrics as sm


def fixture():
    n = 8
    grid = np.zeros((n, 5), float)
    grid[:, :3] = np.array([[0, 0, .05], [1, 0, .05], [0, 0, 2], [1, 0, 4],
                           [0, 0, 6], [1, 0, 8], [0, 0, 16], [1, 0, 18]], float)
    grid[:, 3] = np.repeat(np.arange(4), 2)
    grid[:, 4] = np.arange(1, n + 1) * 1e-9
    total = grid[:, 4].copy()
    target = np.zeros(n)
    target[6:] = total[6:] * np.array([.25, .5])
    surface = total * (grid[:, 2] < 5)
    subsurface = total * ((grid[:, 2] >= 5) & (grid[:, 2] < 10))
    weights = dict(total=total, target=target, surface_0_5=surface, subsurface_5_10=subsurface,
                   remaining=total - target - surface - subsurface, off_target=total - target)
    e0 = np.empty((n, 3), np.complex128)
    e1 = np.empty_like(e0)
    for index in range(n):
        e0[index] = [1 + .13 * index + .2j, .3j - .05 * index, .12 + .09j * index]
        e1[index] = [.7 - .03j * index, -.2 + .11j, .09 * index - .4j]
    gamma0 = np.array([.01 + .1j, .2 + .3j, .4 + .5j, .6 + .7j])
    gamma1 = np.array([.02 + .11j, .21 + .31j, .41 + .51j, .61 + .71j])
    electrical = dict(source_Vpp_each=1., source_power_W=2e-5, source_complex_power_W=dict(real=2e-5, imaginary=-3e-6),
                      source_current_RMS_by_output_A=[.01, .02], sum_output_current_RMS_A_bookkeeping=.03,
                      SC_power_W=1e-7, skin_power_W=2e-7, contact_power_W=3e-7,
                      contact_normal_J_RMS_max_A_m2=2., contact_normal_J_RMS_P95_A_m2=1.5,
                      contact_voltage_RMS_max_V=.01)
    return grid, weights, e0, e1, gamma0, gamma1, electrical


def factory_for(e0, e1, rows=3):
    def factory():
        for first in range(0, len(e0), rows):
            last = min(len(e0), first + rows)
            yield first, last, np.ascontiguousarray(e0[first:last]), np.ascontiguousarray(e1[first:last])
    return factory


def reference_maps(e0, e1, gamma0, gamma1, grid):
    directions = sm.directions(np)
    directional = 2 * np.minimum(np.abs(e0 @ directions.T), np.abs(e1 @ directions.T))
    winner = np.argmax(directional, axis=1).astype(np.int32)
    indices = np.arange(len(e0))
    # Independently form actual gamma*E vectors, rather than use |gamma|²||E||².
    layers = grid[:, 3].astype(int)
    j0 = gamma0[layers, None] * e0
    j1 = gamma1[layers, None] * e1
    result = dict(AM_max2074=directional[indices, winner],
                  carrier_RMS=np.sqrt((np.linalg.norm(e0, axis=1) ** 2 + np.linalg.norm(e1, axis=1) ** 2) / 2),
                  carrier0_RMS=np.linalg.norm(e0, axis=1) / np.sqrt(2),
                  carrier1_RMS=np.linalg.norm(e1, axis=1) / np.sqrt(2),
                  Jtotal_vector_RMS=np.sqrt((np.linalg.norm(j0, axis=1) ** 2 + np.linalg.norm(j1, axis=1) ** 2) / 2),
                  AM_direction_index=winner)
    for index, name in enumerate(('AM_x', 'AM_y', 'AM_z')):
        result[name] = 2 * np.minimum(np.abs(e0[:, index]), np.abs(e1[:, index]))
    return result


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.grid, self.weights, self.e0, self.e1, self.g0, self.g1, self.electrical = fixture()
        self.factory = factory_for(self.e0, self.e1)
        self.maps = reference_maps(self.e0, self.e1, self.g0, self.g1, self.grid)

    def evaluate(self, **kwargs):
        electrical = self.electrical
        if (kwargs.get('a0', 1.), kwargs.get('a1', 1.)) != (1., 1.):
            electrical = dict(electrical, source_Vpp_by_frequency={'2000': kwargs.get('a0', 1.), '2010': kwargs.get('a1', 1.)})
        return sm.evaluate(np, self.grid, self.weights, self.factory, self.g0, self.g1, electrical, **kwargs)

    def gate(self):
        reference = self.evaluate()['summary']
        def actual_saved_map_reader(name, first, last):
            self.assertIn(name, sm.BASELINE_MAP_NAMES + ('AM_direction_index',))
            return self.maps[name][first:last]
        result = self.evaluate(baseline_arrays=actual_saved_map_reader, baseline_summary=reference)
        self.assertEqual(result['baseline_agreement']['status'], 'passed')
        self.assertEqual(set(result['baseline_agreement']['pointwise_compared_original_float_maps']),
                         {'AM_max2074', 'carrier_RMS', 'Jtotal_vector_RMS'})
        self.assertEqual(set(result['baseline_agreement']['unavailable_original_pixel_maps']),
                         {'AM_x', 'AM_y', 'AM_z', 'carrier0_RMS', 'carrier1_RMS'})
        return result['baseline_agreement']

    def test_exact_directions_order_and_unit_vectors(self):
        directions = sm.directions(np)
        self.assertEqual(directions.shape, (2074, 3))
        np.testing.assert_allclose(np.linalg.norm(directions, axis=1), 1., rtol=0, atol=1e-15)
        expected = []
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                for z in (-1, 0, 1):
                    if x or y or z:
                        vector = np.array([x, y, z], float)
                        expected.append(vector / np.linalg.norm(vector))
        np.testing.assert_array_equal(directions[:26], np.asarray(expected))
        self.assertEqual(directions[26, 1], 0.)
        self.assertEqual(directions[26, 2], 1 - 1 / 2048)
        self.assertEqual(directions[-1, 2], -1 + 1 / 2048)

    def test_inverse_ecdf_ignores_zero_weight_extrema_and_keeps_fractional_native_centre(self):
        values = np.array([-100., 1., 2., 3., 100.])
        weights = np.array([0., .25, 0., .75, 0.])
        grid = np.zeros((5, 5))
        grid[:, 0] = np.arange(5) + .9
        stats = sm.weighted_stats(np, values, weights, grid)
        self.assertEqual((stats['min'], stats['max'], stats['p10'], stats['median'], stats['p95']), (1., 3., 1., 3., 3.))
        self.assertEqual(stats['positive_weight_cells'], 2)
        self.assertEqual(stats['maximum_native_cell_index'], 3)
        self.assertEqual(stats['maximum_xyz_mm'], [3.9, 0., 0.])
        self.assertEqual(stats['volume_m3'], 1.)

    def test_baseline_all_scalar_statistics_and_all_original_scopes(self):
        result = self.evaluate()
        self.assertEqual(result['arrays'], {})
        self.assertNotEqual(result['baseline_agreement']['status'], 'passed')
        regions = result['summary']['regions']
        self.assertEqual(set(regions), set(sm.SCOPES))
        for scope, region in regions.items():
            self.assertEqual(set(region['statistics']), set(sm.SCALAR_NAMES))
            for metric in sm.SCALAR_NAMES:
                if scope in self.weights:
                    w = self.weights[scope]
                elif scope == 'surface_without_SC':
                    w = self.weights['surface_0_5'] * (self.grid[:, 3] != 0)
                elif scope == 'skin_SC_plus_dermis':
                    w = self.weights['total'] * (self.grid[:, 3] <= 1)
                else:
                    w = self.weights['total'] * (self.grid[:, 3] == sm.LAYER_NAMES.index(scope[6:]))
                map_name = sm.MAP_NAMES[sm.SCALAR_NAMES.index(metric)]
                value = self.maps[map_name]
                expected = np.sum(w * value) / np.sum(w)
                self.assertAlmostEqual(region['statistics'][metric]['mean'], expected, places=13)
                self.assertIn('CV', region['statistics'][metric])
        self.assertEqual(result['summary']['waveform_checks']['status'], 'passed')

    def test_complete_baseline_gate_then_two_bounded_maps_per_candidate(self):
        gate = self.gate()
        before0, before1 = self.e0.copy(), self.e1.copy()
        for a0, a1 in ((.8, 1.), (1., .8)):
            sampled = []
            def take_rows(indices):
                sampled.append(list(indices))
                return self.e0[indices].copy(), self.e1[indices].copy()
            result = self.evaluate(a0=a0, a1=a1, baseline_gate=gate, take_rows=take_rows)
            self.assertEqual(set(result['arrays']), {'AM_max2074', 'carrier_RMS'})
            expected = reference_maps(self.e0 * a0, self.e1 * a1, self.g0, self.g1, self.grid)
            for name, value in result['arrays'].items():
                np.testing.assert_allclose(value, expected[name], rtol=2e-14, atol=2e-14)
                self.assertEqual(value.dtype, np.dtype(float))
            self.assertEqual(len(sampled), 1)
            self.assertLessEqual(len(sampled[0]), 2)
            self.assertFalse(result['summary']['holds']['candidate_adopted'])
            del result
        np.testing.assert_array_equal(self.e0, before0)
        np.testing.assert_array_equal(self.e1, before1)

    def test_full_map_failure_blocks_both_new_conditions(self):
        reference = self.evaluate()['summary']
        bad = {key: value.copy() for key, value in self.maps.items()}
        bad['AM_max2074'][4] += .01
        result = self.evaluate(baseline_arrays=lambda name, first, last: bad[name][first:last], baseline_summary=reference)
        gate = result['baseline_agreement']
        self.assertEqual(gate['status'], 'failed')
        self.assertEqual(gate['array_agreement']['float_maps']['AM_max2074']['failed_cells'], 1)
        for a0, a1 in ((.8, 1.), (1., .8)):
            with self.assertRaisesRegex(ValueError, 'complete passed baseline gate'):
                self.evaluate(a0=a0, a1=a1, baseline_gate=gate)

    def test_summary_original_fields_gate_and_new_electrical_metadata_allowed(self):
        baseline = self.evaluate()['summary']
        computed = copy.deepcopy(baseline)
        computed['electrical']['new_metadata'] = 'explicit additional carrier provenance'
        checks = self.gate()['array_agreement']
        self.assertEqual(sm.compare_baseline(np, computed, baseline, checks)['status'], 'passed')
        computed['electrical']['source_power_W'] += 1e-9
        failure = sm.compare_baseline(np, computed, baseline, checks)
        self.assertEqual(failure['status'], 'failed')
        self.assertTrue(any(v['path'] == 'electrical/source_power_W' for v in failure['summary_failures']))
        computed = copy.deepcopy(baseline)
        computed['regions']['target']['statistics']['maxTIS']['p10'] += .01
        self.assertEqual(sm.compare_baseline(np, computed, baseline, checks)['status'], 'failed')

    def test_direction_index_changes_are_separate_diagnostic(self):
        reference = self.evaluate()['summary']
        changed = {key: value.copy() for key, value in self.maps.items()}
        changed['AM_direction_index'] = (changed['AM_direction_index'] + 1) % 2074
        result = self.evaluate(baseline_arrays=lambda name, first, last: changed[name][first:last], baseline_summary=reference)
        checks = result['baseline_agreement']['array_agreement']
        self.assertEqual(result['baseline_agreement']['status'], 'passed')
        self.assertEqual(checks['direction_first_tie']['differing_cells'], len(self.grid))

    def test_incomplete_out_of_order_and_nonfinite_stream_rejected(self):
        good = self.factory
        bad_factories = [lambda: iter(list(good())[:-1]),
                         lambda: iter(list(good())[1:]),
                         lambda: iter([(0, 3, self.e0[:3], self.e1[:3, ::-1])])]
        for factory in bad_factories:
            with self.assertRaises(ValueError):
                sm.evaluate(np, self.grid, self.weights, factory, self.g0, self.g1, self.electrical)
        broken = self.e0.copy()
        broken[0, 0] = np.nan
        with self.assertRaises(ValueError):
            sm.evaluate(np, self.grid, self.weights, factory_for(broken, self.e1), self.g0, self.g1, self.electrical)

    def test_oversized_chunk_is_rejected_before_angular_work(self):
        e0 = np.zeros((129, 3), np.complex128)
        e1 = np.zeros_like(e0)
        with self.assertRaisesRegex(ValueError, 'chunk <=128'):
            list(sm._chunks(np, lambda: iter([(0, 129, e0, e1)]), 129, lambda: None, None))

    def test_readonly_reused_carrier_buffers_are_consumed_without_retention(self):
        reference = self.evaluate()['summary']
        def reused_factory():
            a = np.empty((3, 3), np.complex128)
            b = np.empty_like(a)
            for first in range(0, len(self.e0), 3):
                last = min(len(self.e0), first + 3)
                count = last - first
                a[:count] = self.e0[first:last]
                b[:count] = self.e1[first:last]
                av, bv = a[:count].view(), b[:count].view()
                av.setflags(write=False)
                bv.setflags(write=False)
                yield first, last, av, bv
        result = sm.evaluate(np, self.grid, self.weights, reused_factory, self.g0, self.g1, self.electrical,
                             baseline_arrays=lambda name, first, last: self.maps[name][first:last],
                             baseline_summary=reference)
        self.assertEqual(result['baseline_agreement']['status'], 'passed')
        self.assertEqual(result['arrays'], {})

    def test_guard_deadline_and_invalid_geometry_or_weights_fail_closed(self):
        with self.assertRaises(TimeoutError):
            self.evaluate(deadline=0.)
        def stop():
            raise RuntimeError('manufactured aggregate resource guard')
        with self.assertRaisesRegex(RuntimeError, 'manufactured aggregate resource guard'):
            self.evaluate(guard=stop)
        self.weights['target'][0] = self.weights['total'][0] * 2
        with self.assertRaisesRegex(ValueError, 'weights must agree'):
            self.evaluate()

    def test_normalization_preserves_distinct_current_power_and_joint_eight_caps(self):
        baseline = self.evaluate()['summary']
        candidate = copy.deepcopy(baseline)
        candidate['electrical']['source_power_W'] *= 4
        candidate['electrical']['contact_power_W'] *= 9
        candidate['electrical']['contact_normal_J_RMS_max_A_m2'] *= 2
        normalization = sm.normalize(candidate, baseline)
        comparisons = normalization['comparisons']
        self.assertEqual(comparisons['same_source_voltage']['amplitude_scale'], 1.)
        self.assertEqual(comparisons['same_sum_output_RMS_current_bookkeeping']['amplitude_scale'], 1.)
        self.assertEqual(comparisons['same_source_real_power']['amplitude_scale'], .5)
        joint = comparisons['joint_eight_surface_contact_burden_caps']
        self.assertAlmostEqual(joint['amplitude_scale'], 1 / 3)
        self.assertEqual(joint['limiting_constraints'], ['contact_power_W'])
        self.assertAlmostEqual(joint['electrical']['source_complex_power_W']['imaginary'], -3e-6 / 9)
        self.assertFalse(normalization['simultaneous_equal_current_power_burden_assumed'])

    def test_lazy_weight_lifetime_and_budget_do_not_claim_unbounded_six_weight_admission(self):
        class LazyWeights:
            def __iter__(inner):
                return iter(self.weights)
            def __getitem__(inner, key):
                return self.weights[key].copy()
        result = sm.evaluate(np, self.grid, LazyWeights(), self.factory, self.g0, self.g1, self.electrical)
        self.assertEqual(result['arrays'], {})
        admitted = sm.allocation_budget()
        self.assertTrue(admitted['within_provisional_workspace_limit'])
        self.assertEqual(admitted['two_conditions_two_maps_raw_bytes'], 25403136)
        self.assertFalse(sm.allocation_budget(resident_weights=6)['within_provisional_workspace_limit'])
        self.assertEqual(admitted['actual_aggregate_RSS_plus_owned_tmpfs_hard_limit_bytes'], 8000000000)


if __name__ == '__main__':
    unittest.main()
