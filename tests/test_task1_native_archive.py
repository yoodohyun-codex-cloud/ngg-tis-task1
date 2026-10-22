"""Synthetic storage-integrity fixtures only; no research import or solver."""
import gzip
import importlib.util
import io
import json
import os
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


class TerminalFailureArchiveTests(ArchiveFixture, unittest.TestCase):
    def make_failure(self, status='error'):
        (self.run/'controller.json').write_text(json.dumps(dict(status=status, phase='stopped', pid=None, java_pid=None)))
        (self.run/'summary.json').write_text(json.dumps(dict(status=status,
            cases=[dict(id='fixture', status='complete')], failed_case='partial', not_run=['not-run'])))
        (self.run/'preregistration.json').write_text(json.dumps(dict(source_commit='a'*40,
            cases=[dict(id=value) for value in ('fixture', 'partial', 'not-run', 'missing-inputs')])))
        partial = self.run/'bases/partial'
        partial.mkdir()
        (partial/'partial-field.bin').write_bytes(b'preserve incomplete raw bytes')
        missing = self.run/'bases/missing-inputs'
        missing.mkdir()
        (missing/'BASIS_COMPLETE').write_bytes(b'')
        (self.run/'failure.json').write_text(json.dumps(dict(status=status,
            reason='reference comparison gate failed after native calculation; C1 not run')))
        (self.run/'failure.log').write_bytes(b'original failure and diagnostic evidence\n')

    def test_terminal_error_needs_opt_in_and_restores_status_evidence_and_skips(self):
        self.make_failure()
        failure_bytes = (self.run/'failure.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Only completed'):
            archive.pack(self.run, self.output)
        self.assertFalse(self.output.exists())
        packed = archive.pack(self.run, self.output, include_terminal_failure=True)
        self.assertEqual(packed['original_terminal_status'], 'error')
        self.assertTrue(packed['terminal_failure_included'])
        manifest = archive.read(Path(str(self.output)+'.manifest.json'))
        self.assertEqual(manifest['original_terminal_status'], 'error')
        self.assertFalse(manifest['scientific_validation_claimed'])
        self.assertIn('failure.json', manifest['failure_evidence_files'])
        self.assertIn('failure.log', manifest['failure_evidence_files'])
        restored = archive.restore(self.output, packed['archive_sha256'], self.root/'clean')
        clean_run = self.root/'clean/cloud-fixture'
        self.assertEqual(archive.read(clean_run/'controller.json')['status'], 'error')
        self.assertEqual(archive.read(clean_run/'summary.json')['status'], 'error')
        self.assertEqual((clean_run/'failure.json').read_bytes(), failure_bytes)
        self.assertEqual((clean_run/'failure.log').read_bytes(), b'original failure and diagnostic evidence\n')
        self.assertEqual((clean_run/'bases/partial/partial-field.bin').read_bytes(), b'preserve incomplete raw bytes')
        decode = restored['native_array_decode_verification']
        self.assertEqual(decode['status'], 'available_complete_basis_storage_decode_passed')
        self.assertEqual(decode['original_terminal_status'], 'error')
        self.assertTrue(decode['original_failure_status_preserved'])
        self.assertFalse(decode['scientific_validation_claimed'])
        self.assertEqual(len(decode['arrays']), 20)
        self.assertEqual([row['case_id'] for row in decode['bases']], ['fixture'])
        skipped = {row['case_id']: row for row in decode['skipped_cases']}
        self.assertEqual(skipped['not-run']['reason'], 'preregistered_not_run')
        self.assertEqual(skipped['partial']['reason'], 'incomplete_raw_missing_BASIS_COMPLETE')
        self.assertEqual(skipped['missing-inputs']['reason'], 'incomplete_raw_missing_required_files')
        self.assertIn('grid.csv.gz', skipped['missing-inputs']['missing_files'])
        self.assertEqual(archive.read(self.run/'controller.json')['status'], 'error')
        self.assertFalse(restored['scientific_numerical_reproduction'])

    def test_terminal_active_phase_and_active_pid_are_rejected(self):
        self.make_failure()
        controller = archive.read(self.run/'controller.json')
        controller['phase'] = 'postprocessing'
        (self.run/'controller.json').write_text(json.dumps(controller))
        with self.assertRaisesRegex(ValueError, 'phase must be stopped'):
            archive.pack(self.run, self.output, include_terminal_failure=True)
        controller.update(phase='stopped', pid=os.getpid())
        (self.run/'controller.json').write_text(json.dumps(controller))
        with self.assertRaisesRegex(ValueError, 'active recorded PID'):
            archive.pack(self.run, self.output, include_terminal_failure=True)
        self.assertFalse(self.output.exists())

    def test_only_matching_explicit_terminal_failure_statuses_are_accepted(self):
        self.make_failure('resource_shortage')
        result = archive.inventory(self.run, include_terminal_failure=True)
        self.assertEqual(result['original_terminal_status'], 'resource_shortage')
        controller = archive.read(self.run/'controller.json')
        controller['status'] = 'error'
        (self.run/'controller.json').write_text(json.dumps(controller))
        with self.assertRaisesRegex(ValueError, 'statuses must match'):
            archive.inventory(self.run, include_terminal_failure=True)
        controller['status'] = 'running'
        (self.run/'controller.json').write_text(json.dumps(controller))
        (self.run/'summary.json').write_text('{"status":"running"}')
        with self.assertRaisesRegex(ValueError, 'statuses must match'):
            archive.inventory(self.run, include_terminal_failure=True)

    def test_terminal_no_complete_basis_is_not_labeled_decode_passed(self):
        self.make_failure('stopped')
        (self.run/'bases/fixture/BASIS_COMPLETE').unlink()
        packed = archive.pack(self.run, self.output, include_terminal_failure=True)
        restored = archive.restore(self.output, packed['archive_sha256'], self.root/'clean')
        decode = restored['native_array_decode_verification']
        self.assertEqual(decode['status'], 'no_complete_native_basis_available')
        self.assertEqual(decode['original_terminal_status'], 'stopped')
        self.assertEqual(decode['arrays'], [])
        self.assertFalse(restored['scientific_numerical_reproduction'])


class ResidualDiagnosticArchiveTests(ArchiveFixture, unittest.TestCase):
    """One-frequency diagnostic has its own ABI, never a full TIS basis."""

    def make_residual(self, tolerance=1e-9):
        basis = self.run/'bases/fixture'
        # Synthetic fixture only: omit the legacy other-frequency inputs to
        # prove that the diagnostic truly requires just the declared carrier.
        for frequency in (3030, 9000, 9090):
            for path in basis.glob(f'*-{frequency}.*'):
                path.unlink()
        configs = self.run/'configs'
        configs.mkdir()
        config_path = configs/'fixture.properties'
        config_path.write_text('channels=2\nfrequencies=3000\n'
            f'solver.relative_tolerance={tolerance}\nsolver.max_iterations=12000\n')
        (self.run/'preregistration.json').write_text(json.dumps(dict(source_commit='a'*40,
            cases=[dict(id='fixture', exporter_class='ResidualShapeBasis', frequencies_Hz=[3000],
                        config_file=str(config_path), config_sha256=archive.digest(config_path))])))
        meta = archive.read(basis/'mesh-metadata.json')
        meta.update(exporter_kind='residual_diagnostic_native', exporter_class='ResidualShapeBasis',
            numerical_base_class='SelectivityShapeBasis.ShapeNet', channels=2, n_outputs=2, n_pads=4,
            n_return_nodes=1, return_topology='common_GND', pad_node_ids=[0, 1, -1, -1],
            frequencies_Hz=[3000], h_xy_mm=1.25, sc_cells=2, bulk_layer_counts=[14, 14, 40],
            solver_version='literal-frozen-COCG-rtol-v1', solver_relative_tolerance=tolerance,
            solver_max_iterations=12000, solver_diagnostics_file='solver-diagnostics.json',
            field_reconstruction='half_face_flux; top contact term averaged over full cell face h^2',
            storage='grid/field/potential losslessgzip; density/source/loss raw; little-endian Float64/complex128',
            inactive_source='0V through50ohm', config_sha256=archive.digest(config_path))
        (basis/'mesh-metadata.json').write_text(json.dumps(meta))
        (basis/'contacts-3000.csv').write_text('pad,x_mm,y_mm,area_m2\n'+''.join(
            f'{pad},0,0,0.000225\n' for pad in range(4)))
        for label, count in (('field', 12), ('potential', 4)):
            with gzip.open(basis/f'{label}-3000.bin.gz', 'wb') as stream:
                stream.write(struct.pack('<'+'d'*count, *map(float, range(count))))
        for label, count in (('density', 16), ('source', 8), ('loss', 48)):
            (basis/f'{label}-3000.bin').write_bytes(struct.pack('<'+'d'*count, *map(float, range(count))))
        diagnostics = dict(schema='task1-residual-solver-v1', status='complete',
            solver_version=meta['solver_version'], relative_tolerance=tolerance, max_iterations=12000,
            native_residual_limit=2e-7, recomputed_diagnostic_limit=1e-9 if tolerance == 1e-11 else 2e-7,
            solves=[dict(basis_channel=channel, iterations=16+channel,
                recursive_relative_residual=tolerance/2, recomputed_relative_residual=tolerance*2,
                relative_residual=tolerance*2, requested_relative_tolerance=tolerance, status='complete')
                for channel in (0, 1)])
        (basis/'solver-diagnostics.json').write_text(json.dumps(diagnostics))
        return basis

    def test_single_frequency_two_output_diagnostic_roundtrip_has_five_arrays(self):
        basis = self.make_residual()
        self.assertFalse((basis/'field-3030.bin.gz').exists())
        packed = archive.pack(self.run, self.output)
        result = archive.restore(self.output, packed['archive_sha256'], self.root/'clean')
        decode = result['native_array_decode_verification']
        self.assertEqual(decode['status'], 'passed')
        self.assertEqual(len(decode['arrays']), 5)
        record = decode['bases'][0]
        self.assertEqual(record['exporter_class'], 'ResidualShapeBasis')
        self.assertEqual(record['frequencies_Hz'], [3000])
        self.assertEqual(record['n_pads'], 4)
        self.assertEqual(record['n_outputs'], 2)
        self.assertEqual(record['source_matrix_shape'], [2, 2])
        self.assertEqual(record['loss_matrix_shape'], [6, 2, 2])
        self.assertEqual(record['residual_diagnostic']['requested_relative_tolerance'], 1e-9)
        self.assertFalse(record['residual_diagnostic']['full_two_carrier_TIS_basis'])
        self.assertFalse(record['residual_diagnostic']['scientific_residual_gate_validation_claimed'])
        self.assertFalse(result['scientific_numerical_reproduction'])
        fields = next(item for item in decode['arrays'] if item['path'].endswith('field-3000.bin.gz'))
        self.assertEqual(fields['decoded_bytes'], 2*1*3*16)

    def test_tighter_registered_tolerance_is_preserved_without_accuracy_promotion(self):
        basis = self.make_residual(1e-11)
        diagnostics = archive.read(basis/'solver-diagnostics.json')
        diagnostics['solves'][0].update(recomputed_relative_residual=3e-7, relative_residual=3e-7)
        (basis/'solver-diagnostics.json').write_text(json.dumps(diagnostics))
        record = archive.decode_native(self.run)['bases'][0]['residual_diagnostic']
        self.assertEqual(record['requested_relative_tolerance'], 1e-11)
        self.assertEqual(record['solver_receipts'][0]['recomputed_relative_residual'], 3e-7)
        self.assertFalse(record['scientific_residual_gate_validation_claimed'])

    def test_missing_tolerance_loosened_stop_or_expanded_iteration_cap_rejected(self):
        basis = self.make_residual()
        original = archive.read(basis/'mesh-metadata.json')
        for changes in ({'solver_relative_tolerance': None}, {'solver_relative_tolerance': 1e-7},
                        {'solver_max_iterations': 24000}):
            meta = dict(original, **changes)
            if changes.get('solver_relative_tolerance', 'present') is None:
                del meta['solver_relative_tolerance']
            (basis/'mesh-metadata.json').write_text(json.dumps(meta))
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'registered tolerance'):
                archive.decode_native(self.run)

    def test_other_carrier_and_legacy_exporter_spoof_rejected(self):
        basis = self.make_residual()
        original = archive.read(basis/'mesh-metadata.json')
        (basis/'mesh-metadata.json').write_text(json.dumps(dict(original, frequencies_Hz=[3030])))
        with self.assertRaisesRegex(ValueError, r'exactly \[3000\]'):
            archive.decode_native(self.run)
        (basis/'mesh-metadata.json').write_text(json.dumps(dict(original,
            exporter_kind='selectivity_native', exporter_class='SelectivityShapeBasis')))
        with self.assertRaisesRegex(ValueError, 'never spoof a legacy'):
            archive.decode_native(self.run)

    def test_required_native_file_and_phase_storage_metadata_are_checked(self):
        basis = self.make_residual()
        original = archive.read(basis/'mesh-metadata.json')
        (basis/'mesh-metadata.json').write_text(json.dumps(dict(original, storage='big-endian complex64')))
        with self.assertRaisesRegex(ValueError, 'field/storage/termination ABI'):
            archive.decode_native(self.run)
        (basis/'mesh-metadata.json').write_text(json.dumps(dict(original, phasor_convention='RMS,-jomega_t')))
        with self.assertRaisesRegex(ValueError, 'phasor convention'):
            archive.decode_native(self.run)
        (basis/'mesh-metadata.json').write_text(json.dumps(original))
        (basis/'solver-diagnostics.json').unlink()
        with self.assertRaisesRegex(ValueError, 'missing required native files.*solver-diagnostics'):
            archive.decode_native(self.run)

    def test_nonfinite_native_and_incorrect_physical_pad_output_count_rejected(self):
        basis = self.make_residual()
        original = archive.read(basis/'mesh-metadata.json')
        (basis/'mesh-metadata.json').write_text(json.dumps(dict(original, n_pads=8)))
        with self.assertRaisesRegex(ValueError, 'four physical pads'):
            archive.decode_native(self.run)
        (basis/'mesh-metadata.json').write_text(json.dumps(dict(original, n_outputs=4)))
        with self.assertRaisesRegex(ValueError, 'two independent outputs'):
            archive.decode_native(self.run)
        (basis/'mesh-metadata.json').write_text(json.dumps(original))
        (basis/'source-3000.bin').write_bytes(struct.pack('<'+'d'*8, float('nan'), *([0.]*7)))
        with self.assertRaisesRegex(ValueError, 'Nonfinite native'):
            archive.decode_native(self.run)

    def test_terminal_failure_keeps_complete_one_frequency_and_incomplete_evidence(self):
        basis = self.make_residual()
        (self.run/'controller.json').write_text('{"status":"error","phase":"stopped"}')
        (self.run/'summary.json').write_text(json.dumps(dict(status='error',
            cases=[dict(id='fixture', status='complete')], not_run=['not-run'])))
        pre = archive.read(self.run/'preregistration.json')
        pre['cases'].append(dict(id='not-run'))
        (self.run/'preregistration.json').write_text(json.dumps(pre))
        result = archive.decode_native(self.run, include_terminal_failure=True)
        self.assertEqual(len(result['arrays']), 5)
        self.assertEqual(result['original_terminal_status'], 'error')
        self.assertEqual(result['skipped_cases'][0]['case_id'], 'not-run')
        self.assertEqual(result['skipped_cases'][0]['reason'], 'preregistered_not_run')
        (basis/'potential-3000.bin.gz').unlink()
        result = archive.decode_native(self.run, include_terminal_failure=True)
        self.assertEqual(result['status'], 'no_complete_native_basis_available')
        skipped = next(item for item in result['skipped_cases'] if item['case_id'] == 'fixture')
        self.assertEqual(skipped['reason'], 'incomplete_raw_missing_required_files')
        self.assertEqual(skipped['missing_files'], ['potential-3000.bin.gz'])
        self.assertNotIn('field-3030.bin.gz', skipped['missing_files'])


if __name__ == '__main__':
    unittest.main()
