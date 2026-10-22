"""Targeted cached-ranking tests with synthetic, verified-loader fixtures only."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location('task1_candidate_ranking_tested', TOOLS/'task1_candidate_ranking.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def row(case='candidate', mean=10., p10=5., superficial=20., off=15., maximum=100., scale=1.):
    values = dict(ROI_mean_V_cm=mean, ROI_P10_V_cm=p10, superficial_P95_V_cm=superficial,
        off_target_P95_V_cm=off, global_max_V_cm=maximum, amplitude_scale=scale,
        max_source_current_RMS_mA=2., **{key: 1. for key in M.BURDEN_KEYS})
    raw = {key: value for key, value in values.items()}
    raw['ROI_mean_V_cm'] /= scale
    raw['ROI_P10_V_cm'] /= scale
    return dict(case_id=case, condition_id=case+'-square_3h', run_id='synthetic', comparison_signature='coarse',
        mesh=dict(h_xy_mm=1.25), values=dict(raw=raw, composite_full_skin=values),
        spatial=dict(high_modulation={key: dict(cutoff_V_m=500., regions=dict(off_target=dict(volume_mm3=1.)))
            for key in ('baseline_ROI_P10', 'half_baseline_ROI_mean')}),
        layer_contact_source_losses=dict(metrics=dict(dermis_power_W=3., fat_power_W=4.)))


class RankingCriterionTests(unittest.TestCase):
    def test_balanced_absolute_improvement_and_nonworse_spatial_metrics(self):
        result = M.evaluate(row(mean=10.3, p10=5.1, maximum=99.), row('baseline'))
        self.assertTrue(result['numerically_promising'])
        self.assertTrue(result['ranking_eligible_for_diagnostic'])
        self.assertTrue(all(result['checks'].values()))
        self.assertFalse(result['adopted'])
        self.assertEqual(result['high_modulation']['status'], 'available_at_exact_unit_scale')

    def test_only_one_point_or_mean_improvement_cannot_hide_ROI_P10_loss(self):
        result = M.evaluate(row(mean=12., p10=4.99, maximum=90.), row('baseline'))
        self.assertFalse(result['numerically_promising'])
        self.assertFalse(result['checks']['both_absolute_ROI_mean_P10_nonworse'])
        self.assertTrue(result['ranking_eligible_for_diagnostic'])

    def test_exact_one_percent_does_not_satisfy_strict_improvement_gate(self):
        result = M.evaluate(row(mean=10.1, p10=5.), row('baseline'))
        self.assertFalse(result['checks']['at_least_one_absolute_gain_strictly_exceeds_1percent'])
        self.assertFalse(result['numerically_promising'])

    def test_worse_selectivity_or_global_peak_blocks_numerical_promise(self):
        for values, failed in [({'superficial': 30.}, 'target_mean_over_superficial_P95_nonworse'),
                               ({'off': 30.}, 'target_mean_over_all_offtarget_P95_nonworse'),
                               ({'maximum': 101.}, 'matched_global_maximum_not_increased')]:
            with self.subTest(values=values):
                result = M.evaluate(row(mean=10.5, p10=5.2, **values), row('baseline'))
                self.assertFalse(result['numerically_promising'])
                self.assertFalse(result['checks'][failed])

    def test_nonunit_scale_does_not_relabel_raw_high_modulation_volume(self):
        result = M.evaluate(row(mean=10.5, p10=5.2, maximum=90., scale=.5), row('baseline'))
        self.assertTrue(result['numerically_promising'])
        self.assertTrue(result['ranking_eligible_for_diagnostic'])
        self.assertEqual(result['high_modulation']['status'], 'held_high_modulation_normalization_missing')
        self.assertIsNone(result['high_modulation']['matched_burden_volume'])
        self.assertFalse(result['adopted'])

    def test_missing_full_skin_or_any_excess_registered_cap_blocks_selection(self):
        missing = row()
        missing['values']['composite_full_skin'] = None
        self.assertFalse(M.evaluate(missing, row('baseline'))['ranking_eligible_for_diagnostic'])
        excessive = row(mean=11., p10=6.)
        excessive['values']['composite_full_skin']['bulk_skin_J95_mA_cm2'] = 1.01
        result = M.evaluate(excessive, row('baseline'))
        self.assertFalse(result['ranking_eligible_for_diagnostic'])
        self.assertFalse(result['checks']['all_registered_full_skin_composite_caps_satisfied'])


class CachedRankingBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.items = {}
        self.rows = {}
        self.base = self.fixture('baseline', baseline=True)
        self.first = self.fixture('first', result=row('first', mean=10.5, p10=5.2, maximum=90., scale=.5))
        self.second = self.fixture('second', result=row('second', mean=10.4, p10=5.15, maximum=91.))
        self.third = self.fixture('third', result=row('third', mean=10.1, p10=4.9, maximum=92.))

    def fixture(self, name, baseline=False, signature='coarse', result=None):
        run = self.root/name
        path = run/'postprocess'/name/'summary.json'
        path.parent.mkdir(parents=True)
        (run/'audit').mkdir()
        config = run/'config.properties'
        config.write_text('synthetic=only\n')
        (run/'preregistration.json').write_text('{}')
        path.write_text(json.dumps(dict(id=name, status='complete')))
        audit = run/'audit/skin.json'
        audit.write_text(json.dumps(dict(synthetic=True, case_id=name)))
        condition = dict(id=name+'-square_3h', waveform='square_3h', actual_fundamental_Hz=[3000, 3030],
                         phase_deg=[0., 0.], source_Vpp_per_output=1.)
        self.items[path.resolve()] = dict(path=path.resolve(), run=run, summary=dict(id=name, mesh_metadata=dict(h_xy_mm=1.25)),
            case=dict(id=name, design_id='baseline-square15' if baseline else name, config_file=str(config), config_sha256=M.view.sha(config)),
            circuit=dict(n_pads=4, n_outputs=2), conditions=[condition], signature=signature, eligibility={},
            full_skin={condition['id']: dict(audit=dict(path=str(audit), SHA256=M.view.sha(audit), summary_sha256=M.view.sha(path)))},
            audit_paths=[audit])
        value = result or row(name)
        value.update(case_id=name, condition_id=condition['id'], run_id=run.name, comparison_signature=signature)
        self.rows[name] = value
        return path.resolve()

    def loader(self, path):
        return self.items[Path(path).resolve()]

    def row_builder(self, item, condition, reference=None, reference_item=None):
        return copy.deepcopy(self.rows[item['summary']['id']])

    def build(self, paths, **kwargs):
        return M.build_ranking([self.base], paths, loader=self.loader, row_builder=self.row_builder,
                               discovery_paths=kwargs.pop('discovery_paths', []), **kwargs)

    def test_deterministic_top_two_are_diagnostics_and_preserve_baseline(self):
        report = self.build([self.third, self.second, self.first])
        self.assertEqual(report['status'], 'calculated_unadopted')
        self.assertEqual(report['selected_case_ids'], ['first', 'second'])
        self.assertEqual(report['sorted_all_cases'], ['first', 'second', 'third'])
        self.assertEqual(report['selected_for_followup'][0]['design_id'], 'first')
        self.assertTrue(report['latest_baseline_unchanged'])
        self.assertFalse(report['baseline_update_performed'])
        self.assertFalse(report['selection']['automatic_execution'])
        self.assertFalse(report['adopted'])
        self.assertEqual(report['native_array_reads'], 0)
        self.assertEqual(report['rows'][0]['absolute_all_available_layer_losses_W_at_matched_burden']['dermis_power_W'], .75)
        self.assertIn(str(self.base), report['input_sha256'])

    def test_zero_or_one_followup_and_no_promising_candidates_still_unadopted(self):
        report = self.build([self.third], select_max=1)
        self.assertEqual(report['selected_case_ids'], ['third'])
        self.assertFalse(report['rows'][0]['numerically_promising'])
        self.assertEqual(self.build([self.third], select_max=0)['selected_case_ids'], [])

    def test_matching_signature_baseline_is_required_and_can_be_discovered(self):
        fine = self.fixture('fine', signature='fine', result=row('fine', mean=10.2, p10=5.2, maximum=90.))
        held = self.build([fine])
        self.assertEqual(held['selected_case_ids'], [])
        self.assertEqual(held['rows'][0]['status'], 'held_matching_same_grid_baseline_missing')
        baseline = self.fixture('fine-baseline', baseline=True, signature='fine')
        report = self.build([fine], discovery_paths=[baseline])
        self.assertEqual(report['selected_case_ids'], ['fine'])
        self.assertEqual(report['rows'][0]['baseline_summary_path'], str(baseline))
        self.assertEqual(report['primary_baseline_summary_path'], str(self.base))

    def test_control_not_selected_and_input_limit_duplicate_and_audit_tamper_rejected(self):
        self.assertEqual(self.build([self.base])['selected_case_ids'], [])
        for paths in ([self.first, self.first], [self.first]*13):
            with self.assertRaisesRegex(ValueError, '1..12 unique'):
                self.build(paths)
        audit = Path(self.items[self.first]['audit_paths'][0])
        audit.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'audit reference changed'):
            self.build([self.first])


if __name__ == '__main__':
    unittest.main()
