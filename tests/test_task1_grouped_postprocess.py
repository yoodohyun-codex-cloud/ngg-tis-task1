"""Synthetic grouped exporter accounting fixtures; no phantom PDE/postprocess.

The tiny grid exists only to exercise file decoding, source-current grouping
and rejection boundaries. It is deliberately not a complete phantom mesh and
is never passed to the volume/probe routines or presented as a simulation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('grouped_postprocess_test_target', ROOT/'tools/task1_grouped_postprocess.py')
grouped = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grouped)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class GroupedNativeLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.native = self.root/'native'
        self.native.mkdir()
        self.nodes = [0, 0, 1, 1, -1, -1, -1, -1]
        self.area = 1e-6
        self.mask = self.root/'mask.csv'
        self.mask.write_text('pad,i,j,area_m2\n'+''.join(f'{i},{i},0,0.000001\n' for i in range(8)))
        self.config = self.root/'case.properties'
        properties = dict(channels='2', n_outputs='2', n_pads='8', n_return_nodes='1',
                          return_topology='common_GND', **{'mask.path': str(self.mask), 'mask.sha256': sha(self.mask)})
        for i, node in enumerate(self.nodes):
            properties[f'pad.node.{i}'] = str(node)
            properties[f'pad.{i}.represented_area_m2'] = str(self.area)
        self.config.write_text(''.join(f'{key}={value}\n' for key, value in properties.items()))
        self.metadata = dict(exporter_class='GroupedPadBasis', exporter_kind='grouped_native',
            numerical_base_class='SelectivityShapeBasis', source_peak_V=.5, source_resistance_ohm=50.,
            phasor_convention='peak,+jomega_t', field_reconstruction=grouped.RECONSTRUCTION,
            frequencies_Hz=list(grouped.FREQUENCIES), radius_mm=25, total_depth_mm=25.1,
            tissue_boundaries_mm=[0, .1, 5.1, 10.1, 25.1], h_xy_mm=1.25, sc_cells=2,
            bulk_layer_counts=[14, 14, 40], n_pads=8, n_outputs=2, channels=2,
            n_return_nodes=1, return_topology='common_GND', pad_node_ids=self.nodes,
            cells=8, config_sha256=sha(self.config))
        self.case = dict(id='synthetic-grouped-loader', exporter_class='GroupedPadBasis',
            n_pads=8, n_outputs=2, pad_node_ids=self.nodes,
            pads=[dict(pad_id=i, parent_group=i//2, node=node) for i, node in enumerate(self.nodes)],
            config_file=str(self.config), config_sha256=sha(self.config),
            mask_file=str(self.mask), mask_sha256=sha(self.mask),
            h_xy_mm=1.25, sc_cells=2, bulk_counts=[14, 14, 40], expected_pad_areas_m2=[self.area]*8)
        self.write_metadata()
        validation = dict(channels=2, n_outputs=2, n_pads=8, cells=8,
            max_residual=1e-12, max_power_error=1e-12, max_current_error=1e-12,
            max_area_relative_error=0., max_interface_normal_current_relative_error=1e-12)
        (self.native/'validation.json').write_text(json.dumps(validation))
        (self.native/'BASIS_COMPLETE').touch()
        (self.native/'grid.csv').write_text('x_mm,y_mm,z_mm,layer,volume_m3\n'+
                                           ''.join(f'{i},0,0.025,0,1e-10\n' for i in range(8)))
        # Reciprocal complex transfer is generally not Hermitian. Its real
        # Hermitian power part, not its imaginary part, supplies real losses.
        self.source = np.array([[.001+.0003j, .0001+.00002j],
                                [.0001+.00002j, .002+.0005j]], dtype='<c16')
        self.loss = np.zeros((6, 2, 2), dtype='<c16')
        self.loss[0] = .25*self.source.real
        self.density = np.zeros((2, 8), dtype='<c16')
        self.density[:, :2] = self.source[0, :, None]/(2*self.area)
        self.density[:, 2:4] = self.source[1, :, None]/(2*self.area)
        self.density[:, 4:] = -(self.source.sum(axis=0)[:, None])/(4*self.area)
        self.contact_text = 'pad,x_mm,y_mm,area_m2\n'+''.join(f'{i},{i},0,{self.area}\n' for i in range(8))
        for f in grouped.FREQUENCIES:
            self.array('field', f, np.zeros((2, 8, 3), dtype='<c16'))
            self.array('potential', f, np.zeros((2, 8), dtype='<c16'))
            self.array('density', f, self.density)
            self.array('source', f, self.source)
            self.array('loss', f, self.loss)
            (self.native/f'contacts-{f}.csv').write_text(self.contact_text)

    def write_metadata(self):
        (self.native/'mesh-metadata.json').write_text(json.dumps(self.metadata))

    def array(self, name, frequency, value):
        (self.native/f'{name}-{frequency}.bin').write_bytes(np.asarray(value, dtype='<c16').tobytes())

    def load(self):
        return grouped._load_basis(self.native, self.case, time.monotonic()+30)

    def test_raw_physical_ids_and_shared_current_accounting_are_preserved(self):
        before = (self.native/'contacts-3000.csv').read_bytes()
        basis = self.load()
        row = basis['f'][3000]
        np.testing.assert_array_equal(row['physical_contacts']['pad'], np.arange(8))
        np.testing.assert_array_equal(row['contacts']['pad'], [0, 0, 1, 1, 2, 2, 3, 3])
        np.testing.assert_array_equal(row['density'], self.density)
        for output in (0, 1):
            use = np.asarray(self.nodes) == output
            current = np.sum(row['density'][:, use]*row['physical_contacts']['area_m2'][use], axis=1)
            np.testing.assert_allclose(current, self.source[output], rtol=1e-14, atol=1e-18)
        self.assertEqual((self.native/'contacts-3000.csv').read_bytes(), before)
        self.assertEqual(basis['metadata']['exporter_class'], 'GroupedPadBasis')
        self.assertFalse(basis['grouped_contact_adapter']['old_strict_loader_used'])
        self.assertFalse(basis['grouped_contact_adapter']['exporter_identity_changed'])
        self.assertFalse(np.allclose(self.source, self.source.conj().T))

    def test_exporter_identity_and_additional_outputs_rejected(self):
        self.metadata['exporter_class'] = 'SelectivityShapeBasis'
        self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'honest GroupedPadBasis'):
            self.load()
        self.metadata['exporter_class'] = 'GroupedPadBasis'
        self.write_metadata()
        self.case['n_outputs'] = 4
        with self.assertRaisesRegex(ValueError, 'exactly2 outputs'):
            self.load()

    def test_metadata_pad_mapping_and_missing_return_group_rejected(self):
        self.metadata['pad_node_ids'] = [0, 1, 0, 1, -1, -1, -1, -1]
        self.write_metadata()
        with self.assertRaisesRegex(ValueError, 'topology differs'):
            self.load()
        self.metadata['pad_node_ids'] = self.nodes
        self.write_metadata()
        self.case['pads'][-1]['parent_group'] = 2
        with self.assertRaisesRegex(ValueError, 'parent-group counts'):
            self.load()

    def test_wrong_physical_area_and_missing_raw_pad_rejected(self):
        changed = self.contact_text.replace('0,0,0,1e-06', '0,0,0,1.1e-06')
        self.assertNotEqual(changed, self.contact_text)
        (self.native/'contacts-3000.csv').write_text(changed)
        with self.assertRaisesRegex(ValueError, 'physical pad area changed'):
            self.load()
        changed = self.contact_text.replace('7,7,0,', '6,7,0,')
        (self.native/'contacts-3000.csv').write_text(changed)
        with self.assertRaisesRegex(ValueError, 'raw physical grouped contact'):
            self.load()

    def test_wrong_raw_source_current_sum_rejected(self):
        changed = self.density.copy()
        changed[0, 0] += 10
        self.array('density', 3000, changed)
        with self.assertRaisesRegex(ValueError, 'electrical-node/source balance'):
            self.load()

    def test_nonhermitian_and_incorrect_real_power_rejected(self):
        changed = self.loss.copy()
        changed[0, 0, 1] += .0001j
        self.array('loss', 3000, changed)
        with self.assertRaisesRegex(ValueError, 'Hermitian'):
            self.load()
        self.array('loss', 3000, self.loss*1.1)
        with self.assertRaisesRegex(ValueError, 'power conservation'):
            self.load()

    def test_truncated_and_nonfinite_native_arrays_rejected(self):
        path = self.native/'field-3000.bin'
        original = path.read_bytes()
        path.write_bytes(original[:-1])
        with self.assertRaisesRegex(ValueError, 'Truncated native binary'):
            self.load()
        path.write_bytes(original)
        changed = self.source.copy()
        changed[0, 0] = np.nan+1j
        self.array('source', 3000, changed)
        with self.assertRaisesRegex(ValueError, 'Nonfinite native transfer array'):
            self.load()

    def test_native_config_hash_and_mask_corruption_rejected(self):
        self.config.write_text(self.config.read_text()+'extra=changed\n')
        with self.assertRaisesRegex(ValueError, 'config SHA'):
            self.load()
        self.metadata['config_sha256'] = self.case['config_sha256'] = sha(self.config)
        self.write_metadata()
        self.mask.write_text(self.mask.read_text()+'9,9,9,1\n')
        with self.assertRaisesRegex(ValueError, 'contact mask SHA'):
            self.load()


if __name__ == '__main__':
    unittest.main()
