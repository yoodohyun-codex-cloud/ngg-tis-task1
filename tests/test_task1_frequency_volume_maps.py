"""Synthetic saved-scalar map checks; no native inputs, rendering or PDE."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('frequency_volume_maps_tested', ROOT/'tools/task1_frequency_volume_maps.py')
MAPS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAPS)


class FrequencyVolumeMapsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        xy = [(0., -1.), (-1., 0.), (0., 0.), (1., 0.), (0., 1.)]
        self.grid = np.array([(x, y, z) for z in (.5, 2.) for x, y in xy])
        self.values = np.array([1., 2., 3., 4., 5., 11., 12., 13., 14., 15.])
        self.meta = {'cells': 10, 'h_xy_mm': 1., 'z_faces_mm': [0., 1., 3.]}
        self.archive = {key: np.array([1., 2., 3.]) for key in MAPS.METRICS}
        self.archive.update(region_total_m3=np.ones(3), region_target_m3=np.array([.5, 0., 1.]),
                            region_surface_0_5_m3=np.array([0., 1., 0.]))

    def write_npz(self, arrays=None):
        path = self.folder/'volume.npz'
        np.savez_compressed(path, **(self.archive if arrays is None else arrays))
        return path

    def test_native_slices_preserve_exact_values_faces_mask_and_actual_planes(self):
        grid_before, value_before = self.grid.copy(), self.values.copy()
        result = MAPS.native_slices(self.grid, self.meta, self.values, xy_depth_mm=1.8)
        np.testing.assert_equal(result['xy'], [[np.nan, 11., np.nan], [12., 13., 14.], [np.nan, 15., np.nan]])
        np.testing.assert_equal(result['xz'], [[2., 3., 4.], [12., 13., 14.]])
        np.testing.assert_array_equal(result['x_edges_mm'], [-1.5, -.5, .5, 1.5])
        np.testing.assert_array_equal(result['y_edges_mm'], [-1.5, -.5, .5, 1.5])
        np.testing.assert_array_equal(result['z_edges_mm'], [0., 1., 3.])
        self.assertEqual(result['xy_actual_depth_mm'], 2.)
        self.assertEqual(result['xz_actual_y_mm'], 0.)
        np.testing.assert_array_equal(self.grid, grid_before)
        np.testing.assert_array_equal(self.values, value_before)

    def test_native_depth_is_selected_not_interpolated(self):
        result = MAPS.native_slices(self.grid, self.meta, self.values, xy_depth_mm=.6)
        self.assertEqual(result['xy_actual_depth_mm'], .5)
        self.assertEqual(result['xy'][1, 1], 3.)
        self.assertNotEqual(result['xy'][1, 1], 3.+(.6-.5)/(2.-.5)*10.)

    def test_native_guards_reject_shape_nonfinite_and_count(self):
        for grid, values, meta in ((self.grid[:, :2], self.values, self.meta),
                (self.grid, self.values[:-1], self.meta),
                (self.grid, self.values, dict(self.meta, cells=11)),
                (self.grid, np.r_[np.nan, self.values[1:]], self.meta)):
            with self.subTest(shape=np.shape(grid), count=len(values), cells=meta['cells']):
                with self.assertRaises(ValueError):
                    MAPS.native_slices(grid, meta, values)

    def test_native_guards_reject_wrong_faces_spacing_and_duplicates(self):
        for meta in (dict(self.meta, z_faces_mm=[0., 2., 3.]),
                     dict(self.meta, z_faces_mm=[0., 1., 1.]),
                     dict(self.meta, h_xy_mm=2.)):
            with self.subTest(meta=meta):
                with self.assertRaises(ValueError):
                    MAPS.native_slices(self.grid, meta, self.values)
        duplicate = self.grid.copy(); duplicate[1] = duplicate[0]
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            MAPS.native_slices(duplicate, self.meta, self.values)

    def test_shared_color_range_includes_every_condition_and_saved_scale(self):
        cases = [dict(arrays={'maxTIS': np.array([1., 4.])}, scales={'raw_1Vpp': 1., 'skin_contact_only': .5}),
                 dict(arrays={'maxTIS': np.array([2., 3.])}, scales={'raw_1Vpp': 1., 'skin_contact_only': 3.})]
        before = copy.deepcopy(cases)
        self.assertEqual(MAPS.shared_color_limits(cases, 'maxTIS', 'raw_1Vpp'), (0., 4.))
        self.assertEqual(MAPS.shared_color_limits(cases, 'maxTIS', 'skin_contact_only'), (0., 9.))
        for case, old in zip(cases, before):
            np.testing.assert_array_equal(case['arrays']['maxTIS'], old['arrays']['maxTIS'])
            self.assertEqual(case['scales'], old['scales'])

    def test_optional_deep_roi_range_is_common_saved_roi_not_global(self):
        cases = [dict(arrays={'maxTIS': np.array([100., 2., 1.]),
                             'region_target_m3': np.array([0., .5, 1.])},
                      scales={'raw_1Vpp': 1., 'skin_contact_only': 2.}),
                 dict(arrays={'maxTIS': np.array([40., 3., 2.]),
                             'region_target_m3': np.array([0., .5, 1.])},
                      scales={'raw_1Vpp': 1., 'skin_contact_only': 3.})]
        self.assertEqual(MAPS.shared_color_limits(cases, 'maxTIS', 'raw_1Vpp'), (0., 100.))
        self.assertEqual(MAPS.shared_color_limits(cases, 'maxTIS', 'raw_1Vpp', deep_roi=True), (0., 3.))
        self.assertEqual(MAPS.shared_color_limits(cases, 'maxTIS', 'skin_contact_only', deep_roi=True), (0., 9.))
        empty = copy.deepcopy(cases[0]); empty['arrays']['region_target_m3'][:] = 0
        with self.assertRaises(ValueError):
            MAPS.shared_color_limits([empty], 'maxTIS', 'raw_1Vpp', deep_roi=True)

    def test_shared_color_guards_and_zero_display_fallback(self):
        case = dict(arrays={'RMS': np.zeros(2)}, scales={'raw_1Vpp': 1.})
        self.assertEqual(MAPS.shared_color_limits([case], 'RMS', 'raw_1Vpp'), (0., 1.))
        for scale in (0., -1., float('nan'), float('inf')):
            bad = copy.deepcopy(case); bad['scales']['raw_1Vpp'] = scale
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                MAPS.shared_color_limits([bad], 'RMS', 'raw_1Vpp')
        for metric, mode, cases in (('unknown','raw_1Vpp',[case]), ('RMS','unknown',[case]), ('RMS','raw_1Vpp',[])):
            with self.assertRaises(ValueError):
                MAPS.shared_color_limits(cases, metric, mode)
        for value in (-1., float('nan')):
            bad = copy.deepcopy(case); bad['arrays']['RMS'][0] = value
            with self.assertRaises(ValueError):
                MAPS.shared_color_limits([bad], 'RMS', 'raw_1Vpp')

    def test_load_only_saved_scalars_and_frozen_weights_with_sha(self):
        arrays = dict(self.archive, unused=np.array(['not consumed'], dtype=object))
        path = self.write_npz(arrays)
        result = MAPS.load_scalars(path, MAPS.sha(path), 3)
        self.assertEqual(set(result), set(self.archive))
        for key, values in self.archive.items():
            np.testing.assert_array_equal(result[key], values)
        with self.assertRaisesRegex(ValueError, 'SHA'):
            MAPS.load_scalars(path, '0'*64, 3)

    def test_load_rejects_wrong_shape_nonfinite_negative_and_nonfloat(self):
        replacements = (np.array([1., 2.]), np.array([1., np.nan, 3.]),
                        np.array([1., -2., 3.]), np.array([1, 2, 3]))
        for replacement in replacements:
            arrays = dict(self.archive, maxTIS=replacement)
            path = self.write_npz(arrays)
            with self.subTest(values=replacement), self.assertRaises(ValueError):
                MAPS.load_scalars(path, MAPS.sha(path), 3)

    def test_load_rejects_invalid_fractional_weights_and_cell_bound(self):
        for name, replacement in (('region_total_m3', np.array([0., 1., 1.])),
                                  ('region_target_m3', np.array([2., 0., 0.])),
                                  ('region_surface_0_5_m3', np.array([0., 2., 0.]))):
            arrays = dict(self.archive); arrays[name] = replacement
            path = self.write_npz(arrays)
            with self.subTest(name=name), self.assertRaises(ValueError):
                MAPS.load_scalars(path, MAPS.sha(path), 3)
        path = self.write_npz()
        for cells in (0, 800001):
            with self.assertRaises(ValueError):
                MAPS.load_scalars(path, MAPS.sha(path), cells)

    def test_json_binding_records_actual_sha_and_rejects_mismatch(self):
        path = self.folder/'condition.json'; path.write_text(json.dumps({'status': 'calculated_unadopted'}))
        pins = {}
        self.assertEqual(MAPS.bound_json(path, pins, MAPS.sha(path))['status'], 'calculated_unadopted')
        self.assertEqual(pins, {str(path.resolve()): MAPS.sha(path)})
        with self.assertRaisesRegex(ValueError, 'SHA'):
            MAPS.bound_json(path, {}, '0'*64)

    def test_verify_pins_detects_mutation_and_removal(self):
        path = self.folder/'input.json'; path.write_text('{}')
        pins = {str(path): MAPS.sha(path)}
        MAPS.verify_pins(pins)
        path.write_text('{"changed":true}')
        with self.assertRaisesRegex(ValueError, 'SHA changed'):
            MAPS.verify_pins(pins)
        path.unlink()
        with self.assertRaises(ValueError):
            MAPS.verify_pins(pins)


if __name__ == '__main__':
    unittest.main()
