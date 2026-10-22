"""Synthetic, stdlib-only contracts for the offline top-five dashboard.

No repository result data, scientific modules, browsers, or native arrays are
used. render() is exercised in memory and is forbidden to write its output.
"""
import base64
import copy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / 'tools/task1_top5_dashboard.py'
SPEC = importlib.util.spec_from_file_location('synthetic_top5_dashboard', SOURCE)
dashboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dashboard)

MODES = ('raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
         'skin_contact_only', 'legacy_composite_full_skin')
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
PRIMARY = 'primary_r5_depth15_20'
REGIONS = (PRIMARY, 'surface_0_5', 'primary_complement', 'total')
BURDENS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2',
           'contact_voltage_RMS_max_V', 'SC_power_W', 'contact_power_W',
           'bulk_skin_J_vector_RMS_max_A_m2', 'bulk_skin_J_vector_RMS_p95_A_m2',
           'skin_SC_plus_dermis_power_W', 'source_power_W')


def encoded(values, dtype='f'):
    return base64.b64encode(struct.pack('<' + dtype * len(values), *values)).decode()


def fixtures():
    scales = dict(zip(MODES, (1.0, .8, .7, .6, .5)))
    rows = []
    for i, pads in enumerate((4, 4, 8, 12, 16, 4)):
        normalizations = {}
        for mode, scale in scales.items():
            normalizations[mode] = {
                'amplitude_scale': scale,
                'normalized_burdens': {k: .01 for k in BURDENS},
                'source_output_RMS_by_output_mA': [.1, .2],
                'source_Vpp_per_output': scale,
                'regions': {region: {metric: {
                    'mean': 3.0, 'p10': 2.0, 'p95': 3.5, 'max': 4.0,
                    'CV': .1, 'p10_over_mean': 2 / 3, 'volume_m3': 1e-6,
                } for metric in METRICS} for region in REGIONS},
            }
        rows.append({
            'id': 'baseline' if i == 0 else 'layout-' + str(i),
            'label': '원래 기준' if i == 0 else 'Synthetic layout ' + str(i),
            'geometry_key': 'physical-geometry-' + str(i),
            'circuit': {'n_pads': pads, 'n_outputs': 2,
                        'n_return_nodes': 1, 'source_resistance_ohm': 50},
            'normalizations': normalizations,
            'ranking_score': [.1, .2], 'gate_checks': [],
        })
    catalog = {'schema': 'task1-top5-layout-catalog-v1',
               'canonical_baseline': rows[0], 'selected_layouts': rows[1:],
               'candidate_adopted': False}
    grid = {'x_edges_mm': [-25, -12.5, 0, 12.5, 25],
            'y_edges_mm': [-25, -12.5, 0, 12.5, 25],
            'z_faces_mm': [0, .1, 10.1, 25.1],
            'XY_actual_depths_mm': [5, 10, 15, 17.5, 20],
            'XZ_actual_y_mm': .3125, 'YZ_actual_x_mm': -.3125}
    cases = []
    for i, row in enumerate(rows):
        pads = row['circuit']['n_pads']
        # The last candidate is 250 mm² per pad, not the historical 225.
        area = 250 if i == 5 else 900 / pads
        cases.append({
            'id': row['id'], 'geometry_key': row['geometry_key'],
            'scales': scales.copy(),
            'pad_centres': [
                {'pad': p, 'node': 'out' + str(p) if p < 2 else 'GND',
                 'x_mm': float(p % 4), 'y_mm': float(p // 4), 'area_mm2': area}
                for p in range(pads)],
            'pad_mask_b64': encoded(list(range(pads)) + [-1] * (16 - pads), 'h'),
            'planes': {metric: {'xy': [encoded([1.] * 16) for _ in range(5)],
                               'xz': encoded([1.] * 12),
                               'yz': encoded([1.] * 12)} for metric in METRICS},
            'contact_J_RMS': {'values_b64': encoded([2.] * 16)},
        })
    display = {
        'schema': 'task1-top5-native-display-v1', 'no_new_PDE': True,
        'fieldunits': 'V/m', 'contactunits': 'A/m2', 'grid': grid, 'cases': cases,
        'color_limits': {mode: {metric: {'global': [0, 10], 'primary_ROI': [0, 4]}
                                for metric in METRICS} for mode in MODES},
        'contact_color_limits': {mode: [0, 20] for mode in MODES},
    }
    return catalog, display


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = []
        self.current_script = None
        self.external_resources = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'script':
            self.current_script = {'attrs': attrs, 'text': ''}
            self.scripts.append(self.current_script)
        if tag in ('script', 'iframe', 'img') and 'src' in attrs:
            self.external_resources.append(attrs['src'])
        if tag == 'link':
            self.external_resources.append(attrs.get('href'))

    def handle_data(self, data):
        if self.current_script is not None:
            self.current_script['text'] += data

    def handle_endtag(self, tag):
        if tag == 'script':
            self.current_script = None

    def payload(self):
        return json.loads(next(s['text'] for s in self.scripts
                               if s['attrs'].get('id') == 'data'))


class DashboardContracts(unittest.TestCase):
    def setUp(self):
        self.catalog, self.display = fixtures()

    def rejected(self):
        with self.assertRaises(ValueError):
            dashboard.validate_display(self.catalog, self.display)

    def add_outlines(self):
        case = self.display['cases'][0]
        case['physical_outlines'] = [
            {'pad': p['pad'], 'node': p['node'], 'area_mm2': p['area_mm2'],
             'polygon_mm': [[p['x_mm'], .123456789012345],
                            [p['x_mm'] + 1, .123456789012345],
                            [p['x_mm'] + 1, .5],
                            [p['x_mm'] + .5, .5],
                            [p['x_mm'] + .5, 1], [p['x_mm'], 1]]}
            for p in case['pad_centres']]
        return case

    def add_pad_count_reference(self):
        reference = {
            'source': {'path': '/synthetic/docs/pad-reference.json', 'SHA256': 'a' * 64},
            'scope': 'Synthetic separate strip family; fixed raw and skin8 only',
            'rows': [],
        }
        for i, pads in enumerate((4, 4, 8, 12, 16)):
            reference['rows'].append({
                'id': 'pad-reference-' + str(i), 'label': 'Reference ' + str(i),
                'n_pads': pads, 'n_outputs': 2,
                'return_topology': 'all_return_pads_ideal_common_GND',
                'normalizations': {mode: {
                    'mean_V_m': 3., 'P10_V_m': 2., 'source_Vpp_per_output': scale,
                    'normalized_burdens': {k: .01 for k in BURDENS},
                    'source_output_RMS_by_output_mA': [.1, .2],
                } for mode, scale in (('raw_1Vpp', 1.), ('skin_contact_only', .6))},
            })
        self.catalog['pad_count_reference'] = reference
        return reference

    def test_valid_six_layouts_with_all_five_modes(self):
        self.assertEqual(6, len(dashboard.validate_catalog(self.catalog)))
        self.assertEqual(6, len(dashboard.validate_display(self.catalog, self.display)))

    def test_1000_square_mm_contact_is_allowed(self):
        self.assertEqual(1000, sum(p['area_mm2'] for p in self.display['cases'][-1]['pad_centres']))
        dashboard.validate_display(self.catalog, self.display)

    def test_duplicate_geometry_including_baseline_is_rejected(self):
        self.catalog['selected_layouts'][0]['geometry_key'] = 'physical-geometry-0'
        self.rejected()

    def test_exactly_five_nonbaseline_layouts_required(self):
        self.catalog['selected_layouts'].pop()
        self.rejected()

    def test_duplicate_catalog_id_is_rejected(self):
        self.catalog['selected_layouts'][0]['id'] = 'baseline'
        self.rejected()

    def test_adoption_claim_is_rejected(self):
        self.catalog['candidate_adopted'] = True
        self.rejected()

    def test_physical_pads_do_not_create_more_outputs(self):
        self.catalog['selected_layouts'][3]['circuit']['n_outputs'] = 16
        self.rejected()

    def test_missing_saved_mode_or_burden_is_rejected(self):
        for key in ('mode', 'burden', 'metric', 'region'):
            with self.subTest(key=key):
                self.catalog, self.display = fixtures()
                modes = self.catalog['selected_layouts'][0]['normalizations']
                if key == 'mode': del modes['equal_total_power']
                elif key == 'burden': del modes['raw_1Vpp']['normalized_burdens'][BURDENS[0]]
                elif key == 'metric': del modes['raw_1Vpp']['regions'][PRIMARY]['RMS']
                else: del modes['raw_1Vpp']['regions']['primary_complement']
                self.rejected()

    def test_nonfinite_or_negative_authoritative_roi_stats_are_rejected(self):
        for value in (float('nan'), float('inf'), -1):
            with self.subTest(value=value):
                self.catalog, self.display = fixtures()
                self.catalog['canonical_baseline']['normalizations']['raw_1Vpp']['regions'][PRIMARY]['maxTIS']['mean'] = value
                self.rejected()

    def test_common_units_and_no_new_pde_are_required(self):
        for key, value in (('fieldunits', 'V/cm'), ('contactunits', 'mA/mm2'), ('no_new_PDE', False)):
            with self.subTest(key=key):
                self.catalog, self.display = fixtures(); self.display[key] = value
                self.rejected()

    def test_display_id_and_geometry_join_are_required(self):
        for key in ('id', 'geometry_key'):
            with self.subTest(key=key):
                self.catalog, self.display = fixtures()
                self.display['cases'][0][key] = 'other'
                self.rejected()

    def test_duplicate_display_id_is_rejected(self):
        self.display['cases'][1]['id'] = 'baseline'; self.rejected()

    def test_every_scale_is_exact_saved_value(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                self.catalog, self.display = fixtures()
                self.display['cases'][0]['scales'][mode] += 1e-12
                self.rejected()
        self.catalog, self.display = fixtures()
        del self.display['cases'][0]['scales']['equal_total_power']; self.rejected()

    def test_native_edges_must_be_finite_and_strictly_ascending(self):
        for edge in ('x_edges_mm', 'y_edges_mm', 'z_faces_mm'):
            with self.subTest(edge=edge):
                self.catalog, self.display = fixtures()
                self.display['grid'][edge][1] = self.display['grid'][edge][0]
                self.rejected()

    def test_actual_depth_count_and_range_are_checked(self):
        for depths in ([5, 10, 15, 20], [5, 10, 15, 20, 26]):
            with self.subTest(depths=depths):
                self.display['grid']['XY_actual_depths_mm'] = depths
                self.rejected()

    def test_float32_plane_shape_counts_are_checked(self):
        for axis in ('xy', 'xz', 'yz'):
            with self.subTest(axis=axis):
                self.catalog, self.display = fixtures()
                plane = self.display['cases'][0]['planes']['maxTIS']
                if axis == 'xy': plane[axis][0] = encoded([1.] * 15)
                else: plane[axis] = encoded([1.] * 11)
                self.rejected()

    def test_int16_pad_mask_and_contact_grid_byte_counts_are_checked(self):
        for kind in ('mask', 'contact'):
            with self.subTest(kind=kind):
                self.catalog, self.display = fixtures()
                case = self.display['cases'][0]
                if kind == 'mask': case['pad_mask_b64'] = encoded([0] * 15, 'h')
                else: case['contact_J_RMS']['values_b64'] = encoded([1.] * 15)
                self.rejected()

    def test_mask_requires_known_pad_or_negative_one(self):
        for pad in (-2, 4):
            with self.subTest(pad=pad):
                self.display['cases'][0]['pad_mask_b64'] = encoded([pad] * 16, 'h')
                self.rejected()

    def test_pad_identity_and_role_are_checked(self):
        for key, value in (('pad', 10), ('node', 'out3'), ('area_mm2', 0)):
            with self.subTest(key=key):
                self.catalog, self.display = fixtures()
                self.display['cases'][0]['pad_centres'][0][key] = value
                self.rejected()

    def test_invalid_base64_is_rejected(self):
        self.display['cases'][0]['planes']['maxTIS']['xy'][0] = '!invalid!'
        self.rejected()

    def test_all_modes_require_shared_zero_based_positive_color_limits(self):
        for mode in MODES:
            for bounds in ([1, 4], [0, 0], [0, float('inf')]):
                with self.subTest(mode=mode, bounds=bounds):
                    self.catalog, self.display = fixtures()
                    self.display['color_limits'][mode]['RMS']['primary_ROI'] = bounds
                    self.rejected()
        self.catalog, self.display = fixtures()
        del self.display['contact_color_limits']['equal_total_power']; self.rejected()

    def test_display_nan_remains_unsupported_not_numeric_zero(self):
        self.display['cases'][0]['planes']['maxTIS']['xy'][0] = encoded([float('nan')] + [1.] * 15)
        dashboard.validate_display(self.catalog, self.display)

    def test_render_escapes_script_breakout_and_is_self_contained(self):
        label = '</script><img src=x onerror=alert(1)> & 한국\u2028\u2029'
        self.catalog['selected_layouts'][0]['label'] = label
        with tempfile.TemporaryDirectory() as tmp:
            result = dashboard.render(self.catalog, self.display, Path(tmp) / 'out.html')
        page = Page(); page.feed(result)
        self.assertEqual(2, len(page.scripts))
        self.assertEqual([], page.external_resources)
        self.assertEqual(label, page.payload()['catalog']['selected_layouts'][0]['label'])
        self.assertNotIn('</script><img', result)
        self.assertIn('\\u003c/script', result)
        script = next(s['text'] for s in page.scripts if s['attrs'].get('id') != 'data')
        self.assertNotIn('fetch(', script)
        self.assertNotIn('XMLHttpRequest', script)
        self.assertIn('window.task1Top5=', script)
        self.assertTrue({'mode', 'metric', 'plane', 'depth', 'range', 'field-legend',
                         'contact-legend', 'mode-note', 'cards'} <= page.ids)

    def test_render_is_memory_only_and_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.catalog, self.display))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'never-created.html'
            with mock.patch('builtins.open', side_effect=AssertionError('file opened')), \
                 mock.patch.object(Path, 'open', side_effect=AssertionError('file opened')), \
                 mock.patch.object(Path, 'write_text', side_effect=AssertionError('file written')), \
                 mock.patch.object(Path, 'write_bytes', side_effect=AssertionError('file written')):
                result = dashboard.render(self.catalog, self.display, output)
            self.assertTrue(result.startswith('<!doctype html>'))
            self.assertEqual([], list(Path(tmp).iterdir()))
        self.assertEqual(before, (self.catalog, self.display))

    def test_nonuniform_native_edges_and_all_mode_controls_are_embedded_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = dashboard.render(self.catalog, self.display, Path(tmp) / 'out.html')
        page = Page(); page.feed(result); payload = page.payload()
        self.assertEqual([0, .1, 10.1, 25.1], payload['display']['grid']['z_faces_mm'])
        self.assertEqual(6, len(payload['display']['cases']))
        for case in payload['display']['cases']:
            self.assertEqual(set(MODES), set(case['scales']))
        # Source contract: the vertical drawing uses physical edges for every
        # cell rectangle, not an assumed uniform layer thickness.
        script = next(s['text'] for s in page.scripts if s['attrs'].get('id') != 'data')
        self.assertIn('grid.z_faces_mm', script)
        self.assertIn('Y(ye[j+1])', script)
        self.assertIn('v.getFloat32(i*4,true)', script)
        self.assertIn('v.getInt16(i*2,true)', script)

    def test_optional_physical_polygons_preserve_vertices_order_and_area_metadata(self):
        case = self.add_outlines()
        case['physical_outlines'].reverse()
        # Role aliases are semantic, and metadata is authoritative here. The
        # deliberately small synthetic polygon is not an area reconstruction
        # request; the renderer must not replace its declared 225 mm² value.
        next(p for p in case['physical_outlines'] if p['pad'] == 0)['node'] = 0
        before = copy.deepcopy(case['physical_outlines'])
        dashboard.validate_display(self.catalog, self.display)
        with tempfile.TemporaryDirectory() as tmp:
            result = dashboard.render(self.catalog, self.display, Path(tmp) / 'out.html')
        page = Page(); page.feed(result)
        self.assertEqual(before, page.payload()['display']['cases'][0]['physical_outlines'])
        self.assertEqual(before, case['physical_outlines'])
        self.assertIn("geometryMethod='exact_physical_polygons'", result)
        self.assertIn('c.lineTo(X(x),Y(y))', result)

    def test_optional_outlines_reject_duplicate_pad_identity(self):
        case = self.add_outlines()
        case['physical_outlines'][1]['pad'] = 0
        self.rejected()

    def test_optional_outlines_reject_nonfinite_or_malformed_vertices(self):
        bad = ([[0, 0], [1, 0]],
               [[0, 0], [1, 0], [1, float('nan')]],
               [[0, 0], [1, 0], [float('inf'), 1]],
               [[0, 0], [1, 0], [1, '1']],
               [[0, 0], [1, 0], [1, 1, 2]])
        for polygon in bad:
            with self.subTest(polygon=polygon):
                self.catalog, self.display = fixtures()
                case = self.add_outlines()
                case['physical_outlines'][0]['polygon_mm'] = polygon
                self.rejected()

    def test_optional_outlines_reject_role_or_area_metadata_mismatch(self):
        for key, value in (('node', 'out1'), ('area_mm2', 226)):
            with self.subTest(key=key):
                self.catalog, self.display = fixtures()
                case = self.add_outlines()
                case['physical_outlines'][0][key] = value
                self.rejected()

    def test_no_outline_export_keeps_explicit_native_cell_fallback_and_contact_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = dashboard.render(self.catalog, self.display, Path(tmp) / 'out.html')
        page = Page(); page.feed(result)
        self.assertTrue(all('physical_outlines' not in c
                            for c in page.payload()['display']['cases']))
        self.assertIn("geometryMethod='native_cell_mask_partial_contact_cell_display'", result)
        self.assertIn('부분접촉은 셀로 표시', result)
        self.assertIn('부분접촉면은 해당 native 셀로 표시', result)
        self.assertIn('정확 형상은 배치 윤곽', result)

    def test_optional_pad_count_reference_preserves_fixed_raw_skin8_and_source_receipt(self):
        reference = copy.deepcopy(self.add_pad_count_reference())
        dashboard.validate_display(self.catalog, self.display)
        with tempfile.TemporaryDirectory() as tmp:
            result = dashboard.render(self.catalog, self.display, Path(tmp) / 'out.html')
        page = Page(); page.feed(result)
        self.assertEqual(reference, page.payload()['catalog']['pad_count_reference'])
        self.assertEqual(reference, self.catalog['pad_count_reference'])
        self.assertIn('pad-count-reference', page.ids)
        self.assertIn('raw 평균 V/m', result)
        self.assertIn('skin8 평균 V/m', result)
        self.assertIn('위 정규화 선택과 독립', result)
        self.assertIn(reference['source']['SHA256'], result)
        # No-reference catalogs remain valid and must not fabricate this family.
        del self.catalog['pad_count_reference']
        with tempfile.TemporaryDirectory() as tmp:
            fallback = dashboard.render(self.catalog, self.display, Path(tmp) / 'out.html')
        empty_page = Page(); empty_page.feed(fallback)
        self.assertNotIn('pad_count_reference', empty_page.payload()['catalog'])
        self.assertIn('별도 strip 가족의 수치 영수증이 제공되지 않았습니다', fallback)

    def test_optional_pad_count_reference_rejects_extra_outputs_wrong_pads_or_return(self):
        for key, value in (('n_outputs', 4), ('n_pads', 7),
                           ('return_topology', 'independent_returns')):
            with self.subTest(key=key):
                self.catalog, self.display = fixtures()
                reference = self.add_pad_count_reference()
                reference['rows'][-1][key] = value
                self.rejected()


if __name__ == '__main__':
    unittest.main()
