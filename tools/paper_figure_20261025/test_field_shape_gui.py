"""Pure format/CSP checks; parent owns real browser and data assertions."""
import base64
import hashlib
import json
import re
import unittest
import field_shape_gui as ui


BASE='<!doctype html><meta content="default-src \'none\'; script-src \'sha256-old\'; style-src \'unsafe-inline\'"><style></style><main>old</main><body><script id="olddata" type="application/octet-stream">unchanged packed data</script><script>window.task1FieldShape={};</script><script>secondOriginal();</script><script>thirdOriginal();</script></body>'


def payload():
    return dict(paper_reference={'DOI':'10.1016/j.cell.2017.05.024','title':'Cited paper'},
                paper_proofs={'new_PDE':0,'display_vectors_reused_unchanged':True},
                planes='Large scientific payload must not be embedded again')


class PaperGUI(unittest.TestCase):
    def test_preserves_existing_data_and_three_scripts(self):
        out=ui.render(BASE,payload())
        old=re.findall(r'<script(?:\s[^>]*)?>.*?</script>',BASE,re.S)
        new=re.findall(r'<script(?:\s[^>]*)?>.*?</script>',out,re.S)
        self.assertEqual(old,new[:-2]);self.assertEqual(len(new),len(old)+2)
        self.assertIn('sha256-'+base64.b64encode(hashlib.sha256(ui.SCRIPT.encode()).digest()).decode(),out)
        self.assertEqual(out.count('id="paper-figure"'),1)

    def test_only_small_citation_and_proof_metadata_embedded(self):
        out=ui.render(BASE,payload())
        text=re.search(r'<script id="paper-config" type="application/json">(.*?)</script>',out,re.S).group(1)
        data=json.loads(text)
        self.assertEqual(set(data),{'paper_reference','paper_proofs'})
        self.assertNotIn(payload()['planes'],out)

    def test_unsafe_DOI_and_missing_reuse_proof_rejected(self):
        p=payload();p['paper_reference']['DOI']='javascript:alert(1)'
        with self.assertRaisesRegex(ValueError,'DOI'):ui.render(BASE,p)
        p=payload();p['paper_proofs']['new_PDE']=1
        with self.assertRaisesRegex(ValueError,'reuse-only'):ui.render(BASE,p)

    def test_cannot_extend_already_extended_or_unrelated_GUI(self):
        with self.assertRaisesRegex(ValueError,'previously'):ui.render(BASE.replace('window.task1FieldShape','unrelated'),payload())
        out=ui.render(BASE,payload())
        with self.assertRaisesRegex(ValueError,'previously'):ui.render(out,payload())


if __name__=='__main__':unittest.main()
