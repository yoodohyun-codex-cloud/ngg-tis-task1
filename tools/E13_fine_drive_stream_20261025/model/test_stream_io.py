"""Manufactured-only tests: tiny in-memory ZIP/NPY bytes, no native files.

The sole controller runs these only in its source-bound MFG child.  Fixture
creation neither calls np.save/load nor accesses the filesystem.  No fixture
array has more than 65536 elements.
"""
import io
import struct
import unittest
import zipfile

import numpy as np

import stream_io


def npy_bytes(array, *, version=(1, 0), shape=None, descr=None, fortran=False,
              truncate=0, extra=b''):
    assert array.size <= 65536
    header = dict(descr=array.dtype.str if descr is None else descr,
                  fortran_order=fortran,
                  shape=array.shape if shape is None else shape)
    length_size = 2 if version == (1, 0) else 4
    text = repr(header).encode('utf-8' if version == (3, 0) else 'latin1')
    padding = (-(8 + length_size + len(text) + 1)) % 64
    text += b' ' * padding + b'\n'
    prefix = b'\x93NUMPY' + bytes(version) + len(text).to_bytes(length_size, 'little')
    data = array.tobytes(order='F' if fortran else 'C')
    if truncate:
        data = data[:-truncate]
    return prefix + text + data + extra


def zip_bytes(members, *, compression=zipfile.ZIP_DEFLATED):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=compression) as saved:
        for name, payload in members:
            saved.writestr(name, payload)
    archive.seek(0)
    return archive


def field(n=7):
    assert n * 3 <= 65536
    return (np.arange(n * 3).reshape(n, 3) + 1j *
            np.arange(n * 3, 2 * n * 3).reshape(n, 3)).astype(np.complex128)


def reader(array0, array1=None, *, n=None, chunk_rows=3, options0=None,
           options1=None, guard=lambda: None, deadline=None):
    if array1 is None:
        array1 = 2 * array0
    if n is None:
        n = int(array0.size // 3)
    return stream_io.PairedEReader.from_archives_for_testing(
        zip_bytes([(stream_io.E_MEMBER, npy_bytes(array0, **(options0 or {})))]),
        zip_bytes([(stream_io.E_MEMBER, npy_bytes(array1, **(options1 or {})))]),
        np=np, expected_cells=n, chunk_rows=chunk_rows,
        guard=guard, deadline=deadline)


class PairedEReaderTests(unittest.TestCase):
    def test_order_exact_last_chunk_native_vectors_and_read_only(self):
        expected = field(7)
        records = []
        for first, last, e0, e1 in reader(expected).iter_chunks():
            self.assertEqual(e0.shape, (last - first, 3))
            self.assertEqual(e0.dtype, np.dtype('complex128'))
            self.assertTrue(e0.flags.c_contiguous)
            self.assertFalse(e0.flags.writeable)
            records.append((first, last, e0.copy(), e1.copy()))
        self.assertEqual([(r[0], r[1]) for r in records], [(0, 3), (3, 6), (6, 7)])
        np.testing.assert_array_equal(np.concatenate([r[2] for r in records]), expected)
        np.testing.assert_array_equal(np.concatenate([r[3] for r in records]), 2 * expected)

    def test_c_order_prefix_flatten_and_supported_header_versions(self):
        expected = field(6)
        for version in ((1, 0), (2, 0), (3, 0)):
            with self.subTest(version=version):
                paired = reader(expected.reshape(2, 3, 3), expected, n=6,
                                options0={'version': version}, options1={'version': version})
                got = [e0.copy() for _, _, e0, _ in paired.iter_chunks()]
                np.testing.assert_array_equal(np.concatenate(got), expected)

    def test_reader_reuses_one_buffer_per_carrier(self):
        expected = field(7)
        chunks = reader(expected).iter_chunks()
        _, _, first0, first1 = next(chunks)
        pointer0 = first0.__array_interface__['data'][0]
        pointer1 = first1.__array_interface__['data'][0]
        _, _, second0, second1 = next(chunks)
        self.assertEqual(pointer0, second0.__array_interface__['data'][0])
        self.assertEqual(pointer1, second1.__array_interface__['data'][0])
        np.testing.assert_array_equal(second0, expected[3:6])
        list(chunks)

    def test_take_rows_scans_and_preserves_order_duplicates_and_reuse(self):
        expected = field(7)
        paired = reader(expected)
        indices = [6, 0, 6, 3]
        e0, e1 = paired.take_rows(indices)
        np.testing.assert_array_equal(e0, expected[indices])
        np.testing.assert_array_equal(e1, 2 * expected[indices])
        again0, again1 = paired.take_rows([2])
        np.testing.assert_array_equal(again0, expected[[2]])
        np.testing.assert_array_equal(again1, 2 * expected[[2]])

    def test_selected_count_indices_and_chunk_limits(self):
        paired = reader(field(40))
        for indices in ([], [-1], [40], [True], [1.5], range(33)):
            with self.subTest(indices=str(indices)):
                with self.assertRaises(ValueError):
                    paired.take_rows(indices)
        for count in (0, 129):
            with self.assertRaises(ValueError):
                reader(field(3), chunk_rows=count)

    def test_rejects_non_complex128_object_fortran_and_wrong_counts(self):
        expected = field(6)
        invalid = [
            (expected.astype(np.complex64), {}),
            (expected.real.astype(np.float64), {}),
            (expected, {'descr': '|O'}),
            (expected, {'descr': np.dtype('complex128').newbyteorder('S').str}),
            (expected, {'fortran': True}),
            (expected, {'shape': (7, 3)}),
            (expected, {'shape': (9, 2)}),
            (expected, {'shape': (0, 3)}),
        ]
        for array, options in invalid:
            with self.subTest(dtype=array.dtype, options=options):
                with self.assertRaises(ValueError):
                    list(reader(array, expected, n=6, options0=options).iter_chunks())

    def test_rejects_missing_member_and_duplicate_member(self):
        expected = field(3)
        good = zip_bytes([(stream_io.E_MEMBER, npy_bytes(expected))])
        missing = zip_bytes([('phi_peak_V.npy', npy_bytes(expected))])
        paired = stream_io.PairedEReader.from_archives_for_testing(
            missing, good, np=np, expected_cells=3, guard=lambda: None)
        with self.assertRaises(ValueError):
            list(paired.iter_chunks())
        # Build two central entries by renaming equal-length toy entries in bytes,
        # avoiding ZipFile's duplicate-name warning (warnings may be fatal in MFG).
        other = 'F_peak_V_m.npy'
        duplicate = zip_bytes([(stream_io.E_MEMBER, npy_bytes(expected)),
                               (other, npy_bytes(expected))])
        duplicate = io.BytesIO(duplicate.getvalue().replace(other.encode(), stream_io.E_MEMBER.encode()))
        paired = stream_io.PairedEReader.from_archives_for_testing(
            duplicate, good, np=np, expected_cells=3, guard=lambda: None)
        with self.assertRaises(ValueError):
            list(paired.iter_chunks())

    def test_rejects_truncated_and_oversized_uncompressed_data(self):
        expected = field(7)
        for options in ({'truncate': 1}, {'truncate': 48}, {'extra': b'x'},
                        {'extra': b'\0' * 48}):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    list(reader(expected, options0=options).iter_chunks())

    def test_crc_is_consumed_including_tail_after_selected_rows(self):
        # >4096 payload bytes places the corrupt tail beyond ZipExtFile's first
        # internal read, so returning early after selected row zero would fail.
        expected = field(300)
        saved = zip_bytes([(stream_io.E_MEMBER, npy_bytes(expected))],
                          compression=zipfile.ZIP_STORED)
        raw = bytearray(saved.getvalue())
        # Local header is 30 bytes plus filename and extra fields; alter last data
        # byte without updating CRC.  The NPY data shape/header remain valid.
        name_length, extra_length = struct.unpack('<HH', raw[26:30])
        data_start = 30 + name_length + extra_length
        payload_length = len(npy_bytes(expected))
        raw[data_start + payload_length - 1] ^= 1
        bad = io.BytesIO(raw)
        good = zip_bytes([(stream_io.E_MEMBER, npy_bytes(expected))])
        paired = stream_io.PairedEReader.from_archives_for_testing(
            bad, good, np=np, expected_cells=300, chunk_rows=1, guard=lambda: None)
        with self.assertRaises(zipfile.BadZipFile):
            paired.take_rows([0])

    def test_unsupported_npy_version_and_trailing_archive_bytes(self):
        expected = field(3)
        with self.assertRaises(ValueError):
            list(reader(expected, options0={'version': (4, 0)}).iter_chunks())
        bad = zip_bytes([(stream_io.E_MEMBER, npy_bytes(expected))])
        bad = io.BytesIO(bad.getvalue() + b'extra')
        good = zip_bytes([(stream_io.E_MEMBER, npy_bytes(expected))])
        paired = stream_io.PairedEReader.from_archives_for_testing(
            bad, good, np=np, expected_cells=3, guard=lambda: None)
        with self.assertRaises(ValueError):
            list(paired.iter_chunks())

    def test_guard_and_expired_deadline_precede_open_or_chunks(self):
        calls = []
        def reject():
            calls.append(True)
            raise RuntimeError('guard rejected')
        paired = reader(field(3), guard=reject)
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(RuntimeError, 'guard rejected'):
            next(paired.iter_chunks())
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, 'deadline'):
            next(reader(field(3), deadline=-1).iter_chunks())

    def test_fixture_constructor_never_accepts_filesystem_path(self):
        with self.assertRaises(ValueError):
            stream_io.PairedEReader.from_archives_for_testing(
                '/unregistered.npz', io.BytesIO(), np=np, expected_cells=3,
                guard=lambda: None)


class NarrowMemberTests(unittest.TestCase):
    def test_electrical_members_bounded_and_allowlisted(self):
        currents = np.array([1 + 2j, 3 + 4j], dtype=np.complex128)
        archive = zip_bytes([('source_current_peak_A.npy', npy_bytes(currents)),
                             ('not_allowed.npy', npy_bytes(currents))])
        with stream_io.NativeArchive.from_archive_for_testing(
                np, archive, 'raw', expected_cells=3, guard=lambda: None) as saved:
            np.testing.assert_array_equal(saved.read_member('source_current_peak_A'), currents)
            with self.assertRaises(ValueError):
                saved.read_member('source_current_peak_A', max_bytes=16)
            with self.assertRaises(ValueError):
                saved.read_member('not_allowed')
            with self.assertRaises(ValueError):
                saved.read_member('E_peak_V_m')

    def test_scalar_row_stream_reopens_on_backward_request(self):
        values = np.arange(7, dtype=np.float64)
        archive = zip_bytes([('AM_max2074.npy', npy_bytes(values))])
        with stream_io.NativeArchive.from_archive_for_testing(
                np, archive, 'scalars', expected_cells=7, guard=lambda: None) as saved:
            np.testing.assert_array_equal(saved.read_rows('AM_max2074', 2, 5), values[2:5])
            np.testing.assert_array_equal(saved.read_rows('AM_max2074', 5, 7), values[5:7])
            np.testing.assert_array_equal(saved.read_rows('AM_max2074', 0, 2), values[:2])
            with self.assertRaises(ValueError):
                saved.read_member('AM_max2074')


if __name__ == '__main__':
    unittest.main()
