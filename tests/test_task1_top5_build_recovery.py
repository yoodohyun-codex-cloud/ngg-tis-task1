"""Display area metadata only; no actual files, native decode or workers."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_top5_build_recovery as recovery


class OutlineAreaRecoveryTest(unittest.TestCase):
    def fixture(self):
        return dict(physical_outlines=[dict(pad=0,node='out0',polygon_mm=[[0,0],[1,0],[0,1]])],pad_centres=[dict(pad=0,area_mm2=225.)],planes={'unchanged':'binarysource'}),dict(case=dict(expected_pad_areas_m2=[.000225]))

    def test_registered_area_is_added_without_mutating_polygon_or_saved_input(self):
        source,row=self.fixture();result=recovery.with_outline_areas(source,row)
        self.assertEqual(result['physical_outlines'][0]['area_mm2'],225.)
        self.assertEqual(result['physical_outlines'][0]['polygon_mm'],source['physical_outlines'][0]['polygon_mm'])
        self.assertEqual(result['planes'],source['planes']);self.assertNotIn('area_mm2',source['physical_outlines'][0])

    def test_mismatched_represented_area_fails_closed(self):
        source,row=self.fixture();source['pad_centres'][0]['area_mm2']=200.
        with self.assertRaisesRegex(ValueError,'differs'):recovery.with_outline_areas(source,row)

    def test_thousand_square_mm_family_keeps_250_square_mm_per_pad(self):
        source,row=self.fixture();source['pad_centres'][0]['area_mm2']=250.;row['case']['expected_pad_areas_m2']=[.00025]
        self.assertEqual(recovery.with_outline_areas(source,row)['physical_outlines'][0]['area_mm2'],250.)


if __name__=='__main__':unittest.main()
