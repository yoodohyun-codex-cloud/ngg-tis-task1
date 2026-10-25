"""Unrun small scalar/frame/admission fixtures; no native geometry or data."""
import copy,unittest
from fractions import Fraction as F
import e13_screen as model

class ConditionalE13FrameContracts(unittest.TestCase):
    def test_raw_frame_only_returns_JSON_and_collects_before_postprocessing(self):
        events=[]
        def raw():events.append('raw');return dict(E13={'2000':{'path':'saved-native-file'}})
        def collect():events.append('GC')
        result=model.separated_stage(raw,collect);self.assertEqual(events,['raw','GC']);self.assertIn('E13',result)
        with self.assertRaises(ValueError):model.separated_stage(lambda:dict(Q=object()),collect)
    def test_exact_centroids_keep_rational_values_without_rounding_or_adjustment(self):
        values=[(-25,-25),(25,25),(25,-25),(-25,25)]
        proof=dict(rows=[dict(pad=i,exact_centroid_mm=[dict(numerator=x,denominator=2),dict(numerator=y,denominator=2)])for i,(x,y)in enumerate(values)])
        before=copy.deepcopy(proof);result=model.exact_centres(proof)
        self.assertEqual(result[0],(F(-25,2),F(-25,2)));self.assertEqual(proof,before)
        proof['rows'][0]['exact_centroid_mm'][0]['denominator']=0
        with self.assertRaises(ValueError):model.exact_centres(proof)
    def test_failed_skipped_or_changed_source_tests_cannot_admit_new_RHS(self):
        source={'canonical/source.py':'a'*64};good=dict(status='passed',model_source_sha256=source,
            model_source_test_count=3,model_tests_run=3,tests_run=5,expected_total_tests=5,tests_failed=0,tests_errors=0,tests_skipped=0)
        self.assertTrue(model.validate_local_MFG(good,source,3)['passed'])
        for key,value in(('tests_errors',1),('tests_skipped',1),('tests_failed',False),('model_source_sha256',{}),('tests_run',True),('model_tests_run',2),('model_tests_run',None)):
            bad=dict(good);bad[key]=value
            with self.assertRaises(ValueError):model.validate_local_MFG(bad,source,3)

if __name__=='__main__':unittest.main()
