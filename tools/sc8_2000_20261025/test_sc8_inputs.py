"""Pure stale-input contracts; no cell counting or research execution on import."""
import unittest
import sc8_inputs as i
class InputContracts(unittest.TestCase):
 def test_changed_material_receipt_rejected(self):
  with self.assertRaises(ValueError):i.verified_materials(b'{"rows":[]}')
 def test_wrong_SC4_source_rejected(self):
  with self.assertRaises(ValueError):i.derive_config(b'wrong',b'wrong',b'wrong')
 def test_duplicate_property_rejected(self):
  with self.assertRaises(ValueError):i.properties(b'x=1\nx=2\n')
if __name__=='__main__':unittest.main()
