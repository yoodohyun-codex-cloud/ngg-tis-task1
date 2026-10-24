from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_best1_pair_verify as verify

class DepthHarnessTests(unittest.TestCase):
    def test_every_depth_operation_is_in_xy_and_all_conditions_are_covered(self):
        mode=match=plane=None;combinations=set();depths=set()
        for actions in verify.selections():
            for key,value in actions:
                if key=='mode':mode=value
                elif key=='match':match=value
                elif key=='plane':plane=value
                elif key=='depth':
                    self.assertEqual(plane,'xy');depths.add(value)
            if any(k=='mode' for k,v in actions):combinations.add((mode,match,plane))
        self.assertEqual(len(combinations),12)
        self.assertEqual(depths,{'0','1','2','3','4'})

if __name__=='__main__':unittest.main()
