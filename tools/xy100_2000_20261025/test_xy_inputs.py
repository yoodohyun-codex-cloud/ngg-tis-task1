"""Pure stale-input and namespace rejection; no geometry count at import."""
import unittest
import xy_inputs as i
class InputContracts(unittest.TestCase):
 def test_modified_material_rejected(self):
  with self.assertRaises(ValueError):i.verified_materials(b'{"rows":[]}')
 def test_wrong_coarse_source_rejected(self):
  with self.assertRaises(ValueError):i.derive_config(b'wrong',b'wrong',b'wrong')
 def test_duplicate_config_rejected(self):
  with self.assertRaises(ValueError):i.properties(b'x=1\nx=2\n')
if __name__=='__main__':unittest.main()
