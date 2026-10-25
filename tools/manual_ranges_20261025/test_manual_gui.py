from pathlib import Path
import base64,hashlib,re,unittest
import manual_gui
BASE=Path('/dev/shm/task1-fixed-scales-20261025-r2/results/index.html')
class ManualMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=BASE.read_text()
    def payload(self):return dict(manual_range_proof=dict(new_PDE=0,scientific_data_unchanged=True))
    def test_original_numerical_payload_and_CSP_are_preserved(self):
        result=manual_gui.render(self.html,self.payload());pattern=r'<script\s+[^>]*type="(?:application/octet-stream|application/json)"[^>]*>.*?</script>'
        self.assertEqual(re.findall(pattern,self.html,re.S),re.findall(pattern,result,re.S))
        scripts=re.findall(r'<script>(.*?)</script>',result,re.S);self.assertEqual(len(scripts),4)
        for script in scripts:self.assertIn('sha256-'+base64.b64encode(hashlib.sha256(script.encode()).digest()).decode(),result)
    def test_manual_policy_replaces_fixed_policy(self):
        result=manual_gui.render(self.html,self.payload());self.assertIn('id="manual-range-controls"',result);self.assertNotIn('id="fixed-scale-notice"',result)
        self.assertTrue('id="manual-global-groups"' in result,'Global controls host missing');self.assertFalse('모든 파형은 같은 고정 ±전기장 상한' in result,'Stale fixed-axis prose')
    def test_tampered_or_repeated_sources_are_rejected(self):
        with self.assertRaises(ValueError):manual_gui.render(self.html.replace('function pixels(','function alteredPixels(',1),self.payload())
        with self.assertRaises(ValueError):manual_gui.render(manual_gui.render(self.html,self.payload()),self.payload())
if __name__=='__main__':unittest.main()
