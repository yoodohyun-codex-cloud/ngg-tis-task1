"""Synthetic-only centred-y0 wrapper tests; no result data or native reads."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


dashboard = module('synthetic_centered_dashboard', Path(__file__).with_name('centered_dashboard.py'))
fixtures = module('synthetic_pair_fixtures',
                  '/workspace/ngg-tis-task1/tests/test_task1_best1_pair_dashboard.py')


def fixture():
    payload = fixtures.fixture()
    analysis = payload['analysis']
    analysis.update(status='calculated_unadopted', new_PDE=1, new_native_RHS=1,
                    full_convergence_validated=False)
    analysis['single_pair'].update(case_id='centered-square15-C1-y0-xy80-f3000',
                                  frequency_Hz=3000,
                                  physical_pad_centres_mm=[[-10, 0], [10, 0]])
    for pad in payload['spatial']['C1']['pad_centres']:
        pad['y_mm'] = 0
    for outline in payload['spatial']['C1']['physical_outlines']:
        for point in outline['polygon_mm']:
            point[1] += 10
    old = {'required_source_Vpp': 1.625, 'source_current_RMS_mA': .625,
           'burdens': {k: .011 for k in dashboard.base.BURDENS},
           'shape_comparison': {'weighted_RMS_difference_V_m': .123}}
    new = {'required_source_Vpp': 1.375, 'source_current_RMS_mA': .525,
           'burdens': {k: .022 for k in dashboard.base.BURDENS},
           'shape_comparison': {'weighted_RMS_difference_V_m': .087}}
    # Deliberately independent sentinel deltas verify display of source-provided
    # relative_change rather than a new ratio calculation in this pure wrapper.
    changes = {'required_source_Vpp': .01234, 'source_current_RMS_mA': -.2345,
               'burdens': {k: .25 for k in dashboard.base.BURDENS}}
    payload['offcenter_comparison'] = {
        'schema': 'synthetic-centered-offcenter-v1',
        'old_case_id': 'baseline-square15-C1pair0-xy80',
        'new_case_id': 'centered-square15-C1-y0-xy80-f3000',
        'old_centres_mm': [[-10, -10], [10, -10]],
        'new_centres_mm': [[-10, 0], [10, 0]],
        'modes': {'skin_contact_only': {'ROI_energy_RMS': {
            'old': old, 'new': new, 'relative_change': changes}}},
    }
    payload['spatial']['proofs'] = {
        'raw_RMS_global_max': {
            'C1': {'value_V_m': 17.125, 'center_xyz_mm': [-10, 0, .025],
                   'layer_index': 0, 'layer': 'stratum_corneum'},
            'TIS': {'value_V_m': 21.125, 'center_xyz_mm': [-10, -10, .025],
                    'layer_index': 0, 'layer': 'stratum_corneum'}},
        'contact_Jmax': {'C1': {'value_A_m2': 31.25, 'center_xyz_mm': [-10, 0, 0],
                               'layer': 'contact'}},
        'bulk_skin_Jmax': {'C1': {'value_A_m2': 29.5, 'center_xyz_mm': [-10, 0, .025],
                                 'layer': 'stratum_corneum'}},
    }
    return payload


class Page(fixtures.Page):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if tag == 'table': self.table = []
        if tag == 'tr': self.row = []
        if tag in ('td', 'th'): self.cell = []

    def handle_data(self, data):
        super().handle_data(data)
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell)); self.cell = None
        if tag == 'tr' and self.row is not None:
            self.table.append(self.row); self.row = None
        if tag == 'table' and self.table is not None:
            self.tables.append(self.table); self.table = None


class CenteredDashboard(unittest.TestCase):
    def setUp(self):
        self.payload = fixture()

    def rejected(self):
        with self.assertRaises(ValueError):
            dashboard.validate(self.payload)

    def test_actual_centered_case_contract_is_accepted(self):
        self.assertIs(self.payload, dashboard.validate(self.payload))
        page = Page(); page.feed(dashboard.render(self.payload))
        self.assertEqual(['TIS', 'C1'], page.cards)
        self.assertTrue({'offcenter-fixed-comparison', 'centered-raw-hotspots'} <= page.ids)

    def test_active_script_csp_and_packed_data_remain_frozen(self):
        base = Page(); base.feed(dashboard.base.render(self.payload))
        centered = Page(); centered.feed(dashboard.render(self.payload))
        self.assertEqual(base.scripts, centered.scripts)
        self.assertEqual(base.metas, centered.metas)
        self.assertEqual(self.payload, centered.unpack())
        self.assertEqual(dashboard.base.SCRIPT, centered.scripts[1]['text'])

    def test_old_y_minus10_analysis_display_or_outline_cannot_be_relabelled(self):
        for location in ('analysis', 'display', 'outline'):
            with self.subTest(location=location):
                self.payload = fixture()
                if location == 'analysis':
                    self.payload['analysis']['single_pair']['physical_pad_centres_mm'] = [[-10, -10], [10, -10]]
                elif location == 'display':
                    self.payload['spatial']['C1']['pad_centres'][0]['y_mm'] = -10
                else:
                    for point in self.payload['spatial']['C1']['physical_outlines'][0]['polygon_mm']:
                        point[1] -= 10
                self.rejected()

    def test_old_alias_or_wrong_new_pde_rhs_or_adoption_status_is_rejected(self):
        for key, value in (('new_PDE', 0), ('new_native_RHS', 0),
                           ('status', 'prepared'), ('full_convergence_validated', True)):
            with self.subTest(key=key):
                self.payload = fixture(); self.payload['analysis'][key] = value
                self.rejected()
        self.payload = fixture()
        self.payload['analysis']['single_pair']['case_id'] = dashboard.OLD_ID
        self.rejected()

    def test_fixed_skin8_roi_table_displays_stored_values_and_signed_changes(self):
        page = Page(); page.feed(dashboard.render(self.payload))
        rows = page.tables[0]
        self.assertEqual(['1.625', '1.375', '1.234 %'], rows[1][1:])
        self.assertEqual(['0.625', '0.525', '-23.45 %'], rows[2][1:])
        self.assertEqual(['0.011', '0.022', '25 %'], rows[3][1:])
        self.assertEqual(12, len(rows))  # header + source/current + nine burdens
        self.assertIn('위 선택을 바꿔도 변하지 않습니다', dashboard.render(self.payload))

    def test_memory_only_no_mutation(self):
        before = copy.deepcopy(self.payload)
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch('builtins.open', side_effect=AssertionError('I/O forbidden')), \
                 mock.patch.object(Path, 'open', side_effect=AssertionError('I/O forbidden')), \
                 mock.patch.object(Path, 'write_text', side_effect=AssertionError('I/O forbidden')), \
                 mock.patch.object(Path, 'write_bytes', side_effect=AssertionError('I/O forbidden')):
                dashboard.render(self.payload)
            self.assertEqual([], list(Path(tmp).iterdir()))
        self.assertEqual(before, self.payload)

    def test_hotspots_prose_and_html_escaping_do_not_promote_safety_or_convergence(self):
        marker = '</script><img src=x onerror=alert(1)>'
        self.payload['spatial']['proofs']['contact_Jmax']['C1']['layer'] = marker
        result = dashboard.render(self.payload)
        page = Page(); page.feed(result)
        self.assertEqual([], page.resources)
        self.assertEqual(2, len(page.scripts))
        self.assertNotIn(marker, result)
        self.assertIn('&lt;/script&gt;', result)
        self.assertIn('17.125 V/m', result)
        self.assertIn('31.25 A/m²', result)
        self.assertIn('실제 신규1조건/3000Hz1주파수/1출력/1RHS', result)
        self.assertIn('native PDE1조건·1RHS가 실제 완료', result)
        self.assertNotIn('신규 PDE는 수행하지 않습니다.', result)
        self.assertIn('RMS 일치는 형상·전류·표면 부담·생리적 효과의 동등성이 아닙니다', result)
        self.assertIn('전체 수렴·실험·채택은 미검증', result)

    def test_previous_gui_is_explicit_or_unavailable_and_unsafe_href_is_rejected(self):
        result = dashboard.render(self.payload)
        self.assertIn('과거y=−10 GUI 링크는 이payload에 미제공', result)
        self.payload['provenance']['previous_GUI'] = {'href': 'javascript:alert(1)'}
        with self.assertRaises(ValueError):
            dashboard.render(self.payload)


if __name__ == '__main__':
    unittest.main()
