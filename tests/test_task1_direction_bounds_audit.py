"""Synthetic direction-bound contracts; no native files, PDE or preparation."""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))


class DirectionBoundsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'direction_bounds_audit_synthetic', ROOT/'tools/task1_direction_bounds_audit.py')
        cls.audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def bounds(self, first, second, **kwargs):
        return self.audit.field_bounds(np.asarray(first, complex), np.asarray(second, complex), **kwargs)

    def test_fixed_lambda_grid_contains_endpoints_and_midpoint(self):
        self.assertEqual(tuple(self.audit.LAMBDAS), tuple(i/8 for i in range(9)))

    def test_parallel_carriers_have_exact_continuous_maximum(self):
        first = np.array([[3+4j, 0, 0], [.2-.1j, 0, 0]], complex)
        second = np.array([[1j, 0, 0], [-.3+.4j, 0, 0]], complex)
        result = self.bounds(first, second)
        exact = 2*np.minimum(abs(first[:, 0]), abs(second[:, 0]))
        np.testing.assert_allclose(result['continuous_direction_UB_raw_V_m'], exact, rtol=2e-13, atol=1e-14)
        np.testing.assert_allclose(result['X_TIS'], exact, rtol=2e-13, atol=1e-14)
        np.testing.assert_array_equal(result['Y_TIS'], np.zeros(2))
        np.testing.assert_array_equal(result['Z_TIS'], np.zeros(2))

    def test_orthogonal_real_carriers_require_a_diagonal_direction(self):
        result = self.bounds([[1, 0, 0]], [[0, 1, 0]])
        np.testing.assert_allclose(result['continuous_direction_UB_raw_V_m'], [math.sqrt(2)], rtol=2e-13, atol=1e-14)
        for key in ('X_TIS', 'Y_TIS', 'Z_TIS'):
            np.testing.assert_array_equal(result[key], [0.])
        self.assertGreater(result['continuous_direction_UB_V_m'][0], 1.)

    def test_complex_elliptical_carriers_use_real_and_imaginary_outer_products(self):
        result = self.bounds([[1, 1j, 0]], [[1, -1j, 0]])
        np.testing.assert_allclose(result['continuous_direction_UB_raw_V_m'], [2.], rtol=2e-13, atol=1e-14)
        np.testing.assert_array_equal(result['X_TIS'], [2.])
        np.testing.assert_array_equal(result['Y_TIS'], [2.])
        np.testing.assert_array_equal(result['Z_TIS'], [0.])

    def test_zero_carrier_has_exact_zero_modulation_despite_nonzero_other_field(self):
        result = self.bounds([[0, 0, 0], [1+2j, -.2j, 3]], [[1, 2j, 3], [0, 0, 0]])
        for key in ('X_TIS', 'Y_TIS', 'Z_TIS', 'continuous_direction_UB_raw_V_m', 'continuous_direction_UB_V_m'):
            np.testing.assert_array_equal(result[key], np.zeros(2))

    def test_raw_bound_is_homogeneous_and_independent_carrier_phase_invariant(self):
        rng = np.random.default_rng(1701)
        first = rng.normal(size=(7, 3))+1j*rng.normal(size=(7, 3))
        second = rng.normal(size=(7, 3))+1j*rng.normal(size=(7, 3))
        original = self.bounds(first, second)
        changed = self.bounds(first*np.exp(.37j)*2.3, second*np.exp(-.91j)*2.3)
        for key in ('X_TIS', 'Y_TIS', 'Z_TIS', 'continuous_direction_UB_raw_V_m'):
            np.testing.assert_allclose(changed[key], original[key]*2.3, rtol=2e-12, atol=1e-13)

    def test_continuous_upper_bound_is_invariant_under_real_orthogonal_rotation(self):
        rng = np.random.default_rng(1702)
        rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        first = rng.normal(size=(5, 3))+1j*rng.normal(size=(5, 3))
        second = rng.normal(size=(5, 3))+1j*rng.normal(size=(5, 3))
        original = self.bounds(first, second)
        changed = self.bounds(first@rotation, second@rotation)
        np.testing.assert_allclose(changed['continuous_direction_UB_raw_V_m'], original['continuous_direction_UB_raw_V_m'],
            rtol=2e-12, atol=1e-13)

    def test_dense_synthetic_projection_never_exceeds_guarded_upper_bound(self):
        rng = np.random.default_rng(1703)
        first = rng.normal(size=(11, 3))+1j*rng.normal(size=(11, 3))
        second = rng.normal(size=(11, 3))+1j*rng.normal(size=(11, 3))
        directions = rng.normal(size=(2049, 3))
        directions /= np.linalg.norm(directions, axis=1)[:, None]
        lower = 2*np.minimum(abs(first@directions.T), abs(second@directions.T)).max(axis=1)
        result = self.bounds(first, second, chunk_cells=3)
        self.assertTrue(np.all(lower <= result['continuous_direction_UB_V_m']+1e-12))
        self.assertTrue(np.all(result['continuous_direction_UB_V_m'] >= result['continuous_direction_UB_raw_V_m']))
        self.audit.validate_lower_bound(lower, result['continuous_direction_UB_V_m'])

    def test_chunking_does_not_change_outputs_or_modify_source_arrays(self):
        rng = np.random.default_rng(1704)
        first = rng.normal(size=(13, 3))+1j*rng.normal(size=(13, 3))
        second = rng.normal(size=(13, 3))+1j*rng.normal(size=(13, 3))
        before = (first.copy(), second.copy())
        single = self.bounds(first, second, chunk_cells=1)
        larger = self.bounds(first, second, chunk_cells=256)
        for key in ('X_TIS', 'Y_TIS', 'Z_TIS', 'continuous_direction_UB_raw_V_m', 'continuous_direction_UB_V_m'):
            np.testing.assert_allclose(single[key], larger[key], rtol=1e-14, atol=1e-14)
        np.testing.assert_array_equal(first, before[0]); np.testing.assert_array_equal(second, before[1])

    def test_field_bound_rejects_dimension_mismatch_nonfinite_and_invalid_chunk(self):
        valid = np.ones((2, 3), complex)
        for first, second in ((np.ones((2, 2)), valid), (valid, np.ones((3, 3))),
                              (np.ones((2, 3, 1)), valid), (np.empty((0, 3)), np.empty((0, 3)))):
            with self.subTest(first=np.shape(first), second=np.shape(second)), self.assertRaises(ValueError):
                self.audit.field_bounds(first, second)
        for value in (np.nan, np.inf, -np.inf):
            bad = valid.copy(); bad[0, 0] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.audit.field_bounds(bad, valid)
        with self.assertRaises(ValueError): self.audit.field_bounds(valid, valid, chunk_cells=0)

    def test_lower_bound_validation_rejects_material_inversion_and_nonfinite_values(self):
        self.audit.validate_lower_bound(np.array([1.+5e-11]), np.array([1.]))
        for lower, upper in (([1.01], [1.]), ([np.nan], [1.]), ([1.], [np.inf]), ([1., 2.], [2.])):
            with self.subTest(lower=lower, upper=upper), self.assertRaises(ValueError):
                self.audit.validate_lower_bound(np.asarray(lower), np.asarray(upper))

    def test_threshold_volume_uses_fractional_weights_and_inclusive_ties(self):
        lower = np.array([.5, 1., 2.]); upper = np.array([1., 2., 3.]); weights = np.array([.125, .25, .625])
        result = self.audit.weighted_volume_interval(lower, upper, weights, 1.)
        self.assertAlmostEqual(result['lower_volume_m3'], .875)
        self.assertAlmostEqual(result['upper_volume_m3'], 1.)
        self.assertNotAlmostEqual(result['lower_volume_m3'], 2/3)

    def test_tolerated_roundoff_inversion_cannot_emit_an_inverted_volume_interval(self):
        lower = np.array([1.+5e-11]); upper = np.array([1.]); weights = np.array([.125])
        self.audit.validate_lower_bound(lower, upper)
        try:
            result = self.audit.weighted_volume_interval(lower, upper, weights, 1.+2e-11)
        except ValueError:
            # Strict interval rejection is acceptable; silently reversed bounds are not.
            return
        self.assertLessEqual(result['lower_volume_m3'], result['upper_volume_m3'])

    def test_common_amplitude_scaling_precedes_fixed_threshold_classification(self):
        lower = np.array([.5, 1., 2.]); upper = np.array([1., 2., 3.]); weights = np.array([.125, .25, .625])
        raw = self.audit.weighted_volume_interval(lower, upper, weights, 1.)
        scaled = self.audit.weighted_volume_interval(lower, upper, weights, 1., scale=.5)
        direct = self.audit.weighted_volume_interval(lower*.5, upper*.5, weights, 1.)
        self.assertAlmostEqual(scaled['lower_volume_m3'], .625)
        self.assertAlmostEqual(scaled['upper_volume_m3'], .875)
        self.assertEqual(scaled['lower_volume_m3'], direct['lower_volume_m3'])
        self.assertEqual(scaled['upper_volume_m3'], direct['upper_volume_m3'])
        self.assertNotAlmostEqual(scaled['lower_volume_m3'], raw['lower_volume_m3']*.5)

    def test_threshold_volume_interval_contains_every_compatible_synthetic_field(self):
        lower = np.array([.5, 1., 2.]); upper = np.array([1., 2., 3.]); weights = np.array([.125, .25, .625])
        result = self.audit.weighted_volume_interval(lower, upper, weights, 1.2, scale=.8)
        for fraction in np.linspace(0., 1., 9):
            actual = lower+(upper-lower)*fraction
            volume = float(weights[actual*.8 >= 1.2].sum())
            self.assertGreaterEqual(volume+1e-15, result['lower_volume_m3'])
            self.assertLessEqual(volume, result['upper_volume_m3']+1e-15)

    def test_robust_failure_uses_opposite_interval_ends_for_target_and_nontarget(self):
        target = self.audit.robust_failure(.5, .8, 1., 1.2, direction='greater')
        surface = self.audit.robust_failure(1.3, 1.5, 1., 1.2, direction='less')
        self.assertEqual(target['status'], 'conditional_direction_robust_failure')
        self.assertEqual(surface['status'], 'conditional_direction_robust_failure')
        for direction in ('greater', 'less'):
            overlapping = self.audit.robust_failure(.9, 1.1, 1., 1.2, direction=direction)
            self.assertEqual(overlapping['status'], 'inconclusive')

    def test_equality_and_existing_arithmetic_allowance_do_not_become_robust_failures(self):
        target = self.audit.robust_failure(.99, 1.-5e-11, 1., 1.2, direction='greater')
        surface = self.audit.robust_failure(1.2+5e-11, 1.3, 1., 1.2, direction='less')
        self.assertEqual(target['status'], 'inconclusive')
        self.assertEqual(surface['status'], 'inconclusive')
        tied = self.audit.robust_failure(1., 1., 1., 1., direction='greater')
        self.assertEqual(tied['status'], 'inconclusive')

    def test_robust_failure_rejects_unordered_nonfinite_or_unknown_direction_inputs(self):
        for bounds in ((2., 1., 1., 2.), (1., 2., 2., 1.), (np.nan, 1., 1., 2.), (1., 2., 1., np.inf)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                self.audit.robust_failure(*bounds, direction='greater')
        with self.assertRaises(ValueError): self.audit.robust_failure(1., 2., 1., 2., direction='equal')


if __name__ == '__main__': unittest.main()
