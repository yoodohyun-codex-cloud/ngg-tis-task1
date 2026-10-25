"""Native scalar maxima/depth/high-volume audit without research imports."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('task1_spatial_audit', TOOLS/'task1_spatial_audit.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class SpatialTests(unittest.TestCase):
    def setUp(self):
        self.grid = np.array([(0., 0., .05, 0), (10., 0., .05, 0),
                              (0., 0., 17., 3), (10., 0., 17., 3)],
                             dtype=[('x_mm', 'f8'), ('y_mm', 'f8'), ('z_mm', 'f8'), ('layer', 'i4')])
        self.total = np.array([1., 1., 2., 2.])*1e-9
        self.weights = dict(total=self.total, target=np.array([0., 0., 2., 0.])*1e-9,
                            surface_0_5=np.array([1., 1., 0., 0.])*1e-9,
                            off_target=np.array([1., 1., 0., 2.])*1e-9)
        self.scalars = dict(maxTIS=np.array([10., 20., 4., 3.]),
                            fixedTIS=np.array([5., 10., 2., 1.5]), RMS=np.array([12., 30., 9., 7.]))

    def test_global_surface_peak_is_not_ROI_peak_or_deep_focus(self):
        result = M.spatial_from_arrays(self.grid, self.scalars, self.weights,
            np.array([1., 0., 2., 0.])*1e-9, dict(baseline_ROI_P10=4., half_baseline_ROI_mean=2.))
        self.assertEqual(result['global_maxima']['maxTIS']['cell_centre_mm'], [10., 0., .05])
        self.assertFalse(result['global_maxima']['maxTIS']['centre_inside_nominal_target'])
        self.assertEqual(result['target_maxima']['maxTIS']['cell_centre_mm'], [0., 0., 17.])
        self.assertEqual(result['central_column_peak_mean_depth']['maxTIS']['depth_mm'], .05)
        self.assertFalse(result['central_column_peak_mean_depth']['maxTIS']['in_target_depth_15_20'])
        high = result['high_modulation']['baseline_ROI_P10']['regions']
        self.assertAlmostEqual(high['surface_0_5']['volume_mm3'], 2.)
        self.assertAlmostEqual(high['off_target']['volume_mm3'], 2.)
        self.assertAlmostEqual(high['target']['volume_mm3'], 2.)
        self.assertEqual(high['surface_0_5']['cell_centre_bounds_mm'], [[0., 10.], [0., 0.], [.05, .05]])

    def test_boundary_overlap_maximum_reports_outside_center(self):
        weights = {key: value.copy() for key, value in self.weights.items()}
        weights['target'][3] = 1e-12
        values = self.scalars['maxTIS'].copy()
        values[3] = 8.
        result = M.maximum_location(self.grid, values, weights['target'])
        self.assertEqual(result['cell_centre_mm'], [10., 0., 17.])
        self.assertFalse(result['centre_inside_nominal_target'])
        self.assertEqual(result['exact_tied_maximum_cells'], 1)

    def test_inverse_volume_quantile(self):
        stats = M.statistics(np.array([1., 9.]), np.array([.96, .04]))
        self.assertEqual(stats['p95'], 1.)
        self.assertAlmostEqual(stats['mean'], 1.32)


if __name__ == '__main__':
    unittest.main()
