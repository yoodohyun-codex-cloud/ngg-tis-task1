import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from task1_producer_regression import compare_producer


class ProducerComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a=Path(self.tmp.name)/'a';self.b=Path(self.tmp.name)/'b'
        self.a.mkdir();self.b.mkdir()
        for frequency in (3000,3030,9000,9090):
            for kind in ('field','potential','density','source','loss'):
                raw=np.array([0.,.1,-.2,3.],dtype='<f8').tobytes()
                for folder in (self.a,self.b):
                    (folder/f'{kind}-{frequency}.bin').write_bytes(raw)

    def test_all_twenty_peak_complex_files_must_match(self):
        result=compare_producer(self.a,self.b)
        self.assertEqual(result['status'],'passed')
        self.assertEqual(len(result['comparisons']),20)
        self.assertTrue(all(r['decompressed_byte_equal'] for r in result['comparisons']))

    def test_potential_mismatch_blocks_next_geometries(self):
        np.array([0.,.1,-.2,3.1],dtype='<f8').tofile(self.b/'potential-3030.bin')
        self.assertEqual(compare_producer(self.a,self.b)['status'],'failed')

    def test_truncated_or_nonfinite_arrays_are_rejected(self):
        (self.b/'loss-9000.bin').write_bytes(b'bad')
        with self.assertRaises(ValueError):
            compare_producer(self.a,self.b)


if __name__=='__main__':
    unittest.main()
