"""Synthetic, stdlib-only tests; no research data or browser is opened."""
import base64
import copy
import gzip
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'tools/task1_best1_pair_dashboard.py'
SPEC = importlib.util.spec_from_file_location('synthetic_best1_pair', SOURCE)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)
MODES = ('raw_1Vpp', 'skin_contact_only')
MATCHES = ('ROI_energy_RMS', 'centre20_E_RMS')
REGIONS = ('primary_r5_depth15_20', 'surface_0_5', 'primary_complement', 'total')
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2',
           'contact_voltage_RMS_max_V', 'bulk_skin_J_vector_RMS_max_A_m2',
           'bulk_skin_J_vector_RMS_p95_A_m2', 'SC_power_W', 'contact_power_W',
           'skin_SC_plus_dermis_power_W', 'source_power_W')


def encoded(values, kind='e'):
    return base64.b64encode(struct.pack('<' + kind * len(values), *values)).decode()


def fixture():
    modes = {}
    for mode, scale in zip(MODES, (1., 1.1)):
        modes[mode] = {
            'reference_amplitude_scale': scale,
            'reference_source_Vpp_intervals_V': [[.99, 1.], [.999, 1.]],
            'reference_burdens': {k: .01 for k in BURDENS},
            'target_ROI_energy_RMS_V_m': 2.1,
            'target_centre20_E_RMS_V_m': 2.,
            'matches': {key: {
                'amplitude_scale': 1.2, 'required_source_Vpp': 1.2,
                'burdens': {k: .02 for k in BURDENS},
                'achieved_ROI_energy_RMS_V_m': 2.1,
                'achieved_centre20_E_RMS_V_m': 2., 'source_current_RMS_mA': .4,
                'loaded_metal_Vpp': .9,
                'unloaded_probe40': [{'id': 'probe-' + str(i), 'RMS_V': .01}
                                     for i in range(40)],
            } for key in MATCHES},
        }
    analysis = {
        'schema': 'task1-best1-single-pair-comparison-v1', 'modes': modes,
        'candidate_adopted': False,
        'same_field_RMS_implies_same_modulation_or_activation': False,
        'single_pair': {'circuit': {'n_pads': 2, 'n_outputs': 1,
                                   'n_return_nodes': 1, 'source_resistance_ohm': 50}},
    }
    spatial = {
        'fieldunits': 'V/m', 'contactunits': 'A/m2',
        'grid': {'x_edges_mm': [-25, -12.5, 0, 12.5, 25],
                 'y_edges_mm': [-25, -12.5, 0, 12.5, 25],
                 'z_faces_mm': [0, .1, 10.1, 25.1],
                 'XY_requested_depths_mm': [5, 10, 15, 17.5, 20],
                 'XY_actual_depths_mm': [4.9, 9.9, 15.1, 17.4, 20.1],
                 'XZ_actual_y_mm': .3125, 'YZ_actual_x_mm': -.3125},
        'regions': {},
    }
    for key, centres in (
        ('TIS', [(-10, -10, 'out0'), (10, 10, 'out1'),
                 (10, -10, 'GND'), (-10, 10, 'GND')]),
        ('C1', [(-10, -10, 'out0'), (10, -10, 'GND')]),
    ):
        pads = [{'pad': i, 'node': node, 'x_mm': x, 'y_mm': y, 'area_mm2': 225.}
                for i, (x, y, node) in enumerate(centres)]
        spatial[key] = {
            'pad_centres': pads,
            'physical_outlines': [
                {'pad': p['pad'], 'node': p['node'], 'polygon_mm': [
                    [p['x_mm'] - 7.5, p['y_mm'] - 7.5],
                    [p['x_mm'] + 7.5, p['y_mm'] - 7.5],
                    [p['x_mm'] + 7.5, p['y_mm'] + 7.5],
                    [p['x_mm'] - 7.5, p['y_mm'] + 7.5]]}
                for p in pads],
            'pad_mask_b64': encoded(list(range(len(pads))) + [-1] * (16 - len(pads)), 'h'),
            'RMS': {'xy': [encoded([.5] * 16) for _ in range(5)],
                    'xz': encoded([.5] * 12), 'yz': encoded([.5] * 12)},
            'contactJ': {'values_b64': encoded([1.] * 16)},
        }
        spatial['regions'][key] = {region: {
            'mean': 2., 'p10': 1., 'p95': 3., 'max': 4., 'std': .25,
            'volume_m3': 1e-6, 'energy_RMS_V_m': 2.1,
        } for region in REGIONS}
    return {'analysis': analysis, 'spatial': spatial,
            'provenance': {'label': '합성 fixture only'}}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.cards = set(), []
        self.scripts, self.resources, self.metas = [], [], []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'article' and 'data-case-id' in attrs:
            self.cards.append(attrs['data-case-id'])
        if tag == 'meta':
            self.metas.append(attrs)
        if tag == 'script':
            self.current = {'attrs': attrs, 'text': ''}
            self.scripts.append(self.current)
        if tag in ('script', 'img', 'iframe') and 'src' in attrs:
            self.resources.append(attrs['src'])
        if tag == 'link':
            self.resources.append(attrs.get('href'))

    def handle_data(self, data):
        if self.current is not None:
            self.current['text'] += data

    def handle_endtag(self, tag):
        if tag == 'script':
            self.current = None

    def unpack(self):
        packed = next(x['text'] for x in self.scripts if x['attrs'].get('id') == 'packed')
        return json.loads(gzip.decompress(base64.b64decode(packed, validate=True)))


class Best1PairDashboard(unittest.TestCase):
    def setUp(self):
        self.payload = fixture()

    def rejected(self):
        with self.assertRaises(ValueError):
            dashboard.validate(self.payload)

    def test_valid_payload_and_packed_gzip_json_roundtrip(self):
        dashboard.validate(self.payload)
        page = Page(); page.feed(dashboard.render(self.payload))
        self.assertEqual(self.payload, page.unpack())
        self.assertEqual(['TIS', 'C1'], page.cards)
        self.assertEqual('application/octet-stream', page.scripts[0]['attrs']['type'])

    def test_script_breakout_is_compressed_and_offline_csp_hash_matches(self):
        marker = '</script><script src="https://invalid.test/payload.js">&한국\u2028\u2029'
        self.payload['provenance']['label'] = marker
        result = dashboard.render(self.payload)
        page = Page(); page.feed(result)
        self.assertEqual(marker, page.unpack()['provenance']['label'])
        self.assertNotIn(marker, result)
        self.assertEqual(2, len(page.scripts))
        self.assertEqual([], page.resources)
        script = page.scripts[1]['text']
        self.assertNotIn('fetch(', script)
        self.assertNotIn('XMLHttpRequest', script)
        self.assertIn("new DecompressionStream('gzip')", script)
        csp = next(x['content'] for x in page.metas
                   if x.get('http-equiv') == 'Content-Security-Policy')
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn("'sha256-" + digest + "'", csp)
        self.assertIn("default-src 'none'", csp)

    def test_render_is_memory_only_and_inputs_are_unchanged(self):
        before = copy.deepcopy(self.payload)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch('builtins.open', side_effect=AssertionError('I/O forbidden')), \
                 mock.patch.object(Path, 'open', side_effect=AssertionError('I/O forbidden')), \
                 mock.patch.object(Path, 'write_text', side_effect=AssertionError('I/O forbidden')), \
                 mock.patch.object(Path, 'write_bytes', side_effect=AssertionError('I/O forbidden')):
                result = dashboard.render(self.payload)
            self.assertEqual([], list(Path(tmp).iterdir()))
        self.assertTrue(result.startswith('<!doctype html>'))
        self.assertEqual(before, self.payload)

    def test_units_modes_and_no_physiology_equivalence_claim(self):
        for key, value in (('fieldunits', 'V/cm'), ('contactunits', 'mA/mm2')):
            with self.subTest(key=key):
                self.payload = fixture(); self.payload['spatial'][key] = value
                self.rejected()
        for key in ('candidate_adopted', 'same_field_RMS_implies_same_modulation_or_activation'):
            with self.subTest(key=key):
                self.payload = fixture(); self.payload['analysis'][key] = True
                self.rejected()
        self.payload = fixture()
        del self.payload['analysis']['modes']['raw_1Vpp']; self.rejected()

    def test_positive_saved_scales_voltage_and_separate_matches_are_required(self):
        for key, value in (('amplitude_scale', 0), ('required_source_Vpp', -1),
                           ('source_current_RMS_mA', float('nan'))):
            with self.subTest(key=key):
                self.payload = fixture()
                self.payload['analysis']['modes']['skin_contact_only']['matches']['ROI_energy_RMS'][key] = value
                self.rejected()
        self.payload = fixture()
        self.payload['analysis']['modes']['raw_1Vpp']['reference_amplitude_scale'] = 0
        self.rejected()
        self.payload = fixture()
        del self.payload['analysis']['modes']['raw_1Vpp']['matches']['centre20_E_RMS']
        self.rejected()

    def test_genuine_pair_topology_and_all_nine_burdens_are_required(self):
        for key, value in (('n_pads', 4), ('n_outputs', 2),
                           ('n_return_nodes', 2), ('source_resistance_ohm', 0)):
            with self.subTest(key=key):
                self.payload = fixture()
                self.payload['analysis']['single_pair']['circuit'][key] = value
                self.rejected()
        self.payload = fixture()
        del self.payload['analysis']['modes']['raw_1Vpp']['reference_burdens']['SC_power_W']
        self.rejected()

    def test_native_grid_depths_and_authoritative_float64_statistics(self):
        for key in ('x_edges_mm', 'y_edges_mm', 'z_faces_mm'):
            with self.subTest(key=key):
                self.payload = fixture()
                self.payload['spatial']['grid'][key][1] = self.payload['spatial']['grid'][key][0]
                self.rejected()
        self.payload = fixture()
        self.payload['spatial']['grid']['XY_actual_depths_mm'].pop(); self.rejected()
        self.payload = fixture()
        del self.payload['spatial']['regions']['C1']['total']['energy_RMS_V_m']; self.rejected()

    def test_f16_and_i16_little_endian_byte_counts_are_enforced(self):
        for key in ('TIS', 'C1'):
            for plane in ('xy', 'xz', 'yz', 'contactJ', 'mask'):
                with self.subTest(key=key, plane=plane):
                    self.payload = fixture(); case = self.payload['spatial'][key]
                    if plane == 'xy': case['RMS']['xy'][0] = encoded([1.] * 15)
                    elif plane in ('xz', 'yz'): case['RMS'][plane] = encoded([1.] * 11)
                    elif plane == 'contactJ': case['contactJ']['values_b64'] = encoded([1.] * 15)
                    else: case['pad_mask_b64'] = encoded([0] * 15, 'h')
                    self.rejected()
        self.payload = fixture()
        self.payload['spatial']['TIS']['RMS']['xy'][0] = encoded([1.] * 16, 'f')
        self.rejected()

    def test_outlines_and_known_physical_pad_labels_are_required(self):
        self.payload['spatial']['C1']['pad_mask_b64'] = encoded([2] * 16, 'h')
        self.rejected()
        self.payload = fixture()
        self.payload['spatial']['TIS']['physical_outlines'][0]['polygon_mm'][0][0] = float('nan')
        self.rejected()
        self.payload = fixture()
        self.payload['spatial']['C1']['physical_outlines'].pop(); self.rejected()

    def test_nonuniform_grid_and_offline_controls_remain_explicit(self):
        result = dashboard.render(self.payload)
        page = Page(); page.feed(result)
        self.assertEqual([0, .1, 10.1, 25.1], page.unpack()['spatial']['grid']['z_faces_mm'])
        self.assertTrue({'mode', 'match', 'plane', 'depth', 'range', 'field-legend',
                         'contact-legend', 'TIS-field', 'C1-field'} <= page.ids)
        script = page.scripts[1]['text']
        self.assertIn("fill('mode',modes,'skin_contact_only')", script)
        self.assertIn("fill('match',matches,'ROI_energy_RMS')", script)
        self.assertIn('G.z_faces_mm', script)
        self.assertIn('Y(ye[j+1])', script)
        self.assertIn('view.getInt16(i*2,true)', script)
        self.assertIn('view.getUint16(i*2,true)', script)
        self.assertIn('window.task1Best1Pair=', script)


if __name__ == '__main__':
    unittest.main()
