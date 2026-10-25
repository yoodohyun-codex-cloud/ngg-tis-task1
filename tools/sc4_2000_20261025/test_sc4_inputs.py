"""Pure stale-input contracts. No cell-count evaluation during import."""
import unittest
import sc4_inputs as i
class InputContracts(unittest.TestCase):
 def test_changed_receipt_rejected(self):
  with self.assertRaises(ValueError):i.verified_materials(b'{"rows":[]}')
 def test_wrong_bulk_source_rejected(self):
  with self.assertRaises(ValueError):i.derive_config(b'wrong',b'wrong',b'wrong')
 def test_duplicate_property_rejected(self):
  with self.assertRaises(ValueError):i.properties(b'x=1\nx=2\n')
if __name__=='__main__':unittest.main()
