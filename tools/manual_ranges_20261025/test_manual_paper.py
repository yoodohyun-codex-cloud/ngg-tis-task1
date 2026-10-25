"""Source-level regressions; parent owns actual browser and scientific checks."""
from pathlib import Path
import re,unittest
import manual_paper as ui

BASE=Path('/dev/shm/task1-fixed-scales-20261025-r2/results/index.html')


def block(script,name):
    start=script.index('function '+name+'(');opening=script.index('{',start);depth=0
    for stop in range(opening,len(script)):
        if script[stop]=='{':depth+=1
        elif script[stop]=='}':
            depth-=1
            if depth==0:return script[start:stop+1]
    raise ValueError('Balanced reviewed function source required')


class ManualPaperContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=re.findall(r'<script>(.*?)</script>',BASE.read_text(),re.S)[3]

    def test_physics_formulas_and_source_statistics_preserved(self):
        result=ui.patch_paper(self.source)
        for name in ('rawVector','vectorRMS','projection','amplitude','fixedAM','toneReal','envelope','metrics','roiTable','validateForTest'):
            with self.subTest(name=name):self.assertEqual(block(self.source,name),block(result,name))

    def test_manual_time_changes_actual_samples_and_has_bounded_cost(self):
        result=ui.patch_paper(self.source)
        self.assertIn('range.xMin+span*i/(n-1)',result)
        self.assertIn('n=Math.min(40001,desired)',result)
        self.assertIn('el.dataset.timeFirst=String(wave.x[0])',result)
        self.assertIn('manual_wave_windows:',result)

    def test_manual_viewports_do_not_replace_native_edges_or_hide_clipping(self):
        result=ui.patch_paper(self.source)
        self.assertIn('ue=p.u_edges_mm,ve=p.v_edges_mm',result)
        self.assertIn('color(value,range.cMax,range.cMin)',result)
        self.assertIn('viewportHidden:hidden',result)
        self.assertIn('저장된 native 격자 범위 밖',result)

    def test_old_or_repeated_sources_fail_closed(self):
        with self.assertRaises(ValueError):ui.patch_paper(self.source.replace('function color(v,max){','function color(v,maximum){'))
        with self.assertRaises(ValueError):ui.patch_paper(ui.patch_paper(self.source))


if __name__=='__main__':unittest.main()
