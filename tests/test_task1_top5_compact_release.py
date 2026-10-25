"""Display precision contracts only; no native/GUI execution."""
from pathlib import Path
import sys
import unittest
import base64
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_top5_compact_release as compact


class CompactPixelTest(unittest.TestCase):
    def fixture(self):
        a=np.array([0.,1e-7,3.6457357,1346.4003,np.nan],dtype='<f4');s=base64.b64encode(a.tobytes()).decode()
        return dict(catalog=dict(saved_float64_mean=4.053222312232493,gate_passed=False),display=dict(cases=[dict(planes=dict(maxTIS=dict(xy=[s],xz=s,yz=s)),contact_J_RMS=dict(values_b64=s))],color_limits={'exact':1346.400298562412},contact_color_limits={'exact':25.49124012699599})),a

    def test_only_pixels_change_scientific_Float64_and_failure_flags_unchanged(self):
        original,a=self.fixture();result,proof=compact.quantize_display(original)
        self.assertEqual(result['catalog'],original['catalog']);self.assertEqual(result['display']['color_limits'],original['display']['color_limits']);self.assertFalse(result['catalog']['gate_passed']);self.assertEqual(proof['values'],20)
        self.assertEqual(len(base64.b64decode(original['display']['cases'][0]['planes']['maxTIS']['xz'])),20)

    def test_explicit_quantization_bound_and_NaN_mask_are_preserved(self):
        original,a=self.fixture();result,proof=compact.quantize_display(original);v=np.frombuffer(base64.b64decode(result['display']['cases'][0]['planes']['maxTIS']['xz']),dtype='<f2').astype(float);use=np.isfinite(a)
        self.assertTrue(np.isnan(v[-1]));self.assertTrue(np.all(abs(v[use]-a[use])<=compact.ABSOLUTE+compact.RELATIVE*abs(a[use])));self.assertTrue(proof['all_checks_passed'])

    def test_out_of_range_display_does_not_silently_saturate(self):
        original,a=self.fixture();original['display']['cases'][0]['planes']['maxTIS']['xz']=base64.b64encode(np.array([70000.],dtype='<f4').tobytes()).decode()
        with np.errstate(over='ignore'),self.assertRaisesRegex(ValueError,'fit Float16'):compact.quantize_display(original)


if __name__=='__main__':unittest.main()
