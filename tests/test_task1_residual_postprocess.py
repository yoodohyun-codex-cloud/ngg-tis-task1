"""Synthetic comparisons and byte decoding only; never run a research producer.

The module under test imports only the standard library at module scope.  These
tests call three pure readback helpers with an explicit NumPy argument; neither
process_case nor any research-module import or PDE is invoked.
"""
import gzip
import importlib.util
import math
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np


SPEC = importlib.util.spec_from_file_location('task1_residual_postprocess_tested',
    Path(__file__).resolve().parents[1]/'tools/task1_residual_postprocess.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ResidualComparisonTests(unittest.TestCase):
    def test_nearly_zero_imaginary_component_fails_preserved_gate_but_passes_normwise(self):
        reference = np.array([[1.+1e-16j, .3+0j], [-.2+1e-14j, 0j]], dtype='<c16')
        actual = reference.copy()
        actual[0, 0] += 2e-14j
        result = M.compare_arrays(actual, reference, np, include_failed_entries=True)
        self.assertFalse(result['componentwise_passed'])
        self.assertTrue(result['normwise_passed'])
        self.assertFalse(result['decoded_binary_byte_equal'])
        self.assertEqual(result['failed_component_count'], 1)
        failed = result['failed_entries'][0]
        self.assertEqual(failed['index'], [0, 0])
        self.assertEqual(failed['component'], 'imag')
        self.assertEqual(failed['reference'], 1e-16)
        self.assertGreater(failed['absolute_error'], failed['allowed_absolute_error'])
        self.assertLess(result['max_abs_error'], result['normwise_limit_abs'])
        self.assertEqual(result['componentwise_tolerance'], dict(relative=1e-8, absolute=1e-14))

    def test_exact_absolute_threshold_is_inclusive_and_next_float_fails(self):
        reference = np.array([0j], dtype='<c16')
        boundary = np.array([complex(1e-14, -1e-14)], dtype='<c16')
        result = M.compare_arrays(boundary, reference, np, include_failed_entries=True)
        self.assertTrue(result['componentwise_passed'])
        self.assertTrue(result['normwise_passed'])
        self.assertEqual(result['failed_component_count'], 0)
        self.assertEqual(result['failed_entries'], [])
        above = np.array([complex(np.nextafter(1e-14, math.inf), 0.)], dtype='<c16')
        result = M.compare_arrays(above, reference, np, include_failed_entries=True)
        self.assertFalse(result['componentwise_passed'])
        self.assertFalse(result['normwise_passed'])
        self.assertEqual(result['failed_component_count'], 1)

    def test_failed_entries_keep_full_loss_tensor_index_and_real_imag_components(self):
        reference = np.zeros((6, 2, 2), dtype='<c16')
        actual = reference.copy()
        actual[2, 1, 0] = 3e-12-4e-12j
        actual[5, 0, 1] = 2e-12j
        result = M.compare_arrays(actual, reference, np, include_failed_entries=True)
        entries = {(tuple(row['index']), row['component']): row for row in result['failed_entries']}
        self.assertEqual(set(entries), {((2, 1, 0), 'real'), ((2, 1, 0), 'imag'), ((5, 0, 1), 'imag')})
        self.assertEqual(result['failed_component_count'], 3)
        self.assertEqual(entries[((2, 1, 0), 'real')]['actual'], 3e-12)
        self.assertEqual(entries[((2, 1, 0), 'imag')]['actual'], -4e-12)
        self.assertEqual(entries[((2, 1, 0), 'imag')]['absolute_error'], 4e-12)
        self.assertEqual(entries[((2, 1, 0), 'imag')]['allowed_absolute_error'], 1e-14)
        self.assertNotIn('failed_entries', M.compare_arrays(actual, reference, np))

    def test_shape_and_nonfinite_values_are_rejected_on_either_side(self):
        finite = np.zeros((2, 2), dtype='<c16')
        invalid = [
            (finite, np.zeros(4, dtype='<c16')),
            (np.full((2, 2), complex(math.nan, 0), dtype='<c16'), finite),
            (np.full((2, 2), complex(0, math.inf), dtype='<c16'), finite),
            (finite, np.full((2, 2), complex(0, math.nan), dtype='<c16'))]
        for actual, reference in invalid:
            with self.subTest(actual_shape=actual.shape, reference_shape=reference.shape), self.assertRaisesRegex(ValueError, 'shape/nonfinite'):
                M.compare_arrays(actual, reference, np, include_failed_entries=True)

    def test_signed_zero_can_be_numerically_equal_without_decoded_byte_identity(self):
        reference = np.array([complex(0., 0.)], dtype='<c16')
        actual = np.array([complex(-0., 0.)], dtype='<c16')
        result = M.compare_arrays(actual, reference, np)
        self.assertFalse(result['decoded_binary_byte_equal'])
        self.assertTrue(result['componentwise_passed'])
        self.assertTrue(result['normwise_passed'])
        self.assertEqual(result['max_abs_error'], 0.)

    def test_noncontiguous_input_retains_logical_matrix_indices(self):
        reference = np.arange(12, dtype=float).astype('<c16').reshape(3, 4).T
        actual = reference.copy(order='F')
        actual[2, 1] += 2e-7j
        self.assertFalse(reference.flags.c_contiguous)
        result = M.compare_arrays(actual, reference, np, include_failed_entries=True)
        self.assertEqual(result['shape'], [4, 3])
        self.assertEqual(result['failed_entries'][0]['index'], [2, 1])
        self.assertEqual(result['failed_entries'][0]['component'], 'imag')
        self.assertFalse(result['normwise_passed'])


class ResidualNativeReadbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.values = np.array([[1.+2j, -3.+4j], [5.-6j, 7.+8j]], dtype='<c16')
        self.raw = self.values.tobytes(order='C')

    def deadline(self):
        return time.monotonic()+10.

    def write_gzip(self, name, data, *, stored_name='native-field', mtime=1, level=6):
        path = self.root/name
        with path.open('wb') as raw:
            with gzip.GzipFile(fileobj=raw, filename=stored_name, mode='wb', mtime=mtime, compresslevel=level) as stream:
                stream.write(data)
        return path

    def test_plain_and_gzip_exact_little_endian_complex_dimensions(self):
        plain = self.root/'source.bin'
        plain.write_bytes(self.raw)
        zipped = self.write_gzip('source.bin.gz', self.raw)
        for path in (plain, zipped):
            with self.subTest(path=path.name):
                result = M._array(path, (2, 2), self.deadline(), np)
                np.testing.assert_array_equal(result, self.values)
                self.assertEqual(result.shape, (2, 2))
                self.assertEqual(result.dtype, np.dtype('<c16'))

    def test_short_extra_and_wrong_complex_dimension_are_rejected(self):
        for name, raw, shape in [('short.bin', self.raw[:-1], (2, 2)),
                                 ('extra.bin', self.raw+b'\0', (2, 2)),
                                 ('dimensions.bin', self.raw, (2, 3)),
                                 ('complex64.bin', self.values.astype('<c8').tobytes(), (2, 2))]:
            path = self.root/name
            path.write_bytes(raw)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Exact complex128 array byte count'):
                M._array(path, shape, self.deadline(), np)

    def test_extra_decoded_gzip_byte_and_second_member_are_not_ignored(self):
        extra = self.write_gzip('extra.bin.gz', self.raw+b'\0')
        appended = self.write_gzip('appended.bin.gz', self.raw)
        with appended.open('ab') as stream:
            stream.write(gzip.compress(b'\0'))
        for path in (extra, appended):
            with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, 'Exact complex128 array byte count'):
                M._array(path, (2, 2), self.deadline(), np)

    def test_nonfinite_decoded_real_or_imaginary_component_is_rejected(self):
        for index, value in [(0, complex(math.nan, 2.)), (3, complex(1., math.inf))]:
            invalid = self.values.copy().reshape(-1)
            invalid[index] = value
            path = self.write_gzip(f'nonfinite-{index}.bin.gz', invalid.tobytes())
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'Nonfinite complex native array'):
                M._array(path, (2, 2), self.deadline(), np)

    def test_array_deadline_is_checked_before_readback(self):
        path = self.root/'source.bin'
        path.write_bytes(self.raw)
        with self.assertRaisesRegex(ValueError, 'Residual postprocess deadline: array'):
            M._array(path, (2, 2), time.monotonic()-1., np)

    def test_equivalent_decoded_gzip_data_ignores_header_and_compression_differences(self):
        left = self.write_gzip('left.csv.gz', self.raw, stored_name='old-name', mtime=1, level=1)
        right = self.write_gzip('right.csv.gz', self.raw, stored_name='new-name', mtime=123, level=9)
        self.assertNotEqual(left.read_bytes(), right.read_bytes())
        self.assertTrue(M._same_decoded_bytes(left, right, self.deadline()))
        plain = self.root/'plain.csv'
        plain.write_bytes(self.raw)
        self.assertTrue(M._same_decoded_bytes(left, plain, self.deadline()))

    def test_decoded_content_difference_after_first_chunk_and_length_difference_fail(self):
        payload = b'x_mm,y_mm,z_mm,layer,volume_m3\n'+b'0,0,1,1,1e-9\n'*100000
        self.assertGreater(len(payload), 1024**2)
        left = self.write_gzip('left.csv.gz', payload)
        changed = self.write_gzip('changed.csv.gz', payload[:-1]+b'!')
        longer = self.write_gzip('longer.csv.gz', payload+b'\0')
        self.assertFalse(M._same_decoded_bytes(left, changed, self.deadline()))
        self.assertFalse(M._same_decoded_bytes(left, longer, self.deadline()))

    def test_decoded_byte_comparison_deadline_is_enforced(self):
        left = self.write_gzip('left.csv.gz', self.raw)
        right = self.write_gzip('right.csv.gz', self.raw)
        with self.assertRaisesRegex(ValueError, 'Residual postprocess deadline: exact_decoded'):
            M._same_decoded_bytes(left, right, time.monotonic()-1.)


if __name__ == '__main__':
    unittest.main()
