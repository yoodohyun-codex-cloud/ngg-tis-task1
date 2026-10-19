"""Synthetic storage-integrity fixtures only; no research import or solver."""
import gzip
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location('task1_archive', Path(__file__).resolve().parents[1]/'tools/task1_native_archive.py')
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)


class ArchiveFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.patcher = patch.object(archive, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.run = self.root/'data-native/cloud-fixture'
        basis = self.run/'bases/fixture'
        basis.mkdir(parents=True)
        for name in ('controller.json', 'summary.json'):
            (self.run/name).write_text('{"status":"complete"}')
        (self.run/'preregistration.json').write_text(json.dumps({'source_commit': 'a'*40}))
        (basis/'BASIS_COMPLETE').write_bytes(b'')
        meta = dict(cells=1, channels=1, source_peak_V=.5, source_resistance_ohm=50,
                    phasor_convention='peak,+jomega_t', frequencies_Hz=[3000, 3030, 9000, 9090],
                    radius_mm=25., total_depth_mm=25.1, tissue_boundaries_mm=[0,.1,5.1,10.1,25.1])
        (basis/'mesh-metadata.json').write_text(json.dumps(meta))
        with gzip.open(basis/'grid.csv.gz', 'wt') as stream:
            stream.write('x_mm,y_mm,z_mm,layer,volume_m3\n0,0,1,1,1e-9\n')
        for freq in meta['frequencies_Hz']:
            (basis/f'contacts-{freq}.csv').write_text('pad,area_m2\n0,1e-4\n1,1e-4\n')
            for label, count in (('field', 6), ('potential', 2)):
                with gzip.open(basis/f'{label}-{freq}.bin.gz', 'wb') as stream:
                    stream.write(struct.pack('<'+'d'*count, *([0.]*count)))
            for label, count in (('density',4), ('source',2), ('loss',12)):
                (basis/f'{label}-{freq}.bin').write_bytes(struct.pack('<'+'d'*count, *([0.]*count)))
        self.output = self.root/'new-native.tar'


class ArchiveTests(ArchiveFixture, unittest.TestCase):
    def test_byte_roundtrip_and_native_decode_are_separate_verdicts(self):
        packed = archive.pack(self.run, self.output)
        self.assertEqual(packed['byte_hash_verification'], 'passed')
        self.assertEqual(packed['native_array_decode_verification'], 'not_run')
        restored = archive.restore(self.output, packed['archive_sha256'], self.root/'clean')
        self.assertEqual(restored['native_array_decode_verification']['status'], 'passed')
        self.assertEqual(len(restored['native_array_decode_verification']['arrays']), 20)
        self.assertFalse(restored['independent_persistent_backup_verified'])
        self.assertFalse(restored['scientific_numerical_reproduction'])
        self.assertFalse(restored['original_environment_retirement_allowed'])

    def test_changed_archive_rejected_by_independently_pinned_hash(self):
        packed = archive.pack(self.run, self.output)
        with self.output.open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'SHA256 differs'):
            archive.verify(self.output, packed['archive_sha256'])

    def test_partial_runs_and_source_symlinks_rejected(self):
        (self.run/'controller.json').write_text('{"status":"running"}')
        with self.assertRaisesRegex(ValueError, 'Only completed'):
            archive.pack(self.run, self.output)
        self.assertFalse(self.output.exists())
        (self.run/'controller.json').write_text('{"status":"complete"}')
        (self.run/'alias').symlink_to(self.run/'summary.json')
        with self.assertRaisesRegex(ValueError, 'Symlink or special'):
            archive.pack(self.run, self.output)

    def test_existing_archive_and_restore_destination_never_overwritten(self):
        packed = archive.pack(self.run, self.output)
        before = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            archive.pack(self.run, self.output)
        self.assertEqual(before, self.output.read_bytes())
        clean = self.root/'clean'
        clean.mkdir()
        (clean/'failure.bin').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'canonical and absent'):
            archive.restore(self.output, packed['archive_sha256'], clean)
        self.assertEqual((clean/'failure.bin').read_bytes(), b'keep')

    def test_valid_hash_does_not_hide_invalid_native_shape(self):
        (self.run/'bases/fixture/source-3000.bin').write_bytes(b'')
        packed = archive.pack(self.run, self.output)
        with self.assertRaisesRegex(ValueError, 'Decoded array length'):
            archive.restore(self.output, packed['archive_sha256'], self.root/'clean')
        self.assertTrue((self.root/'clean/cloud-fixture/bases/fixture/source-3000.bin').is_file())
        self.assertFalse((self.root/'clean/CLEAN_RESTORE_RECEIPT.json').exists())

    def test_nonfinite_native_is_rejected_after_byte_restore(self):
        (self.run/'bases/fixture/source-3000.bin').write_bytes(struct.pack('<dd', float('nan'), 0.))
        packed = archive.pack(self.run, self.output)
        with self.assertRaisesRegex(ValueError, 'Nonfinite native'):
            archive.restore(self.output, packed['archive_sha256'], self.root/'clean')

    def test_unsafe_members_and_links_are_rejected_before_extraction(self):
        for name, kind in [('../escape',tarfile.REGTYPE), ('/absolute',tarfile.REGTYPE),
                           ('cloud-x/link',tarfile.SYMTYPE), ('cloud-x/hard',tarfile.LNKTYPE)]:
            with self.subTest(name=name):
                fileobj = io.BytesIO()
                with tarfile.open(fileobj=fileobj, mode='w') as bundle:
                    info = tarfile.TarInfo(name)
                    info.type, info.linkname = kind, '../outside'
                    bundle.addfile(info, io.BytesIO())
                fileobj.seek(0)
                with tarfile.open(fileobj=fileobj, mode='r:') as bundle:
                    with self.assertRaises(ValueError):
                        archive.inspect_members(bundle)

    def test_duplicate_members_rejected(self):
        fileobj = io.BytesIO()
        with tarfile.open(fileobj=fileobj, mode='w') as bundle:
            for _ in range(2):
                bundle.addfile(tarfile.TarInfo('same'), io.BytesIO())
        fileobj.seek(0)
        with tarfile.open(fileobj=fileobj, mode='r:') as bundle:
            with self.assertRaisesRegex(ValueError, 'Duplicate archive'):
                archive.inspect_members(bundle)


class GroupedArchiveTests(ArchiveFixture, unittest.TestCase):
    """Group12/16 storage fixtures keep exactly two electrical source dimensions."""

    def make_grouped(self, count):
        basis = self.run/'bases/fixture'
        nodes = [0]*(count//4) + [1]*(count//4) + [-1]*(count//2)
        areas = [.0009/count]*count
        config = dict(channels='2', n_outputs='2', n_pads=str(count),
                      n_return_nodes='1', return_topology='common_GND')
        for pad in range(count):
            config[f'pad.node.{pad}'] = str(nodes[pad])
            config[f'pad.{pad}.represented_area_m2'] = format(areas[pad], '.17g')
        (self.run/'configs').mkdir()
        config_path = self.run/'configs/fixture.properties'
        config_path.write_text(''.join(key+'='+value+'\n' for key, value in config.items()))
        case = dict(id='fixture', exporter_class='GroupedPadBasis', n_pads=count,
                    n_outputs=2, pad_node_ids=nodes, expected_pad_areas_m2=areas,
                    config_sha256=archive.digest(config_path))
        (self.run/'preregistration.json').write_text(json.dumps({'source_commit':'a'*40, 'cases':[case]}))
        meta = archive.read(basis/'mesh-metadata.json')
        meta.update(channels=2, n_outputs=2, n_pads=count, pad_node_ids=nodes,
                    exporter_kind='grouped_native', exporter_class='GroupedPadBasis',
                    numerical_base_class='SelectivityShapeBasis',
                    frozen_four_pad_postprocessor_compatible=False,
                    n_return_nodes=1, return_topology='common_GND', config_sha256=case['config_sha256'])
        (basis/'mesh-metadata.json').write_text(json.dumps(meta))
        for freq in meta['frequencies_Hz']:
            (basis/f'contacts-{freq}.csv').write_text('pad,x_mm,y_mm,area_m2\n'+''.join(
                f'{pad},{pad*.1},0,{areas[pad]:.17g}\n' for pad in range(count)))
            for label, size in (('field',12), ('potential',4)):
                with gzip.open(basis/f'{label}-{freq}.bin.gz', 'wb') as stream:
                    stream.write(struct.pack('<'+'d'*size, *([0.]*size)))
            for label, size in (('density',4*count), ('source',8), ('loss',48)):
                (basis/f'{label}-{freq}.bin').write_bytes(struct.pack('<'+'d'*size, *([0.]*size)))
        return basis

    def test_group12_retains_two_output_source_and_field_dimensions(self):
        self.make_grouped(12)
        packed = archive.pack(self.run, self.output)
        result = archive.restore(self.output, packed['archive_sha256'], self.root/'clean')
        decode = result['native_array_decode_verification']
        self.assertEqual(decode['bases'][0]['n_pads'], 12)
        self.assertEqual(decode['bases'][0]['n_outputs'], 2)
        self.assertEqual(decode['bases'][0]['source_matrix_shape'], [2,2])
        source = next(row for row in decode['arrays'] if row['path'].endswith('/source-3000.bin'))
        density = next(row for row in decode['arrays'] if row['path'].endswith('/density-3000.bin'))
        self.assertEqual(source['decoded_bytes'], 2*2*16)
        self.assertEqual(density['decoded_bytes'], 2*12*16)

    def test_group16_retains_two_output_loss_dimensions(self):
        self.make_grouped(16)
        decode = archive.decode_native(self.run)
        self.assertEqual(decode['bases'][0]['n_pads'], 16)
        self.assertEqual(decode['bases'][0]['n_outputs'], 2)
        self.assertEqual(decode['bases'][0]['loss_matrix_shape'], [6,2,2])
        loss = next(row for row in decode['arrays'] if row['path'].endswith('/loss-3000.bin'))
        self.assertEqual(loss['decoded_bytes'], 6*2*2*16)

    def test_grouped_missing_mapping_and_extra_output_rejected(self):
        basis = self.make_grouped(16)
        meta = archive.read(basis/'mesh-metadata.json')
        original = dict(meta)
        del meta['pad_node_ids']
        (basis/'mesh-metadata.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'Explicit grouped.*mapping'):
            archive.decode_native(self.run)
        meta = dict(original, n_outputs=3)
        (basis/'mesh-metadata.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'exactly two independent outputs'):
            archive.decode_native(self.run)
        meta = dict(original, pad_node_ids=[2]+original['pad_node_ids'][1:])
        (basis/'mesh-metadata.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'Explicit grouped.*mapping'):
            archive.decode_native(self.run)

    def test_grouped_contact_area_and_cross_frequency_order_rejected(self):
        basis = self.make_grouped(12)
        path = basis/'contacts-3000.csv'
        original = path.read_text()
        lines = original.splitlines()
        parts = lines[1].split(',')
        parts[-1] = str(float(parts[-1])*2)
        lines[1] = ','.join(parts)
        path.write_text('\n'.join(lines)+'\n')
        with self.assertRaisesRegex(ValueError, 'physical contact area differs'):
            archive.decode_native(self.run)
        path.write_text(original)
        other = basis/'contacts-3030.csv'
        lines = other.read_text().splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        other.write_text('\n'.join(lines)+'\n')
        with self.assertRaisesRegex(ValueError, 'ordering differs across frequencies'):
            archive.decode_native(self.run)

    def test_grouped_pad_dimension_must_not_replace_source_dimension(self):
        basis = self.make_grouped(16)
        (basis/'source-3000.bin').write_bytes(b'\0'*(16*16*16))
        with self.assertRaisesRegex(ValueError, 'exceeds declared shape'):
            archive.decode_native(self.run)


if __name__ == '__main__':
    unittest.main()
