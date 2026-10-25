"""Bounded, authenticated-input NPZ member streams; importing does no I/O.

The controller authenticates every production descriptor (including source hashes,
canonical paths, publication proofs and stat identity) before the source-bound MFG
gate.  This module consumes that gate's descriptors; it does not authenticate new
paths or hash/open unregistered inputs.  Only an explicit member allowlist is read.
No np.load, extraction, temporary file, full E array or full Q array is used.

PairedEReader(...).iter_chunks is a reusable carrier_factory.  Its half-open
(first,last,E0,E1) records have <=128 rows and native complex128 columns XYZ in
the saved order.  take_rows preserves requested index order and scans to EOF/CRC.
Consumers must exhaust iter_chunks; abandoning a generator closes its archives
but does not certify the unread tail.  BytesIO-only fixture constructors exercise
the same ZIP/NPY decoder without granting a filesystem-opening test bypass.
"""
from __future__ import annotations

import ast
import io
import itertools
import math
import numbers
import struct
import time
import zipfile
from pathlib import Path

N_CELLS = 793848
MAX_CHUNK_ROWS = 128
MAX_SELECTED_ROWS = 32
MAX_HEADER_BYTES = 65536
MAX_ARCHIVE_BYTES = 512 * 1024**2
MAX_DIRECTORY_BYTES = 256 * 1024
MAX_MEMBERS = 128
MAX_CONTACT_ROWS = 32768
SMALL_MEMBER_BYTES = 2 * 1024**2
E_MEMBER = 'E_peak_V_m.npy'
REGIONS = ('total', 'target', 'surface_0_5', 'subsurface_5_10',
           'remaining', 'off_target')
SCALARS = ('carrier_RMS', 'carrier0_RMS', 'carrier1_RMS', 'AM_x',
           'AM_y', 'AM_z', 'AM_max2074', 'Jtotal_vector_RMS')
CONTACT_COMPLEX = ('contact_normal_J_peak_A_m2', 'contact_drop_peak_V')
CONTACT_INTEGER = ('contact_pad', 'contact_xy_index')


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _check(guard, deadline):
    guard()
    _require(deadline is None or time.monotonic() < deadline,
             'Finite NPZ stream deadline')


def _positive_int(value, maximum, label):
    _require(type(value) is int and 0 < value <= maximum, label)
    return value


def _descriptor(value, expected_cells, require_e=False):
    """Validate the shape of an already authenticated controller descriptor."""
    _require(isinstance(value, dict), 'Controller archive descriptor required')
    result = dict(value)
    path = result.get('path')
    _require(isinstance(path, str) and Path(path).is_absolute() and
             str(Path(path)) == path and '..' not in Path(path).parts,
             'Controller must supply a canonical absolute registered path')
    digest = result.get('SHA256')
    _require(isinstance(digest, str) and len(digest) == 64 and
             all(c in '0123456789abcdef' for c in digest),
             'Controller archive SHA256 required')
    _positive_int(result.get('bytes'), MAX_ARCHIVE_BYTES,
                  'Bounded authenticated archive byte count required')
    _require(result.get('readback_passed') is True and
             isinstance(result.get('publication_commit'), str) and
             bool(result['publication_commit']) and
             isinstance(result.get('publication_target'), str) and
             bool(result['publication_target']),
             'Exact original publication/readback descriptor required')
    if require_e:
        _require(result.get('member') == E_MEMBER,
                 'Only the registered E_peak_V_m.npy field may supply carriers')
        shape = result.get('shape')
        _require(isinstance(shape, (list, tuple)) and len(shape) >= 2 and
                 all(type(n) is int and n > 0 for n in shape) and
                 shape[-1] == 3 and math.prod(shape[:-1]) == expected_cells,
                 'Registered E shape must flatten exactly to N by XYZ')
        _require(result.get('dtype') in ('<c16', '=c16') and
                 result.get('fortran_order') is False,
                 'Registered native complex128 C-order E metadata required')
        result['shape'] = tuple(shape)
    return result


def _directory_bound(handle, expected_bytes, guard, deadline):
    """Bound ZipFile's central-directory allocation before constructing it.

    NPZ files below this module's 512 MiB cap need no ZIP64 end record.  NumPy's
    ZIP64 *local* headers are accepted; ZIP64/multidisk end records are rejected.
    """
    _check(guard, deadline)
    handle.seek(0, 2)
    _require(handle.tell() == expected_bytes, 'Archive byte count changed after gate')
    tail_bytes = min(expected_bytes, 65557)
    handle.seek(expected_bytes - tail_bytes)
    _check(guard, deadline)
    tail = handle.read(tail_bytes)
    _require(len(tail) == tail_bytes, 'Short archive end record')
    end = tail.rfind(b'PK\x05\x06')
    _require(end >= 0 and end + 22 <= len(tail), 'Missing bounded ZIP end record')
    fields = struct.unpack('<4s4H2LH', tail[end:end + 22])
    _, disk, directory_disk, disk_count, total, directory_bytes, offset, comment = fields
    _require(end + 22 + comment == len(tail), 'Trailing ZIP bytes or malformed comment')
    _require(disk == directory_disk == 0 and disk_count == total and
             0 < total <= MAX_MEMBERS and
             0 < directory_bytes <= MAX_DIRECTORY_BYTES,
             'Bounded single-disk ZIP directory required')
    end_offset = expected_bytes - tail_bytes + end
    _require(offset + directory_bytes == end_offset,
             'ZIP64, prepended or inconsistent ZIP directory rejected')
    handle.seek(0)


class _Rows:
    def __init__(self, owner, name):
        self.owner = owner
        self.name = name
        self.first = 0
        self.finished = False
        self.buffer = None
        _check(owner.guard, owner.deadline)
        matches = [info for info in owner._archive.infolist() if info.filename == name + '.npy']
        _require(len(matches) == 1, 'Exactly one allowlisted NPY member required: ' + name)
        self.info = matches[0]
        _require(not self.info.is_dir() and not self.info.flag_bits & 1 and
                 self.info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                 'Unencrypted stored/deflated NPY member required')
        _check(owner.guard, owner.deadline)
        self.stream = owner._archive.open(self.info, 'r')
        try:
            self._header()
        except BaseException:
            self.stream.close()
            raise

    def _read_exact(self, count):
        limit = max(MAX_HEADER_BYTES, getattr(self, 'row_bytes', 0) * MAX_CHUNK_ROWS)
        _require(type(count) is int and 0 <= count <= limit,
                 'Internal bounded stream read')
        _check(self.owner.guard, self.owner.deadline)
        result = self.stream.read(count)
        _require(len(result) == count, 'Short NPY member payload')
        return result

    def _header(self):
        start = self._read_exact(8)
        _require(start[:6] == b'\x93NUMPY', 'NPY magic required')
        version = tuple(start[6:8])
        _require(version in ((1, 0), (2, 0), (3, 0)), 'Unsupported NPY header version')
        length_bytes = 2 if version == (1, 0) else 4
        header_length = int.from_bytes(self._read_exact(length_bytes), 'little')
        _positive_int(header_length, MAX_HEADER_BYTES, 'Bounded NPY header required')
        raw_header = self._read_exact(header_length)
        _require(raw_header.endswith(b'\n'), 'NPY header newline required')
        text = raw_header.decode('utf-8' if version == (3, 0) else 'latin1')
        expression = ast.parse(text.strip(), mode='eval')
        _require(isinstance(expression.body, ast.Dict), 'NPY dictionary header required')
        keys = [ast.literal_eval(key) for key in expression.body.keys]
        _require(len(keys) == 3 and set(keys) == {'descr', 'fortran_order', 'shape'},
                 'Exact NPY header keys required')
        header = ast.literal_eval(expression)
        _require(isinstance(header['descr'], str) and header['fortran_order'] is False and
                 isinstance(header['shape'], tuple) and len(header['shape']) > 0 and
                 all(type(n) is int and n > 0 for n in header['shape']),
                 'Non-object C-order positive-shape NPY required')
        self.dtype = self.owner.np.dtype(header['descr'])
        _require(not self.dtype.hasobject and self.dtype.fields is None and
                 self.dtype.subdtype is None and self.dtype.isnative,
                 'Plain native non-object NPY dtype required')
        self.shape = header['shape']
        self.rows, self.tail = self.owner._validate_header(self.name, self.shape, self.dtype)
        self.row_bytes = math.prod(self.tail) * self.dtype.itemsize
        self.data_bytes = self.rows * self.row_bytes
        header_bytes = 8 + length_bytes + header_length
        _require(self.info.file_size == header_bytes + self.data_bytes,
                 'NPY member has short/extra uncompressed data')

    def read(self, count):
        _positive_int(count, MAX_CHUNK_ROWS, 'At most 128 rows per stream read')
        _require(not self.finished and self.first + count <= self.rows,
                 'Requested rows exceed member')
        raw = self._read_exact(count * self.row_bytes)
        if self.buffer is None:
            self.buffer = bytearray(MAX_CHUNK_ROWS * self.row_bytes)
        self.buffer[:len(raw)] = raw
        array = self.owner.np.frombuffer(self.buffer, dtype=self.dtype,
                                       count=count * math.prod(self.tail)).reshape((count,) + self.tail)
        array.setflags(write=False)
        if self.dtype.kind in 'fc':
            _require(bool(self.owner.np.isfinite(array).all()), 'Finite saved member values required')
        self.first += count
        if self.first == self.rows:
            _check(self.owner.guard, self.owner.deadline)
            _require(self.stream.read(1) == b'', 'Extra NPY member data')
            self.finished = True
            self.stream.close()  # EOF above consumes ZIP CRC validation.
        return array

    def close(self):
        self.stream.close()


class NativeArchive:
    """Narrow allowlisted helper for registered grid/scalar/electrical members.

    read_rows keeps a forward stream per requested member, reopening on backward
    requests.  Full E/grid/scalar reads are forbidden.  read_member may allocate
    <=2 MiB small members or one <=N*8-byte grid weight, never a hidden matrix.
    All floating/complex values read are checked finite.  Native integer members
    are accepted only for producer-declared integer index arrays.
    """
    def __init__(self, np, descriptor, archive_kind='raw', *, guard, deadline=None,
                 expected_cells=N_CELLS):
        _require(callable(guard), 'Runtime guard required')
        _require(type(expected_cells) is int and expected_cells == N_CELLS,
                 'Production archives must have exactly 793848 cells')
        _require(archive_kind in ('raw', 'grid', 'scalars'), 'Explicit archive kind required')
        self.np, self.guard, self.deadline = np, guard, deadline
        self.kind, self.expected_cells = archive_kind, expected_cells
        self.descriptor = _descriptor(descriptor, expected_cells)
        self._fixture = None
        self._archive = self._handle = None
        self._streams = {}
        self._contact_count = None

    @classmethod
    def from_archive_for_testing(cls, np, archive, archive_kind='raw', *, guard,
                                 deadline=None, expected_cells):
        _require(type(archive) is io.BytesIO, 'Manufactured archive must be BytesIO')
        _require(archive.getbuffer().nbytes <= 2 * 1024**2, 'Bounded manufactured ZIP')
        obj = cls.__new__(cls)
        _require(callable(guard) and archive_kind in ('raw', 'grid', 'scalars'),
                 'Manufactured guard/archive kind required')
        _positive_int(expected_cells, 65536 // 3, 'Tiny manufactured cell count required')
        obj.np, obj.guard, obj.deadline = np, guard, deadline
        obj.kind, obj.expected_cells = archive_kind, expected_cells
        obj.descriptor = None
        obj._fixture = archive
        obj._archive = obj._handle = None
        obj._streams = {}
        obj._contact_count = None
        return obj

    def _open(self):
        if self._archive is not None:
            return
        _check(self.guard, self.deadline)
        self._handle = self._fixture if self._fixture is not None else Path(self.descriptor['path']).open('rb')
        expected_bytes = (self._fixture.getbuffer().nbytes if self._fixture is not None
                          else self.descriptor['bytes'])
        try:
            _directory_bound(self._handle, expected_bytes, self.guard, self.deadline)
            _check(self.guard, self.deadline)
            self._archive = zipfile.ZipFile(self._handle, 'r')
            _require(len(self._archive.infolist()) <= MAX_MEMBERS, 'Too many ZIP members')
        except BaseException:
            self.close()
            raise

    def _validate_header(self, name, shape, dtype):
        n = self.expected_cells
        float64 = dtype == self.np.dtype('float64')
        complex128 = dtype == self.np.dtype('complex128')
        integer = dtype.kind in 'iu' and dtype.itemsize in (1, 2, 4, 8)
        if self.kind == 'raw':
            if name == 'E_peak_V_m':
                _require(complex128 and len(shape) >= 2 and shape[-1] == 3 and
                         math.prod(shape[:-1]) == n, 'Exact native complex128 N by XYZ field required')
                return n, (3,)
            if name in ('source_current_peak_A', 'metal_peak_V'):
                ok = complex128 and shape == (2,)
            elif name == 'layer_complex_power_W':
                ok = complex128 and shape == (4,)
            else:
                _require(name in CONTACT_COMPLEX + CONTACT_INTEGER + ('contact_area_m2',),
                         'Raw member is outside explicit electrical allowlist')
                ok = (len(shape) == 1 and 0 < shape[0] <= MAX_CONTACT_ROWS and
                      ((name in CONTACT_COMPLEX and complex128) or
                       (name in CONTACT_INTEGER and integer) or
                       (name == 'contact_area_m2' and float64)))
                if ok:
                    _require(self._contact_count in (None, shape[0]), 'Contact member row counts disagree')
                    self._contact_count = shape[0]
            _require(ok, 'Exact electrical member shape/dtype required: ' + name)
        elif self.kind == 'grid':
            if name == 'grid':
                ok = float64 and shape == (n, 5)
            elif name == 'ij':
                ok = integer and shape == (8184, 2)
            elif name == 'z_faces_m':
                ok = float64 and shape == (98,)
            else:
                ok = name in tuple(r + '_volume_weight_m3' for r in REGIONS) and float64 and shape == (n,)
            _require(ok, 'Exact allowlisted grid member shape/dtype required: ' + name)
        else:
            ok = (name in SCALARS and float64 or
                  name == 'AM_direction_index' and dtype == self.np.dtype('int32'))
            _require(ok and shape == (n,), 'Exact allowlisted scalar member shape/dtype required')
        return shape[0], shape[1:]

    def _member(self, name):
        # Reject names before touching an archive, including path-like names.
        raw = ('E_peak_V_m', 'source_current_peak_A', 'metal_peak_V',
               'layer_complex_power_W', 'contact_area_m2') + CONTACT_COMPLEX + CONTACT_INTEGER
        grid = ('grid', 'ij', 'z_faces_m') + tuple(r + '_volume_weight_m3' for r in REGIONS)
        allowed = raw if self.kind == 'raw' else grid if self.kind == 'grid' else SCALARS + ('AM_direction_index',)
        _require(isinstance(name, str) and name in allowed, 'Member outside explicit archive allowlist')
        self._open()
        return _Rows(self, name)

    def iter_rows(self, name, chunk_rows=MAX_CHUNK_ROWS):
        _positive_int(chunk_rows, MAX_CHUNK_ROWS, 'At most 128 rows per chunk')
        rows = self._member(name)
        try:
            while rows.first < rows.rows:
                first = rows.first
                array = rows.read(min(chunk_rows, rows.rows - first))
                yield first, rows.first, array
        finally:
            rows.close()

    def read_rows(self, name, first, last):
        _require(type(first) is int and type(last) is int and 0 <= first < last and
                 last - first <= MAX_CHUNK_ROWS, 'Bounded half-open row interval required')
        rows = self._streams.get(name)
        if rows is None or rows.first > first or rows.finished:
            if rows is not None:
                rows.close()
            rows = self._member(name)
            self._streams[name] = rows
        _require(last <= rows.rows, 'Row interval outside member')
        while rows.first < first:
            rows.read(min(MAX_CHUNK_ROWS, first - rows.first))
        return rows.read(last - first)

    def read_member(self, name, max_bytes=SMALL_MEMBER_BYTES):
        _positive_int(max_bytes, max(SMALL_MEMBER_BYTES, self.expected_cells * 8) if self.kind == 'grid'
                      else SMALL_MEMBER_BYTES, 'Explicit bounded member allocation required')
        _require(name != 'E_peak_V_m' and name != 'grid' and self.kind != 'scalars',
                 'Full E/grid/scalar allocation forbidden; use row streams')
        rows = self._member(name)
        try:
            is_weight = self.kind == 'grid' and name.endswith('_volume_weight_m3')
            _require(rows.data_bytes <= max_bytes and (is_weight or rows.data_bytes <= SMALL_MEMBER_BYTES),
                     'Member exceeds explicit allocation bound')
            result = self.np.empty(rows.shape, dtype=rows.dtype)
            while rows.first < rows.rows:
                first = rows.first
                value = rows.read(min(MAX_CHUNK_ROWS, rows.rows - first))
                result[first:rows.first] = value
            return result
        finally:
            rows.close()

    def close(self):
        for rows in self._streams.values():
            rows.close()
        self._streams.clear()
        if self._archive is not None:
            self._archive.close()
            self._archive = None
        if self._handle is not None and self._fixture is None:
            self._handle.close()
        self._handle = None

    def __enter__(self):
        self._open()
        return self

    def __exit__(self, *unused):
        self.close()


class PairedEReader:
    def __init__(self, descriptor0, descriptor1, *, guard, deadline=None,
                 expected_cells=N_CELLS, chunk_rows=MAX_CHUNK_ROWS, np=None):
        _require(callable(guard), 'Runtime guard required')
        _require(type(expected_cells) is int and expected_cells == N_CELLS,
                 'Production paired fields must have exactly 793848 cells')
        _positive_int(chunk_rows, MAX_CHUNK_ROWS, 'At most 128 carrier rows per chunk')
        self.descriptors = tuple(_descriptor(d, expected_cells, True) for d in (descriptor0, descriptor1))
        self.guard, self.deadline = guard, deadline
        self.expected_cells, self.chunk_rows = expected_cells, chunk_rows
        self.np, self._fixtures = np, None

    @classmethod
    def from_archives_for_testing(cls, archive0, archive1, *, guard,
                                  deadline=None, expected_cells, chunk_rows=MAX_CHUNK_ROWS, np=None):
        _require(type(archive0) is io.BytesIO and type(archive1) is io.BytesIO,
                 'Manufactured paired archives must be BytesIO')
        _positive_int(expected_cells, 65536 // 3, 'Tiny manufactured paired field required')
        _positive_int(chunk_rows, MAX_CHUNK_ROWS, 'At most 128 carrier rows per chunk')
        _require(callable(guard), 'Manufactured runtime guard required')
        obj = cls.__new__(cls)
        obj.descriptors, obj._fixtures = None, (archive0, archive1)
        obj.guard, obj.deadline = guard, deadline
        obj.expected_cells, obj.chunk_rows, obj.np = expected_cells, chunk_rows, np
        return obj

    def _archives(self):
        if self.np is None:
            import numpy as np
            self.np = np
        if self._fixtures is not None:
            return tuple(NativeArchive.from_archive_for_testing(
                self.np, archive, 'raw', guard=self.guard, deadline=self.deadline,
                expected_cells=self.expected_cells) for archive in self._fixtures)
        return tuple(NativeArchive(self.np, descriptor, 'raw', guard=self.guard,
                                  deadline=self.deadline, expected_cells=self.expected_cells)
                     for descriptor in self.descriptors)

    def iter_chunks(self):
        """Yield read-only views, valid until advancing to the next chunk."""
        archives = self._archives()
        rows = []
        try:
            for archive in archives:
                rows.append(archive._member('E_peak_V_m'))
            if self.descriptors is not None:
                for descriptor, stream in zip(self.descriptors, rows):
                    _require(tuple(descriptor['shape']) == stream.shape and
                             self.np.dtype(descriptor['dtype']) == stream.dtype,
                             'Actual E header differs from authenticated descriptor')
            first = 0
            while first < self.expected_cells:
                _check(self.guard, self.deadline)
                count = min(self.chunk_rows, self.expected_cells - first)
                e0 = rows[0].read(count)
                e1 = rows[1].read(count)
                last = first + count
                yield first, last, e0, e1
                first = last
                # Do not retain the previous pair while constructing the next.
                del e0, e1
            _require(all(stream.finished for stream in rows), 'Both E streams must reach CRC/EOF')
        finally:
            for stream in rows:
                stream.close()
            for archive in archives:
                archive.close()

    def take_rows(self, indices, max_rows=MAX_SELECTED_ROWS):
        _positive_int(max_rows, MAX_SELECTED_ROWS, 'At most 32 representative vectors')
        selected = tuple(itertools.islice(indices, max_rows + 1))
        _require(0 < len(selected) <= max_rows and
                 all(isinstance(i, numbers.Integral) and not isinstance(i, bool) and
                     0 <= i < self.expected_cells for i in selected),
                 'Small in-range integer representative indices required')
        selected = tuple(int(i) for i in selected)
        if self.np is None:
            import numpy as np
            self.np = np
        result0 = self.np.empty((len(selected), 3), dtype=self.np.complex128)
        result1 = self.np.empty_like(result0)
        by_row = {}
        for slot, index in enumerate(selected):
            by_row.setdefault(index, []).append(slot)
        for first, last, e0, e1 in self.iter_chunks():
            for index, slots in by_row.items():
                if first <= index < last:
                    for slot in slots:
                        result0[slot] = e0[index - first]
                        result1[slot] = e1[index - first]
        return result0, result1


def paired_e_chunks(descriptor0, descriptor1, **options):
    """One-pass convenience iterator; use reader.iter_chunks for a factory."""
    return PairedEReader(descriptor0, descriptor1, **options).iter_chunks()
