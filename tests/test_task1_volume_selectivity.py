"""Synthetic-only cached scalar audit tests. No research modules/native runs."""
import math
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_volume_selectivity as audit


def grid(depths=(5., 15., 22.5), volumes=(1e-8, 1e-8, 5e-9)):
    result = np.zeros(3, dtype=[('x_mm', float), ('y_mm', float), ('z_mm', float),
        ('layer', int), ('volume_m3', float)])
    result['z_mm'], result['layer'], result['volume_m3'] = depths, [1, 3, 3], volumes
    return result


def arrays():
    result = {key: np.array([1., 3., 10.]) for key in audit.METRICS}
    result['maxTIS_direction_index'] = np.array([0, 1, 2])
    result.update(region_total_m3=np.array([1e-8, 1e-8, 5e-9]),
        region_target_m3=np.array([0., 4e-9, 0.]),
        region_surface_0_5_m3=np.array([5e-9, 0., 0.]),
        region_subsurface_5_10_m3=np.array([5e-9, 0., 0.]),
        region_remaining_m3=np.array([0., 6e-9, 5e-9]),
        region_off_target_m3=np.array([1e-8, 6e-9, 5e-9]))
    return result


def metadata(**changes):
    return dict(h_xy_mm=1., z_faces_mm=[0., 10., 20., 25.], cells=3,
        tissue_boundaries_mm=[0., .1, 5.1, 10.1, 25.1], **changes)


class WeightedStatisticsTests(unittest.TestCase):
    def test_inverse_ecdf_inclusive_boundary_not_interpolated(self):
        stats = audit.weighted_statistics([1., 7., 20.], [1., 4., 5.])
        self.assertEqual(stats['p10'], 1.)
        self.assertEqual(stats['p50'], 7.)
        self.assertEqual(stats['p90'], 20.)
        self.assertAlmostEqual(stats['mean'], 12.9)
        self.assertAlmostEqual(stats['p10_over_mean'], 1/12.9)
        self.assertGreater(stats['CV'], 0)

    def test_fractional_weights_and_zero_support_not_counted_as_peak(self):
        stats = audit.weighted_statistics([100., 2., 6.], [0., .25, .75])
        self.assertEqual(stats['max'], 6.)
        self.assertEqual(stats['p10'], 2.)
        self.assertEqual(stats['mean'], 5.)
        self.assertEqual(stats['positive_weight_cells'], 2)

    def test_nonfinite_shape_negative_and_empty_guard(self):
        for values, weights in (([1, 2], [1]), ([math.nan], [1]),
                ([1], [-1]), ([1], [0]), ([[1]], [[1]])):
            with self.subTest(values=values, weights=weights), self.assertRaises(ValueError):
                audit.weighted_statistics(values, weights)


class RegionTests(unittest.TestCase):
    def test_face_clipped_whole_slab_and_primary_weights_retained(self):
        data = arrays()
        weights = audit.region_weights(data, grid(), metadata())
        np.testing.assert_array_equal(weights[audit.PRIMARY], data['region_target_m3'])
        np.testing.assert_allclose(weights[audit.SLAB], [0., 5e-9, 0.], rtol=1e-15)
        self.assertNotEqual(weights[audit.SLAB].sum(), weights[audit.PRIMARY].sum())
        np.testing.assert_allclose(weights['supplemental_complement']+weights[audit.SLAB], weights['total'])

    def test_saved_native_volume_and_grid_depth_mismatch_rejected(self):
        bad = arrays()
        bad['region_total_m3'][0] *= 1.01
        with self.assertRaises(ValueError):
            audit.region_weights(bad, grid(), metadata())
        with self.assertRaises(ValueError):
            audit.region_weights(arrays(), grid(depths=[5., 16., 22.5]),
                metadata())

    def test_native_bound_metadata_count_xy_and_tissue_layers_rejected(self):
        oversized = arrays()
        oversized['region_total_m3'] = np.zeros(800001)
        with self.assertRaises(ValueError):
            audit.region_weights(oversized, grid(), metadata())
        bad_meta = metadata()
        bad_meta['cells'] = 4
        with self.assertRaises(ValueError):
            audit.region_weights(arrays(), grid(), bad_meta)
        for column, value in (('x_mm', 25.), ('y_mm', math.nan), ('layer', 0)):
            invalid = grid()
            invalid[column][1] = value
            with self.subTest(column=column), self.assertRaises(ValueError):
                audit.region_weights(arrays(), invalid, metadata())

    def test_near_zero_scalar_regression_uses_scalar_not_volume_absolute_tolerance(self):
        saved = {key: 0. for key in ('mean', 'p10', 'p50', 'p95', 'min', 'max')}
        saved['volume_m3'] = 1e-9
        near = {key: value+1e-13 for key, value in saved.items()}
        near['volume_m3'] = saved['volume_m3']
        audit.verify_primary_statistics(near, saved, 'maxTIS')
        near['mean'] = 2e-12
        with self.assertRaises(ValueError):
            audit.verify_primary_statistics(near, saved, 'maxTIS')
        near['mean'] = 0.
        near['volume_m3'] += 1e-18
        with self.assertRaises(ValueError):
            audit.verify_primary_statistics(near, saved, 'maxTIS')

    def test_analytic_volume_is_reported_separately_not_weight_rescaled(self):
        volumes = audit.analytic_volumes(dict(radius_mm=25., total_depth_mm=25.1))
        self.assertAlmostEqual(volumes[audit.SLAB]/volumes[audit.PRIMARY], 25.)
        with self.assertRaises(ValueError):
            audit.analytic_volumes(dict(radius_mm=30., total_depth_mm=25.1))


class NormalizationTests(unittest.TestCase):
    def test_skin_only_can_exceed_1Vpp_and_excludes_source_power(self):
        baseline = {key: 4. for key in audit.BURDENS}
        candidate = {key: 1. for key in audit.BURDENS}
        candidate['source_power_W'] = 400.
        modes = audit.normalization_modes(candidate, baseline, 2., 8.)
        self.assertEqual(modes['skin_contact_only']['amplitude_scale'], 2.)
        self.assertEqual(modes['skin_contact_only']['normalized_burdens']['source_power_W'], 1600.)
        self.assertTrue(modes['skin_contact_only']['may_require_more_than_1Vpp'])
        self.assertFalse(modes['skin_contact_only']['includes_source_power_cap'])
        self.assertAlmostEqual(modes['legacy_composite_full_skin']['amplitude_scale'], .1)
        self.assertEqual(modes['equal_total_source_output_RMS_sum']['amplitude_scale'], 4.)
        self.assertEqual(modes['equal_total_source_output_RMS_sum']['sum_source_output_RMS_mA'], 8.)
        self.assertAlmostEqual(modes['equal_total_power']['normalized_burdens']['source_power_W'], 4.)

    def test_legacy_1Vpp_ceiling_is_distinct(self):
        baseline = {key: 100. for key in audit.BURDENS}
        candidate = {key: 1. for key in audit.BURDENS}
        modes = audit.normalization_modes(candidate, baseline, 1., 20.)
        self.assertEqual(modes['skin_contact_only']['amplitude_scale'], 10.)
        self.assertEqual(modes['legacy_composite_full_skin']['amplitude_scale'], 1.)
        self.assertEqual(len(modes['raw_1Vpp']['normalized_burdens']), 9)

    def test_threshold_volume_reclassified_after_amplitude_scaling(self):
        data = arrays()
        weights = {'test': np.array([.2, .3, .5])}
        cutoffs = {metric: {'frozen': 3.} for metric in audit.METRICS}
        raw = audit.summarize_regions(data, weights, grid(), 1., cutoffs)['test']
        scaled = audit.summarize_regions(data, weights, grid(), .2, cutoffs)['test']
        self.assertEqual(raw['maxTIS']['fixed_baseline_threshold_volume']['frozen']['volume_m3'], .8)
        self.assertEqual(scaled['maxTIS']['fixed_baseline_threshold_volume']['frozen']['volume_m3'], 0.)
        self.assertEqual(raw['RMS']['fixed_baseline_threshold_volume']['frozen']['quantity'], 'high_field_RMS')
        self.assertEqual(scaled['maxTIS']['hotspot']['center_xyz_mm'], [0., 0., 22.5])
        self.assertEqual(scaled['maxTIS']['hotspot']['layer'], 'muscle')

    def test_required_actual_two_output_currents_and_dermis_inclusion(self):
        c = dict(id='square', metrics={key: 1. for key in audit.view.CAPS})
        c['metrics']['source_current_RMS_by_output_mA'] = [2., 3.]
        item = dict(circuit=dict(n_outputs=2), full_skin={'square': dict(
            J_vector_RMS_max_A_m2=4., J_vector_RMS_p95_A_m2=2., skin_SC_plus_dermis_power_W=10.)})
        burden, current = audit.burdens(item, c)
        self.assertEqual(sum(current), 5.)
        self.assertEqual(burden['skin_SC_plus_dermis_power_W'], 10.)
        self.assertNotEqual(burden['skin_SC_plus_dermis_power_W'], burden['SC_power_W'])
        c['metrics']['source_current_RMS_by_output_mA'] = [2.]
        with self.assertRaises(ValueError):
            audit.burdens(item, c)


class PreregistrationTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        cases, refs = [], {}
        for name in ('baseline', 'candidate'):
            source = root/(name+'-grid.csv')
            source.write_text('synthetic grid only')
            row = dict(case_id=name)
            native = {str(source): audit.view.sha(source)}
            for field in ('registration', 'case_receipt', 'volume_npz'):
                file = root/(name+'-'+field)
                file.write_text('synthetic '+field)
                row[field] = str(file)
                refs[str(file)] = audit.view.sha(file)
            summary = root/(name+'-summary.json')
            summary.write_text(json.dumps(dict(input_sha256=native)))
            refs[str(summary)] = audit.view.sha(summary)
            row.update(summary=str(summary), summary_sha256=refs[str(summary)],
                volume_npz_sha256=refs[row['volume_npz']], native_expected_input_sha256=native)
            cases.append(row)
        plan = dict(schema='task1-volume-selectivity-audit-preregistration-v1',
            status='preregistered_not_executed', feedback_id='T1-F010-S1-GH6297472037',
            source_comment_id=6297472037, new_PDE_conditions=0, initial_case_count=2,
            baseline_case_id='baseline', cases=cases, input_sha256=refs)
        path = root/'plan.json'
        path.write_text(json.dumps(plan))
        return path, plan, [cases[0]['summary']], [case['summary'] for case in cases]

    def test_order_and_baseline_paths_must_match_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, plan, base, rows = self.fixture(tmp)
            check = audit.verify_preregistration(path, base, rows)
            self.assertEqual(check['SHA256'], audit.view.sha(path))
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, base, rows[::-1])
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, [rows[1]], rows)

    def test_changed_file_or_plan_hash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, plan, base, rows = self.fixture(tmp)
            digest = audit.view.sha(path)
            Path(plan['cases'][1]['volume_npz']).write_text('changed bytes')
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, base, rows)
            path.write_text(path.read_text()+'\n')
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, base, rows, expected_plan_sha=digest)

    def test_explicit_ordered_multiple_baseline_paths_override_legacy_single_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, plan, base, rows = self.fixture(tmp)
            plan['baseline_summary_paths'] = rows
            path.write_text(json.dumps(plan))
            audit.verify_preregistration(path, rows, rows)
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, rows[::-1], rows)
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, base, rows)

    def test_preregistered_native_source_digest_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, plan, base, rows = self.fixture(tmp)
            native = plan['cases'][1]['native_expected_input_sha256']
            native[next(iter(native))] = '0'*64
            path.write_text(json.dumps(plan))
            with self.assertRaises(ValueError):
                audit.verify_preregistration(path, base, rows)


if __name__ == '__main__':
    unittest.main()
