"""Synthetic carrier/projection and tiny field-ABI tests; no research inputs."""
import copy
import gzip
import importlib.util
import itertools
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


TOOLS = Path(__file__).resolve().parents[1]/'tools'


def base_directions():
    return np.array([np.asarray(v, float)/np.linalg.norm(v)
                     for v in itertools.product((-1, 0, 1), repeat=3) if any(v)])


def axis_index(vector):
    unit=np.asarray(vector, float)/np.linalg.norm(vector)
    return next(i for i, row in enumerate(base_directions()) if np.array_equal(row, unit))


def expected_saved(first, second, indices):
    # Evaluate only the supplied stored directions; never search for a maximum.
    directions=base_directions()[indices]
    fixed=np.array([1., 1., 0.])/math.sqrt(2.)
    maximum=2*np.minimum(np.abs(np.sum(directions*first, axis=1)),
                         np.abs(np.sum(directions*second, axis=1)))
    fixed_value=2*np.minimum(np.abs(first@fixed), np.abs(second@fixed))
    return maximum, fixed_value


class CarrierBalanceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(TOOLS))
        spec=importlib.util.spec_from_file_location('carrier_balance_tested', TOOLS/'task1_carrier_balance_audit.py')
        cls.audit=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.audit)

    def fixture(self, n=3):
        first=np.tile(np.array([3.+4.j, 0., 0.]), (n, 1))
        second=np.tile(np.array([0.+2.j, 0., 0.]), (n, 1))
        indices=np.full(n, axis_index((1, 0, 0)), dtype=np.int64)
        maximum, fixed=expected_saved(first, second, indices)
        return first, second, indices, maximum, fixed

    def test_direction_ABI_has_exact_26_prefix_2048_golden_points_and_unit_norms(self):
        result=self.audit.directions()
        self.assertEqual(result.shape, (2074, 3))
        np.testing.assert_array_equal(result[:26], base_directions())
        np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1., rtol=0, atol=4e-16)
        for i in (0, 1, 1023, 2047):
            z=1-2*(i+.5)/2048
            phase=i*np.pi*(3-np.sqrt(5))
            radius=np.sqrt(1-z*z)
            np.testing.assert_allclose(result[26+i], [radius*np.cos(phase), radius*np.sin(phase), z],
                                       rtol=0, atol=1e-15)

    def test_complex_directional_projection_preserves_phase_and_stored_winner(self):
        first=np.array([[1.+1.j, 1.-1.j, 0.]])
        second=np.array([[2., 2.j, 0.]])
        indices=np.array([axis_index((1, 1, 0))], dtype=np.int64)
        maximum, fixed=expected_saved(first, second, indices)
        before=copy.deepcopy((first, second, indices, maximum, fixed))
        result=self.audit.carrier_metrics(first, second, indices, maximum, fixed)
        np.testing.assert_allclose(result['maxTIS_reconstructed_V_m'], [2*math.sqrt(2.)], rtol=1e-15)
        np.testing.assert_allclose(result['fixedTIS_reconstructed_V_m'], [2*math.sqrt(2.)], rtol=1e-15)
        np.testing.assert_allclose(result['max_direction_balance'], [1/math.sqrt(2.)], rtol=1e-15)
        for original, saved in zip((first, second, indices, maximum, fixed), before):
            np.testing.assert_array_equal(original, saved)

    def test_balance_distinguishes_equal_and_unequal_carriers(self):
        first=np.array([[2., 0., 0.], [4., 0., 0.]], dtype=complex)
        second=np.array([[2.j, 0., 0.], [1.j, 0., 0.]], dtype=complex)
        indices=np.full(2, axis_index((1, 0, 0)), dtype=np.int64)
        maximum, fixed=expected_saved(first, second, indices)
        result=self.audit.carrier_metrics(first, second, indices, maximum, fixed)
        np.testing.assert_allclose(result['max_direction_balance'], [1., .25], rtol=0, atol=1e-15)
        np.testing.assert_allclose(result['fixed_direction_balance'], [1., .25], rtol=0, atol=1e-15)

    def test_zero_over_zero_balance_policy_is_zero_with_finite_zero_metrics(self):
        first=np.zeros((2, 3), complex);second=first.copy()
        indices=np.array([0, 25], dtype=np.int64)
        result=self.audit.carrier_metrics(first, second, indices, np.zeros(2), np.zeros(2))
        for key in ('carrier0_RMS_V_m', 'carrier1_RMS_V_m', 'combined_fundamental_RMS_V_m',
                    'max_direction_balance', 'fixed_direction_balance',
                    'maxTIS_reconstructed_V_m', 'fixedTIS_reconstructed_V_m'):
            values=result[key]
            self.assertTrue(np.isfinite(values).all())
            np.testing.assert_array_equal(values, np.zeros(2))
        for key in ('max_direction_zero_zero', 'fixed_direction_zero_zero'):
            np.testing.assert_array_equal(result[key], [True, True])

    def test_carrier_RMS_is_full_vector_RMS_not_a_directional_projection(self):
        first=np.array([[3.+4.j, 12., 0.]])
        second=np.array([[2.j, 0., 0.]])
        indices=np.array([axis_index((1, 0, 0))], dtype=np.int64)
        maximum, fixed=expected_saved(first, second, indices)
        result=self.audit.carrier_metrics(first, second, indices, maximum, fixed)
        self.assertAlmostEqual(result['carrier0_RMS_V_m'][0], 13/math.sqrt(2.))
        self.assertAlmostEqual(result['carrier1_RMS_V_m'][0], math.sqrt(2.))
        self.assertAlmostEqual(result['combined_fundamental_RMS_V_m'][0], math.sqrt((169+4)/2))
        self.assertNotAlmostEqual(result['carrier0_RMS_V_m'][0], 5/math.sqrt(2.))

    def test_invalid_field_and_saved_shapes_or_nonfinite_values_are_rejected(self):
        for variant in ('first_shape', 'second_count', 'saved_shape', 'nan_first', 'inf_second', 'nan_saved'):
            first,second,indices,maximum,fixed=self.fixture()
            if variant=='first_shape':first=first[:, :2]
            elif variant=='second_count':second=second[:2]
            elif variant=='saved_shape':maximum=maximum[:, None]
            elif variant=='nan_first':first[1, 2]=complex(0, math.nan)
            elif variant=='inf_second':second[2, 1]=math.inf
            else:fixed[1]=math.nan
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                self.audit.carrier_metrics(first, second, indices, maximum, fixed)

    def test_stored_direction_indices_require_integer_shape_and_valid_range(self):
        first,second,_,maximum,fixed=self.fixture()
        for indices in (np.array([0., 1., 2.]), np.array([-1, 0, 1]),
                        np.array([0, 1, 2074]), np.array([[0], [1], [2]]), np.array([0, 1])):
            with self.subTest(indices=repr(indices)), self.assertRaises(ValueError):
                self.audit.carrier_metrics(first, second, indices, maximum, fixed)

    def test_every_cell_saved_metric_regression_uses_fixed_absolute_and_relative_tolerances(self):
        first,second,indices,maximum,fixed=self.fixture()
        accepted=maximum.copy();accepted[1]+=2e-10
        self.audit.carrier_metrics(first, second, indices, accepted, fixed)
        for field in ('maximum', 'fixed'):
            bad_max,bad_fixed=maximum.copy(),fixed.copy()
            (bad_max if field=='maximum' else bad_fixed)[1]+=1e-6
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.audit.carrier_metrics(first, second, indices, bad_max, bad_fixed)

    def field_fixture(self):
        real=np.arange(18, dtype=float).reshape(2, 3, 3)+.125
        imaginary=np.arange(18, dtype=float)[::-1].reshape(2, 3, 3)+.25
        return (real+1.j*imaginary).astype('<c16')

    def test_raw_and_gzip_little_endian_ABI_selects_correct_asymmetric_active_channel(self):
        expected=self.field_fixture()
        with tempfile.TemporaryDirectory() as directory:
            for compressed in (False, True):
                path=Path(directory)/('field.bin.gz' if compressed else 'field.bin')
                payload=expected.tobytes(order='C')
                path.write_bytes(gzip.compress(payload) if compressed else payload)
                for channel in (0, 1):
                    result=self.audit.read_active_field(path, 3, channel)
                    np.testing.assert_array_equal(result, expected[channel])
                    self.assertEqual(result.shape, (3, 3))
                    self.assertFalse(np.shares_memory(result, expected))
                self.assertNotEqual(expected[0, 0, 0], expected[1, 0, 0])

    def test_exact_decoded_byte_length_rejects_truncated_or_trailing_raw_and_gzip(self):
        payload=self.field_fixture().tobytes(order='C')
        with tempfile.TemporaryDirectory() as directory:
            for compressed in (False, True):
                for variant, malformed in (('truncated', payload[:-1]), ('trailing', payload+b'\x00'*16)):
                    path=Path(directory)/(variant+('.bin.gz' if compressed else '.bin'))
                    path.write_bytes(gzip.compress(malformed) if compressed else malformed)
                    with self.subTest(compressed=compressed, variant=variant), self.assertRaises(ValueError):
                        self.audit.read_active_field(path, 3, 0)

    def test_nonfinite_in_either_active_or_inactive_basis_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for bad_channel in (0, 1):
                values=self.field_fixture();values[bad_channel, 1, 2]=complex(math.inf, 0)
                path=Path(directory)/f'field-{bad_channel}.bin'
                path.write_bytes(values.tobytes(order='C'))
                with self.subTest(bad_channel=bad_channel), self.assertRaises(ValueError):
                    self.audit.read_active_field(path, 3, 0)

    def test_field_reader_rejects_invalid_active_channel_and_cell_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'field.bin'
            path.write_bytes(self.field_fixture().tobytes(order='C'))
            for n, channel in ((3, -1), (3, 2), (0, 0), (-1, 0), (3.5, 0)):
                with self.subTest(n=n, channel=channel), self.assertRaises(ValueError):
                    self.audit.read_active_field(path, n, channel)


if __name__=='__main__':
    unittest.main()
