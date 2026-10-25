"""UNEXECUTED source tests; no real datasets or cache files are opened.

Pure controls cover admission/resource/memory boundary/min4/metadata labels.
Deferred tiny NumPy tests independently assemble physical-pair MNA; they do
not validate large cached-Q GMRES or the real provisional field reconstruction.
Run only if the numerical owner separately chooses to review these tests.
"""
import copy
import unittest

import p23_adapter as adapter
import p23_comparison as proposal
import p23_inputs as inputs


def admission_fields():
    return dict(schema='task1-floating-P23-comparison-root-admission-v1',
        status='selected_finite_hypothetical_P23_topology_comparison', root_selected=True,
        new_driven_RHS=2, new_metric_evaluations=1, control_aliases=2,
        new_common_return_RHS=0, new_B0_RHS=0, new_eigen_solves=0,
        candidate_adopted=False, actual_hardware_wiring_claimed=False,
        maximum_effective_CPU=4, total_RSS_plus_all_owned_tmpfs_bytes=8000000000,
        maximum_physical_evaluation_cells=800000, physical_evaluation_cells=793860,
        root_reviewed_synthetic_MNA=True, source_allocation_amplitudes=[1., 1.],
        physical_pairs=[[0, 2], [1, 3]], frequency_output_assignment=[[2000, 0], [2010, 1]],
        total_differential_series_ohm_per_output=50.,
        forecast_child_RSS_bytes=800000000, forecast_new_output_bytes=200000000,
        existing_results_read_only=True, Windows_assignments_unchanged=True,
        output_directory='/dev/shm/task1-floating-P23-comparison-20261025-run-SYNTHETIC-NOT-CREATED',
        source_sha256={}, synthetic_test_receipt={}, decision_basis='Synthetic field-validator fixture only')


def normalized(mean=2., p10=1., surface=1., off=4., scale=1.):
    def region(m, q=None):
        return dict(maxTIS=dict(mean=m, p10=m if q is None else q))
    return dict(status='calculated_global_amplitude_rescaling', amplitude_scale=scale,
        absolute_ROI_fields_V_m=dict(target=region(mean, p10),
            surface_0_5=region(surface), off_target=region(off)), electrical={})


class PureTests(unittest.TestCase):
    def test_no_admission_or_changed_scope_cannot_pass(self):
        with self.assertRaisesRegex(ValueError, 'New explicit root admission'):
            inputs.validate_admission(None)
        valid = admission_fields()
        self.assertEqual(inputs.validate_admission(valid), valid)
        for key, value in (('new_driven_RHS', 4), ('physical_pairs', [[0, 1], [2, 3]]),
                ('frequency_output_assignment', [[2000, 1], [2010, 0]]),
                ('total_differential_series_ohm_per_output', 100.),
                ('root_reviewed_synthetic_MNA', False), ('new_common_return_RHS', 2),
                ('actual_hardware_wiring_claimed', True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                changed = copy.deepcopy(valid)
                changed[key] = value
                inputs.validate_admission(changed)

    def test_complete_resource_forecast_required_and_unchanged_cap(self):
        snapshot = dict(scope='ALL_RSS_plus_ALL_owned_task1_tmpfs', observations_current=True,
                        aggregate_bytes=7000000000)
        self.assertEqual(inputs.check_resource_forecast(snapshot, raw_stage=True)['forecast_aggregate_bytes'], 8000000000)
        snapshot['aggregate_bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'BLOCKED'):
            inputs.check_resource_forecast(snapshot, raw_stage=True)
        for bad in (None, {'aggregate_bytes': 1}, dict(snapshot, observations_current=False)):
            with self.assertRaises(ValueError):
                inputs.check_resource_forecast(bad, raw_stage=True)

    def test_raw_frame_has_returned_and_collected_before_metric_entry(self):
        events = []
        class Token:
            pass
        def raw():
            token = Token()
            self.assertIsInstance(token, Token)
            events.append('raw_return')
            return {'paths': ['raw0', 'raw1'], 'new_RHS': 2}
        def collect():
            events.append('collect')
        def metric(value):
            self.assertEqual(events, ['raw_return', 'collect'])
            events.append('metrics')
            return value['new_RHS']
        self.assertEqual(proposal.separated_stages(raw, metric, collect), 2)
        self.assertEqual(events, ['raw_return', 'collect', 'metrics'])
        with self.assertRaisesRegex(ValueError, 'leaked'):
            proposal.separated_stages(lambda: {'Q': Token()}, metric, collect)

    def test_min4_requires_all_four_gains_and_never_fills_zero_reference(self):
        reference = dict(target_mean=1., target_P10=0.5,
            target_to_surface_mean=1., target_to_offtarget_mean=1.)
        row = proposal.min4(normalized(), reference)
        self.assertEqual(row['four_ratios_to_reference'], dict(target_mean=2.,
            target_P10=2., target_to_surface_mean=2., target_to_offtarget_mean=0.5))
        self.assertEqual(row['robust_minimum_four_ratio'], 0.5)
        reference['target_P10'] = 0
        self.assertIsNone(proposal.min4(normalized(), reference)['robust_minimum_four_ratio'])

    def test_descriptive_adapter_preserves_masks_and_separate_metal_nodes(self):
        original = dict(mask_sha256='synthetic', pads=[dict(pad=p,
            node='out' + str(p) if p < 2 else 'GND', node_index=p if p < 2 else -1)
            for p in range(4)])
        saved = copy.deepcopy(original)
        geometry = adapter.floating_geometry(original)
        self.assertEqual(original, saved)
        self.assertEqual(geometry['mask_sha256'], original['mask_sha256'])
        self.assertEqual([p['node_index'] for p in geometry['pads']], [0, 1, 2, 3])
        self.assertEqual([p['output_index'] for p in geometry['pads']], [0, 1, 0, 1])
        self.assertEqual([p['polarity'] for p in geometry['pads']], ['+', '+', '-', '-'])
        result = dict(summary=dict(return_topology='old common return', electrical={}),
                      arrays={'synthetic_untouched': [1, 2]})
        self.assertIs(adapter.correct_metric_metadata(result), result)
        self.assertEqual(result['summary']['return_topology'], adapter.TOPOLOGY)
        self.assertEqual(result['arrays'], {'synthetic_untouched': [1, 2]})


class PhysicalPairMNATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import frozen_floating_cem as floating
        import frozen_test_floating_cem as reference
        cls.np, cls.floating, cls.reference = np, floating, reference

    def setUp(self):
        self.fixture = self.reference.SyntheticTests()
        self.fixture.np = self.np
        self.fixture.setUp()

    def full_physical_mna(self, ideal, shift=0j):
        """Independent literal physical incidence: output0=(0,2), output1=(1,3)."""
        np, f = self.np, self.fixture
        K = np.zeros((12, 12), dtype=complex)
        K[:8, :8] = f.A
        for p, i, area in zip(f.pads, f.cells, f.areas):
            metal, g = 8 + int(p), area / f.zA
            K[i, i] += g
            K[metal, metal] += g
            K[i, metal] -= g
            K[metal, i] -= g
        B = np.zeros((12, 2), dtype=complex)
        B[8 + 0, 0], B[8 + 2, 0] = 1, -1
        B[8 + 1, 1], B[8 + 3, 1] = 1, -1
        c = np.zeros(12)
        c[8 + 3] = 1
        A = np.zeros((15, 15), dtype=complex)
        A[:12, :12] = K
        A[:12, 12:14] = -B
        A[12:14, :12] = B.T
        A[12:14, 12:14] = 50 * np.eye(2)
        A[:12, 14], A[14, :12] = c, c
        x = np.linalg.solve(A, np.r_[np.zeros(12), ideal, complex(shift)])
        return dict(phi=x[:8], metal=x[8:12], current=x[12:14], gauge=x[14])

    def solve_adapter(self, output):
        f, np = self.fixture, self.np
        def tiny_floating(*args, **kwargs):
            return self.floating.solve(*args, **kwargs, h_m=1.)
        return adapter.solve(np, f.Q, f.profiles(), f.pads, f.cells, f.areas, f.zA,
            output, f.guard, None, floating_solver=tiny_floating,
            transform=f.transform, gmres=f.tiny_dense_gmres, linear_operator=f.linear_operator)

    def test_each_output_has_correct_physical_pair_and_unchanged_source_order(self):
        np, f = self.np, self.fixture
        for output in (0, 1):
            with self.subTest(output=output):
                ideal = np.zeros(2, dtype=complex)
                ideal[output] = 0.5
                result = self.solve_adapter(output)
                full = self.full_physical_mna(ideal)
                f.assert_close(result['phi_surface'], full['phi'])
                f.assert_close(result['metal'], full['metal'])
                f.assert_close(result['source_current'], full['current'])
                self.assertLess(abs(full['gauge']), 1e-13)
                proof = result['proof']
                self.assertTrue(proof['passed'])
                self.assertEqual(proof['pair_pad_indices'], [[0, 2], [1, 3]])
                self.assertEqual(proof['driven_output'], output)
                self.assertTrue(proof['source_output_order_preserved'])
                q = np.asarray([complex(v['real'], v['imaginary']) for v in
                    proof['all_pad_outward_tissue_to_metal_current_peak_A']])
                f.assert_close([q[0] + q[2], q[1] + q[3]], [0j, 0j])
                f.assert_close(-q[[0, 1]], result['source_current'])
                inactive = 1 - output
                p, m = ((0, 2), (1, 3))[inactive]
                f.assert_close(result['metal'][p] - result['metal'][m],
                              -50 * result['source_current'][inactive])
                drop = result['metal'][f.pads] - result['phi_surface'][f.cells]
                f.assert_close(drop, result['contact_drop'])
                inward = drop * (f.areas / f.zA)
                f.assert_close(inward, result['contact_current'])
                tissue = 0.5 * np.sum(result['phi_surface'] * (f.A @ result['phi_surface']).conj())
                contact = 0.5 * np.sum(drop * inward.conj())
                resistor = 0.5 * 50 * np.sum(abs(result['source_current']) ** 2)
                source = 0.5 * np.sum(ideal * result['source_current'].conj())
                f.assert_close(source, tissue + contact + resistor)

    def test_same_frequency_reciprocity_and_physical_gauge_shift(self):
        np, f = self.np, self.fixture
        Yport = np.column_stack([self.solve_adapter(k)['source_current'] / 0.5 for k in (0, 1)])
        f.assert_close(Yport, Yport.T)
        ideal = np.asarray([0.4 + 0.2j, -0.2 + 0.1j])
        zero = self.full_physical_mna(ideal)
        shift = 0.25 - 0.35j
        shifted = self.full_physical_mna(ideal, shift)
        f.assert_close(zero['current'], Yport @ ideal)
        f.assert_close(shifted['phi'], zero['phi'] + shift)
        f.assert_close(shifted['metal'], zero['metal'] + shift)
        f.assert_close(shifted['current'], zero['current'])
        self.assertLess(abs(shifted['gauge']), 1e-13)


if __name__ == '__main__':
    unittest.main()
