"""Meaningful format/provenance checks; actual native/browser checks belong to parent."""
import base64
import copy
import hashlib
import re
import struct
import unittest
import field_shape_gui as ui


def payload():
    d={'shape':[2,2,3,2],'dtype':'<f4','data_base64':base64.b64encode(struct.pack('<24f',*range(24))).decode()}
    return dict(schema='fixture',reference_result_commit='b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe',
                analysis={'modes':{'skin_contact_only':{'reference_amplitude_scale':1.1,'matches':{'ROI_energy_RMS':{'required_source_Vpp':1.3}}}}},
                cases={},planes=[{'id':'XZ','kind':'XZ','u_mm':[-.3125,.3125],'v_mm':[5,15],
                                  'native_indices':[0,1,2,3],'fields':{'TIS':{'3000':d},'C1':{'3000':d}}}],proofs={},source_sha256={},holds=[])


class Format(unittest.TestCase):
    def test_preserves_original_executable_and_adds_exact_csp(self):
        base='<!doctype html><meta content="default-src \'none\'; script-src \'sha256-original\'; style-src \'unsafe-inline\'"><style></style><main><p>original</p></main><body><script>original();</script></body>'
        result=ui.render(base,payload())
        self.assertIn('<script>original();</script>',result)
        self.assertIn('sha256-'+base64.b64encode(hashlib.sha256(ui.SCRIPT.encode()).digest()).decode(),result)
        self.assertEqual(re.findall(r'<script>(.*?)</script>',result,re.S),['original();',ui.SCRIPT])
        self.assertEqual(result.count('id="field-shape"'),1)

    def test_truncated_complex_descriptor_rejected(self):
        p=payload();p['planes'][0]['fields']['TIS']['3000']=dict(p['planes'][0]['fields']['TIS']['3000'],data_base64=base64.b64encode(b'bad').decode())
        with self.assertRaisesRegex(ValueError,'byte count'):ui.validate(p)

    def test_wrong_reim_axis_rejected(self):
        p=payload();p['planes'][0]['fields']['TIS']['3000']=dict(p['planes'][0]['fields']['TIS']['3000'],shape=[2,2,2,3])
        with self.assertRaisesRegex(ValueError,'ABI'):ui.validate(p)

    def test_stale_result_and_nonpositive_matching_are_rejected(self):
        p=payload();p['reference_result_commit']='unknown'
        with self.assertRaisesRegex(ValueError,'commit'):ui.validate(p)
        p=payload();p['analysis']['modes']['skin_contact_only']['matches']['ROI_energy_RMS']['required_source_Vpp']=0
        with self.assertRaisesRegex(ValueError,'positive'):ui.validate(p)


if __name__=='__main__':unittest.main()
