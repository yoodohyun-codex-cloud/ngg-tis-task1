"""Synthetic unchanged-screen/provenance checks; never read native arrays."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_candidate_screen as screen


def row_fixture():
    regions = ('total', screen.PRIMARY, 'supplemental_wholeXY_depth15_20',
        'surface_0_5', 'primary_complement', 'supplemental_complement')
    cutoff_keys = {r+'_'+s:float(i+1) for i, r in enumerate((screen.PRIMARY, 'supplemental_wholeXY_depth15_20'))
        for s in ('mean', 'p10')}
    cutoffs = {q:dict(cutoff_keys) for q in ('maxTIS', 'fixedTIS', 'RMS')}
    caps = {k:1. for k in (*screen.CAP_DEGREES, 'source_power_W')}
    stats = dict(mean=4., p10=3., p95=8., min=1., max=10., CV=.2, std=.8,
        volume_m3=1e-6, positive_weight_cells=10,
        fixed_baseline_threshold_volume={k:dict(cutoff_V_m=v, volume_m3=2e-7, region_volume_fraction=.2)
            for k, v in cutoff_keys.items()})
    mode = dict(amplitude_scale=1., baseline_derived_numerical_limits=copy.deepcopy(caps),
        normalized_burdens=copy.deepcopy(caps), source_output_RMS_by_output_mA=[1., 1.],
        sum_source_output_RMS_mA=2., includes_source_power_cap=False, includes_1Vpp_ceiling=False,
        regions={r:{q:copy.deepcopy(stats) for q in cutoffs} for r in regions})
    return dict(fixed_same_grid_baseline_cutoffs_V_m=cutoffs,
        represented_geometry={r:dict(represented_volume_m3=1e-6) for r in regions},
        normalizations={m:copy.deepcopy(mode) for m in screen.MODES})


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def native_fixture(root):
    run = root/'data-native/synthetic'
    path = run/'postprocess/candidate/summary.json'
    config = run/'configs/candidate.properties'
    config.parent.mkdir(parents=True)
    config.write_text('sc.sigma=0.0002\nz.3000.re=0.00004\n')
    frozen = run/'frozen-source/source.py'
    frozen.parent.mkdir(parents=True); frozen.write_text('value = 1\n')
    original = str(root/'source.py')
    meta = dict(config_sha256=screen.sha(config), h_xy_mm=.625, radius_mm=25., total_depth_mm=25.1,
        sc_cells=2, bulk_layer_counts=[14, 14, 40], z_faces_mm=[0., .1, 5.1, 10.1, 25.1],
        tissue_boundaries_mm=[0., .1, 5.1, 10.1, 25.1], field_reconstruction='native', source_resistance_ohm=50)
    validation = {k:limit/100 for k, limit in screen.NATIVE_GATES.items()}
    summary = dict(status='complete', id='candidate', mesh_metadata=meta, validation=validation,
        validation_gate_status={k:dict(status='passed', value=validation[k], limit=v) for k, v in screen.NATIVE_GATES.items()})
    write(path, summary)
    record = dict(status='complete', id='candidate', postprocess_path=str(path), postprocess_sha256=screen.sha(path),
        config_sha256=screen.sha(config), validation=validation)
    write(run/'cases/candidate.json', record)
    pre = dict(source_commit='commit', gates=screen.NATIVE_GATES,
        cases=[dict(id='candidate', config_file=str(config), config_sha256=screen.sha(config))],
        source_and_input_sha256={original:screen.sha(frozen)})
    write(run/'preregistration.json', pre)
    write(run/'summary.json', dict(status='complete', registration_sha256=screen.sha(run/'preregistration.json'),
        source_commit='commit', cases=[record]))
    write(run/'frozen-source-manifest.json', dict(source_commit='commit', files={original:dict(path=str(frozen), sha256=screen.sha(frozen))}))
    refs = {str(p):screen.sha(p) for p in (path, run/'cases/candidate.json', run/'preregistration.json',
        config, run/'frozen-source-manifest.json')}
    row = dict(case_id='candidate', summary_path=str(path), source_commit='commit', configuration_sha256=screen.sha(config),
        mesh=meta, comparison_signature=screen.comparison_signature(summary, config))
    return run, row, refs


class ExistingEightGateTests(unittest.TestCase):
    def test_equality_passes_exactly_eight_unchanged_checks(self):
        base = row_fixture(); before = copy.deepcopy(base)
        checks = screen.screen_checks(base, base)
        self.assertEqual(len(checks), 8)
        self.assertTrue(all(c['passed'] for c in checks))
        self.assertEqual(base, before)
        self.assertEqual(checks[0]['arithmetic_tolerance'], 1e-12+4e-10)
        self.assertAlmostEqual(checks[3]['arithmetic_tolerance'], 1e-18+2e-17, delta=1e-32)

    def test_better_ratio_from_absolute_target_loss_cannot_pass(self):
        base, candidate = row_fixture(), row_fixture()
        regions = candidate['normalizations']['skin_contact_only']['regions']
        regions[screen.PRIMARY]['maxTIS']['mean'] = 3.
        regions[screen.PRIMARY]['maxTIS']['p10'] = 2.5
        regions['surface_0_5']['maxTIS']['p95'] = 4.
        checks = screen.screen_checks(candidate, base)
        self.assertFalse(checks[0]['passed']); self.assertFalse(checks[1]['passed'])
        self.assertTrue(checks[2]['passed'])

    def test_target_improvement_with_non_target_p95_increase_cannot_pass(self):
        base, candidate = row_fixture(), row_fixture()
        candidate['normalizations']['skin_contact_only']['regions'][screen.PRIMARY]['maxTIS']['mean'] = 4.5
        candidate['normalizations']['skin_contact_only']['regions']['primary_complement']['maxTIS']['p95'] = 8.001
        checks = screen.screen_checks(candidate, base)
        self.assertTrue(checks[0]['passed']); self.assertFalse(checks[5]['passed'])

    def test_arithmetic_tolerance_is_not_a_new_one_percent_gate(self):
        base, candidate = row_fixture(), row_fixture()
        stats = candidate['normalizations']['skin_contact_only']['regions'][screen.PRIMARY]['maxTIS']
        stats['mean'] = 4.-.5*screen.tolerance(4.)
        self.assertTrue(screen.screen_checks(candidate, base)[0]['passed'])
        stats['mean'] = 4.-2*screen.tolerance(4.)
        self.assertFalse(screen.screen_checks(candidate, base)[0]['passed'])

    def test_fixed_cutoff_changes_and_fake_high_volume_are_rejected(self):
        base, candidate = row_fixture(), row_fixture()
        screen.validate_statistics(candidate, base)
        candidate['fixed_same_grid_baseline_cutoffs_V_m']['maxTIS'][screen.PRIMARY+'_mean'] = 2.
        with self.assertRaisesRegex(ValueError, 'cutoffs differ'): screen.validate_statistics(candidate, base)
        candidate = row_fixture()
        candidate['normalizations']['skin_contact_only']['regions']['surface_0_5']['maxTIS']['fixed_baseline_threshold_volume'][screen.PRIMARY+'_mean']['cutoff_V_m'] = 2.
        with self.assertRaisesRegex(ValueError, 'cutoff/weight'): screen.validate_statistics(candidate, base)

    def test_normalized_skin_cap_violation_is_not_allowed_by_good_roi_metrics(self):
        base, candidate = row_fixture(), row_fixture()
        candidate['normalizations']['skin_contact_only']['normalized_burdens']['bulk_skin_J_vector_RMS_max_A_m2'] = 1.01
        with self.assertRaisesRegex(ValueError, 'cap violation'): screen.validate_statistics(candidate, base)

    def test_all_five_original_modes_and_positive_weights_required(self):
        base, candidate = row_fixture(), row_fixture()
        del candidate['normalizations']['equal_total_power']
        with self.assertRaisesRegex(ValueError, 'five'): screen.validate_statistics(candidate, base)
        candidate = row_fixture(); candidate['represented_geometry'][screen.PRIMARY]['represented_volume_m3'] = 0
        with self.assertRaisesRegex(ValueError, 'positive represented'): screen.validate_statistics(candidate, base)


class SourceBindingTests(unittest.TestCase):
    def test_actual_five_values_and_limits_are_preserved_without_field_reads(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            run, row, refs = native_fixture(Path(temp))
            before = copy.deepcopy(refs)
            receipt = screen.source_receipt(row, refs)
            self.assertEqual(set(receipt['native_self_gates']['values']), set(screen.NATIVE_GATES))
            self.assertTrue(receipt['native_self_gates']['passed'])
            self.assertEqual(refs, before)

    def test_fake_complete_record_with_native_gate_failure_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            run, row, refs = native_fixture(Path(temp))
            p = Path(row['summary_path']); summary = screen.read(p)
            summary['validation']['max_residual'] = 1e-3
            write(p, summary); refs[str(p)] = screen.sha(p)
            record_path = run/'cases/candidate.json'; record = screen.read(record_path)
            record['postprocess_sha256'] = screen.sha(p); record['validation']['max_residual'] = 1e-3
            write(record_path, record); refs[str(record_path)] = screen.sha(record_path)
            with self.assertRaisesRegex(ValueError, 'Native equation gate'): screen.source_receipt(row, refs)

    def test_complete_label_does_not_override_wrong_case_or_config_hash(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            run, row, refs = native_fixture(Path(temp))
            p = run/'cases/candidate.json'; record = screen.read(p); record['postprocess_sha256'] = 'forged'
            write(p, record); refs[str(p)] = screen.sha(p)
            with self.assertRaisesRegex(ValueError, 'completion/summary'): screen.source_receipt(row, refs)

    def test_fields_and_npz_are_never_read_even_for_hash_verification(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            for name in ('volume.npz', 'field-3000.bin', 'potential-3030.bin.gz', 'grid.csv'):
                path = Path(temp)/name; path.write_bytes(b'not a real numerical artifact')
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'never opens'):
                    screen.metadata_hash(path)

    def test_frozen_source_mutation_is_rejected_without_reinterpreting_results(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            run, row, refs = native_fixture(Path(temp))
            (run/'frozen-source/source.py').write_text('value = 2\n')
            with self.assertRaisesRegex(ValueError, 'Frozen implementation'): screen.source_receipt(row, refs)


class LedgerAdmissionTests(unittest.TestCase):
    def test_insufficient_budget_preserves_ledger_history_and_creates_no_attempt(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            root = Path(temp); (root/'docs').mkdir()
            args = SimpleNamespace(output=root/'docs/screen.json', report=root/'report.json', preregistration=root/'plan.json')
            ledger = dict(limit_seconds=13800, spent_seconds=13700., runs=[{'historical':'preserved'}])
            before = copy.deepcopy(ledger)
            with mock.patch.object(screen.argparse.ArgumentParser, 'parse_args', return_value=args), \
                mock.patch.object(screen.policy, 'load_ledger', return_value=ledger), \
                mock.patch.object(screen.policy, 'remaining_seconds', return_value=100), \
                self.assertRaisesRegex(ValueError, '120s'):
                screen.main()
            self.assertEqual(ledger, before)
            self.assertFalse(args.output.exists()); self.assertFalse(args.output.with_suffix('.attempt.json').exists())

    def test_attempted_output_is_not_retried_or_overwritten(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(screen, 'ROOT', Path(temp)):
            root = Path(temp); (root/'docs').mkdir()
            args = SimpleNamespace(output=root/'docs/screen.json', report=root/'report.json', preregistration=root/'plan.json')
            marker = args.output.with_suffix('.attempt.json'); marker.write_text('failure evidence')
            with mock.patch.object(screen.argparse.ArgumentParser, 'parse_args', return_value=args), \
                mock.patch.object(screen.policy, 'load_ledger') as load_ledger, \
                self.assertRaisesRegex(ValueError, 'Never overwrite'):
                screen.main()
            load_ledger.assert_not_called(); self.assertEqual(marker.read_text(), 'failure evidence')


if __name__ == '__main__': unittest.main()
