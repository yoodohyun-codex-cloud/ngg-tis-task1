"""Grid text equivalence must not conflate a formatting change with model drift."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_rounded_single_pair as s
class SameSC2Grid(unittest.TestCase):
    def test_decimal_formats_are_identical_but_different_physical_grids_are_held(self):
        a={'h_mm':'.625','validation.sc_cells':'2','bulk.counts':'14,14,40'}
        b=dict(a,h_mm='0.625')
        self.assertTrue(s.same_sc2_grid(a,b))
        for key,value in [('h_mm','0.625000001'),('validation.sc_cells','4'),('bulk.counts','14,14,41')]:
            bad=dict(b);bad[key]=value;self.assertFalse(s.same_sc2_grid(a,bad))
