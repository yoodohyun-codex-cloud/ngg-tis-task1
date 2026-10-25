"""Contract fixtures only. These fabricated values are never solver inputs."""
import copy,json,unittest
import human_sc4_inputs as h

def fixture():
    return dict(schema='task1-human-tissue-materials-v1',status='source_verified_for_declared_scope',
        rows=[dict(layer=layer,frequency_Hz=f,sigma_S_m=1.,epsilon_r=1000.,sigma_unit='S/m',epsilon_r_unit='dimensionless',
            source_verified=True,source_id='unit-test fixture only; never a material input',source_location='fabricated contract fixture',
            assignment_type='declared_surrogate',limitation='fabricated values for parser rejection tests only')for layer in h.LAYERS for f in h.FREQUENCIES])
def raw(obj):return json.dumps(obj).encode()

class VerifiedInputContracts(unittest.TestCase):
    def test_missing_carrier_layer_rejected(self):
        obj=fixture();obj['rows'].pop()
        with self.assertRaises(ValueError):h.verified_materials(raw(obj))
    def test_unverified_source_rejected(self):
        obj=fixture();obj['rows'][0]['source_verified']=False
        with self.assertRaises(ValueError):h.verified_materials(raw(obj))
    def test_surrogate_requires_explicit_limitation(self):
        obj=fixture();obj['rows'][0].pop('limitation')
        with self.assertRaises(ValueError):h.verified_materials(raw(obj))
    def test_wrong_units_rejected(self):
        obj=fixture();obj['rows'][0]['sigma_unit']='mS/cm'
        with self.assertRaises(ValueError):h.verified_materials(raw(obj))
    def test_duplicate_pair_rejected(self):
        obj=fixture();obj['rows'][-1]=copy.deepcopy(obj['rows'][0])
        with self.assertRaises(ValueError):h.verified_materials(raw(obj))
    def test_numeric_boolean_rejected(self):
        obj=fixture();obj['rows'][0]['epsilon_r']=True
        with self.assertRaises(ValueError):h.verified_materials(raw(obj))

if __name__=='__main__':unittest.main()
