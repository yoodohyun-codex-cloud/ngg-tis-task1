"""Synthetic-only checks for the finite Rs-window analysis contract.

No measured coating data, workbooks, PDE, Java, preparation or publication is
used by these tests.  The constrained optimizer is exercised on synthetic data.
"""
from copy import deepcopy
import math
import unittest
from unittest import mock

import numpy as np

import eis_rs_window_analysis as analysis


def synthetic_points(rs=17.25, q=3.7e-4, exponent=.65):
    frequencies = np.geomspace(1., 10000., 30)
    frequencies[0], frequencies[-1] = 1., 10000.
    impedance = rs + 1 / (q * (2j * np.pi * frequencies) ** exponent)
    return [dict(frequency_Hz=float(f), Z_real_ohm=float(z.real),
                 Z_imag_ohm=float(z.imag))
            for f, z in zip(frequencies, impedance)]


def reported_fit(rs=17.25, q=3.7e-4, exponent=.65, *, passive=True):
    return dict(Rs_ohm=rs, Q_S_s_power_n=q, n=exponent,
                weighted_SSE=.125, relative_complex_RMS_percent=1.25,
                relative_complex_max_percent=1.75,
                subtraction_nonnegative_real_over_full_measured_band=passive,
                diagnostic_marker='retain the original unconstrained result')


class RsWindowAnalysisTests(unittest.TestCase):
    def assert_parameters_recovered(self, fitted):
        self.assertTrue(math.isclose(fitted['Rs_ohm'], 17.25,
                                     rel_tol=2e-7, abs_tol=0.))
        self.assertTrue(math.isclose(fitted['Q_S_s_power_n'], 3.7e-4,
                                     rel_tol=2e-7, abs_tol=0.))
        self.assertAlmostEqual(fitted['n'], .65, delta=2e-7)

    def test_analytic_recovery_and_actual_window_metadata(self):
        points = synthetic_points()
        retained = deepcopy(points)
        all_f = np.array([point['frequency_Hz'] for point in points])
        all_z = np.array([complex(point['Z_real_ohm'], point['Z_imag_ohm'])
                          for point in points])
        for cutoff, expected_count in ((500, 10), (2000, 6)):
            with self.subTest(cutoff=cutoff):
                f, z = analysis.validate_points(points, cutoff)
                self.assertIsInstance(f, np.ndarray)
                self.assertIsInstance(z, np.ndarray)
                np.testing.assert_array_equal(f, all_f)
                np.testing.assert_array_equal(z, all_z)
                with mock.patch.object(analysis, 'constrained_window_fit',
                                       side_effect=AssertionError('passive fit must not fall back')):
                    result = analysis.analyze_points(points, cutoff)
                selected_f = all_f[all_f >= cutoff]
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['cutoff_Hz'], cutoff)
                self.assertTrue(result['unconstrained_passive'])
                self.assertEqual(result['selection'], 'unconstrained')
                self.assertEqual(result['fallback_calls'], 0)
                self.assertEqual(result['n_points'], expected_count)
                np.testing.assert_allclose(result['actual_frequency_range_Hz'],
                                           [selected_f[0], 10000.], rtol=0, atol=0)
                self.assertTrue(result['model_window_sensitivity_not_confidence_interval'])
                self.assert_parameters_recovered(result['unconstrained_fit'])
                self.assert_parameters_recovered(result['selected_fit'])
        self.assertEqual(points, retained)

    def test_real_constrained_fit_recovers_an_interior_grid_exponent(self):
        points = synthetic_points()
        for cutoff in (500, 2000):
            with self.subTest(cutoff=cutoff):
                f, z = analysis.validate_points(points, cutoff)
                fitted = analysis.constrained_window_fit(f, z, cutoff)
                self.assert_parameters_recovered(fitted)
                self.assertGreaterEqual(fitted['Rs_ohm'], 0)
                self.assertLessEqual(fitted['Rs_ohm'], float(z.real.min()) + 1e-9)

    def test_point_exactly_at_cutoff_is_included(self):
        for cutoff, replacement_index, expected_count in ((500, 19, 11), (2000, 23, 7)):
            with self.subTest(cutoff=cutoff):
                points = synthetic_points()
                value = 17.25 + 1 / (3.7e-4 * (2j * np.pi * cutoff) ** .65)
                points[replacement_index] = dict(frequency_Hz=float(cutoff),
                                                Z_real_ohm=float(value.real),
                                                Z_imag_ohm=float(value.imag))
                with mock.patch.object(analysis, 'fit_series_cpe', return_value=reported_fit()):
                    result = analysis.analyze_points(points, cutoff)
                self.assertEqual(result['n_points'], expected_count)
                self.assertEqual(result['actual_frequency_range_Hz'], [float(cutoff), 10000.])

    def test_nonpassive_original_is_preserved_and_real_fallback_uses_full_band_bound(self):
        points = synthetic_points()
        # Outside either fitting window: this point must still bound Rs.
        points[0]['Z_real_ohm'] = 2.
        retained = deepcopy(points)
        unconstrained = reported_fit(rs=25., passive=False)
        original_fit = deepcopy(unconstrained)
        real_fallback = analysis.constrained_window_fit
        with mock.patch.object(analysis, 'fit_series_cpe', return_value=unconstrained) as fitter:
            with mock.patch.object(analysis, 'constrained_window_fit', wraps=real_fallback) as fallback:
                result = analysis.analyze_points(points, 2000)
        fitter.assert_called_once()
        fallback.assert_called_once()
        self.assertEqual(result['status'], 'complete')
        self.assertFalse(result['unconstrained_passive'])
        self.assertEqual(result['selection'], 'passivity_constrained_fallback')
        self.assertEqual(result['fallback_calls'], 1)
        self.assertEqual(result['unconstrained_fit'], original_fit)
        self.assertEqual(unconstrained, original_fit)
        selected = result['selected_fit']
        self.assertGreaterEqual(selected['Rs_ohm'], 0)
        self.assertLessEqual(selected['Rs_ohm'], 2. + 1e-9)
        self.assertGreater(selected['Q_S_s_power_n'], 0)
        self.assertTrue(math.isfinite(selected['Q_S_s_power_n']))
        self.assertGreaterEqual(selected['n'], .2 - 1e-12)
        self.assertLessEqual(selected['n'], 1. + 1e-12)
        self.assertEqual(points, retained)

    def test_invalid_measurements_are_rejected_before_either_fitter(self):
        valid = synthetic_points()
        invalid = [('29 points', valid[:-1]), ('31 points', valid + [deepcopy(valid[-1])])]
        duplicate = deepcopy(valid)
        duplicate[4]['frequency_Hz'] = duplicate[3]['frequency_Hz']
        invalid.append(('duplicate frequency', duplicate))
        unordered = deepcopy(valid)
        unordered[4], unordered[5] = unordered[5], unordered[4]
        invalid.append(('unordered frequency', unordered))
        for field in ('frequency_Hz', 'Z_real_ohm', 'Z_imag_ohm'):
            for value in (math.nan, math.inf, -math.inf):
                points = deepcopy(valid)
                points[8][field] = value
                invalid.append((f'{field}={value}', points))
        for index, value in ((0, .5), (-1, 10001.)):
            points = deepcopy(valid)
            points[index]['frequency_Hz'] = value
            invalid.append(('outside measured span', points))
        for index, value in ((0, 1.01), (-1, 9999.)):
            points = deepcopy(valid)
            points[index]['frequency_Hz'] = value
            invalid.append(('missing exact measured endpoint', points))
        missing = deepcopy(valid)
        del missing[8]['Z_real_ohm']
        invalid.append(('missing measured impedance field', missing))
        zero = deepcopy(valid)
        zero[8].update(Z_real_ohm=0., Z_imag_ohm=0.)
        invalid.append(('zero magnitude cannot receive relative-error weight', zero))
        for name, points in invalid:
            with self.subTest(name=name):
                with mock.patch.object(analysis, 'fit_series_cpe') as fitter:
                    with mock.patch.object(analysis, 'constrained_window_fit') as fallback:
                        with self.assertRaises((ValueError, TypeError)):
                            analysis.analyze_points(points, 500)
                fitter.assert_not_called()
                fallback.assert_not_called()

    def test_unregistered_cutoff_is_rejected_before_fitting(self):
        for cutoff in (0, -500, 1000, 3000, 500.5, math.nan, math.inf, True, '500'):
            with self.subTest(cutoff=cutoff):
                with mock.patch.object(analysis, 'fit_series_cpe') as fitter:
                    with mock.patch.object(analysis, 'constrained_window_fit') as fallback:
                        with self.assertRaises((ValueError, TypeError)):
                            analysis.analyze_points(synthetic_points(), cutoff)
                fitter.assert_not_called()
                fallback.assert_not_called()

    def test_nonpositive_or_nonfinite_fitted_q_is_not_a_successful_analysis(self):
        for q in (0., -1e-4, math.nan, math.inf):
            with self.subTest(q=q):
                bad_fit = reported_fit(q=q)
                with mock.patch.object(analysis, 'fit_series_cpe', return_value=bad_fit):
                    with mock.patch.object(analysis, 'constrained_window_fit') as fallback:
                        with self.assertRaises((ValueError, TypeError)):
                            analysis.analyze_points(synthetic_points(), 500)
                fallback.assert_not_called()

    def test_missing_required_cost_is_rejected_before_fallback(self):
        for cost in ('weighted_SSE', 'relative_complex_RMS_percent',
                     'relative_complex_max_percent'):
            with self.subTest(missing_cost=cost):
                bad_fit = reported_fit()
                del bad_fit[cost]
                with mock.patch.object(analysis, 'fit_series_cpe', return_value=bad_fit) as fitter:
                    with mock.patch.object(analysis, 'constrained_window_fit') as fallback:
                        with self.assertRaises((ValueError, TypeError)):
                            analysis.analyze_points(synthetic_points(), 500)
                fitter.assert_called_once()
                fallback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
