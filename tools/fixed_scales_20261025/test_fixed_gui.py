"""Regression checks for the actual stacked GUI's axes and data preservation."""
from pathlib import Path
import base64,hashlib,re,unittest
import fixed_gui

BASE=Path('/dev/shm/task1-paper-figure-20261025/results/index.html')

class FixedStack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=BASE.read_text()
    def payload(self):return dict(fixed_scale_contract=dict(schema='task1-fixed-scale-contract-v1',automatic_rescaling=False,electric_field=dict(upper_V_m=5000.),current_density=dict(upper_A_m2=50.)))
    def test_scientific_payloads_preserved_and_new_scripts_authorized(self):
        result=fixed_gui.render(self.html,self.payload())
        old=re.findall(r'<script\s+[^>]*type="(?:application/octet-stream|application/json)"[^>]*>.*?</script>',self.html,re.S)
        new=re.findall(r'<script\s+[^>]*type="(?:application/octet-stream|application/json)"[^>]*>.*?</script>',result,re.S)
        self.assertEqual(old,new[1:])
        scripts=re.findall(r'<script>(.*?)</script>',result,re.S);self.assertEqual(len(scripts),4)
        for script in scripts:self.assertIn('sha256-'+base64.b64encode(hashlib.sha256(script.encode()).digest()).decode(),result)
    def test_no_dynamic_ranges_survive_in_the_changed_graphs(self):
        result=fixed_gui.render(self.html,self.payload())
        self.assertNotIn('ymax=max>0?max*1.04:1',result)
        self.assertNotIn('limit=max>0?max:1',result)
        self.assertNotIn("primary_ROI:'목표 ROI 공통 범위 · 표시 clipping'",result)
        self.assertIn("profile.axis==='z'?25.1:25",result)
        self.assertIn("el.dataset.vmin=String(-ymax)",result)
    def test_changed_source_or_repeated_migration_is_rejected(self):
        with self.assertRaises(ValueError):fixed_gui.render(self.html.replace('max*1.04','max*1.05'),self.payload())
        with self.assertRaises(ValueError):fixed_gui.render(fixed_gui.render(self.html,self.payload()),self.payload())

if __name__=='__main__':unittest.main()
