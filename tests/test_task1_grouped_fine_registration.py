"""Fine grouped geometry/readiness/admission fixtures; never a PDE worker."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_grouped_fine_registration as fine


class GeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name).resolve()
        cls.plan = fine.geometry.generate_family(cls.root/'family', h_mm=.625)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_exact_four_fine_strip_cases_exclude_baseline_rerun(self):
        selected = fine.select_cases(self.plan, self.root/'run')
        self.assertEqual(tuple(c['id'] for c in selected), fine.CASE_IDS)
        self.assertEqual([c['n_pads'] for c in selected], [4, 8, 12, 16])
        self.assertTrue(all(c['cells'] == 351680 and c['postprocessor'] == 'grouped' and
                            c['java_class'] == 'GroupedPadBasis' for c in selected))
        self.assertTrue(all(not c['requires_original_producer_regression_before_next'] for c in selected))
        self.assertEqual(len(self.plan['cases']), 5)
        self.assertTrue(all(c['status'] == 'prepared_not_executed' for c in self.plan['cases']))
        self.assertEqual(sum(c['cells']*600 for c in selected), 844032000)
        self.assertEqual(fine.MAX_NATIVE_RHS, 32)

    def test_fractional_contact_area_and_node_budgets_remain_exact(self):
        for case in fine.select_cases(self.plan, self.root/'run'):
            nodes = case['pad_node_ids']; n = case['n_pads']; circ = case['circuit']
            self.assertEqual((nodes.count(0), nodes.count(1), nodes.count(-1)), (n//4, n//4, n//2))
            self.assertEqual(circ['n_outputs'], 2); self.assertEqual(circ['n_return_nodes'], 1)
            self.assertEqual(circ['source_resistance_ohm'], 50.)
            self.assertEqual(circ['inactive_source_at_other_frequencies'], '0 V through50 ohm')
            self.assertAlmostEqual(sum(case['expected_pad_areas_m2']), .0009, places=14)
            self.assertTrue(all(abs(a/(.0009/n)-1) < 1e-10 for a in case['expected_pad_areas_m2']))
            rows, _ = fine.geometry.mask_rows(case['pads'], .625)
            self.assertTrue(any(0 < a < (.625e-3)**2 for _, _, _, a in rows))
            self.assertEqual(len({(i, j) for _, i, j, _ in rows}), len(rows))
            self.assertGreaterEqual(case['geometry']['minimum_pad_gap_mm']+1e-10, 1.)

    def test_duplicate_missing_or_foreign_case_is_rejected(self):
        for replacement in ('duplicate', 'missing', 'foreign'):
            bad = copy.deepcopy(self.plan)
            if replacement == 'duplicate': bad['cases'][-1] = copy.deepcopy(bad['cases'][1])
            elif replacement == 'missing': bad['cases'].pop(0)
            else: bad['cases'][-1]['id'] = 'foreign'
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, 'five geometry'):
                fine.select_cases(bad, self.root/'run')

    def test_area_geometry_and_extra_outputs_cannot_be_silently_changed(self):
        for key, value in [('n_outputs', 4), ('h_xy_mm', 1.25), ('sc_cells', 4)]:
            bad = copy.deepcopy(self.plan); bad['cases'][1][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'physical geometry/circuit/fine mesh'):
                fine.select_cases(bad, self.root/'run')
        bad = copy.deepcopy(self.plan); bad['cases'][1]['pads'][0]['width_mm'] += .01
        with self.assertRaisesRegex(ValueError, 'physical geometry/circuit/fine mesh'):
            fine.select_cases(bad, self.root/'run')

    def test_rehashed_config_mutation_cannot_change_materials(self):
        case = self.plan['cases'][1]; p = Path(case['config_file']); original = p.read_bytes()
        bad = copy.deepcopy(self.plan)
        try:
            p.write_bytes(original.replace(b'sc.sigma=0.0002', b'sc.sigma=0.0003'))
            self.assertNotEqual(p.read_bytes(), original)
            bad['cases'][1]['config_sha256'] = fine.core.sha(p)
            with self.assertRaisesRegex(ValueError, 'changes tissue/contact/circuit'):
                fine.select_cases(bad, self.root/'run')
        finally: p.write_bytes(original)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = mock.patch.object(fine.core, 'REPO', self.root); self.repo.start(); self.addCleanup(self.repo.stop)
        old_names = ['execute', 'execute_locked', 'main', 'operator_signature', 'prepare', 'source_pins']
        old = ''.join('def '+n+'():\n return 1\n' for n in old_names)
        new = ''.join('def '+n+'():\n return 2\n' for n in ['effective_limits', *old_names])
        codes = {}
        for relative in fine.grouped.RECEIPT_CODE_FILES:
            p = self.root/relative; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new if relative == 'tools/task1_cloud_batch.py' else '# unchanged '+relative+'\n')
            codes[relative] = fine.core.sha(p)
        legacy = self.root/'data-native'/fine.LEGACY_RUN
        frozen = legacy/'frozen-source/tools/task1_cloud_batch.py'; frozen.parent.mkdir(parents=True); frozen.write_text(old)
        oldsha = fine.core.sha(frozen); newsha = codes['tools/task1_cloud_batch.py']; codes['tools/task1_cloud_batch.py'] = oldsha
        for key, value in [('LEGACY_CORE_SHA256', oldsha), ('REVIEWED_CORE_SHA256', newsha)]:
            patch = mock.patch.object(fine, key, value); patch.start(); self.addCleanup(patch.stop)
        fine.core.write(legacy/'frozen-source-manifest.json', dict(files={str(self.root/'tools/task1_cloud_batch.py'):dict(path=str(frozen))}))
        docs = self.root/'docs/cloud-restart-20261020'; docs.mkdir(parents=True)
        log = docs/'tests.log'; log.write_text('synthetic readiness log\n')
        self.receipt = docs/'grouped-readiness.json'
        fine.core.write(self.receipt, dict(status='passed', code_sha256=codes,
            checks={k:True for k in fine.grouped.RECEIPT_CHECKS}, test_logs=[dict(path=str(log), sha256=fine.core.sha(log))]))
        comparisons = [dict(file=f'{kind}-{f}.bin', passed=True, max_absolute_error=0., max_relative_global_error=0.)
            for kind in ('field', 'potential', 'density', 'source', 'loss') for f in (3000, 3030, 9000, 9090)]
        fine.core.write(docs/'grouped-producer-regression.json', dict(status='passed', comparisons=comparisons,
            relative_global_norm_tolerance=1e-8, absolute_tolerance=1e-14))
        for run, ident in [('cloud-baseline-20261019T185900Z', 'baseline-square15-coarse'),
                           (fine.LEGACY_RUN, 'grouped-historical-square15-xy40')]:
            base = self.root/'data-native'/run
            for part in ('cases', 'postprocess'): (base/part).mkdir(parents=True, exist_ok=True)
            config = base/'config.properties'; config.write_text('synthetic=1\n')
            mask = base/'mask.csv'; mask.write_text('pad,i,j,area_m2\n')
            summary = base/'postprocess/summary.json'; fine.core.write(summary, dict(status='complete'))
            fine.core.write(base/'preregistration.json', dict(cases=[dict(id=ident, config_file=str(config), config_sha256=fine.core.sha(config),
                mask_file=str(mask), mask_sha256=fine.core.sha(mask))]))
            fine.core.write(base/'cases'/(ident+'.json'), dict(status='complete', postprocess_path=str(summary), postprocess_sha256=fine.core.sha(summary)))

    def test_old_readiness_is_preserved_and_exact_core_exception_is_explicit(self):
        before = self.receipt.read_bytes(); result, refs = fine.validate_readiness()
        self.assertEqual(before, self.receipt.read_bytes())
        self.assertEqual(result['status'], 'passed_for_finite_fine_exploration')
        self.assertEqual(result['inherited_cached_producer_regression']['passed_comparisons'], 20)
        self.assertFalse(result['inherited_cached_producer_regression']['array_comparison_repeated'])
        self.assertFalse(result['raw_native_bytes_rehashed_in_this_readiness'])
        self.assertEqual(len(result['explicitly_reviewed_orchestration_drift']), 1)
        self.assertTrue(refs)

    def test_changed_numerical_source_or_future_core_drift_is_rejected(self):
        p = self.root/'tools/java/GroupedPadBasis.java'; old = p.read_bytes(); p.write_bytes(old+b'// drift\n')
        with self.assertRaisesRegex(ValueError, 'numerical/geometry/test code changed'): fine.validate_readiness()
        p.write_bytes(old)
        current = self.root/'tools/task1_cloud_batch.py'; current.write_text(current.read_text()+'# new drift\n')
        with self.assertRaisesRegex(ValueError, 'explicitly reviewed orchestration'): fine.validate_readiness()

    def test_failed_or_incomplete_cached_regression_blocks_fine_registration(self):
        p = self.root/'docs/cloud-restart-20261020/grouped-producer-regression.json'; obj = fine.core.read(p)
        obj['comparisons'].pop(); fine.core.write(p, obj)
        with self.assertRaisesRegex(ValueError, 'All20 cached'): fine.validate_readiness()

    def test_partial_preparation_failure_is_saved_and_time_history_preserved(self):
        (self.root/'runtime').mkdir()
        budget = dict(limit_seconds=13800, spent_seconds=100., runs=[dict(stage='prior')])
        budget_path = self.root/'runtime/task1-budget.json'; fine.core.write(budget_path, budget)
        for relative in ('tools/task1_grouped_fine_registration.py', 'tests/test_task1_grouped_fine_registration.py'):
            p = self.root/relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('# synthetic\n')
        target = self.root/'data-native/cloud-failed-fine'
        def check_output(argv, **kw):
            return 'a'*40 if argv[1] == 'rev-parse' else (self.root/argv[-1].split(':', 1)[1]).read_bytes()
        with mock.patch.object(fine, '__file__', str(self.root/'tools/task1_grouped_fine_registration.py')), \
             mock.patch.object(fine.geometry, '__file__', str(self.root/'tools/task1_grouped_geometry.py')), \
             mock.patch.object(fine.grouped, '_caller_owns_execution_lock'), \
             mock.patch.object(fine.os, 'sched_setaffinity'), \
             mock.patch.object(fine.policy, 'load_ledger', return_value=copy.deepcopy(budget)), \
             mock.patch.object(fine.policy, 'effective_limit', return_value=13800), \
             mock.patch.object(fine.policy, 'remaining_seconds', return_value=5000), \
             mock.patch.object(fine.core, 'source_pins', return_value={}), \
             mock.patch.object(fine.core, 'original_integrity', return_value=dict(status='passed')), \
             mock.patch.object(fine.subprocess, 'check_output', side_effect=check_output), \
             mock.patch.object(fine, 'validate_readiness', side_effect=ValueError('synthetic readiness blocker')):
            with self.assertRaisesRegex(ValueError, 'synthetic readiness blocker'): fine.prepare(target)
        failure = fine.core.read(target/'preparation-failure.json')
        self.assertTrue(failure['partial_evidence_preserved']); self.assertFalse(failure['automatic_retry'])
        after = fine.core.read(budget_path)
        self.assertEqual(after['runs'][0], budget['runs'][0]); self.assertGreater(after['spent_seconds'], 100.)
        self.assertEqual(after['runs'][-1]['status'], 'preparation_failed_preserved')
        with self.assertRaisesRegex(ValueError, 'New unique'): fine.prepare(target)


if __name__ == '__main__': unittest.main()
