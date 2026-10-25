"""Synthetic bounded continuation contracts; no native data or research execution."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


class RoundedDriveExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'rounded_drive_expansion_tested', ROOT / 'tools/task1_rounded_drive_expansion.py')
        cls.tool = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.tool
        spec.loader.exec_module(cls.tool)

    def record(self, gene):
        return dict(objective=[sum(abs(v) for v in gene[:4]) + abs(gene[4] - 1), 0., -1.],
                    synthetic_only=True)

    def cached(self, gene, source='source-A', metric='metric-A', index=91):
        record = self.record(gene)
        return dict(evaluation_index=index, genes=list(gene),
                    key=self.tool.gene_key(gene, source, metric),
                    objective=list(record['objective']), record=record)

    def search(self, evaluator=None, **kwargs):
        options = dict(deadline=10., clock=lambda: 0., source_identity='source-A',
                       metric_identity='metric-A')
        options.update(kwargs)
        return self.tool.bounded_pattern_search(evaluator or self.record, **options)

    def test_expanded_bounds_four_seed_contract_and_finite_limits(self):
        self.assertEqual(tuple(map(tuple, self.tool.BOUNDS)), ((-.25, .25),) * 4 + ((.8, 1.2),))
        self.assertEqual(tuple(self.tool.STEPS), (.05, .02, .01, .005))
        self.assertEqual(tuple(map(tuple, self.tool.SEEDS)), (
            (.01, -.02, .015, -.01, 1.), (0., 0., 0., 0., 1.),
            (0., .05, 0., .05, 1.), (0., -.05, 0., -.05, 1.)))
        self.assertEqual(self.tool.SEARCH_CONTRACT['maximum_new_proxy_evaluations'], 124)
        self.assertEqual(self.tool.SEARCH_CONTRACT['maximum_final_candidates'], 2)
        self.assertEqual(self.tool.SEARCH_CONTRACT['total_seconds'], 600)

    def test_strict_64MiB_output_contract_is_separate_from_disk_reserve(self):
        self.assertEqual(self.tool.OUTPUT_BOUND_BYTES, 64 * 1024 ** 2)
        self.assertEqual(self.tool.SEARCH_CONTRACT['output_bound_bytes'], self.tool.OUTPUT_BOUND_BYTES)
        self.assertEqual(self.tool.SEARCH_CONTRACT['per_condition_seconds'], 120)
        self.assertLess(self.tool.OUTPUT_BOUND_BYTES, 2 * self.tool.GIB)

    def test_no_gene_clipping_or_nonfinite_array_coercion(self):
        for gene in ((-.25, .25, -.25, .25, .8), (.25, -.25, .25, -.25, 1.2)):
            self.assertTrue(self.tool.valid_gene(gene))
        for gene in ([.25001, 0, 0, 0, 1], [0, 0, 0, 0, .79999],
                     [0, 0, 0, 0, 1.20001], [0, float('nan'), 0, 0, 1],
                     [0, 0, 0, 0, float('inf')], [0, 0, 0, 1], np.zeros(5)):
            before = copy.deepcopy(gene)
            self.assertFalse(self.tool.valid_gene(gene))
            with self.assertRaises(ValueError):
                self.tool.gene_key(gene)
            np.testing.assert_equal(gene, before)

    def test_exact_float_key_preserves_namespace_and_old_narrow_identity(self):
        gene = [.01, -.02, .015, -.01, 1.]
        near = gene.copy()
        near[0] = float(np.nextafter(near[0], math.inf))
        self.assertNotEqual(self.tool.gene_key(gene), self.tool.gene_key(near))
        self.assertEqual(self.tool.gene_key(gene), self.tool.gene_key(tuple(gene)))
        self.assertNotEqual(self.tool.gene_key(gene, 'A', 'M'), self.tool.gene_key(gene, 'B', 'M'))
        self.assertNotEqual(self.tool.gene_key(gene, 'A', 'M'), self.tool.gene_key(gene, 'A', 'N'))
        import task1_rounded_drive_optimization as frozen
        self.assertEqual(self.tool.gene_key(gene, 'A', 'M'), frozen.gene_key(gene, 'A', 'M'))

    def test_expanded_complex_coefficients_preserve_both_output_ratios(self):
        gene = [.2, -.15, -.125, .175, 1.15]
        before = gene.copy()
        coefficients = self.tool.gene_coefficients(gene)
        self.assertEqual(set(coefficients), {3000, 3030, 9000, 9090})
        np.testing.assert_allclose(coefficients[3000], [-1j, -.15 - .2j], rtol=0, atol=1e-15)
        np.testing.assert_allclose(coefficients[3030], [.175 + .125j, -1.15j], rtol=0, atol=1e-15)
        np.testing.assert_array_equal(coefficients[9000], [0j, 0j])
        np.testing.assert_array_equal(coefficients[9090], [0j, 0j])
        self.assertEqual(gene, before)

    def test_old_exact_proxy_seed_reuse_avoids_evaluator_and_preserves_record(self):
        cached = self.cached(self.tool.SEEDS[0])
        before = copy.deepcopy(cached)
        calls = []
        def evaluate(gene):
            calls.append(gene)
            return self.record(gene)
        result = self.search(evaluate, initial_cache=[cached], max_evaluations=3)
        self.assertNotIn(tuple(cached['genes']), calls)
        self.assertTrue(result['cache_hits'])
        reused = next(row for row in result['evaluations'] if row['key'] == cached['key'])
        self.assertFalse(reused['new_evaluation'])
        self.assertEqual(reused['record'], cached['record'])
        self.assertEqual(cached, before)
        self.assertEqual(result['completed_new_evaluations'], len(calls))

    def test_unique_new_cap_does_not_count_old_seed_cache_hits(self):
        cache = [self.cached(g, index=80 + index) for index, g in enumerate(self.tool.SEEDS)]
        calls = []
        def evaluate(gene):
            calls.append(gene)
            return self.record(gene)
        result = self.search(evaluate, initial_cache=cache, max_evaluations=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['completed_new_evaluations'], 2)
        self.assertEqual(result['new_evaluation_attempts'], 2)
        self.assertEqual(len(result['evaluations']), 6)
        self.assertEqual(len({row['key'] for row in result['evaluations']}), 6)
        self.assertTrue(result['stop_reason'])

    def test_search_fixed_anchor_ten_neighbors_and_once_only_update(self):
        calls = []
        def evaluate(gene):
            calls.append(gene)
            return dict(objective=[gene[0] + 1., 0., -1.])
        result = self.search(evaluate, max_evaluations=14)
        self.assertEqual(calls[:4], [tuple(map(float, seed)) for seed in self.tool.SEEDS])
        expected = []
        for dimension in range(5):
            for sign in (-1, 1):
                gene = list(self.tool.SEEDS[0])
                gene[dimension] += sign * .05
                expected.append(tuple(map(float, gene)))
        self.assertEqual(calls[4:14], expected)
        level = result['levels'][0]
        self.assertEqual(level['anchor_genes'], list(self.tool.SEEDS[0]))
        self.assertTrue(level['completed'])
        self.assertTrue(level['anchor_updated_once'])
        self.assertEqual(level['returned_neighbor_records'], 10)

    def test_duplicate_seeds_and_out_of_bounds_neighbors_never_rerun_or_clip(self):
        calls = []
        seed = (.25, 0., 0., 0., 1.)
        def evaluate(gene):
            calls.append(gene)
            return dict(objective=[0., 0., -1.])
        with patch.object(self.tool, 'SEEDS', (seed,) * 4):
            result = self.search(evaluate)
        self.assertTrue(result['aliases'])
        self.assertTrue(result['skipped'])
        self.assertEqual(len(calls), len(set(calls)))
        self.assertTrue(all(self.tool.valid_gene(gene) for gene in calls))

    def test_deadline_preserves_completed_rows_without_retry_or_partial_record(self):
        calls = []
        def evaluate(gene):
            calls.append(gene)
            if len(calls) == 3:
                raise self.tool.ProxyDeadline('synthetic proxy deadline')
            return self.record(gene)
        result = self.search(evaluate)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result['completed_new_evaluations'], 2)
        self.assertEqual(result['new_evaluation_attempts'], 3)
        self.assertEqual(len(result['evaluations']), 2)
        self.assertIn('synthetic proxy deadline', result['stop_reason'])
        self.assertFalse(result['global_optimum_claimed'])

    def test_expired_clock_can_reuse_cache_but_never_start_new_evaluation(self):
        calls = []
        cache = [self.cached(self.tool.SEEDS[0])]
        result = self.search(lambda gene: calls.append(gene), initial_cache=cache,
                             deadline=0., clock=lambda: 1.)
        self.assertFalse(calls)
        self.assertEqual(result['completed_new_evaluations'], 0)
        self.assertEqual(len(result['evaluations']), 1)
        self.assertTrue(result['stop_reason'])

    def test_cache_namespace_or_mutated_key_cannot_be_reused(self):
        good = self.cached(self.tool.SEEDS[0])
        for bad in (dict(good, key='0' * 64), self.cached(self.tool.SEEDS[0], source='different-source')):
            with self.assertRaises(ValueError):
                self.search(initial_cache=[bad], max_evaluations=1)

    def test_duplicate_or_internally_mutated_old_cache_rows_are_rejected(self):
        good = self.cached(self.tool.SEEDS[0])
        with self.assertRaises(ValueError):
            self.search(initial_cache=[good, copy.deepcopy(good)], max_evaluations=1)
        bad = copy.deepcopy(good)
        bad['objective'][0] += .01
        with self.assertRaises(ValueError):
            self.search(initial_cache=[bad], max_evaluations=1)

    def test_final_selection_is_strict_novel_improvement_and_at_most_two(self):
        genes = [list(seed) for seed in self.tool.SEEDS]
        rows = []
        for index, gene in enumerate(genes):
            rows.append(dict(evaluation_index=index, genes=gene,
                key=self.tool.gene_key(gene, 'source-A', 'metric-A'),
                objective=[1., 1., -1.], record={}, new_evaluation=False))
        for index, value in enumerate((.1, .11, .12, .13), 4):
            gene = [value, 0., 0., 0., 1.]
            rows.append(dict(evaluation_index=index, genes=gene,
                key=self.tool.gene_key(gene, 'source-A', 'metric-A'),
                objective=[.5 - index * .01, .5, -1.], record={}, new_evaluation=True))
        search = dict(evaluations=rows, seed_evaluation_indices=list(range(4)))
        aliases = [dict(genes=rows[-1]['genes'])]
        selected = self.tool.select_final_candidates(search, aliases, 'source-A', 'metric-A')
        self.assertEqual(len(selected), 2)
        self.assertNotIn(rows[-1]['key'], [row['key'] for row in selected])
        self.assertTrue(all(tuple(row['objective']) < (1., 1., -1.) for row in selected))
        self.assertEqual(selected, sorted(selected, key=lambda row: (tuple(row['objective']), row['key'])))
        equal = copy.deepcopy(search)
        for row in equal['evaluations']:
            row['objective'] = [1., 1., -1.]
        self.assertEqual(self.tool.select_final_candidates(equal, [], 'source-A', 'metric-A'), [])


if __name__ == '__main__':
    unittest.main()
