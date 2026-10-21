"""Scientific plot-cache provenance tests; tiny PNG fixtures, no render or solve."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image


TOOLS = Path(__file__).resolve().parents[1] / 'tools'
SPEC = importlib.util.spec_from_file_location('task1_results_view_cache_tested', TOOLS / 'task1_results_view.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def payload():
    rows = []
    for name, digest, scale in [('baseline-square_3h', 'a' * 64, 1.),
                                ('candidate-square_3h', 'b' * 64, .5)]:
        values = dict(amplitude_scale=scale, ROI_mean_V_cm=.02 * scale)
        rows.append(dict(condition_id=name, summary_sha256=digest,
            comparison_signature='c' * 64, n_outputs=2,
            values=dict(raw=dict(amplitude_scale=1., ROI_mean_V_cm=.02),
                        composite_full_skin=values)))
    return dict(schema='task1_offline_result_comparison_v1',
        generator_sha256='d' * 64,
        definitions=dict(target='r<=5 mm, surface depth15–20 mm volume',
            maxTIS='fundamental-only sampled-direction max',
            RMS='complete-harmonic vector RMS',
            display_supplements=dict(shared_log_floor_V_cm=.0001,
                fixed_ROI_linear_limits_V_cm=[0., .1])),
        conditions=rows)


def map_identity(value):
    return dict(contract='native-phi-scientific-plot-v1', family='maps',
        cohort_signature='c' * 64, mode='composite_full_skin',
        metric='square_maxTIS_V_m', supplement=False, units='V/cm',
        clims=dict(shared_linear=[0., .04]),
        conditions=[dict(condition_id=row['condition_id'],
            summary_sha256=row['summary_sha256'],
            comparison_signature=row['comparison_signature'],
            normalization_values=copy.deepcopy(row['values']['composite_full_skin']),
            source_map_sha256='e' * 64, row_label=row['condition_id'])
            for row in value['conditions']],
        ROI=dict(radius_mm=5, depth_mm=[15, 20]))


class PlotCacheTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.old, self.new = self.root / 'completed', self.root / 'new'
        self.old.mkdir()
        self.new.mkdir()
        self.payload = payload()
        self.identity = map_identity(self.payload)
        self.name = 'grid-1-cccccccc-composite_full_skin-square_maxTIS_V_m.png'
        self.source = self.old / self.name
        Image.new('RGB', (2, 2), color=(17, 31, 47)).save(self.source, format='PNG')

    def manifest(self):
        manifest = dict(schema='task1-offline-evidence-bundle-v1', assets={
            path.name: dict(SHA256=M.sha(path), bytes=path.stat().st_size)
            for path in self.old.iterdir() if path.is_file()
            and path.name not in ('asset-manifest.json', 'render-receipt.json')})
        (self.old / 'asset-manifest.json').write_text(json.dumps(manifest))
        self.terminal()
        return manifest

    def terminal(self, status='rendered_offline_evidence', manifest_sha=None):
        value = dict(status=status, asset_manifest=dict(SHA256=manifest_sha
            if manifest_sha is not None else M.sha(self.old / 'asset-manifest.json')))
        (self.old / 'render-receipt.json').write_text(json.dumps(value))

    def fixture(self, receipt=True, manifest=True):
        (self.old / 'comparison.json').write_text(json.dumps(self.payload))
        if receipt:
            M.PlotCache(self.old, [], self.payload).record(self.source, self.identity)
        if manifest:
            self.manifest()

    def cache(self, current=None):
        return M.PlotCache(self.new, [self.old], self.payload if current is None else current)

    def assert_rejected(self, identity=None, current=None):
        cache = self.cache(current)
        self.assertIsNone(cache.reuse(self.name, self.identity if identity is None else identity))
        self.assertFalse((self.new / self.name).exists())
        self.assertEqual(cache.reused, 0)
        return cache

    def test_exact_signed_cache_copies_and_records_new_provenance_preserving_source(self):
        self.fixture()
        before = {path.name: path.read_bytes() for path in self.old.iterdir()}
        cache = self.cache()
        target = cache.reuse(self.name, self.identity)
        self.assertEqual(target, self.new / self.name)
        self.assertEqual(target.read_bytes(), before[self.name])
        self.assertEqual(cache.reused, 1)
        self.assertEqual(cache.generated, 0)
        receipt = json.loads(target.with_suffix('.plot.json').read_text())
        self.assertEqual(receipt['image_sha256'], M.sha(target))
        self.assertEqual(receipt['plot_identity_sha256'], M.identity_sha(self.identity))
        self.assertEqual(receipt['plot_identity'], self.identity)
        self.assertEqual(receipt['source_asset']['path'], str(self.source))
        self.assertEqual(receipt['source_asset']['source_manifest_sha256'], M.sha(self.old / 'asset-manifest.json'))
        self.assertEqual(receipt['source_asset']['source_comparison_sha256'], M.sha(self.old / 'comparison.json'))
        self.assertEqual(receipt['source_asset']['admission'], 'exact_per_PNG_identity_and_asset_SHA')
        self.assertEqual({path.name: path.read_bytes() for path in self.old.iterdir()}, before)

    def test_record_fresh_png_has_identity_and_never_claims_numeric_validation(self):
        cache = M.PlotCache(self.old, [], self.payload)
        self.assertEqual(cache.record(self.source, self.identity), self.source)
        receipt = json.loads(self.source.with_suffix('.plot.json').read_text())
        self.assertIsNone(receipt['source_asset'])
        self.assertEqual(cache.generated, 1)
        self.assertIn('not numerical convergence or experimental validation', receipt['meaning'])

    def test_signed_identity_rejects_changed_summary_cohort_scale_and_color_limits(self):
        self.fixture()
        variants = []
        value = copy.deepcopy(self.identity)
        value['conditions'][1]['summary_sha256'] = 'f' * 64
        variants.append(value)
        value = copy.deepcopy(self.identity)
        value['conditions'].reverse()
        variants.append(value)
        value = copy.deepcopy(self.identity)
        value['conditions'][1]['normalization_values']['amplitude_scale'] = .6
        variants.append(value)
        value = copy.deepcopy(self.identity)
        value['clims']['shared_linear'][1] = .08
        variants.append(value)
        value = copy.deepcopy(self.identity)
        value['metric'] = 'square_RMS_V_m'
        variants.append(value)
        for identity in variants:
            with self.subTest(identity=identity):
                self.assert_rejected(identity)

    def test_signed_receipt_must_itself_match_source_asset_manifest(self):
        self.fixture()
        path = self.source.with_suffix('.plot.json')
        path.write_text(path.read_text() + ' ')
        self.assert_rejected()

    def test_identity_body_must_match_its_stored_hash(self):
        self.fixture()
        path = self.source.with_suffix('.plot.json')
        value = json.loads(path.read_text())
        value['plot_identity']['conditions'][0]['summary_sha256'] = '0' * 64
        path.write_text(json.dumps(value))
        self.manifest()
        self.assert_rejected()

    def test_png_bytes_must_match_source_asset_hash(self):
        self.fixture()
        Image.new('RGB', (2, 2), color=(255, 0, 0)).save(self.source, format='PNG')
        cache = self.assert_rejected()
        self.assertIn('PNG_asset_SHA_or_size_mismatch', [r['reason'] for r in cache.rejected])

    def test_matching_hash_does_not_admit_undecodable_png(self):
        self.fixture()
        self.source.write_bytes(b'not a PNG despite its file suffix')
        path = self.source.with_suffix('.plot.json')
        receipt = json.loads(path.read_text())
        receipt['image_sha256'] = M.sha(self.source)
        receipt['bytes'] = self.source.stat().st_size
        path.write_text(json.dumps(receipt))
        self.manifest()
        cache = self.assert_rejected()
        self.assertIn('PNG_decode_failed', [r['reason'] for r in cache.rejected])

    def test_partial_failed_cache_without_manifest_is_rejected(self):
        self.fixture(manifest=False)
        (self.old / 'render-failure.json').write_text('{"status":"failed"}')
        cache = self.assert_rejected()
        self.assertIn('completed_asset_or_comparison_manifest_missing', [r['reason'] for r in cache.rejected])

    def test_manifest_without_terminal_render_receipt_is_rejected(self):
        self.fixture()
        (self.old / 'render-receipt.json').unlink()
        self.assert_rejected()

    def test_noncomplete_terminal_status_is_rejected(self):
        self.fixture()
        self.terminal(status='failed')
        self.assert_rejected()

    def test_terminal_receipt_must_reference_current_manifest_hash(self):
        self.fixture()
        self.terminal(manifest_sha='0' * 64)
        self.assert_rejected()

    def test_failure_marker_rejects_even_an_otherwise_valid_terminal_receipt(self):
        self.fixture()
        (self.old / 'render-failure.json').write_text('{"status":"failed"}')
        self.assert_rejected()

    def test_comparison_bytes_must_match_source_manifest(self):
        self.fixture()
        path = self.old / 'comparison.json'
        path.write_text(path.read_text() + ' ')
        cache = self.assert_rejected()
        self.assertIn('comparison_manifest_SHA_mismatch', [r['reason'] for r in cache.rejected])

    def test_missing_comparison_or_manifest_entry_rejects_even_signed_png(self):
        self.fixture()
        path = self.old / 'comparison.json'
        path.unlink()
        self.assert_rejected()

    def test_legacy_exact_order_summary_scale_and_definitions_can_be_reused(self):
        self.fixture(receipt=False)
        cache = self.cache()
        target = cache.reuse(self.name, self.identity)
        self.assertEqual(target.read_bytes(), self.source.read_bytes())
        receipt = json.loads(target.with_suffix('.plot.json').read_text())
        self.assertEqual(receipt['source_asset']['admission'],
            'legacy_v1_exact_cohort_summary_normalization_and_clim_contract')

    def test_legacy_rejects_added_removed_or_reordered_cohort(self):
        self.fixture(receipt=False)
        for count in ('added', 'removed', 'reordered'):
            identity = copy.deepcopy(self.identity)
            if count == 'added':
                identity['conditions'].append(dict(identity['conditions'][0], condition_id='new-square_3h'))
            elif count == 'removed':
                identity['conditions'].pop()
            else:
                identity['conditions'].reverse()
            with self.subTest(change=count):
                self.assert_rejected(identity)

    def test_legacy_rejects_changed_summary_or_normalization(self):
        self.fixture(receipt=False)
        for field, value in [('summary_sha256', '9' * 64),
                             ('normalization_values', dict(amplitude_scale=.25, ROI_mean_V_cm=.005))]:
            identity = copy.deepcopy(self.identity)
            identity['conditions'][1][field] = value
            with self.subTest(field=field):
                self.assert_rejected(identity)

    def test_legacy_rejects_changed_roi_and_metric_definitions(self):
        self.fixture(receipt=False)
        for key in ('target', 'maxTIS', 'RMS'):
            current = copy.deepcopy(self.payload)
            current['definitions'][key] = 'changed physical definition'
            with self.subTest(key=key):
                self.assert_rejected(current=current)

    def test_legacy_supplement_rejects_changed_display_definitions(self):
        self.fixture(receipt=False)
        identity = copy.deepcopy(self.identity)
        identity['supplement'] = True
        current = copy.deepcopy(self.payload)
        current['definitions']['display_supplements']['shared_log_floor_V_cm'] = .001
        self.assert_rejected(identity, current)

    def test_legacy_waveform_uses_same_summary_and_target_definition(self):
        self.identity = dict(family='waveform', conditions=[{
            key: self.identity['conditions'][0][key]
            for key in ('condition_id', 'summary_sha256', 'comparison_signature')}],
            probe_id='center-depth20-x', tip_spacing_mm=5)
        self.fixture(receipt=False)
        target = self.cache().reuse(self.name, self.identity)
        self.assertEqual(target.read_bytes(), self.source.read_bytes())
        self.assertEqual(json.loads(target.with_suffix('.plot.json').read_text())['plot_identity'], self.identity)

    def test_legacy_waveform_rejects_changed_summary_or_target(self):
        self.identity = dict(family='waveform', conditions=[{
            key: self.identity['conditions'][0][key]
            for key in ('condition_id', 'summary_sha256', 'comparison_signature')}])
        self.fixture(receipt=False)
        identity = copy.deepcopy(self.identity)
        identity['conditions'][0]['summary_sha256'] = '8' * 64
        self.assert_rejected(identity)
        current = copy.deepcopy(self.payload)
        current['definitions']['target'] = 'all-XY slab rather than original central ROI'
        self.assert_rejected(current=current)

    def test_missing_png_manifest_entry_rejects(self):
        self.fixture()
        path = self.old / 'asset-manifest.json'
        manifest = json.loads(path.read_text())
        del manifest['assets'][self.name]
        path.write_text(json.dumps(manifest))
        self.terminal()
        self.assert_rejected()

    def test_cache_never_overwrites_an_existing_target(self):
        self.fixture()
        target = self.new / self.name
        target.write_bytes(b'preserve existing evidence')
        with self.assertRaises(FileExistsError):
            self.cache().reuse(self.name, self.identity)
        self.assertEqual(target.read_bytes(), b'preserve existing evidence')


if __name__ == '__main__':
    unittest.main()
