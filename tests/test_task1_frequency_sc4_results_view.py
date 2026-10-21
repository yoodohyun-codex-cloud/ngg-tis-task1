"""SC4 display scope/escaping tests; no native arrays or research jobs."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
SPEC=importlib.util.spec_from_file_location('sc4_view_tested',ROOT/'tools/task1_frequency_sc4_results_view.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class SC4ViewTests(unittest.TestCase):
    def model(self):
        return dict(source=dict(run_id='synthetic',case_id='baseline-square15-sc4',source_commit='a'*40,
            configuration_sha256='b'*64,circuit=dict(n_pads=4,n_outputs=2)),input_proofs=[],
            summary_metadata={},old_gui_path=str(ROOT/'docs/old.html'),conditions=[],baseline={},
            cohorts=list(M.COHORTS),normalizations=list(M.base.MODES),metrics=list(M.base.METRICS),
            rois=[M.base.PRIMARY,M.base.SLAB],sc2_context={},erratum='SC2 frozen thresholds; raw </script> 한글 unchanged')

    def test_three_explicit_cohorts_and_erratum_preserve_model(self):
        model=self.model();before=copy.deepcopy(model)
        text=M.render_html(model,ROOT/'docs/new.html',ROOT/'docs/sc2.html')
        self.assertEqual(model,before)
        for cohort in M.COHORTS:self.assertIn(cohort,text)
        self.assertIn('Erratum:',text);self.assertIn('absolute cross-grid burden reference',text)
        self.assertIn('Original SC2 frequency GUI',text)

    def test_historical_SC4_own_volume_is_not_mislabeled_as_SC2_threshold_volume(self):
        text=M.render_html(self.model(),ROOT/'docs/new.html',ROOT/'docs/sc2.html')
        self.assertIn('SC4 own cutoff; separate',text)
        self.assertIn('ROI>=frozen SC2 mean m³',text)
        self.assertIn('not SC4 own cutoffs',text)
        self.assertIn("matched=cohort==='cached_SC2_square_3000_3030_caps'",text)
        self.assertIn('not a matched-normalization comparison',text)

    def test_combined_inline_script_CSP_and_hostile_JSON_are_valid(self):
        model=self.model();text=M.render_html(model,ROOT/'docs/new.html',ROOT/'docs/sc2.html')
        js=re.search(r'<script>(.*?)</script>',text,re.DOTALL).group(1)
        expected=base64.b64encode(hashlib.sha256(js.encode()).digest()).decode()
        self.assertIn('sha256-'+expected,text)
        raw=re.search(r'<script type="application/json" id="view-data">(.*?)</script>',text,re.DOTALL).group(1)
        self.assertEqual(json.loads(raw)['erratum'],model['erratum'])
        self.assertNotIn('</script>',raw)
        self.assertNotIn('fetch(',text);self.assertNotIn('<script src=',text)

    def test_non_SC4_summary_is_rejected_before_any_other_artifact(self):
        with tempfile.TemporaryDirectory()as directory:
            p=Path(directory)/'summary.json';p.write_text('{"schema":"wrong"}')
            with self.assertRaises(ValueError):M.load_model(p,Path(directory)/'absent.json',{},Path(directory)/'old.html')


if __name__=='__main__':unittest.main()
