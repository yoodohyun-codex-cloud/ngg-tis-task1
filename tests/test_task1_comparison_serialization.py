"""Compact comparison JSON contract; tiny cache fixtures, no render or solve."""
import importlib.util
import json
import math
from pathlib import Path
import unittest


TESTS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'comparison_serialization_cache_fixture', TESTS / 'test_task1_plot_cache.py')
CACHE_TESTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CACHE_TESTS)
M = CACHE_TESTS.M


class ComparisonSerializationTests(unittest.TestCase):
    def test_compact_text_roundtrips_binary64_and_nested_JSON_values(self):
        floats = [math.nextafter(1., 2.), 1.7976931348623157e308,
                  2.2250738585072014e-308, 5e-324, -0.]
        value = dict(values=floats, nested=[None, False, True, {'zero': 0}],
                     text='한글 Ω 👩‍🔬', escaped='line1\nline2')
        text = M.comparison_json_text(value)
        restored = json.loads(text)
        self.assertEqual(restored, value)
        self.assertEqual([x.hex() for x in restored['values']], [x.hex() for x in floats])
        self.assertTrue(text.endswith('\n'))
        self.assertEqual(text.count('\n'), 1)
        self.assertNotIn(': ', text)
        self.assertNotIn(', ', text)

    def test_Unicode_is_preserved_without_ASCII_escaping(self):
        value = {'한글': 'Ω ≤5mm \u2028 👩‍🔬'}
        text = M.comparison_json_text(value)
        self.assertIn('한글', text)
        self.assertIn(value['한글'], text)
        self.assertNotIn('\\u', text)
        self.assertEqual(json.loads(text), value)

    def test_nonfinite_numbers_are_rejected_even_when_nested(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    M.comparison_json_text({'nested': [None, {'metric': value}]})

    def test_signed_and_legacy_cache_accept_rehashed_compact_comparison(self):
        for signed in (True, False):
            with self.subTest(signed=signed):
                fixture = CACHE_TESTS.PlotCacheTests('runTest')
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                fixture.fixture(receipt=signed)
                path = fixture.old / 'comparison.json'
                path.write_text(M.comparison_json_text(fixture.payload), encoding='utf-8')
                fixture.manifest()
                old_bytes = {p.name: p.read_bytes() for p in fixture.old.iterdir()}
                cache = fixture.cache(current=json.loads(path.read_text(encoding='utf-8')))
                target = cache.reuse(fixture.name, fixture.identity)
                self.assertIsNotNone(target)
                self.assertEqual(target.read_bytes(), fixture.source.read_bytes())
                self.assertEqual(cache.reused, 1)
                self.assertEqual(cache.generated, 0)
                self.assertEqual({p.name: p.read_bytes() for p in fixture.old.iterdir()}, old_bytes)


if __name__ == '__main__':
    unittest.main()
