"""Source regressions; root owns actual manual-control and numeric browser tests."""
from pathlib import Path
import re,unittest
import manual_legacy as m

BASE=Path('/dev/shm/task1-fixed-scales-20261025-r2/results/index.html')

def function(script,name):
    start=script.index('function '+name+'(');stop=script.find('\nfunction ',start+1)
    if stop<0:stop=len(script)
    return script[start:stop]

class ManualLegacy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.scripts=re.findall(r'<script>(.*?)</script>',BASE.read_text(),re.S)
    def test_unreviewed_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'changed'):m.patch_original(self.scripts[1]+'\n')
        with self.assertRaisesRegex(ValueError,'changed'):m.patch_vectors(self.scripts[2]+'\n')
    def test_original_decode_and_parameter_physics_unchanged(self):
        before=self.scripts[1];after=m.patch_original(before)
        self.assertEqual(function(before,'half'),function(after,'half'))
        for anchor in ('const A=payload.analysis,S=payload.spatial,G=S.grid',
                       'scales={TIS:mode.reference_amplitude_scale,C1:match.amplitude_scale}',
                       'stats.energy_RMS_V_m*amp','F(stats.mean*amp)'):
            self.assertIn(anchor,after)
    def test_actual_vector_waveform_and_native_reference_checks_unchanged(self):
        before=self.scripts[2];after=m.patch_vectors(before)
        self.assertEqual(function(before,'instant'),function(after,'instant'))
        self.assertEqual(function(before,'validateForTest'),function(after,'validateForTest'))

if __name__=='__main__':unittest.main()
