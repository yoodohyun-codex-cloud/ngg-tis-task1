"""Pure missing/stale-input rejection contracts; no model fitting or solve."""
import unittest
import experiment_inputs as i
class InputContracts(unittest.TestCase):
 def test_unpublished_material_bytes_rejected(self):
  with self.assertRaises(ValueError):i.verified_materials(b'{"rows":[]}')
 def test_wrong_geometry_source_rejected(self):
  with self.assertRaises(ValueError):i.derive_config(b'frequencies=2000,2010\n',b'wrong-mask',b'wrong-audit')
 def test_duplicate_property_rejected(self):
  with self.assertRaises(ValueError):i.properties(b'x=1\nx=2\n')
if __name__=='__main__':unittest.main()
