"""Synthetic JSON proof fixtures; no existing artifacts, GUI, native or ledger."""
import base64
import copy
import gzip
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_top5_final_verify as verify


class FinalVerifyTest(unittest.TestCase):
    def fixture(self):
        stats = dict(mean=1., p10=.5, max=2., volume_m3=1e-6)
        rows, cases = [], []
        for i in range(6):
            modes = {mode: dict(regions={region: {metric: dict(stats) for metric in verify.METRICS}
                for region in (verify.PRIMARY, 'total')}, normalized_burdens={key: 2. for key in verify.J_KEYS}) for mode in verify.MODES}
            row = dict(id='row'+str(i), normalizations=modes, electrical_metrics={key: 2. for key in verify.J_KEYS})
            rows.append(row)
            checks = [dict(mode=mode, metric=key, passed=True, saved_A_m2=2., actual_A_m2=2.)
                      for mode in ('raw', *verify.MODES) for key in verify.J_KEYS]
            cases.append(dict(id=row['id'], native_stats_proofs={metric: dict(passed=True, saved=dict(stats), actual=dict(stats))
                for metric in verify.METRICS}, contact_J_RMS=dict(regression=dict(passed=True, checks=checks,
                    relative_tolerance=2e-7, absolute_tolerance_A_m2=1e-14))))
        catalog = dict(canonical_baseline=rows[0], selected_layouts=rows[1:], unchanged_rank=[1, 2, 3, 4, 5])
        rendered = copy.deepcopy(catalog)
        rendered['_ui_pad_count_source'] = '../source.json'
        for row in [rendered['canonical_baseline'], *rendered['selected_layouts']]:
            row['_ui_links'] = {'source': '../source.json'}
        display = dict(cases=cases, color_limits={mode: {metric: {'global': [0., 2.], 'primary_ROI': [0., 2.]}
            for metric in verify.METRICS} for mode in verify.MODES}, contact_color_limits={mode: [0., 2.] for mode in verify.MODES})
        payload = dict(catalog=rendered, display=display)
        manifest = dict(status='compact_dashboard_complete_unadopted', source_HTML={'SHA256': 'old'},
            candidate_adopted=False, full_convergence_validated=False, experimentally_validated=False,
            contact_regression={c['id']: copy.deepcopy(c['contact_J_RMS']['regression']) for c in cases},
            native_scalar_primary_proofs={c['id']: copy.deepcopy(c['native_stats_proofs']) for c in cases})
        return payload, manifest, {'catalog': catalog}, {'source_HTML_SHA256': 'old'}

    def run_fixture(self, payload, manifest, plan, diagnostic):
        encoded = base64.b64encode(gzip.compress(json.dumps(payload).encode(), mtime=0)).decode()
        html = '<script id="packed" type="application/octet-stream">'+encoded+'</script>'
        return verify.verify_payload(html, manifest, plan, diagnostic)

    def test_exact_seven_renderer_keys_only_and_all_72_plus_18_proofs(self):
        fixture = self.fixture()
        before = copy.deepcopy(fixture)
        _, receipt = self.run_fixture(*fixture)
        self.assertEqual(72, receipt['contact_checks_passed'])
        self.assertEqual(18, receipt['scalar_proofs_passed'])
        self.assertEqual(7, len(receipt['ignored_renderer_only_paths']))
        self.assertEqual(before, fixture)
        self.assertFalse(receipt['display_arrays_decoded'])

    def test_unknown_ui_key_or_changed_scientific_value_cannot_be_stripped(self):
        for kind in ('unknown_UI', 'scientific_value'):
            data, manifest, plan, diagnostic = self.fixture()
            if kind == 'unknown_UI':
                data['catalog']['_ui_hide_bad_rank'] = True
            else:
                data['catalog']['unchanged_rank'][0] = 99
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'seven renderer'):
                self.run_fixture(data, manifest, plan, diagnostic)

    def test_pass_flag_does_not_replace_contact_or_scalar_actual_regression(self):
        for kind in ('scalar', 'contact', 'duplicate_contact'):
            data, manifest, plan, diagnostic = self.fixture()
            case = data['display']['cases'][0]
            if kind == 'scalar':
                case['native_stats_proofs']['maxTIS']['actual']['mean'] = 9.
                manifest['native_scalar_primary_proofs'][case['id']] = copy.deepcopy(case['native_stats_proofs'])
            else:
                regression = case['contact_J_RMS']['regression']
                if kind == 'contact':
                    regression['checks'][0]['actual_A_m2'] = 99.
                else:
                    regression['checks'][0] = copy.deepcopy(regression['checks'][1])
                manifest['contact_regression'][case['id']] = copy.deepcopy(regression)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.run_fixture(data, manifest, plan, diagnostic)

    def test_aggregate_rss_keeps_only_startticks_proven_live_descendants(self):
        with mock.patch.object(verify.bounded, 'owned_descendants', return_value={1: 10, 2: 20, 3: 30}), \
             mock.patch.object(verify.bounded, 'live', side_effect=lambda pid, ticks: pid != 3), \
             mock.patch.object(verify.bounded, 'rss', side_effect=lambda pid: pid*100):
            rss, live = verify.aggregate_rss(1, 10, {})
        self.assertEqual(300, rss)
        self.assertEqual({1: 10, 2: 20}, live)


if __name__ == '__main__':
    unittest.main()
